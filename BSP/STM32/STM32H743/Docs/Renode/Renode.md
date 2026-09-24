# Renode 仿真测试使用手册

本文记录 STM32H743 BSP 的 Renode 启动、SD 卡读写、eMMC + SD 双存储、双机 FDCAN 通信和日志采集方法。

## 1. 环境与输入窗口

当前使用 Renode `1.17.0 (1.17.0+20260913gite8c7c2d28)`，安装目录为 `D:/App/Code/renode`。以下命令按当前本机路径编写，移动工程后需替换对应路径。

| 输入位置 | 提示符示例 | 用途 |
| --- | --- | --- |
| Windows PowerShell | `PS ...>` | 启动 Renode、运行工程构建命令 |
| Renode Monitor | `(monitor)`、`(STM32H743)` | 加载模型、挂接镜像、加载 ELF、控制仿真 |
| USART2 串口窗口中的 FinSH/MSH | `msh />` | 查看设备、挂载文件系统、读写文件、执行 CAN 测试 |

代码块内不包含提示符，逐行输入命令即可。不要把 Monitor 命令输入到 FinSH 中。

由用户手动启动 Renode。若希望在 PowerShell 中使用 Monitor：

```powershell
& "D:\App\Code\renode\renode.exe" --console
```

`showAnalyzer sysbus.usart2` 会打开独立串口窗口。不要让两个 Renode 实例同时以可写方式使用同一个存储镜像。eMMC 与 SD 卡也必须使用不同的镜像文件。

## 2. 文件与固件准备

以下路径相对于 `F:/Project/RT-Thread_Env/RT-Thread/BSP/STM32/STM32H743`：

| 文件 | 用途 |
| --- | --- |
| `Config/renode/STM32H743SDMMC.cs` | 本项目的 SDMMC2 功能仿真模型 |
| `Config/renode/stm32h743-sdmmc2.repl` | 继承官方 H743 平台，添加 SDMMC2，地址 `0x48022400`，IRQ 124 |
| `Build/renode/sdcard.img` | 已创建的 64 MiB FAT32 镜像；整盘文件系统，无 MBR 分区表 |
| `Config/renode/STM32H743EMMC.cs` | SDMMC1 + eMMC 用户区功能模型，直接读写独立原始镜像 |
| `Config/renode/stm32h743-emmc-sd.repl` | 用自定义 eMMC 控制器替换官方 SDMMC1，同时接入 SDMMC2 |
| `Config/renode/stm32h743-emmc-sd.resc` | 双存储加载脚本；执行后仍需手动 `start` |
| `Build/renode/emmc.img` | 本次创建的 64 MiB 空白 eMMC 镜像，首次使用需格式化 |
| `Build/scons/rt-thread.elf` | SCons 生成的待测固件 |
| `Build/renode/sdmmc-debug.log` | 按第 6 节命令生成的诊断日志 |

`Build/` 已被 Git 忽略。新检出工程或清理构建目录后，需检查镜像是否仍存在；本平台文件不会自动创建、格式化镜像。镜像必须是原始磁盘数据文件，不能用普通空文本文件代替。

当前 SD 卡测试所需配置包括：

```c
#define RT_NAME_MAX 16
#define RT_USING_DFS
#define RT_USING_DFS_V1
#define RT_USING_DFS_ELMFAT
#define RT_USING_SDIO
#define RT_USING_BLK
#define BSP_USING_SDIO
#define BSP_USING_SDIO2
#define SDIO_MAX_FREQ 20000000
```

当前 FatFs 使用 512 字节扇区、堆上长文件名缓冲区、线程安全模式；未启用 exFAT。通过配置工具同步 `.config` 与 `rtconfig.h` 后重新构建。修改 `RT_NAME_MAX` 会影响对象结构布局，需要完整重编译相关固件源码。

## 3. 单机 SD 卡仿真

当前双控制器固件建议使用第 9 节。以下旧平台只给 SDMMC2 挂接 SD 卡；若固件仍启用 SDMMC1，不能据此验证 eMMC，未挂卡的控制器可能出现探测超时。

