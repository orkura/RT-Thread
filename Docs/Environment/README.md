# 开发环境

## 支持状态

| 平台 | 工具环境 | 状态 | 文档 |
| --- | --- | --- | --- |
| Windows | PowerShell + MSYS2 UCRT64 | 已支持 | [Windows 开发环境搭建](Windows开发环境搭建.md) |
| Linux | 待定 | 暂未提供 | — |

当前项目以 Windows 环境为主。Linux 环境的依赖、命令和验证流程尚未定义，请勿直接套用 Windows 步骤。

## 注意事项

- 由于部分 Agent 的砂箱机制，导致进入 ucrt64 环境后会出现异常，所以 Agent 不得使用 MSYS2 Bash 或登录 Shell。
