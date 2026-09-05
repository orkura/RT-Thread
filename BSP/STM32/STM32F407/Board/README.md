# CubeMX 移植适配说明

## 1. 基本原则

CubeMX 负责生成芯片时钟、引脚、外设和 MSP 底层配置；RT-Thread 负责程序入口、系统调度、系统节拍、设备驱动和应用程序生命周期。两者不能同时管理同一个入口或同一套底层驱动，否则容易出现重复初始化、重复中断函数或重复符号。因此，本 BSP 使用 `board.c` 和 `board.h` 作为稳定适配层，CubeMX 生成的 `Core` 目录保持相对独立。

## 2. 文件职责

| 文件或目录 | 使用方式 | 作用 |
| --- | --- | --- |
| `board.c` | 手工维护并参与编译 | 保存 `SystemClock_Config()`、`Error_Handler()` 等板级适配代码 |
| `board.h` | 手工维护并参与编译 | 定义 SRAM、Flash、系统堆边界及板级接口 |
| `Core/Inc/main.h` | CubeMX 生成，直接包含 | 提供 CubeMX 引脚定义、公共声明及 HAL 头文件入口 |
| `Core/Inc/stm32f4xx_hal_conf.h` | CubeMX 生成，直接使用 | 控制启用哪些 HAL 模块 |
| `Core/Src/stm32f4xx_hal_msp.c` | CubeMX 生成并参与编译 | 配置外设时钟、GPIO 复用、DMA 和 NVIC |
| `Core/Src/main.c` | CubeMX 生成但不参与编译 | 作为时钟和外设初始化配置的参考来源 |
| `Core/Src/stm32f4xx_it.c` | 不整体参与编译 | 其中部分异常和中断入口由 RT-Thread 接管 |
| `Core/Src/system_stm32f4xx.c` | CubeMX 生成并参与编译 | 提供 `SystemInit()` 和 `SystemCoreClock` 更新 |
| `Drivers/CMSIS` | 本地管理并参与构建 | 提供 CMSIS Core 和 STM32F4 设备头文件 |
| `Drivers/STM32F4xx_HAL_Driver` | 本地管理并参与编译 | 提供 CubeMX 配套的 STM32F4 HAL 源码和头文件 |
| `GCC`、`MDK-ARM`、`EWARM` | 本地管理并按工具链选择 | 提供启动文件和链接文件 |

当前 `SConscript` 编译：

```text
board.c
Core/Src/stm32f4xx_hal_msp.c
Core/Src/system_stm32f4xx.c
GCC、MDK-ARM 或 EWARM 中对应的启动文件
Drivers/SConscript 根据 stm32f4xx_hal_conf.h 选中的 HAL 源文件
```

## 3. CubeMX 工程配置

时钟源、晶振频率、引脚和外设必须根据实际硬件配置，不能直接套用其他开发板的参数。

在 CubeMX 的代码生成设置中，建议：

- 保留用户代码区域，避免重新生成时覆盖 `USER CODE` 中的内容。
- 对需要自行管理的外设，启用“每个外设生成独立的 `.c/.h` 文件”。
- 生成代码到独立目录，再有选择地同步到本目录，避免直接覆盖 BSP 文件。

## 4. 首次导入 CubeMX 代码

将 CubeMX 生成的 `Core` 目录复制到当前 `Board` 目录。如果需要更新 HAL 或 CMSIS，则分别同步 `Drivers/CMSIS` 和 `Drivers/STM32F4xx_HAL_Driver`，不要直接覆盖整个 `Drivers` 目录。

不要使用 CubeMX 生成文件直接覆盖以下内容：

```text
board.c
board.h
SConscript
Kconfig
GCC/
MDK-ARM/
EWARM/
Drivers/SConscript
```

导入后按以下方式处理：

1. 保留 `Core/Inc/main.h` 和 `Core/Inc/stm32f4xx_hal_conf.h`。
2. 编译 `Core/Src/stm32f4xx_hal_msp.c`。
3. 从 `Core/Src/main.c` 中同步 `SystemClock_Config()` 到 `board.c`。
4. 不编译 CubeMX 生成的 `main()` 和无限循环。
5. 不整体编译 `stm32f4xx_it.c`。

## 5. 系统启动职责

CubeMX 的典型 `main()` 包含以下流程：

```c
HAL_Init();
SystemClock_Config();
MX_GPIO_Init();
MX_USART1_UART_Init();
while (1)
{
}
```

在当前 BSP 中，其职责对应如下：

| CubeMX 操作 | 当前处理方式 |
| --- | --- |
| `main()` | 由 RT-Thread 和 `Applications/main.c` 接管 |
| `HAL_Init()` | 由公共 STM32 驱动的 `rt_hw_board_init()` 调用 |
| `SystemClock_Config()` | 放在 `board.c` 中，由 `rt_hw_board_init()` 调用 |
| `MX_*_Init()` | 由 RT-Thread 驱动或自定义组件接管 |
| `while (1)` | 不使用，由 RT-Thread 调度线程 |

因此，不要直接把 CubeMX 的整个 `main.c` 加入编译。

## 6. 同步系统时钟

当 CubeMX 中的时钟树发生变化时，只需要把最新的 `SystemClock_Config()` 函数体同步到 `board.c`。

同步后重点检查：