### 3.1 首次加载

在新启动的 Renode Monitor 中依次执行：

```text
include @F:/Project/RT-Thread_Env/RT-Thread/BSP/STM32/STM32H743/Config/renode/STM32H743SDMMC.cs
mach create "STM32H743"
machine LoadPlatformDescription @F:/Project/RT-Thread_Env/RT-Thread/BSP/STM32/STM32H743/Config/renode/stm32h743-sdmmc2.repl
machine SdCardFromFile @F:/Project/RT-Thread_Env/RT-Thread/BSP/STM32/STM32H743/Build/renode/sdcard.img sysbus.sdmmc2 0x4000000 true
sysbus LoadELF @F:/Project/RT-Thread_Env/RT-Thread/BSP/STM32/STM32H743/Build/scons/rt-thread.elf
showAnalyzer sysbus.usart2
start
```

说明：

- 必须先 `include` 自定义 C# 模型，才能加载引用该类型的 `.repl`。
- `0x4000000` 表示 64 MiB，应与当前镜像容量一致。
- `true` 表示将虚拟卡写入保存到镜像；`false` 使用非持久化存储，原镜像不会保存本次修改。
- 官方 `stm32h743.repl` 默认只有 SDMMC1 实例，不能直接覆盖本固件使用的 SDMMC2。
- `start` 后观察 USART2 串口，出现 RT-Thread 横幅和 `msh />` 仅证明系统启动，不代表 SD 卡已识别。

### 3.2 重建仿真机器

若已有旧机器，需要替换平台或重新挂接镜像，先在 Monitor 执行：

```text
pause
mach clear
```

这会清除当前仿真中的机器，包含双机测试节点。然后重新执行第 3.1 节的创建与加载步骤。模型已在当前 Renode 进程中导入且内容未变时，可跳过 `include`。

修改 C# 模型后，建议退出并重新启动 Renode，再从 `include` 开始加载，避免继续使用已加载的旧类型。

### 3.3 仅更新编译后的 ELF

平台和模型未变时，不需要重建机器。先等待文件操作结束；如已挂载 SD 卡，可先在 FinSH 执行 `umount /`。随后在当前机器的 Monitor 中执行：

```text
pause
machine Reset
sysbus LoadELF @F:/Project/RT-Thread_Env/RT-Thread/BSP/STM32/STM32H743/Build/scons/rt-thread.elf
start
```

此流程复位机器并重新读取磁盘上的 ELF，保留已经建立的外设连接。复位后需要重新挂载文件系统。若串口窗口已关闭，在 `start` 前补充：

```text
showAnalyzer sysbus.usart2
```

## 4. FinSH 中的 SD 卡测试

本节命令全部在 USART2 串口窗口的 `msh />` 中执行。示例假设识别出的 SD 卡块设备名为 `sd0`；实际名称以 `list_device` 输出为准。

### 4.1 检查设备与挂载

```text
list_device
```

只有出现 SD 卡块设备后才继续。若列表只有 `fdcan2`、`uart2`、`pin`，说明识卡尚未成功，应先排查启动日志。

当前工程未配置 SD 卡自动挂载。根目录尚未挂载时执行：

```text
mount sd0 / elm
ls /
df /
```

`mount` 参数顺序是：设备名、挂载路径、文件系统类型。`elm` 是本工程 FatFs 的文件系统类型名称。已有根文件系统时，不要重复挂到 `/`；应在已有文件系统中创建目录，并将 SD 卡挂到该目录。

镜像已格式化为 FAT32，正常测试无需执行 `mkfs`。识卡或挂载失败时，先定位原因；格式化会清除镜像原有文件。

### 4.2 创建文件、写入与追加

```text
echo "Hello RT-Thread!" /test.txt
cat /test.txt
```

当前 `echo` 语法为 `echo "内容" 文件路径`：文件不存在时创建，存在时追加，不自动写入换行，也不需要 `>` 或 `>>`。

继续追加：

