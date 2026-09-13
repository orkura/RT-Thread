# Copy this file to toolchain_config.local.py and adjust the paths.
# Forward slashes avoid backslash escaping and are accepted on Windows.

TOOLCHAIN_PATHS = {
    'gcc': r'C:/Tools/ArmGNU/bin',
    'armcc': r'C:/Keil_v5/ARM/ARMCC/bin',
    'armclang': r'C:/Keil_v5/ARM/ARMCLANG/bin',
    'iccarm': r'C:/Program Files/IAR Systems/Embedded Workbench/arm/bin',
}

DOWNLOAD_TOOL_PATHS = {
    'jlink': r'C:/Program Files/SEGGER/JLink/JLink.exe',
}