- HSE、LSE 或 HSI 的选择是否符合实际硬件。
- `PLLM`、`PLLN`、`PLLP`、`PLLQ` 是否与 CubeMX 一致。
- AHB、APB1、APB2 分频是否一致。
- Flash 等待周期是否与系统频率匹配。
- `SystemCoreClock` 最终值是否正确。

不要在 `SystemClock_Config()` 中再次调用 `HAL_Init()`。

### 6.1 SRAM、堆与主栈边界

F407 的 128KB 常规 SRAM 位于 `0x20000000` 到 `0x20020000`。各工具链统一在 SRAM 顶部保留 8KB 主栈，即 `0x2001E000` 到 `0x20020000`；RT-Thread 系统堆从静态 RW/ZI 数据末尾开始，并在主栈起点 `0x2001E000` 结束。GCC 链接脚本还会在静态数据侵入主栈预留区时直接报告链接错误。

## 7. 外设适配

### 7.1 RT-Thread 已提供驱动的外设

UART、GPIO、RTC、SPI、I2C、ADC 等外设优先使用 RT-Thread STM32 驱动：

1. 在 `Board/Kconfig` 中启用对应 BSP 选项。
2. 在 `board.h` 或对应驱动配置文件中提供实例、引脚、DMA 和中断配置。
3. 保留 CubeMX 生成的 MSP 配置。
4. 不再调用同一外设的 `MX_*_Init()`，避免重复初始化。

### 7.2 RT-Thread 未接管的自定义外设

如果需要使用 CubeMX 生成的外设初始化文件，应将它作为独立模块加入构建，并通过 RT-Thread 初始化机制调用，而不是放回 CubeMX 的 `main()`：

```c
static int custom_device_init(void)
{
    MX_CUSTOM_Init();
    return 0;
}
INIT_DEVICE_EXPORT(custom_device_init);
```

初始化阶段必须根据外设依赖关系选择。必须在系统设备初始化之前完成的底层硬件可使用 `INIT_BOARD_EXPORT`，普通设备通常使用 `INIT_DEVICE_EXPORT`。

## 8. 中断适配

不要整体编译 CubeMX 的 `stm32f4xx_it.c`，因为以下异常入口通常由 RT-Thread或其移植层提供：

```text
HardFault_Handler
PendSV_Handler
SysTick_Handler
```

对于 RT-Thread 已有驱动的外设，中断函数通常由对应驱动提供。对于自定义外设，只迁移所需的中断函数，并在必要时通知 RT-Thread 进入和退出中断：

```c
void CUSTOM_IRQHandler(void)
{
    rt_interrupt_enter();
    HAL_CUSTOM_IRQHandler(&custom_handle);
    rt_interrupt_leave();
}
```

迁移前必须确认工程中不存在同名中断函数。

## 9. HAL、CMSIS 和启动文件由 BSP 本地管理

当前工程直接使用 `Board/Drivers` 中与 CubeMX 配套的 HAL 和 CMSIS：

- `Drivers/SConscript` 读取 `Core/Inc/stm32f4xx_hal_conf.h`。
- 只有 CubeMX 实际启用的 HAL 模块会加入编译。
- 需要额外 LL 实现的 HAL 模块会自动加入对应 LL 源文件。
- `Board/SConscript` 根据当前工具链选择本地启动文件。
- `Core/Src/system_stm32f4xx.c` 提供本地 `SystemInit()`。

不要再额外引入其他 STM32F4 HAL、CMSIS、启动文件或 `system_stm32f4xx.c`，否则会与 BSP 中的本地实现重复。

## 10. CubeMX 重新生成后的更新流程

每次重新生成代码后，建议按以下顺序更新：

1. 对比并同步 `Core/Inc/main.h`。
2. 对比并同步 `Core/Inc/stm32f4xx_hal_conf.h`。
3. 对比并同步 `Core/Src/stm32f4xx_hal_msp.c`。
4. 如果时钟树发生变化，将新的 `SystemClock_Config()` 同步到 `board.c`。
5. HAL 或 CMSIS 版本变化时，同步其子目录，但保留 `Drivers/SConscript`。
6. 如果更新启动文件，重新确认 GCC 在完成 C 运行库初始化后跳转到 `entry`。
7. 检查新增外设是否由 RT-Thread 驱动接管。
8. 只迁移确实需要的自定义外设初始化和中断函数。
9. 检查 `Board/Kconfig` 与 `board.h` 中的外设配置是否匹配。
10. 重新生成 RT-Thread 配置并完成编译验证。

不要把应用逻辑放入 CubeMX 生成目录。应用代码应放在 `Applications`，可复用组件放在 `Components`，调试功能放在 `Debug`。

## 11. 更新检查表

- [ ] `Core/Src/main.c` 未加入编译。
- [ ] `Core/Src/stm32f4xx_it.c` 未被整体加入编译。
- [ ] `SystemClock_Config()` 与最新 CubeMX 时钟树一致。
- [ ] `board.h` 的 SRAM、Flash 和堆边界与链接脚本一致。
- [ ] 同一外设没有同时执行 RT-Thread 和 CubeMX 初始化。
- [ ] 工程中没有重复的中断函数。
- [ ] HAL 和 CMSIS 只有一套源码参与编译。
- [ ] STM32F4 HAL 和 CMSIS Driver 软件包未参与编译。
- [ ] 当前工具链只选择了一个本地启动文件。
- [ ] Kconfig 选项、`board.h` 配置与实际硬件一致。