```text
echo " SD card write test." /test.txt
cat /test.txt
```

若 `/test.txt` 原先不存在，预期内容为：

```text
Hello RT-Thread! SD card write test.
```

重复测试会继续追加，不会覆盖已有内容。查看实际输出，不能仅凭 `echo` 没有报错判定写入成功。

### 4.3 目录与文件读取

```text
mkdir /data
echo "temperature=25" /data/log.txt
ls /data
cat /data/log.txt
```

若目录已存在，可跳过 `mkdir`。示例使用英文文件名和 ASCII 内容，便于先验证基础读写。

### 4.4 验证镜像持久化

1. 完成上述写入后，在 FinSH 执行 `umount /`，确认卸载成功。
2. 在 Monitor 执行第 3.3 节的复位和 ELF 重载命令。
3. 在 FinSH 重新挂载，并读取文件：

```text
mount sd0 / elm
cat /test.txt
cat /data/log.txt
```

还可退出 Renode，再按第 3.1 节挂接同一镜像，检查文件内容是否仍存在。这一步用于验证文件已保存到主机镜像，而不只是保留在当前仿真状态中。

## 5. 双机 FDCAN 通信

本节保留双机 `canHub` 测试方式，并使用当前自定义平台，以适配已经启用 SDMMC2 的固件。请在一个新的 Renode 会话中操作；不要与第 3 节重复创建同名机器。

两台虚拟机器各自以 `false` 挂接同一初始镜像，SD 卡修改不回写原镜像，用于避免两台机器同时修改同一个 FAT 文件系统。

### 5.1 创建第一台机器

在 Monitor 执行：

```text
include @F:/Project/RT-Thread_Env/RT-Thread/BSP/STM32/STM32H743/Config/renode/STM32H743SDMMC.cs
mach create "H743_A"
machine LoadPlatformDescription @F:/Project/RT-Thread_Env/RT-Thread/BSP/STM32/STM32H743/Config/renode/stm32h743-sdmmc2.repl
machine SdCardFromFile @F:/Project/RT-Thread_Env/RT-Thread/BSP/STM32/STM32H743/Build/renode/sdcard.img sysbus.sdmmc2 0x4000000 false
sysbus LoadELF @F:/Project/RT-Thread_Env/RT-Thread/BSP/STM32/STM32H743/Build/scons/rt-thread.elf
emulation CreateCANHub "canHub"
connector Connect sysbus.fdcan2 canHub
showAnalyzer sysbus.usart2
```

### 5.2 创建第二台机器并启动

继续在同一 Monitor 中执行：

```text
mach create "H743_B"
machine LoadPlatformDescription @F:/Project/RT-Thread_Env/RT-Thread/BSP/STM32/STM32H743/Config/renode/stm32h743-sdmmc2.repl
machine SdCardFromFile @F:/Project/RT-Thread_Env/RT-Thread/BSP/STM32/STM32H743/Build/renode/sdcard.img sysbus.sdmmc2 0x4000000 false
sysbus LoadELF @F:/Project/RT-Thread_Env/RT-Thread/BSP/STM32/STM32H743/Build/scons/rt-thread.elf
connector Connect sysbus.fdcan2 canHub
showAnalyzer sysbus.usart2
emulation SetGlobalQuantum "0.00001"
start
```

同一仿真中只创建一次 `canHub`，第二台机器直接连接已存在的 Hub。

### 5.3 FinSH 收发验证

当前固件启用了 `BSP_USING_FDCAN2_DEBUG`。在两台机器各自的串口中分别执行：

```text
fdcan2 open normal 250000
```

在 A 的串口发送：

```text
fdcan2 send 0x123 11 22 AA 55
```

在 B 的串口接收：

```text
fdcan2 recv 5000
fdcan2 status
```

检查收到的 ID 为 `0x123`、长度为 4、数据为 `11 22 AA 55`，再交换收发方向。数据参数按十六进制解释。此调试命令发送的是经典 CAN 帧，不能把结果当作 CAN FD 数据阶段验证。

