# 测试用例目录

本目录包含 RT-Thread 工具的测试脚本。

## 测试脚本

### test_preprocessor.py
SCons PreProcessor 补丁功能测试脚本。测试与 building.py 的集成，验证预处理器补丁是否正常工作。

### test_refactor.py
验证目标模块重构是否成功的测试脚本。测试内容包括：
- 目标模块导入
- Building.py 导入
- 目标函数调用

### test_tools_root.py
验证迁移后的 `Tools` 目录能够独立于 `RTT_ROOT` 解析，并支持从构建环境显式覆盖。

### test_build_dir.py
验证默认及自定义构建目录、编译数据库路径和发布包构建目录排除行为。

### test_mdk_toolchain.py
验证 MDK5/ArmCC 与 MDK6/ArmClang 的工具链映射、Keil 工程编译器选择及版本信息。

### test_project_output.py
验证 MDK5、MDK6 和 IAR 的默认输出目录、显式项目名及目录自动创建行为。

### test_cmake_generator.py
验证 SCons 分组名能转换为合法且唯一的 CMake 变量和目标名。

### mock_rtconfig.py
用于测试的模拟 rtconfig 模块。在实际 rtconfig 不可用的测试场景中提供模拟的 rtconfig 模块。

## 使用方法

要运行测试，请导航到此目录并执行：

```bash
python test_preprocessor.py
python test_refactor.py
python test_tools_root.py
python test_build_dir.py
python test_mdk_toolchain.py
python test_project_output.py
python test_cmake_generator.py
```

## 说明

- 这些测试脚本用于验证 RT-Thread 工具的功能
- 可以独立运行或作为测试套件的一部分
- mock_rtconfig.py 文件被其他测试脚本用来模拟 rtconfig 模块
