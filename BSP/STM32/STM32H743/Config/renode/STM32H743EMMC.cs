// Functional SDMMC1 + eMMC user-area model for the H743 BSP and Renode 1.17.
// Synchronous single-buffer IDMA only. No timing, CRC, PIO, DDR, tuning,
// boot/RPMB partitions, erase/trim, or snapshot-safe image rollback.
using System;
using System.IO;
using Antmicro.Renode.Core;
using Antmicro.Renode.Logging;
using Antmicro.Renode.Peripherals.Bus;

namespace Antmicro.Renode.Peripherals.SD
{
    public class STM32H743EMMC : IDoubleWordPeripheral, IKnownSize
    {
        public STM32H743EMMC(IMachine machine)
        {
            bus = machine.GetSystemBus(this);
            IRQ = new GPIO();
            Reset();
        }

        public long Size => 0x400;
        public GPIO IRQ { get; private set; }
        public uint SectorCount { get; private set; }
        public int CardBusWidth => extCsd[183] == 0 ? 1 : extCsd[183] == 1 ? 4 : 8;

        // Attach an existing raw image while the machine is paused. Images are
        // always writable and persistent. Never creates or truncates a file.
        public void LoadImage(string fileName)
        {
            var path = Path.GetFullPath(fileName);
            using(var file = new FileStream(path, FileMode.Open, FileAccess.ReadWrite, FileShare.None))
            {
                if(file.Length < 512 || file.Length % 512 != 0 || file.Length / 512 > uint.MaxValue)
                {
                    throw new ArgumentException("eMMC image must contain 1..UINT32_MAX complete 512-byte sectors.");
                }
                SectorCount = (uint)(file.Length / 512);
            }
            imagePath = path;
            Reset();
            this.InfoLog("Attached eMMC user area: {0} sectors of 512 bytes", SectorCount);
        }

        public void Reset()
        {
            Array.Clear(registers, 0, registers.Length);
            status = 0;
            ResetCard();
            IRQ.Unset();
        }

        private void ResetCard()
        {
            state = 0; // IDLE; READY=1, IDENT=2, STBY=3, TRAN=4.
            rca = 0;
            Array.Clear(extCsd, 0, extCsd.Length);
            extCsd[192] = 6; // EXT_CSD revision: MMC 4.5.
            extCsd[194] = 2; // CSD structure version.
            extCsd[196] = 3; // SDR 26/52 MHz only; no DDR/HS200/HS400.
            extCsd[199] = 1; // Partition switch time (10 ms units).
            extCsd[217] = 1; // Sleep/awake timeout; no sleep command emulated.
            extCsd[248] = 1; // Generic CMD6 time (10 ms units).
            for(var i = 0; i < 4; i++)
            {
                extCsd[212 + i] = (byte)(SectorCount >> (i * 8));
            }
            // CACHE_SIZE, BOOT_SIZE_MULT and RPMB_SIZE_MULT remain zero.
        }

        public uint ReadDoubleWord(long offset)
        {
            if(!IsRegister(offset))
            {
                this.WarningLog("Unsupported register read at 0x{0:X}", offset);
                return 0;
            }
            if(offset == 0x34)
            {
                return status | (1u << 18) | (1u << 19); // Empty FIFOs.
            }
            return offset == 0x38 ? 0 : registers[offset / 4];
        }

        public void WriteDoubleWord(long offset, uint value)
        {
            if(!IsRegister(offset))
            {
                this.WarningLog("Unsupported register write at 0x{0:X}", offset);
                return;
            }
            if((offset >= 0x10 && offset <= 0x20) || offset == 0x30 || offset == 0x34)
            {
                return;
            }
            if(offset == 0x38)
            {
                status &= ~value;
                UpdateInterrupt();
                return;
            }
            registers[offset / 4] = offset == 0x0C ? value & ~(1u << 12) : value;
            if(offset == 0x3C)
            {
                UpdateInterrupt();
            }
            if(offset == 0x0C && (value & (1u << 12)) != 0)
            {
                ExecuteCommand(value);
            }
        }