测试结束可在各自串口执行 `fdcan2 close`。单机内部回环可使用 `fdcan2 loopback`，它不验证两节点之间的 Hub 连接。

### 5.4 虚拟时间同步与指定机器重载

`emulation SetGlobalQuantum "0.00001"` 设置全局虚拟时间同步周期，单位为秒，即 10 μs。它控制多机器推进和同步的粒度，不修改固件时钟配置、CAN 波特率或 RT-Thread Tick 配置。

| Quantum | 同步粒度 | 通常的性能影响 |
| --- | --- | --- |
| `0.001` | 1 ms | 同步开销较小 |
| `0.0001` | 100 μs | 同步更频繁 |
| `0.00001` | 10 μs | 本文双机测试的起点 |
| `0.000001` | 1 μs | 同步开销更大，可能更慢 |

在两台机器配置完成后、`start` 前设置一次即可。更小的 quantum 不代表真实 CAN 总线仲裁、电气行为或微秒级延迟已得到精确验证。

若按上述顺序创建两台机器，索引 0 为 A、索引 1 为 B。只重载 B 的固件时：

```text
pause
mach set 1
machine Reset
sysbus LoadELF @F:/Project/RT-Thread_Env/RT-Thread/BSP/STM32/STM32H743/Build/scons/rt-thread.elf
start
```

若会话中还有其他机器，应先执行 `mach` 查看列表，确认索引后再选择。机器复位后需重新打开其 CAN 设备。

## 6. SDMMC 日志采集

在已配置好 SDMMC2 的当前机器 Monitor 中执行：

```text
pause
logFile @F:/Project/RT-Thread_Env/RT-Thread/BSP/STM32/STM32H743/Build/renode/sdmmc-debug.log
logLevel -1 file
sysbus LogPeripheralAccess sysbus.sdmmc2 true
machine Reset
sysbus LoadELF @F:/Project/RT-Thread_Env/RT-Thread/BSP/STM32/STM32H743/Build/scons/rt-thread.elf
start
```

复现问题后执行 `pause`，再查看日志文件。日志包含模型输出以及寄存器读写，Monitor 中粘贴过的命令历史本身不能代替外设日志。

同一会话已启用文件日志时，无需反复执行 `logFile`。另一次采集可使用新的文件名保存；详细日志会增加体积和运行开销。采集结束后可执行：

```text
sysbus LogPeripheralAccess sysbus.sdmmc2 false
logLevel 1 file
```

重新创建机器后，需要对新机器再次启用寄存器访问记录。

## 7. 已遇到的问题

| 现象 | 已确认原因或排查方向 | 处理方法 |
| --- | --- | --- |
| `mmcsdhotplugmb exceeds RT_NAME_MAX=12` | 邮箱名 13 个字符，配置还需容纳结束符 | 将 `RT_NAME_MAX` 配置为 16，同步配置并完整重编译 |
| `wait cmd completed timeout` | 最初加载的官方平台没有 SDMMC2 实例 | 使用本项目 `.repl`，确认卡挂到 `sysbus.sdmmc2`，IRQ 为 124；若仍超时则采集日志 |
| `host doesn't support card's voltages`，随后 `init SDIO card failed` | 已采集日志中，原模型对不支持的 CMD5 返回空响应，却设置命令完成，导致 RT-Thread 误进入 SDIO 功能卡初始化 | 加载自定义模型，使无响应命令产生 CTIMEOUT；不能直接据此认定真实供电电压错误 |
| CMD8 参数为 `0x1AA`，响应为 `0x100` | 原卡模型没有正确回显检查字节 | 自定义模型补充 R7 回显 |
| 平台加载时找不到 `STM32H743SDMMC` | C# 类型尚未导入 | 先 `include` 模型，再加载 `.repl` |
| 修改 C# 后行为未变 | 当前进程可能仍使用已加载的旧类型 | 重启 Renode，再加载模型和平台 |
| `list_device` 中没有 SD 块设备 | 卡初始化尚未完成或已经失败 | 检查启动及外设日志，暂不执行挂载或格式化 |
| `mount` 失败 | 设备名、挂载点、镜像文件系统或底层读写异常 | 核对设备列表及日志；当前配置未启用 exFAT |
| `echo` 后内容重复 | 当前命令以追加模式打开文件 | 使用新文件名测试，或在确认无需保留内容后删除旧测试文件 |

