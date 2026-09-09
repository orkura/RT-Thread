# Git 分支管理规范

## 1. 适用范围

本规范适用于本仓库中的普通开发分支、实验分支和发布分支，规定分支的命名、创建、使用及清理方式。

分支名称描述工作的逻辑责任域，不要求机械复制目录结构，也不限制分支只能修改对应目录。

## 2. 普通分支格式

普通分支统一采用以下两种格式之一：

```text
<scope>/<type>/<topic>
<scope>/<target>/<type>/<topic>
```

各字段含义如下：

- `scope`：本次工作的主要责任域。
- `target`：Scope 下的具体目标对象；仅在有明确目标时使用。
- `type`：本次工作的性质。
- `topic`：本次工作的具体内容。

示例：

```text
docs/feature/git-branch-rules
tools/ci/fix/git-diff-output
bsp/stm32f407/feature/spi
rt-thread/fix/scheduler-lock
```

普通开发分支必须采用上述格式；发布分支作为例外，按照第 8 节规定的 `release/<version>` 格式命名。

## 3. 命名规则

### 3.1 字符和大小写

分支名称必须满足以下要求：

- 仅使用小写英文字母、数字、短横线 `-`、斜杠 `/` 和版本号中的点号 `.`。
- 多个单词之间使用短横线连接，不使用空格、下划线或驼峰命名。
- 不使用连续的短横线或斜杠。
- 分支名称不得以短横线或斜杠开头或结尾。
- 普通分支名称建议不超过 80 个字符。

推荐：

```text
tools/ci/fix/keil-build-path
bsp/stm32f407/fix/spi-dma-timeout
```

不推荐：

```text
Tools/CI/Fix/KeilBuildPath
tools_ci_fix_keil_build_path
tools//fix/keil--build-path
```

即使仓库目录使用 `BSP`、`Tools`、`RT-Thread` 等大小写形式，分支名称仍统一使用小写。

### 3.2 命名空间保留

Git 不允许一个引用同时作为分支名和其他分支的路径前缀。因此，禁止创建名称恰好为以下内容的分支：

```text
repo
tools
bsp
rt-thread
docs
release
```

同理，不应创建 `docs/feature` 等可能作为完整分支路径前缀的分支。

## 4. Scope 定义

`scope` 表示本次工作的主要责任域，应与项目结构或逻辑归属保持对应。

| 项目区域 | Scope | 说明 |
| --- | --- | --- |
| `AGENTS.md`、`.agents/`、`.github/`、根目录配置及跨模块规则 | `repo` | Agent 指令、仓库级配置、CI 工作流和跨模块工作 |
| `Tools/` | `tools` | 构建、测试、发布及辅助工具 |
| `BSP/` | `bsp` | 芯片、开发板及板级支持包 |
| `RT-Thread/` | `rt-thread` | 内核、组件、驱动及公共运行时 |
| `Docs/` | `docs` | 仓库级文档与开发规范 |

示例：

```text
repo/ci/fix/windows-build
tools/release/fix/version-export
bsp/stm32f407/feature/spi
rt-thread/rtc/fix/alarm-timeout
docs/feature/git-branch-rules
```

### 4.1 多模块变更

当一个分支需要修改多个目录时，选择交付目标或主要责任所在的 Scope。

例如，实现 STM32F407 的 SPI 功能时，即使需要同时修改构建脚本或公共组件，仍使用：

```text
bsp/stm32f407/feature/spi
```

如果变更是仓库级配置、统一 CI 流程或无法确定单一主要责任域，则使用 `repo`。

如果主要工作是修改 Git 规范，仅顺带更新 `AGENTS.md` 中的引用，仍使用 `docs`。如果主要工作是调整 `AGENTS.md` 或 `.agents/`，则使用 `repo`。同时大范围调整多个仓库级规则且不存在单一主要责任域时，使用不带 Target 的 `repo`。

## 5. Target 定义

`target` 用于标识一个 Scope 下的独立目标，是否使用取决于 Scope 和工作内容。

### 5.1 BSP

BSP 分支必须提供 Target。Target 通常为 MCU、SoC 或开发板名称。

当前仓库中的 STM32F407 使用：

```text
bsp/stm32f407/<type>/<topic>
```

分支名称不完整复制 `BSP/STM32/STM32F407/` 目录层级，避免无意义的重复：

```text
# 推荐
bsp/stm32f407/feature/spi

# 不推荐
bsp/stm32/stm32f407/feature/spi
```

### 5.2 Tools

当变更属于明确的独立工具时，应使用工具名称作为 Target。当前可用的逻辑目标包括：

```text
ci
ng
release
targets
testcases
```

示例：

```text
tools/ci/fix/git-diff-output
tools/ng/feature/package-build
tools/release/fix/version-export
```

无法归属于具体工具的公共工具链变更，可以省略 Target：

```text
tools/refactor/build-system
```

### 5.3 RT-Thread

RT-Thread 分支可在目标清晰且有助于区分工作内容时增加 Target；Target 应表示逻辑子系统，而不是盲目复制目录层级。

```text
rt-thread/rtc/fix/alarm-timeout
rt-thread/dfs/feature/procfs
rt-thread/libcpu-risc-v/fix/context-switch
```

对于内核级或范围已经清楚的工作，可以省略 Target：

```text
rt-thread/fix/scheduler-lock
rt-thread/test/mutex
```

### 5.4 Docs 和 Repo

Docs 和 Repo 可在存在稳定子域时使用 Target，例如 `ci`；否则通常省略 Target。

