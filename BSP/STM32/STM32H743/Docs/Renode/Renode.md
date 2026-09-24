# Renode 仿真测试使用手册

创建一个 STM32H743 的 Renode 虚拟仿真：

```Renode
mach create
machine LoadPlatformDescription @platforms/cpus/stm32h743.repl
sysbus LoadELF @F:/Project/RT-Thread_Env/RT-Thread/BSP/STM32/STM32H743/Build/scons/rt-thread.elf

emulation CreateCANHub "canHub"
connector Connect sysbus.fdcan2 canHub

showAnalyzer sysbus.usart2
start
```

在建立一个：

```Renode
pause
mach create
machine LoadPlatformDescription @platforms/cpus/stm32h743.repl
sysbus LoadELF @F:/Project/RT-Thread_Env/RT-Thread/BSP/STM32/STM32H743/Build/scons/rt-thread.elf

connector Connect sysbus.fdcan2 canHub
showAnalyzer sysbus.usart2

emulation SetGlobalQuantum "0.00001"
start
```

注意不要再次输入：

```
emulation CreateCANHub "canHub"
```

`emulation SetGlobalQuantum "0.00001"`：用于设置多台虚拟机器之间的**虚拟时间同步周期**。`0.00001` 的单位是秒，即：`0.00001 s = 10 μs`。

Renode 允许每个虚拟 MCU 独立执行一小段虚拟时间，然后进行一次全局同步。设置为 10 μs，意味着 `machine-0` 和 `machine-1` 感知到的虚拟时间偏差通常不会超过一个 quantum。

它不改变以下参数：

- STM32H743 的 480 MHz CPU 时钟
- FDCAN 的 40 MHz内核时钟
- CAN 的仲裁波特率或数据波特率
- RT-Thread 的系统 Tick
- 电脑真实时间

参数大小的影响：

| Quantum            | 同步精度 | 仿真速度 |
| ------------------ | -------- | -------- |
| `0.001`（1 ms）    | 较低     | 较快     |
| `0.0001`（100 μs） | 一般     | 较快     |
| `0.00001`（10 μs） | 较高     | 适中     |
| `0.000001`（1 μs） | 很高     | 较慢     |

对于两个 H743 通过 `canHub` 通信：

```
emulation SetGlobalQuantum "0.00001"
```

是比较合适的起点。它可以减少：

- 一个 MCU 已经发送，而另一个 MCU 虚拟时间尚未跟上的情况
- 跨机器中断响应的额外延迟
- 通信超时测试中的时间偏差

如果只是测试单个 MCU 的内部回环，不需要专门设置。如果以后测试 CAN FD 的精确时延或微秒级时间戳，可以尝试 `0.000001`，但运行速度会下降。

它最好只设置一次，并放在两个机器配置完成、`start` 之前。

为了清除旧固件留下的 CPU、RAM 和外设状态，建议先复位，再加载 ELF：

```Renode
mach set 1
pause
machine Reset
sysbus LoadELF @F:/Project/RT-Thread_Env/RT-Thread/BSP/STM32/STM32H743/Build/scons/rt-thread.elf
start
```

如果 UART 窗口已经关闭，加载后、启动前补充：
```Renode
showAnalyzer sysbus.usart2
```