原模型中 IDMA 寄存器只有字段占位，而当前 RT-Thread 驱动通过 IDMA 传输。自定义模型补充了该驱动使用的单缓冲传输路径，不能只修复 CMD5 就认为数据读写已得到验证。

## 8. 当前能力与验证记录

自定义 SDMMC2 模型实现命令响应、单缓冲 IDMA 的单块/多块读写和完成中断；数据传输同步完成。它不模拟精确总线时序、CRC 错误、FIFO/PIO、双缓冲 IDMA、SDIO 功能卡或 eMMC。

截至本次文档整理，已有证据如下：

- Renode 中固件已输出 RT-Thread 启动信息并进入 FinSH。
- 原模型的 CMD5 空响应却报告完成、CMD8 回显异常已由运行日志确认。
- 自定义模型通过本机 Renode 1.17 程序集接口的编译检查。
- 使用模拟卡与内存对象的寄存器级测试已覆盖 CMD5、CMD8、长响应、中断、SCR、速度切换以及单块/多块 IDMA。
- 64 MiB 镜像已检查引导扇区、备份、FSInfo、两份 FAT 表和根目录结构。

上述检查不等于完整 Renode 中的文件系统测试通过。自定义模型的实际识卡、挂载、文件读写、重启后持久化及双机 FDCAN 收发，需要执行本文步骤并保存结果。真实开发板的电气、时序、DMA/Cache 一致性仍需上板验证。

当前固件使用 `Board/drv_sdmmc_h743.c`，已按请求频率计算分频，并为 SDMMC1/2 分别分配 4 KiB 缓冲区及执行对应范围的 Cache 维护。Renode 功能模型不按分频值推进数据传输，读写成功不能证明实际卡时钟、DMA/Cache 一致性或双控制器并发正确；这些仍需实机验证。

### SPI + Flash 状态

当前继承的平台有 SPI4 和 QSPI 控制器模型，但未挂接外部 SPI Flash；当前 BSP 的 SPI、QSPI 和 FAL 配置尚未启用，因此本文没有可直接执行的 SPI Flash 擦写测试。

后续需按实际 Flash 型号、SPI 实例和片选引脚补充模型连接，启用 SPI 与相应 Flash 驱动，再验证芯片 ID、擦除、写入和读回。平台中的 `externalFlash: Memory.MappedMemory` 不能作为 SPI Flash 命令协议测试的替代。

## 9. eMMC + SD 双存储仿真

### 9.1 模型与固件要求

| 控制器 | 模型 | 地址 / IRQ | 镜像 |
| --- | --- | --- | --- |
| SDMMC1 | `STM32H743EMMC` | `0x52007000` / 49 | `Build/renode/emmc.img` |
| SDMMC2 | `STM32H743SDMMC` | `0x48022400` / 124 | `Build/renode/sdcard.img` |

新 `.repl` 将官方继承的 `sdmmc` 取消总线注册并断开 IRQ，再以 `sdmmc1` 名称注册新模型，避免地址和中断冲突。它不修改 Renode 安装目录中的平台，也不影响旧的 SD 单卡配置。

在第 2 节配置基础上，双存储固件还需启用：

```c
#define BSP_USING_SDIO1
#define BSP_SDIO1_USING_8_BIT
```

同时保留 `BSP_USING_SDIO2`。当前工程配置已启用这三项。板级驱动负责 SDMMC1 的 eMMC MSP 初始化、8 位总线能力和时钟切换。

