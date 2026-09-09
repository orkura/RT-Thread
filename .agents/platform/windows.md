# Windows

## 终端环境

本工程统一使用 PowerShell，包括 Windows PowerShell（`powershell.exe`）和 PowerShell 7+（`pwsh.exe`），并在其中使用 MSYS2 UCRT64 工具。不得使用 MSYS2 Bash 或登录 Shell。

每次新建 PowerShell 进程或会话后，必须确保 `C:\msys64\ucrt64\bin` 位于当前进程 `PATH` 的最前面：

```powershell
$env:Path = "C:\msys64\ucrt64\bin;$env:Path"
```

不得假定其他终端或先前进程中的环境修改仍然有效。该设置只能影响当前 PowerShell 进程及其子进程，不得永久修改 Windows 的系统或用户 `PATH`，也不得将 `C:\msys64\usr\bin` 加入 `PATH`。

## 虚拟环境

工程的 Python 虚拟环境位于 `.venv`，由 UCRT64 Python 创建。PowerShell 中无需激活，直接调用：

```powershell
& ..\.venv\bin\python.exe <参数>
```

运行 pip 使用 `& ..\.venv\bin\python.exe -m pip <参数>`，不得改用系统 Python，也不得执行 Bash 风格的激活命令。
