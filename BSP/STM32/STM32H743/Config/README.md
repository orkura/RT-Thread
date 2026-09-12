# 本机工具路径配置

此目录中的示例用于配置编译器和下载工具在本机上的实际位置，不需要修改系统环境变量。

Windows 用户执行：

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
