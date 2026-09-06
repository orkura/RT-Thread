TOOLCHAIN_PATHS = {
    'gcc': r'C:/msys64/ucrt64/bin',
    'armcc': r'D:/App/Code/Keil/ARM/ARM_Compiler_5.06/bin',
    'armclang': r'D:/App/Code/Keil/ARM/ARMCLANG/bin',
    'iccarm': '',
}

# Download tools are kept separate from compiler toolchains so they can be
# replaced without changing rtconfig.py or the build-system configuration.
DOWNLOAD_TOOL_PATHS = {
    'jlink': r'D:/App/Code/Keil/ARM/Segger/JLink.exe',
}

DOWNLOAD_CONFIG = {
    'tool': 'jlink',
    'device': 'STM32F407ZG',
    'interface': 'SWD',
    'speed_khz': 4000,
    'flash_address': 0x08000000,
    'images': {
        'scons': r'Build/scons/rt-thread.elf',
        'keil': r'MDK-ARM/rtthread.bin',
    },
}
