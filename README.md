# Agent+ 嵌入式智能开发平台

## 项目介绍

本项目在 [RT-Thread](https://github.com/RT-Thread/rt-thread) 基础上进行二次开发，旨在构建 Agent+ 嵌入式智能开发平台。

本项目将 [RT-Thread](https://github.com/RT-Thread/rt-thread) 原有的 `components`、`examples`、`include`、`libcpu` 和 `src` 统一归入 `RT-Thread/` 目录，便于与官方版本对比并同步升级。原 `tools` 目录更名为 `Tools/`，并调整至与 `RT-Thread/` 同级，以便独立维护和迭代开发工具。`packages` 相关功能仍在完善中，后续计划支持从 RT-Thread 官方仓库及个人仓库自动下载软件包。

创建本项目的重要背景之一，是 Agent 技术的快速发展。Agent 技术使个性化项目管理、多平台开发等以往难以高效实现的能力成为可能。为充分发挥这些能力，本项目以建设 **Agent+ 嵌入式智能开发平台** 为目标。

**注意：** 本项目不定位为某个具体产品的业务代码仓库，也不作为独立产品开发或交付。它更接近一个可复用的工程基础模板：开发新的嵌入式项目时，可以克隆本仓库，并在现有目录结构、工具链和规范的基础上添加目标硬件与产品功能。部分 BSP 的移植可参考 [RT-Thread 官方仓库](https://github.com/RT-Thread/rt-thread)。

## 整体框架

```text
RT-Thread/
├── .agents/                  # Agent 平台规则、知识和技能配置
├── .github/                  # GitHub Actions 等仓库自动化配置
├── BSP/                      # 芯片、开发板及板级支持包
│   └── STM32/
│       ├── Libraries/        # 基于 RT-Thread 驱动框架的公共驱动代码
│       └── STM32F407/        # STM32F407
├── Docs/                     # 项目说明文档
│   ├── Environment/          # 开发环境搭建说明
│   └── Git/                  # 分支与提交管理规范
├── RT-Thread/                # RT-Thread 内核、组件、驱动框架及测试代码
├── Tools/                    # 构建、配置、CI、发布和测试工具
├── AGENTS.md                 # Agent 在本仓库中的入口规则
├── LICENSE                   # 项目许可证
└── README.md                 # 项目说明
```

**注意：** STM32F407 主要作为测试与验证基准平台。后续开展自动化测试时，可将其作为基准目标，用于验证代码变更的正确性与稳定性。

### 目录职责

#### BSP

`BSP/` 保存芯片、开发板及板级工程。一个 BSP 通常包含：

- 应用入口和板级初始化代码。
- 外设驱动及硬件配置。
- 链接脚本和启动文件。
- SCons、Keil 或其他构建工程配置。
- 板级下载和调试参数。

当前仓库提供 `BSP/STM32/STM32F407/`，默认使用 GNU Arm Embedded Toolchain 和 SCons 构建。项目还支持将 SCons 工程转换为其他工程格式，目前已完成 CMake 和 Keil 工程的验证。

#### RT-Thread

`RT-Thread/` 保存操作系统公共代码，包括：

- 内核源码。
- CPU 架构支持。
- 设备驱动框架。
- 文件系统、网络、POSIX 等组件。
- 示例和公共头文件。

**注意：** `RT-Thread/` 目录保存 RT-Thread 源码；除非确有必要，否则不得修改。

#### Tools

`Tools/` 保存工程工具和自动化能力，包括：

- SCons 构建辅助脚本。
- Kconfig 和工程配置工具。
- CI 检查脚本。
- 工程文件生成器。
- 发布工具和回归测试。

#### Docs

`Docs/` 保存项目级文档，当前包括：

- Windows 开发环境搭建。
- Git 分支管理规范。
- Git 提交管理规范。

后续可以在此扩展调试、烧录、BSP 适配、发布和故障排查文档。

#### Agent 与自动化配置

`AGENTS.md` 是 Agent 的项目入口规则，`.agents/` 保存不同平台或任务的详细约束，`.github/` 保存仓库自动化配置。

这些配置用于让人工开发、Agent 操作和 CI 流程遵循同一套环境与协作规范。

## 工作区与共享环境

推荐将主工作树、共享虚拟环境和其他 worktree 放在同一父目录（如 `RT-Thread_Env/`）下：

```text
RT-Thread_Env/
├── .venv/                          # 所有同级工作树共享的 Python 环境
├── RT-Thread/                      # 主工作树和 Git 公共元数据所在仓库
├── RT-Thread-feature-a/            # 功能分支 worktree
└── RT-Thread-feature-b/            # 其他分支 worktree
```

在这些同级工作树中，以下路径都指向同一套虚拟环境：

```text
..\.venv\bin\python.exe
..\.venv\bin\scons.exe
```

这种布局具有以下作用：

- Python 环境与任意单个工作树解耦。
- 多个 worktree 无需重复安装相同依赖。
- 删除某个临时 worktree 不会同时删除开发环境。
- 不同工作树的源码和构建产物保持隔离。

原仓库及其 `.git` 公共元数据必须保留，关联 worktree 才能正常使用。多个 worktree 共享 `.venv` 时，安装或升级依赖会同时影响所有工作树；如果不同分支需要互不兼容的依赖，应在父目录中创建独立命名的虚拟环境，并修改相应的配置。

## 当前支持范围

当前主要开发基线如下：

| 项目 | 当前配置 |
| --- | --- |
| 主机系统 | 64 位 Windows |
| 命令环境 | PowerShell |
| 基础工具环境 | MSYS2 UCRT64 |
| Python | UCRT64 Python + 独立虚拟环境 |
| 构建系统 | SCons |
| 交叉编译器 | GNU Arm Embedded Toolchain |
| RTOS | RT-Thread |
| BSP | STM32F407，作为基准测试平台，用于支持其他 BSP 的移植与验证 |
| CI | GitHub Actions |

**注意：** 当前主要支持 Windows；Linux 开发环境仍在适配中。

## 结语

💬 欢迎提交 Issue、反馈问题或分享建议，让我们一起把项目做得更好！🙌