eMMC 模型实现 CMD0/1/2/3/6/7/8/9/12/13/16/17/18/24/25 所需的用户区流程：OCR、CID/CSD、512 字节 EXT_CSD、1/4/8 位 SDR 切换、单缓冲 IDMA 和完成中断。SDIO/SD 探测命令返回超时，使协议栈继续探测 MMC；不支持的命令或配置显式返回错误。

模型通过 EXT_CSD 的 `SEC_COUNT` 报告镜像实际容量。本例为 64 MiB，不模拟物理芯片的完整 8 GB 容量。CMD6 只支持 `BUS_WIDTH` 和 `HS_TIMING` 的 SDR 切换；未实现擦除/trim、启动分区、RPMB、卡内 Cache、DDR、HS200/HS400、调谐及精确时序。外部镜像会被直接修改，不能用 Renode 快照恢复镜像历史内容。

### 9.2 镜像准备

本次已创建独立的 `Build/renode/emmc.img`，容量 64 MiB，内容全零，尚无文件系统。原有 `sdcard.img` 不变。首次运行可直接进入第 9.3 节。

重新检出工程或清理 `Build` 后，在 PowerShell 中创建空白 eMMC 镜像：

```powershell
$emmcImage = "F:/Project/RT-Thread_Env/RT-Thread/BSP/STM32/STM32H743/Build/renode/emmc.img"
[System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($emmcImage)) | Out-Null
$emmcFile = [System.IO.File]::Open($emmcImage, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
try { $emmcFile.SetLength(64MB) } finally { $emmcFile.Dispose() }
```

`CreateNew` 在文件已存在时会拒绝执行，避免覆盖已保存的数据。eMMC 的 `LoadImage` 也不会创建或格式化文件，只接受已有、长度为 512 字节整数倍的可写原始镜像。还需准备独立的 64 MiB `sdcard.img` 和构建好的 ELF；脚本不会自动生成这两个输入。

### 9.3 加载双存储平台

由用户启动一个新的 Renode 进程，在 Monitor 中执行：

```text
include @F:/Project/RT-Thread_Env/RT-Thread/BSP/STM32/STM32H743/Config/renode/stm32h743-emmc-sd.resc
start
```

脚本会导入两个 C# 模型、创建 `STM32H743_EMMC_SD`、加载平台、挂接两份镜像、加载 ELF 并打开 USART2 串口窗口。脚本本身不启动运行，也不清除会话中已有机器。不要在同一会话反复导入；模型变化时重启 Renode。

若脚本提示找不到文件或类型，先解决加载错误再 `start`。成功启动后，串口应先后出现 eMMC 容量信息和 SD 卡识别信息，随后用 `list_device` 确认两个块设备均已注册。仅出现 RT-Thread 横幅不算双存储测试通过。

### 9.4 首次格式化与分别读写

板级驱动按控制器固定主机名，设备名称不依赖识别先后顺序：

| 存储 | 主机 / 整盘设备名 | 本例挂载设备 |
| --- | --- | --- |
| SDMMC1 eMMC | `emmc` | `emmc0` |
| SDMMC2 SD 卡 | `sd` | `sd0` |

本例镜像没有分区表，块设备层会为整盘创建编号 0 的分区设备。若换用有分区表的镜像，应根据实际分区选择设备。结合启动日志和 `list_device` 确认 `emmc0`、`sd0` 均已注册，再继续挂载测试。

旧驱动两个主机都沿用默认名 `sd`，会重复注册 `sd` 和 `sd0`，出现 `Put partition.(null)[0] ... error = ERROR`。其中 `(null)` 表示未指定分区表类型；该次错误来自设备重名，不能通过格式化解决。修复命名后须重新编译并复位加载 ELF，原有镜像可继续使用。

在 FinSH 中执行：

```text
list_device
```

只有在确认 `emmc0` 对应本次新建的空白 eMMC 镜像时，首次执行以下格式化命令。格式化会清除该设备原有文件；之后的重启测试无需再次执行。`sd0` 是原有 SD 卡，不需要重新格式化。

```text
mkfs -t elm emmc0
```

将 eMMC 挂到根目录，并把原有 SD 卡挂到其下的目录：

