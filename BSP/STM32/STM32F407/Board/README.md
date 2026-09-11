# STM32F407 板级适配说明

## 1. 设计边界

本目录只保留启动 STM32F407 和运行 RT-Thread 所需的板级实现。CMSIS
负责复位后的芯片初始化，STM32 HAL 负责底层外设访问，RT-Thread 负责程序
入口、系统调度、系统节拍、设备模型和应用生命周期。

CubeMX 只作为时钟树、引脚和外设配置工具使用。生成结果应先放在仓库外的
临时目录中，再按职责同步到 BSP；不要把 CubeMX 的完整裸机工程直接复制到
`Board/Core`。

## 2. 文件职责

| 文件或目录 | 作用 | 维护方式 |
| --- | --- | --- |
| `board.c` | 实现 `SystemClock_Config()`、`Error_Handler()` | 手工维护，时钟树变化时从 CubeMX 对比同步 |
| `board.h` | 引入 HAL、声明板级接口，定义 SRAM、Flash 和堆边界 | 手工维护 |
| `Core/Inc/stm32f4xx_hal_conf.h` | 选择 HAL 模块并提供振荡器等 HAL 配置 | 根据 CubeMX/HAL 版本同步 |
| `Core/Src/stm32f4xx_hal_msp.c` | 配置 UART1 时钟、GPIO 复用和 NVIC | 保留 CubeMX 生成风格和 `USER CODE` 标记，仅使用 `board.h` 替代 `main.h` |
| `Core/Src/system_stm32f4xx.c` | 提供 `SystemInit()`、`SystemCoreClock` | 与当前 CMSIS Device 版本保持一致 |
| `Drivers/CMSIS` | CMSIS Core 和 STM32F4 Device 支持 | 与芯片支持包成套更新 |
| `Drivers/STM32F4xx_HAL_Driver` | STM32F4 HAL 实现 | 与 `stm32f4xx_hal_conf.h` 版本匹配 |
| `Startup` | GCC、Keil 和 IAR 启动文件 | 每次构建只选择当前工具链对应文件 |
| `LinkerScripts` | 各工具链的 Flash/SRAM 布局 | 与 `board.h` 的内存边界保持一致 |

`Core` 的预期结构为：

```text
Core/
├── Inc/
│   └── stm32f4xx_hal_conf.h
└── Src/
    ├── stm32f4xx_hal_msp.c
    └── system_stm32f4xx.c
```

## 3. 不保留的 CubeMX 文件

以下文件属于 CubeMX 裸机工程框架，不应重新加入本 BSP：

| 文件 | 不保留的原因 |
| --- | --- |
| `Core/Src/main.c` | `main()`、时钟配置和外设初始化与 RT-Thread 启动流程重复 |
| `Core/Src/stm32f4xx_it.c` | `PendSV`、`SysTick`、HardFault 和驱动中断由 RT-Thread 接管 |
| `Core/Inc/stm32f4xx_it.h` | 只服务于不再保留的 CubeMX 中断实现 |
| `Core/Src/syscalls.c` | 裸机 C 库系统调用模板与 RT-Thread 控制台、设备和 libc 适配冲突 |
| `Core/Src/sysmem.c` | 裸机 `_sbrk()` 堆实现与 RT-Thread 系统堆职责重复 |
| `Core/Inc/main.h` | 原文件只包装 HAL 头文件和 `Error_Handler()`；职责已并入 `board.h` |

如果 CubeMX 为新增引脚在 `main.h` 中生成了宏，应将确实需要的宏迁移到
`board.h` 或对应外设的专用配置头文件，而不是恢复整个 `main.h`。

## 4. 实际构建内容

`Board/SConscript` 固定编译以下板级源码：

```text
board.c
Core/Src/stm32f4xx_hal_msp.c
Core/Src/system_stm32f4xx.c
Startup/<当前工具链>/Startup.s
```

`Drivers/SConscript` 再根据 `stm32f4xx_hal_conf.h` 选择需要的 HAL 源文件。
不要在 IDE 工程中手工加入已经被 SCons 排除的 CubeMX 文件，否则 SCons 与
IDE 构建行为会不一致。

启动文件和链接脚本采用与芯片型号无关的统一文件名，便于以本 BSP 为模板
移植新的目标。各工具链文件分别放在自己的子目录中：

```text
Board/
├── Startup/
│   ├── GCC/Startup.s
│   ├── MDK-ARM/Startup.s
│   └── EWARM/Startup.s
└── LinkerScripts/
    ├── GCC/LinkerScripts.ld
    ├── MDK-ARM/LinkerScripts.sct
    └── EWARM/
        ├── LinkerScripts.icf
        └── LinkerScripts_SRAM.icf
```