涉及 `AGENTS.md` 或 `.agents/` 的工作，使用 `agents` 作为 Target：

```text
repo/agents/feature/project-instructions
repo/agents/fix/branch-policy-link
repo/agents/docs/windows-environment
```

```text
repo/ci/fix/windows-build
repo/refactor/project-configuration
docs/feature/git-branch-rules
```

## 6. Type 定义

普通分支使用以下 Type：

```text
feature
fix
refactor
docs
test
experiment
```

### 6.1 feature

新增功能、能力、规则或文档体系。

```text
bsp/stm32f407/feature/spi
tools/ng/feature/package-build
docs/feature/git-branch-rules
```

### 6.2 fix

修复已有实现、配置或说明中的具体问题。

```text
tools/ci/fix/keil-build-path
bsp/stm32f407/fix/spi-dma-timeout
docs/fix/incorrect-build-command
```

### 6.3 refactor

不改变主要功能或规则，仅调整结构和实现方式。

```text
tools/refactor/build-system
rt-thread/refactor/device-framework
docs/refactor/git-document-layout
```

### 6.4 docs

为非 Docs Scope 补充或调整使用说明、API 文档等内容。

```text
tools/docs/build-guide
bsp/stm32f407/docs/spi-usage
rt-thread/rtc/docs/driver-usage
```

`docs` 同时是一个 Scope。修改顶层 `Docs/` 时，应按变更意图使用 `feature`、`fix` 或 `refactor`，不使用重复的 `docs/docs/...`。

### 6.5 test

增加或调整测试、测试基础设施或验证场景。

```text
bsp/stm32f407/test/spi-loopback
rt-thread/test/mutex
tools/testcases/test/build-matrix
```

### 6.6 experiment

用于方案验证、原型开发或结果不确定的工作。

```text
bsp/stm32f407/experiment/spi-dma
tools/experiment/cmake-build
```

实验结果稳定后，应整理为正式的 `feature`、`fix` 或其他适当类型的分支，再发起合并请求。

## 7. Topic 命名

`topic` 应简短、明确地描述具体目标，避免重复 Scope、Target 或 Type 已经表达的信息。

推荐：

```text
spi-dma-timeout
keil-build-path
git-branch-rules
scheduler-lock
```

不推荐：

```text
bug
new
update
modify
temp
final
final2
my-branch
```

例如，`tools/fix/bug` 信息不足，应改为：

```text
tools/ci/fix/keil-build-path
```

如果项目后续统一使用需求单或缺陷单编号，可将编号作为 Topic 的前缀，但同一仓库内必须保持一致。

## 8. 发布分支

发布分支是普通分支格式的唯一预定义例外，采用：

```text
release/<version>
```

版本号使用小写 `v` 和语义化版本格式：

```text
release/v1.1.0
release/v1.2.0-rc.1
```

`release` 是保留的顶级前缀，不属于普通分支的 Type。

## 9. 分支生命周期

### 9.1 创建

- 普通开发分支原则上从最新的 `main` 创建。
- 创建前确认分支名符合本规范，且远端不存在同名分支。
- 当前仓库未定义 `develop` 分支，不以 `develop` 作为默认创建或合并基线。

### 9.2 开发与合并

- 每个分支聚焦一个明确目标，避免混入无关变更。
- 普通开发分支通过合并请求进入 `main`。
- 实验分支不能直接作为稳定交付结果；应在验证完成后整理为适当类型的正式分支。
- 发布分支用于版本发布准备，具体合并和打标签流程由发布流程规定。

### 9.3 清理

- 功能、修复、重构、文档、测试和实验分支在完成合并且确认不再使用后，应删除本地与远端分支。
- 发布分支在发布完成、变更已合入且版本标签已创建后，可以删除。
- 删除分支前应确认其中不存在尚未合入或仍需保留的提交。

## 10. 示例速查

### Repo

```text
repo/ci/fix/windows-build
repo/refactor/project-configuration
```

### Tools

```text
tools/ci/fix/git-diff-output
tools/ng/feature/package-build
tools/release/fix/version-export
tools/refactor/build-system
tools/docs/build-guide
tools/experiment/cmake-build
```

### BSP

```text
bsp/stm32f407/feature/spi
bsp/stm32f407/feature/can
bsp/stm32f407/fix/spi-dma-timeout
bsp/stm32f407/refactor/spi-driver
bsp/stm32f407/test/spi-loopback
bsp/stm32f407/experiment/spi-dma
```

### RT-Thread

```text
rt-thread/fix/scheduler-lock
rt-thread/rtc/fix/alarm-timeout
rt-thread/dfs/feature/procfs
rt-thread/libcpu-risc-v/fix/context-switch
rt-thread/test/mutex
```

### Docs

```text
docs/feature/git-branch-rules
docs/fix/incorrect-build-command
docs/refactor/git-document-layout
```

### Release

```text
release/v1.1.0
release/v1.2.0-rc.1
```

## 11. 命名检查清单

创建分支前依次确认：

1. 是否选择了正确的主要责任域？
2. BSP 是否包含 MCU 或开发板 Target？
3. Tools 或 RT-Thread 是否存在有助于辨识的逻辑 Target？
4. Type 是否属于规定集合？
5. Topic 是否能说明具体目标，而不是使用 `update`、`bug` 等泛化词？
6. 是否只使用允许的字符并保持全小写？
7. 是否避免了命名空间前缀冲突？
8. 是否从正确的基线分支创建？

符合这些条件的分支名应能够回答：修改哪里、针对什么对象、进行什么工作。
