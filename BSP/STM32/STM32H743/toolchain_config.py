from pathlib import Path
from runpy import run_path


TOOLCHAIN_PATHS = {
    'gcc': '',
    'armcc': '',
    'armclang': '',
    'iccarm': '',
}

# Download tools are kept separate from compiler toolchains so they can be
# replaced without changing rtconfig.py or the build-system configuration.
DOWNLOAD_TOOL_PATHS = {
    'jlink': '',
}


def _load_local_tool_paths():
    local_config_path = (
        Path(__file__).resolve().parent
        / 'Config'
        / 'toolchain_config.local.py'
    )
    if not local_config_path.is_file():
        return

    local_config = run_path(str(local_config_path))
    path_groups = {
        'TOOLCHAIN_PATHS': TOOLCHAIN_PATHS,
        'DOWNLOAD_TOOL_PATHS': DOWNLOAD_TOOL_PATHS,
    }

    for group_name, shared_paths in path_groups.items():
        local_paths = local_config.get(group_name, {})
        if not isinstance(local_paths, dict):
            raise TypeError(group_name + ' in the local config must be a dict')

        unknown_tools = set(local_paths) - set(shared_paths)
        if unknown_tools:
            raise ValueError(
                'unknown tools in {}: {}'.format(
                    group_name,
                    ', '.join(sorted(unknown_tools)),
                )
            )
        shared_paths.update(local_paths)


_load_local_tool_paths()

DOWNLOAD_CONFIG = {
    'tool': 'jlink',
    'device': 'STM32H743VI',
    'interface': 'SWD',
    'speed_khz': 4000,
    'flash_address': 0x08000000,
    'images': {
        'scons': r'Build/scons/rt-thread.elf',
        'keil-MDK5': r'MDK5-ARM/rtthread.bin',
        'keil-MDK6': r'MDK6-ARM/rtthread.bin',
    },
}