移植其他 BSP 时保持目录和文件名稳定，只替换文件内容，并同步核对
`Board/SConscript`、`rtconfig.py` 和对应 IDE 工程模板中的路径。

## 5. 启动和初始化流程

当前控制流如下：

```text
Reset_Handler
  -> SystemInit()
  -> 初始化 .data/.bss 和 C 运行库
  -> entry()
  -> rtthread_startup()
  -> rt_hw_board_init()
       -> HAL_Init()
       -> SystemClock_Config()
       -> RT-Thread 系统堆和板级组件初始化
  -> RT-Thread main 线程
  -> Applications/main.c
```

`SystemInit()` 必须保留，因为三个工具链的启动文件都会调用它；
`SystemClock_Config()` 则位于 `board.c`，由 STM32 公共驱动中的
`rt_hw_board_init()` 调用。二者职责不同，不能相互替代。

## 6. CubeMX 配置更新流程

每次修改 CubeMX 工程后按以下顺序处理：

1. 将代码生成到仓库外的临时目录，不直接覆盖 `Board`。
2. 对比 `stm32f4xx_hal_conf.h`，只同步需要的 HAL 模块和时钟常量。
3. 对比 `stm32f4xx_hal_msp.c`，保留 CubeMX 的文件结构、注释和 `USER CODE`
   标记，将生成的 `#include "main.h"` 改为 `#include "board.h"`，并只同步 UART1
   所需的时钟、GPIO 和 NVIC 配置。
4. 对比 CubeMX `main.c` 中的 `SystemClock_Config()`，把函数体同步到
   `board.c`，但不要复制 `main()`、`HAL_Init()` 或 `MX_*_Init()`。
5. 只有 CMSIS Device 版本变化时才成套更新
   `system_stm32f4xx.c`、Device 头文件和启动文件。
6. HAL 版本变化时成套更新 `STM32F4xx_HAL_Driver`，并重新检查
   `stm32f4xx_hal_conf.h`。
7. 检查新增外设是否已有 RT-Thread STM32 驱动；优先通过 Kconfig 和驱动配置
   启用，不重复调用 CubeMX 的 `MX_*_Init()`。
8. 重新生成配置，至少完成一次当前工具链的全量构建。

## 7. 外设与中断

当前 BSP 只保留 UART1 和 GPIO。UART1 由 RT-Thread 串口驱动管理，
`stm32f4xx_hal_msp.c` 负责其时钟、PA9/PA10 复用和 NVIC 配置；GPIO 由
RT-Thread PIN 驱动直接调用 HAL GPIO 接口，因此不存在
`HAL_GPIO_MspInit()` 回调。CAN、RTC 及其他外设的 MSP 回调和 HAL 模块均
未启用。

`HardFault_Handler` 和 `PendSV_Handler` 由 Cortex-M4 移植层提供，
`SysTick_Handler` 由 STM32 公共驱动提供，USART 等外设中断通常由对应
RT-Thread 驱动提供。自定义外设确需新增中断时，应放在独立的板级模块中，
先确认没有同名实现，并遵循 RT-Thread 的中断进入/退出约定：

```c
void CUSTOM_IRQHandler(void)
{
    rt_interrupt_enter();
    HAL_CUSTOM_IRQHandler(&custom_handle);
    rt_interrupt_leave();
}
```

## 8. 时钟和内存约束

时钟树更新后应核对 HSE/LSE 来源、PLL 参数、AHB/APB 分频、Flash 等待周期
以及最终的 `SystemCoreClock`。不要在 `SystemClock_Config()` 中再次调用
`HAL_Init()`。

STM32F407 的 128 KiB 常规 SRAM 位于 `0x20000000`—`0x20020000`。
本 BSP 在 SRAM 顶部保留 8 KiB 主栈；RT-Thread 系统堆从静态 RW/ZI 数据末尾
延伸到主栈起点。修改链接脚本、主栈大小或芯片型号时，必须同步检查
`board.h` 中的 `HEAP_BEGIN`、`HEAP_END` 和 SRAM/Flash 容量。

## 9. 更新检查表

- [ ] `Core` 只包含文档列出的三个必要文件。
- [ ] `SystemClock_Config()` 与当前 CubeMX 时钟树一致。
- [ ] `stm32f4xx_hal_msp.c` 只包含全局 MSP 与 UART1 MSP 回调。
- [ ] 同一外设没有同时执行 RT-Thread 初始化和 CubeMX `MX_*_Init()`。
- [ ] 工程中没有重复的异常或外设中断函数。
- [ ] HAL、CMSIS、启动文件和 `system_stm32f4xx.c` 各只有一套参与编译。
- [ ] Kconfig、`rtconfig.h`、板级配置和实际硬件一致。
- [ ] SRAM、Flash、堆和主栈边界与链接脚本一致。
- [ ] GCC、Keil 或 IAR 至少完成一次干净构建。
