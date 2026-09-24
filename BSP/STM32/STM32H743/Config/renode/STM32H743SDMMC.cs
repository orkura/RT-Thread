// Functional SDMMC model for this BSP's RT-Thread driver and Renode 1.17.
// Load with `include @.../STM32H743SDMMC.cs` before loading the board REPL.
// Reuses Renode's SDCard storage and protocol implementation. Transfers are
// synchronous: this model does not simulate bus timing, CRC, FIFO/PIO transfers,
// double-buffer IDMA, SDIO function cards, or eMMC.
using System;
using Antmicro.Renode.Core;
using Antmicro.Renode.Core.Structure;
using Antmicro.Renode.Logging;
using Antmicro.Renode.Peripherals.Bus;
using Antmicro.Renode.Utilities;

namespace Antmicro.Renode.Peripherals.SD
{
    public class STM32H743SDMMC : NullRegistrationPointPeripheralContainer<SDCard>,
        IDoubleWordPeripheral, IKnownSize
    {
        public STM32H743SDMMC(IMachine machine) : base(machine)
        {
            bus = machine.GetSystemBus(this);
            IRQ = new GPIO();
            Reset();
        }

        public long Size => 0x400;
        public GPIO IRQ { get; private set; }

        public override void Reset()
        {
            Array.Clear(registers, 0, registers.Length);
            status = 0;
            selectedFunction = 0;
            transferCompleted = false;
            RegisteredPeripheral?.Reset();
            IRQ.Unset();
        }

        public uint ReadDoubleWord(long offset)
        {
            if(!IsRegister(offset))
            {
                this.WarningLog("Unsupported register read at 0x{0:X}", offset);
                return 0;
            }
            if(offset == (long)Registers.Status)
            {
                // Both FIFOs are empty; the synchronous IDMA engine is idle.
                return status | (1u << 18) | (1u << 19);
            }
            if(offset == (long)Registers.Clear)
            {
                return 0;
            }
            return registers[offset / 4];
        }

        public void WriteDoubleWord(long offset, uint value)
        {
            if(!IsRegister(offset))
            {
                this.WarningLog("Unsupported register write at 0x{0:X}", offset);
                return;
            }
            switch((Registers)offset)
            {
            case Registers.ResponseCommand:
            case Registers.Response1:
            case Registers.Response2:
            case Registers.Response3:
            case Registers.Response4:
            case Registers.DataCount:
            case Registers.Status:
                return;
            case Registers.Clear:
                status &= ~value;
                UpdateInterrupt();
                return;
            case Registers.Command:
                Set(Registers.Command, value & ~(1u << 12));
                if((value & (1u << 12)) != 0)
                {
                    ExecuteCommand(value);
                }
                return;
            case Registers.Mask:
                Set(Registers.Mask, value);
                UpdateInterrupt();
                return;
            default:
                registers[offset / 4] = value;
                return;
            }
        }

        private void ExecuteCommand(uint commandRegister)
        {
            var command = commandRegister & 0x3F;
            var responseWidth = (commandRegister >> 8) & 3;
            var argument = Get(Registers.Argument);
            var card = RegisteredPeripheral;
            Set(Registers.ResponseCommand, command);
            for(var index = 0; index < 4; index++)
            {
                registers[(int)Registers.Response1 / 4 + index] = 0;
            }

            this.DebugLog("CMD{0}, ARG=0x{1:X8}", command, argument);
            if(card == null || (Get(Registers.Power) & 3) != 3)
            {
                Finish(responseWidth == 0 ? CommandSent : CommandTimeout);
                return;
            }

            // SDCard.HandleCommand consumes the CMD55 prefix, including for
            // ACMD6 which it treats as a no-op. Preserve its value beforehand.
            var applicationCommand = card.TreatNextCommandAsAppCommand;
            var response = card.HandleCommand(command, argument);
            if(command == 0)
            {
                selectedFunction = 0;
                transferCompleted = false;
            }
            else if(command == 7 && argument == 0)
            {
                transferCompleted = false;
            }

            if(responseWidth != 0)
            {
                if(command == 8 && !applicationCommand)
                {
                    // R7 must echo the voltage acceptance and check pattern.
                    if((argument & 0xF00) != 0x100)
                    {
                        Finish(CommandTimeout);
                        return;
                    }
                    Set(Registers.Response1, argument & 0xFFF);
                }
                else if(response == null || response.Length == 0)
                {
                    // In particular CMD5 gets no response from an SD memory
                    // card. Report CTIMEOUT so RT-Thread proceeds to ACMD41.
                    Finish(CommandTimeout);
                    return;
                }
                else if(responseWidth == 3)
                {
                    Set(Registers.Response1, response.AsUInt32(96));
                    Set(Registers.Response2, response.AsUInt32(64));
                    Set(Registers.Response3, response.AsUInt32(32));
                    Set(Registers.Response4, response.AsUInt32(0) & 0xFFFFFFFEu);
                }
                else
                {
                    Set(Registers.Response1, response.AsUInt32(0));
                }
                if(command == 13 && !applicationCommand && transferCompleted)
                {
                    // The backend may retain PROGRAM state after WriteData.
                    // Our synchronous transfer has finished: report TRAN and
                    // READY_FOR_DATA while preserving all card error bits.
                    Set(Registers.Response1, (Get(Registers.Response1) & ~0x1E00u) | 0x900u);
                }
            }

            var completion = responseWidth == 0 ? CommandSent : CommandResponse;
            if((commandRegister & (1u << 6)) != 0)
            {
                // Publish response and RAM contents before asserting IRQ.
                completion |= TransferData(card, command, argument, applicationCommand);
            }
            Finish(completion);
        }

        private uint TransferData(SDCard card, uint command, uint argument, bool applicationCommand)
        {
            transferCompleted = false;
            var length = Get(Registers.DataLength) & 0x1FFFFFF;
            var address = Get(Registers.IDMABase0);
            var read = (Get(Registers.DataControl) & 2) != 0;
            var blockSize = 1u << (int)((Get(Registers.DataControl) >> 4) & 0xF);
            var memoryRead = !applicationCommand && (command == 17 || command == 18);
            var memoryWrite = !applicationCommand && (command == 24 || command == 25);
            var registerLength = applicationCommand && command == 51 ? 8u
                : (applicationCommand && command == 13) || (!applicationCommand && command == 6) ? 64u : 0u;
            Set(Registers.DataCount, length);

            // This BSP uses a single IDMA buffer. Reject unsupported modes
            // explicitly instead of reporting a successful transfer of zeros.
            if((Get(Registers.IDMAControl) & 3) != 1 || length == 0 || length > 1024 * 1024
                || (address & 3) != 0 || (ulong)address + length > 0x100000000UL
                || (!memoryRead && !memoryWrite && registerLength == 0)
                || (read != !memoryWrite)
                || (registerLength != 0 && length != registerLength)
                || ((memoryRead || memoryWrite) && (length % blockSize != 0
                    || ((command == 17 || command == 24) && length != blockSize))))
            {
                this.WarningLog("Unsupported IDMA transfer: CMD{0}, length={1}, control=0x{2:X}",
                    command, length, Get(Registers.IDMAControl));
                return DataTimeout | IDMError;
            }

            if(read)
            {
                byte[] data;
                if(!applicationCommand && command == 6)
                {
                    // Renode's SDCard exposes switch status separately from
                    // ReadData. Model default speed / high speed only.
                    data = card.ReadSwitchFunctionStatusRegister();
                    if(data.Length != 64)
                    {
                        return DataTimeout;
                    }
                    data = (byte[])data.Clone();
                    data[12] = 0;
                    data[13] = 3;
                    var requestedFunction = argument & 0xF;
                    if((argument & 0x80000000) != 0 && requestedFunction <= 1)
                    {
                        selectedFunction = (byte)requestedFunction;
                    }
                    data[16] = (byte)((data[16] & 0xF0) | selectedFunction);
                }
                else
                {
                    data = card.ReadData(length);
                }
                if(data.Length != length)
                {
                    return DataTimeout;
                }
                bus.WriteBytes(data, address);
            }
            else
            {
                card.WriteData(bus.ReadBytes(address, (int)length));
            }

            // End the backend data context. CMD13 also accounts for a backend
            // retaining PROGRAM state after WriteData. A later explicit CMD12
            // from the driver remains harmless.
            card.HandleCommand(12, 0);
            transferCompleted = true;
            Set(Registers.DataCount, 0);
            this.DebugLog("IDMA {0}: {1} bytes at 0x{2:X8}", read ? "read" : "write", length, address);
            return DataEnd | DataBlockEnd;
        }

        private bool IsRegister(long offset)
        {
            return offset >= 0 && offset <= (long)Registers.IDMABase1 && (offset & 3) == 0;
        }

        private uint Get(Registers offset) => registers[(int)offset / 4];
        private void Set(Registers offset, uint value) => registers[(int)offset / 4] = value;

        private void Finish(uint flags)
        {
            status |= flags;
            UpdateInterrupt();
        }

        private void UpdateInterrupt() => IRQ.Set((status & Get(Registers.Mask)) != 0);

        private readonly IBusController bus;
        private readonly uint[] registers = new uint[0x60 / 4];
        private uint status;
        private byte selectedFunction;
        private bool transferCompleted;

        private const uint CommandTimeout = 1u << 2;
        private const uint DataTimeout = 1u << 3;
        private const uint CommandResponse = 1u << 6;
        private const uint CommandSent = 1u << 7;
        private const uint DataEnd = 1u << 8;
        private const uint DataBlockEnd = 1u << 10;
        private const uint IDMError = 1u << 27;

        private enum Registers
        {
            Power = 0x00, Clock = 0x04, Argument = 0x08, Command = 0x0C,
            ResponseCommand = 0x10, Response1 = 0x14, Response2 = 0x18,
            Response3 = 0x1C, Response4 = 0x20, DataTimer = 0x24,
            DataLength = 0x28, DataControl = 0x2C, DataCount = 0x30,
            Status = 0x34, Clear = 0x38, Mask = 0x3C,
            IDMAControl = 0x50, IDMABufferSize = 0x54,
            IDMABase0 = 0x58, IDMABase1 = 0x5C
        }
    }
}