        private void ExecuteCommand(uint control)
        {
            var command = control & 0x3F;
            var argument = Get(0x08);
            var hasResponse = (control & 0x300) != 0;
            var hasData = (control & (1u << 6)) != 0;
            Set(0x10, command);
            for(var i = 0; i < 4; i++)
            {
                Set(0x14 + i * 4, 0);
            }
            this.DebugLog("CMD{0}, ARG=0x{1:X8}, state={2}", command, argument, state);
            if(imagePath == null || (Get(0x00) & 3) != 3)
            {
                Finish(hasResponse ? CommandTimeout : CommandSent);
                return;
            }

            uint error = 0;
            switch(command)
            {
            case 0:
                ResetCard();
                break;
            case 1:
                if(state > 1) { error = IllegalCommand; break; }
                if(argument != 0) { state = 1; }
                Set(0x14, 0xC0FF8000); // Ready, sector addressing, 2.7..3.6 V.
                break;
            case 2:
                if(state != 1) { error = IllegalCommand; break; }
                state = 2;
                // Synthetic CID, not an identity claim about the physical chip.
                Set(0x14, 0xFE014552);
                Set(0x18, 0x454E4F44);
                Set(0x1C, 0x45100000);
                Set(0x20, 0x00010100);
                break;
            case 3:
                if(state != 2 || (argument >> 16) == 0) { error = IllegalCommand; break; }
                rca = argument >> 16;
                state = 3;
                Set(0x14, CardStatus);
                break;
            case 5:
            case 55:
                // RT-Thread probes SDIO and SD before MMC. Do not falsely
                // advertise either. MMC sleep/awake (also CMD5) is unsupported.
                Finish(CommandTimeout);
                return;
            case 6:
                if(state != 4) { error = IllegalCommand; break; }
                var access = (argument >> 24) & 3;
                var index = (int)((argument >> 16) & 0xFF);
                var value = (byte)(argument >> 8);
                // RT-Thread passes EXT_CSD_CMD_SET_NORMAL (1), while other
                // hosts use 0 for the default command set. Accept both.
                if(access != 3 || (argument & 7) > 1
                    || !((index == 183 && value <= 2) || (index == 185 && value <= 1)))
                {
                    error = 1u << 7; // SWITCH_ERROR, unsupported EXT_CSD change.
                    break;
                }
                extCsd[index] = value;
                this.DebugLog("EXT_CSD[{0}] = {1}", index, value);
                Set(0x14, CardStatus);
                break;
            case 7:
                if(argument == 0) { state = 3; }
                else if((argument >> 16) == rca && state == 3) { state = 4; }
                else { Finish(CommandTimeout); return; }
                Set(0x14, CardStatus);
                break;
            case 8:
                if(!hasData || state != 4 || argument != 0)
                {
                    // SD SEND_IF_COND probe; not MMC SEND_EXT_CSD.
                    Finish(CommandTimeout);
                    return;
                }
                Set(0x14, CardStatus);
                break;
            case 9:
                if((argument >> 16) != rca || state != 3) { error = IllegalCommand; break; }
                SetCsd();
                break;
            case 12:
            case 13:
                if(state != 4 || (command == 13 && (argument >> 16) != rca))
                { error = IllegalCommand; break; }
                Set(0x14, CardStatus);
                break;
            case 16:
                if(state != 4 || argument != 512) { error = IllegalCommand; break; }
                Set(0x14, CardStatus);
                break;
            case 17:
            case 18:
            case 24:
            case 25:
                if(state != 4 || !hasData) { error = IllegalCommand; break; }
                Set(0x14, CardStatus);
                break;
            default:
                this.WarningLog("Unsupported eMMC CMD{0}", command);
                error = IllegalCommand;
                break;
            }

            var completion = hasResponse ? CommandResponse : CommandSent;
            if(error != 0)
            {
                Set(0x14, CardStatus | error);
                if(hasData) { completion |= DataTimeout; }
            }
            else if(hasData)
            {
                completion |= TransferData(command, argument);
            }
            Finish(completion);
        }

