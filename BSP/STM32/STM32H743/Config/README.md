# STM32H743 工程配置

此目录保存本机工具路径配置和 Renode 仿真配置。工具路径配置供构建、下载工具使用，Renode 配置供主机上的仿真器使用；这些文件不作为 MCU 固件源码参与编译。

## 目录结构

```text
Config/
├── README.md
├── toolchain_config.windows.example.py
├── toolchain_config.linux.example.py
├── toolchain_config.local.py
└── renode/
    ├── STM32H743SDMMC.cs
    └── stm32h743-sdmmc2.repl
```

| 文件或目录 | 用途 |
| --- | --- |
| `toolchain_config.windows.example.py` | Windows 工具路径配置模板 |
| `toolchain_config.linux.example.py` | Linux 工具路径配置模板 |
| `toolchain_config.local.py` | 从模板复制并填写的本机配置，已被 Git 忽略 |
| `renode/` | 当前 BSP 的 Renode 外设模型与平台配置 |

## 本机工具路径配置

此目录中的示例用于配置编译器和下载工具在本机上的实际位置，不需要修改系统环境变量。

先进入当前 `Config` 目录。Windows 用户执行：

```powershell
Copy-Item toolchain_config.windows.example.py toolchain_config.local.py
```

Linux 用户执行：

```bash
cp toolchain_config.linux.example.py toolchain_config.local.py
```

复制后编辑 `toolchain_config.local.py`。其中：

- `TOOLCHAIN_PATHS` 的值是编译器可执行文件所在目录。
- `DOWNLOAD_TOOL_PATHS` 的值是下载工具可执行文件的完整路径。
- 没有使用的工具保持空字符串即可。

`toolchain_config.local.py` 已被 Git 忽略，不会把个人路径提交到仓库。示例文件只展示格式，不应写入个人的真实路径。

## Renode 仿真配置

`renode/` 中的文件用于在电脑上建立 STM32H743 虚拟平台，与真实开发板使用的 HAL 和 RT-Thread 驱动配合验证固件功能。

| 文件 | 职责 |
| --- | --- |
| `renode/STM32H743SDMMC.cs` | 自定义 SDMMC 控制器模型。修正默认模型的 CMD5 无响应处理和 CMD8 回显，并实现当前驱动使用的单缓冲 IDMA 单块、多块读写及完成中断。 |
| `renode/stm32h743-sdmmc2.repl` | 继承 Renode 自带的 `platforms/cpus/stm32h743.repl`，在 `0x48022400` 创建上述 SDMMC2 模型，并连接到 NVIC 中断号 124。 |

`.cs` 定义外设行为，`.repl` 定义外设实例、地址与中断连接。真实 STM32H743 开发板由芯片硬件提供 SDMMC2，不需要加载这两个文件。

使用时在 Renode Monitor 中依次进行：

1. 用 `include` 导入 `STM32H743SDMMC.cs`。
2. 创建机器，加载 `stm32h743-sdmmc2.repl`。
3. 将 SD 卡镜像挂接到 `sysbus.sdmmc2`。
4. 加载编译生成的 ELF，打开 USART2 串口窗口并启动仿真。
5. 在串口窗口的 FinSH 中检查设备、挂载文件系统并测试读写。

SD 卡镜像位于 BSP 的 `Build/renode/sdcard.img`，固件位于 `Build/scons/rt-thread.elf`；它们不存放在本目录，也不会由 `.repl` 自动生成。`Build/` 属于本机构建和测试产物目录，已被 Git 忽略。

当前模型是功能仿真，数据传输同步完成，不模拟精确总线时序、CRC 错误、FIFO/PIO、双缓冲 IDMA、SDIO 功能卡或 eMMC。仿真结果不能替代真实开发板的电气、时序与 DMA/Cache 一致性验证。当前配置尚未接入外部 SPI Flash 测试。

完整的加载命令、固件重载、FinSH 文件读写、双机 FDCAN 测试和日志排查步骤见 [Renode 仿真测试使用手册](../Docs/Renode/Renode.md)。
