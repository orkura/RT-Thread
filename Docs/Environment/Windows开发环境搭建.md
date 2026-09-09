# Windows 开发环境搭建

## 开发约定

在开始安装前，先确认以下约定：

- MSYS2 默认位置 `C:\msys64`。
- 不将 MSYS2 相关路径加入 Windows 的系统或用户 `PATH`。

工作区结构推荐：

```text
<workspace>/
├── .venv/                          # 共享 Python 虚拟环境
├── RT-Thread/                      # 主工作树和 Git 公共元数据
├── RT-Thread-feature-a/            # 同级 Git worktree
└── RT-Thread-feature-b/            # 同级 Git worktree
```

`.venv` 放在**仓库外部**。只要各工作树位于同一个父目录，主工作树和多个 Git worktree 就都可以通过 `..\.venv` 使用同一套 Python、SCons 和项目依赖，无需为每个 worktree 重复创建环境。

## UCRT64 安装配置

从 [MSYS2 官方网站](https://www.msys2.org/) 或 [官方安装器说明](https://www.msys2.org/docs/installer/) 获取 64 位安装器，默认安装在`C:\msys64`。MSYS2 同时提供多个运行环境，本项目统一使用 **UCRT64**。

注意：不同环境的运行库和工具不可随意混用，详情参见 [MSYS2 Environments](https://www.msys2.org/docs/environments/)。

在 PowerShell 执行 `notepad $PROFILE` 可打开配置文件，将以下函数添加到配置文件 `$PROFILE`：

```powershell1
function ucrt64 {
    $ucrt64Bin = 'C:\msys64\ucrt64\bin'

    # 避免重复添加 PATH
    if (($env:PATH -split ';') -notcontains $ucrt64Bin) {
        $env:PATH = "$ucrt64Bin;$env:PATH"
    }

    & 'C:\msys64\msys2_shell.cmd' `
        -defterm `
        -here `
        -no-start `
        -ucrt64 `
        -use-full-path
}
```

在目标 BSP Powershell 终端中执行 `ucrt64`，即可从当前目录进入 UCRT64。

进入 UCRT64 并执行完整更新指令：

```msys2
pacman -Syu
```

该指令增加更新指令，不调整其他内容。

## 开发工具安装

进入 UCRT64 后，安装项目所需的开发软件包：

```bash
pacman -S --needed \
    mingw-w64-ucrt-x86_64-python \
    mingw-w64-ucrt-x86_64-python-pip \
    mingw-w64-ucrt-x86_64-arm-none-eabi-gcc
```

其中：

- `mingw-w64-ucrt-x86_64-python`：提供 UCRT64 Python。
- `mingw-w64-ucrt-x86_64-python-pip`：提供与 UCRT64 Python 匹配的 pip。
- `mingw-w64-ucrt-x86_64-arm-none-eabi-gcc`：ARM 交叉编译器，并自动安装对应的 binutils 和 newlib 依赖。

GNU Arm Embedded Toolchain 的 MSYS2 软件包信息可在 [MSYS2 Packages](https://packages.msys2.org/packages/mingw-w64-ucrt-x86_64-arm-none-eabi-gcc) 查看。

如需命令行调试器，可以额外安装：

```bash
pacman -S --needed mingw-w64-ucrt-x86_64-gdb-multiarch
```

该调试器不是完成 SCons 编译的必要条件。

## Python 环境搭建

创建 `RT-Thread_Env` 工作区并克隆仓库后，在仓库根目录的 UCRT64 中执行：

```bash
python -m venv ../.venv
```

确认 `.venv` 创建成功后，将以下别名添加到 UCRT64 的 `~/.bashrc`：

```bash
alias rtenv='source /f/Project/RT-Thread_Env/.venv/bin/activate'
```

`/f/Project/RT-Thread_Env`仅为示例，应替换为本机 `.venv/bin/activate` 的实际路径。然后执行：

```bash
source ~/.bashrc
rtenv
```

在仓库根目录的 UCRT64 中执行：

```bash
rtenv
python -m pip install --upgrade pip
python -m pip install -r Tools/requirements.txt
python -m pip check
scons --version
```

仅在运行完整 CI 辅助脚本时安装附加依赖：

```bash
python -m pip install -r Tools/ci/requirements.txt
```

## 构建编译

构建 STM32F407 BSP：

```bash
cd BSP/STM32/STM32F407
scons -j8
```

清理构建产物：

```bash
scons -c
```

构建产物位于 `BSP/STM32/STM32F407/Build/scons/`，主要包括 `rt-thread.elf`、`rtthread.bin` 和 `rt-thread.map`。