        private uint TransferData(uint command, uint sector)
        {
            var length = Get(0x28) & 0x1FFFFFF;
            var address = Get(0x58);
            var read = (Get(0x2C) & 2) != 0;
            var memoryRead = command == 17 || command == 18;
            var memoryWrite = command == 24 || command == 25;
            Set(0x30, length);
            if((Get(0x50) & 3) != 1 || length == 0 || length > 1024 * 1024
                || (address & 3) != 0 || (ulong)address + length > 0x100000000UL
                || ((Get(0x04) >> 14) & 3) != extCsd[183]
                || ((Get(0x2C) >> 4) & 0xF) != 9 || length % 512 != 0
                || (!memoryRead && !memoryWrite && command != 8)
                || read == memoryWrite
                || ((command == 8 || command == 17 || command == 24) && length != 512))
            {
                this.WarningLog("Invalid eMMC IDMA: CMD{0}, length={1}, card width={2}",
                    command, length, CardBusWidth);
                return DataTimeout | IDMError;
            }
            if(command != 8 && (ulong)sector + length / 512 > SectorCount)
            {
                Set(0x14, CardStatus | (1u << 31)); // ADDRESS_OUT_OF_RANGE.
                return DataTimeout;
            }

            try
            {
                if(command == 8)
                {
                    bus.WriteBytes((byte[])extCsd.Clone(), address);
                }
                else
                {
                    using(var file = new FileStream(imagePath, FileMode.Open, FileAccess.ReadWrite, FileShare.None))
                    {
                        if(file.Length != (long)SectorCount * 512)
                        {
                            throw new IOException("eMMC image size changed after attachment.");
                        }
                        file.Position = (long)sector * 512;
                        if(read)
                        {
                            var data = new byte[(int)length];
                            var received = 0;
                            while(received < data.Length)
                            {
                                var count = file.Read(data, received, data.Length - received);
                                if(count == 0) { throw new EndOfStreamException(); }
                                received += count;
                            }
                            bus.WriteBytes(data, address);
                        }
                        else
                        {
                            var data = bus.ReadBytes(address, (int)length);
                            file.Write(data, 0, data.Length);
                            file.Flush();
                        }
                    }
                }
            }
            catch(IOException e)
            {
                this.WarningLog("eMMC image I/O failed: {0}", e.Message);
                return DataTimeout;
            }
            catch(UnauthorizedAccessException e)
            {
                this.WarningLog("eMMC image access failed: {0}", e.Message);
                return DataTimeout;
            }
            Set(0x30, 0);
            this.DebugLog("IDMA {0}: CMD{1}, sector={2}, bytes={3}, width={4}",
                read ? "read" : "write", command, sector, length, CardBusWidth);
            return DataEnd | DataBlockEnd;
        }

        private void SetCsd()
        {
            // MMC CSD v1.2, SPEC_VERS=4, 25 MHz default rate, 512-byte blocks.
            // High-capacity user-area size is read from EXT_CSD.SEC_COUNT.
            var csd = new uint[4];
            SetBits(csd, 126, 2, 3);
            SetBits(csd, 122, 4, 4);
            SetBits(csd, 112, 8, 0x0E);
            SetBits(csd, 96, 8, 0x32);
            SetBits(csd, 84, 12, 0x15); // Basic, block read, block write.
            SetBits(csd, 80, 4, 9);
            SetBits(csd, 62, 12, 0xFFF);
            SetBits(csd, 47, 3, 7);
            SetBits(csd, 26, 3, 2);
            SetBits(csd, 22, 4, 9);
            for(var i = 0; i < 4; i++) { Set(0x14 + i * 4, csd[i]); }
        }

        private static void SetBits(uint[] words, int start, int count, uint value)
        {
            for(var i = 0; i < count; i++)
            {
                if((value & (1u << i)) != 0)
                { words[3 - (start + i) / 32] |= 1u << ((start + i) % 32); }
            }
        }

        private bool IsRegister(long offset) => offset >= 0 && offset <= 0x5C && (offset & 3) == 0;
        private uint Get(int offset) => registers[offset / 4];
        private void Set(int offset, uint value) => registers[offset / 4] = value;
        private uint CardStatus => (state << 9) | (state >= 3 ? 1u << 8 : 0);
        private void Finish(uint flags) { status |= flags; UpdateInterrupt(); }
        private void UpdateInterrupt() => IRQ.Set((status & Get(0x3C)) != 0);

        private readonly IBusController bus;
        private readonly uint[] registers = new uint[0x60 / 4];
        private readonly byte[] extCsd = new byte[512];
        private string imagePath;
        private uint status;
        private uint state;
        private uint rca;
        private const uint IllegalCommand = 1u << 22;
        private const uint CommandTimeout = 1u << 2;
        private const uint DataTimeout = 1u << 3;
        private const uint CommandResponse = 1u << 6;
        private const uint CommandSent = 1u << 7;
        private const uint DataEnd = 1u << 8;
        private const uint DataBlockEnd = 1u << 10;
        private const uint IDMError = 1u << 27;
    }
}
