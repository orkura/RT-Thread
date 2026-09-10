# Agent+ 嵌入式智能开发平台

## 项目介绍

本项目在 [RT-Thread](https://github.com/RT-Thread/rt-thread) 基础上进行的二次开发，旨在构建 Agent+ 嵌入式智能开发平台。

本项目将 [RT-Thread](https://github.com/RT-Thread/rt-thread) 原有的 `components`、`examples`、`include`、`libcpu` 和 `src` 统一归入 `RT-Thread/` 目录，便于与官方版本对比并同步升级。原 `tools` 目录更名为 `Tools/`，并调整至与 `RT-Thread/` 同级，以便独立维护和迭代开发工具。`packages` 相关功能仍在完善中，后续计划支持从 RT-Thread 官方仓库及个人仓库自动下载软件包。

创建本项目的重要背景之一，是为了顺应 Agent 技术的快速发展。Agent 技术使个性化项目管理、多平台开发等以往难以高效实现的能力成为可能。为充分发挥这些能力，本项目以建设 **Agent+ 嵌入式智能开发平台** 为目标。

**注意：** 本项目不定位为某个具体产品的业务代码仓库，也不作为独立产品开发或交付。它更接近一个可复用的工程基础模板：开发新的嵌入式项目时，可以克隆本仓库，并在现有目录结构、工具链和规范的基础上添加目标硬件与产品功能。部分 BSP 的移植可参考 [RT-Thread 官方仓库](https://github.com/RT-Thread/rt-thread)。

## 整体框架

```text
RT-Thread/
├── .agents/                  # Agent 平台规则、知识和技能配置
├── .github/                  # GitHub Actions 等仓库自动化配置
├── BSP/                      # 芯片、开发板及板级支持包
│   └── STM32/                # STM32 家族
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

### 重要目录的主要职责

#### BSP

`BSP/` 保存芯片、开发板及板级工程。这里以 `BSP/STM32` 为例：

> `BSP/STM32/Libraries`：提供基于 RT-Thread 设备驱动框架的公共驱动，涵盖整个 STM32 家族，该实现由 [RT-Thread](https://github.com/RT-Thread/rt-thread) 提供，项目在其基础上进行了集成与完善。
> `BSP/STM32/<boards>`：这里是项目开发的正式工作区，一个项目一个 `<boards>` 目录，以保持各项目独立。

当前仓库提供的 `BSP/STM32/STM32F407/`，默认使用 GNU Arm Embedded Toolchain 和 SCons 进行构建，支持将 SCons 工程转换为其他工程格式，目前已完成 CMake 和 Keil 工程的验证。

#### RT-Thread

`RT-Thread/` 目录保存 [RT-Thread](https://github.com/RT-Thread/rt-thread) 源码。**如非必要，不得修改**。

#### Tools

`Tools/` 保存工程工具和自动化能力，主要包含：

- **构建与工程配置工具**：SCons 构建脚本、Kconfig 与工程配置工具。
- **工程转换与工程文件生成**：支持 SCons、CMake、Keil 工程之间的转换与同步，并可自动生成目标工程文件。
- **持续集成与质量保障**：CI 检查脚本、静态检查与回归测试脚本。
- **发布与交付工具**：发布、打包和版本验证相关脚本。
- **协作与环境辅助脚本**：用于统一开发环境、自动化流程和常用运维动作的辅助脚本。

#### Docs

`Docs/` 工程说明文档，详细介绍了如何基于本工程进行开发，当前包括：

- [Windows 开发环境搭建](Docs/Environment/Windows开发环境搭建.md)。
- [Git 分支管理规范](Docs/Git/Git分支管理规范.md)。
- [Git 提交管理规范](Docs/Git/Git提交管理规范.md)。

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

可以使用软连接将 `RT-Thread_Env/.venv` 下的 Python 环境移植到 `RT-Thread`，命令如下：

在 `RT-Thread_Env/RT-Thread/` 目录下，以管理员权限打开终端，输入以下命令：

> Windows Powershell 终端：
>
> ```powershell
> New-Item -ItemType SymbolicLink -Path .\.venv -Target ..\.venv
> ```
>
> Linux Shell 终端：
>
> ```shell
> ln -s ../.venv .venv
> ```

在使用 Git 的 worktree 功能时，可以将工程的 Python 环境，以软连接的方式导入到各自的目录。

**注意：** 需要先在 `.git/info/exclude` 添加以下规则，否则 Git 会提示 `.venv` 未跟踪：

```text
# git ls-files --others --exclude-from=.git/info/exclude
# Lines that start with '#' are comments.
# For a project mostly in C, the following would be a good set of
# exclude patterns (uncomment them if you want to use them):
# *.[oa]
# *~
.venv
```

## 结语

💬 欢迎提交 Issue、反馈问题或分享建议，让我们一起把项目做得更好！🙌