```text
mount emmc0 / elm
mkdir /sdcard
mount sd0 /sdcard elm

echo "eMMC storage test." /emmc_test.txt
echo "SD storage test." /sdcard/sd_test.txt
cat /emmc_test.txt
cat /sdcard/sd_test.txt
df /
df /sdcard
```

若 `/sdcard` 已存在，跳过 `mkdir`。`echo` 为追加写，重复执行会重复追加。上述两条路径应读出各自内容，不能只检查命令没有报错。本例无需 ROMFS/RAMFS 根文件系统，`/` 属于 eMMC，`/sdcard` 属于 SD 卡。

这组顺序读写用于基本功能验证，不等于两个线程同时读写通过。板级驱动的独立缓冲区并发验证还需要专门的双线程压力测试及实机测试。

### 9.5 复位和持久化检查

先在 FinSH 按子挂载点到根目录的顺序卸载：

```text
umount /sdcard
umount /
```

确认卸载成功后，在 Monitor 中执行：

```text
pause
machine Reset
sysbus LoadELF @F:/Project/RT-Thread_Env/RT-Thread/BSP/STM32/STM32H743/Build/scons/rt-thread.elf
start
```

复位后在 FinSH 重新挂载两张卡并 `cat` 两个测试文件，无需再次 `mkfs`。再退出并重新启动 Renode，加载同一脚本、重新挂载、读取文件，验证数据已写入两份主机镜像。eMMC 始终持久化写入；SD 卡脚本参数 `true` 同样启用持久化。

### 9.6 日志与验证范围

第 6 节的日志方法可以沿用，双存储平台额外启用 SDMMC1 记录：

```text
pause
logFile @F:/Project/RT-Thread_Env/RT-Thread/BSP/STM32/STM32H743/Build/renode/emmc-sd-debug.log
logLevel -1 file
sysbus LogPeripheralAccess sysbus.sdmmc1 true
sysbus LogPeripheralAccess sysbus.sdmmc2 true
machine Reset
sysbus LoadELF @F:/Project/RT-Thread_Env/RT-Thread/BSP/STM32/STM32H743/Build/scons/rt-thread.elf
start
```

重点查看 eMMC 的 CMD1、CMD8 数据传输、`EXT_CSD[183] = 2`（8 位）、`EXT_CSD[185] = 1`（SDR 高速）及 IDMA 日志中的 `width=8`。无数据阶段的 SD CMD8 探测和 CMD55 超时属于预期；真正的 MMC 初始化及块读写不应持续失败。

本次已完成本机 Renode 1.17 程序集编译检查，以及 129 项使用模拟内存总线的寄存器/协议断言，覆盖识卡、CSD/EXT_CSD、8 位切换、IRQ、单块/多块读写、独立镜像、越界/非法模式拒绝、复位及重新挂接后的数据保留。测试文件保存在被 Git 忽略的 `Build/emmc-validation/` 中。

用户提供的 Renode 运行日志已确认双存储平台可加载，固件进入 FinSH，eMMC 和 SD 卡均报告 65536 KB 容量。修复 CMD6 参数处理并将 `RT_MMCSD_STACK_SIZE` 增至 4096 后，该次日志中未再出现总线宽度切换失败或检测线程栈溢出；完整日志及线程栈水位仍需后续检查。

随后暴露的 `sd` / `sd0` 重名问题已在板级主机命名处修正。新固件中的双设备注册、格式化、挂载、文件读写及重启后持久化仍需按上述步骤实际验证。上述模型检查和仿真结果不能代替真实开发板验证。

## 10. 参考资料

- [Renode Monitor 和脚本语法](https://renode.readthedocs.io/en/latest/basic/monitor-syntax.html)
- [Renode 日志配置](https://renode.readthedocs.io/en/latest/basic/logger.html)
- [Renode 多机器操作](https://renode.readthedocs.io/en/latest/basic/machines.html)

- [Renode 平台继承、取消注册与中断连接语法](https://renode.readthedocs.io/en/latest/advanced/platform_description_format.html)
