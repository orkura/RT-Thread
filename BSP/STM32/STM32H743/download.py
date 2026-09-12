#!/usr/bin/env python3

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from toolchain_config import DOWNLOAD_CONFIG, DOWNLOAD_TOOL_PATHS


BSP_ROOT = Path(__file__).resolve().parent
SUPPORTED_IMAGE_SUFFIXES = {'.axf', '.bin', '.elf', '.hex'}


def parse_address(value):
    try:
        return int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            'address must be a decimal or hexadecimal integer'
        ) from exc


def resolve_image(image, build_system):
    if image is not None:
        path = image if image.is_absolute() else BSP_ROOT / image
        return path.resolve()

    configured_images = DOWNLOAD_CONFIG.get('images', {})
    if build_system is not None:
        configured_path = configured_images.get(build_system)
        if not configured_path:
            raise RuntimeError(
                'no firmware image is configured for: ' + build_system
            )
        return (BSP_ROOT / configured_path).resolve()

    existing_images = []
    for configured_path in configured_images.values():
        path = (BSP_ROOT / configured_path).resolve()
        if path.is_file():
            existing_images.append(path)

    if not existing_images:
        expected = '\n'.join(
            '  ' + str((BSP_ROOT / path).resolve())
            for path in configured_images.values()
        )
        raise RuntimeError('no firmware image was found:\n' + expected)

    return max(existing_images, key=lambda path: path.stat().st_mtime)


def make_jlink_commands(image, flash_address):
    load_command = 'loadfile "{}"'.format(image)
    if image.suffix.lower() == '.bin':
        load_command += ' 0x{:08X}'.format(flash_address)

    return '\n'.join([
        'r',
        'h',
        load_command,
        'r',
        'g',
        'exit',
        '',
    ])


def build_argument_parser():
    parser = argparse.ArgumentParser(
        description='Download an STM32H743 firmware image with J-Link.'
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        '--build',
        choices=sorted(DOWNLOAD_CONFIG.get('images', {})),
        help='download the configured image from one build system',
    )
    source.add_argument(
        '--image',
        type=Path,
        help='download a specific ELF, AXF, HEX, or BIN image',
    )
    parser.add_argument(
        '--address',
        type=parse_address,
        default=DOWNLOAD_CONFIG['flash_address'],
        help='BIN load address (default: 0x%(default)08X)',
    )
    parser.add_argument(
        '--speed',
        type=int,
        default=DOWNLOAD_CONFIG['speed_khz'],
        help='J-Link interface speed in kHz (default: %(default)s)',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='validate and display the download operation without flashing',
    )
    return parser


def main():
    args = build_argument_parser().parse_args()

    tool_name = DOWNLOAD_CONFIG['tool']
    if tool_name != 'jlink':
        raise RuntimeError('unsupported download tool: ' + tool_name)

    executable_value = DOWNLOAD_TOOL_PATHS.get(tool_name, '')
    if not executable_value:
        raise FileNotFoundError(
            'J-Link Commander is not configured; copy a platform example '
            'from the Config directory to toolchain_config.local.py and '
            'set its path'
        )
    executable = Path(executable_value).expanduser()
    if not executable.is_file():
        raise FileNotFoundError(
            'J-Link Commander was not found: ' + str(executable)
        )

    image = resolve_image(args.image, args.build)
    if not image.is_file():
        raise FileNotFoundError('firmware image was not found: ' + str(image))
    if image.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
        raise ValueError('unsupported firmware image: ' + str(image))
    if args.speed <= 0:
        raise ValueError('J-Link speed must be greater than zero')

    command_text = make_jlink_commands(image, args.address)
    command = [
        str(executable),
        '-NoGui', '1',
        '-ExitOnError', '1',
        '-AutoConnect', '1',
        '-Device', DOWNLOAD_CONFIG['device'],
        '-If', DOWNLOAD_CONFIG['interface'],
        '-Speed', str(args.speed),
    ]

    print('Download tool :', executable)
    print('Target device :', DOWNLOAD_CONFIG['device'])
    print('Interface     :', DOWNLOAD_CONFIG['interface'])
    print('Speed         :', str(args.speed) + ' kHz')
    print('Firmware      :', image)
    if image.suffix.lower() == '.bin':
        print('Flash address : 0x{:08X}'.format(args.address))

    if args.dry_run:
        print('Dry run only; target flash was not changed.')
        return 0

    with tempfile.TemporaryDirectory(prefix='rtos-jlink-') as temp_dir:
        command_file = Path(temp_dir) / 'download.jlink'
        command_file.write_text(command_text, encoding='ascii')
        command.extend(['-CommandFile', str(command_file)])
        result = subprocess.run(command, cwd=BSP_ROOT, check=False)

    if result.returncode != 0:
        print(
            'J-Link download failed with exit code {}.'.format(
                result.returncode
            ),
            file=sys.stderr,
        )
        return result.returncode

    print('Firmware download completed successfully.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print('Error:', exc, file=sys.stderr)
        sys.exit(2)
