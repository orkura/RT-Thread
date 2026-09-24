# Renode 仿真测试使用手册

本文记录 STM32H743 BSP 的 Renode 启动、SD 卡读写、双机 FDCAN 通信和日志采集方法。

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

`showAnalyzer sysbus.usart2` 会打开独立串口窗口。不要让两个 Renode 实例同时以可写方式使用同一个 SD 卡镜像。

## 2. 文件与固件准备

以下路径相对于 `F:/Project/RT-Thread_Env/RT-Thread/BSP/STM32/STM32H743`：

| 文件 | 用途 |
| --- | --- |
| `Config/renode/STM32H743SDMMC.cs` | 本项目的 SDMMC2 功能仿真模型 |
| `Config/renode/stm32h743-sdmmc2.repl` | 继承官方 H743 平台，添加 SDMMC2，地址 `0x48022400`，IRQ 124 |
| `Build/renode/sdcard.img` | 已创建的 64 MiB FAT32 镜像；整盘文件系统，无 MBR 分区表 |
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

另一个独立问题是固件 `drv_sdmmc.c` 当前仍按初始化频率计算分频；`SDIO_MAX_FREQ=20000000` 不能据此视为已实现 20 MHz 传输。仿真读写成功也不能证明实际卡时钟正确。

### SPI + Flash 状态

当前继承的平台有 SPI4 和 QSPI 控制器模型，但未挂接外部 SPI Flash；当前 BSP 的 SPI、QSPI 和 FAL 配置尚未启用，因此本文没有可直接执行的 SPI Flash 擦写测试。

后续需按实际 Flash 型号、SPI 实例和片选引脚补充模型连接，启用 SPI 与相应 Flash 驱动，再验证芯片 ID、擦除、写入和读回。平台中的 `externalFlash: Memory.MappedMemory` 不能作为 SPI Flash 命令协议测试的替代。

## 9. 参考资料

- [Renode Monitor 和脚本语法](https://renode.readthedocs.io/en/latest/basic/monitor-syntax.html)
- [Renode 日志配置](https://renode.readthedocs.io/en/latest/basic/logger.html)
- [Renode 多机器操作](https://renode.readthedocs.io/en/latest/basic/machines.html)
