#!/usr/bin/env python3

import os
import sys
import tempfile
import unittest
from unittest import mock


TESTS_ROOT = os.path.dirname(os.path.abspath(__file__))
TOOLS_ROOT = os.path.normpath(os.path.dirname(TESTS_ROOT))
sys.path.insert(0, TESTS_ROOT)
sys.path.insert(0, TOOLS_ROOT)

import mock_rtconfig
sys.modules['rtconfig'] = mock_rtconfig

from targets import cmake


class SourceNode:
    def __init__(self, path):
        self.abspath = path

    def rfile(self):
        return self


class CMakeGeneratorTests(unittest.TestCase):
    def test_group_name_is_a_valid_cmake_identifier(self):
        self.assertEqual(
            cmake._sanitize_cmake_identifier('STM32F4 HAL'),
            'STM32F4_HAL',
        )
        self.assertEqual(
            cmake._sanitize_cmake_identifier('7-Zip/Driver'),
            'group_7_Zip_Driver',
        )

    def test_sanitized_group_names_are_unique_without_mutating_groups(self):
        groups = [
            {'name': 'Drivers'},
            {'name': 'drivers'},
            {'name': 'Drivers!'},
        ]

        group_names = cmake._make_unique_group_names(groups)

        self.assertEqual(
            [group_names[id(group)] for group in groups],
            ['Drivers', 'drivers_2', 'Drivers_3'],
        )
        self.assertEqual(
            [group['name'] for group in groups],
            ['Drivers', 'drivers', 'Drivers!'],
        )

    def test_relative_linker_script_is_prefixed_and_quoted(self):
        link_flags = '-Wl,--gc-sections -T "Board/Linker Script/flash.ld"'

        generated_flags = cmake._prefix_linker_script(link_flags, '-T')

        self.assertEqual(
            generated_flags,
            '-Wl,--gc-sections -T '
            '"${CMAKE_SOURCE_DIR}/Board/Linker Script/flash.ld"',
        )

    def test_local_include_paths_are_applied_to_the_group_target(self):
        with tempfile.TemporaryDirectory() as temp_root:
            source_path = os.path.join(temp_root, 'drivers', 'drv_common.c')
            include_path = os.path.join(temp_root, 'drivers', 'include')
            project = [
                {
                    'name': 'Applications',
                    'src': [SourceNode(os.path.join(temp_root, 'main.c'))],
                },
                {
                    'name': 'STM32F4 HAL',
                    'src': [SourceNode(source_path)],
                    'LOCAL_CPPPATH': [include_path],
                },
            ]
            env = {
                'CFLAGS': '-mcpu=cortex-m4 -std=gnu11',
                'CXXFLAGS': ['-mcpu=cortex-m4 -std=gnu++17'],
                'ASFLAGS': '-mcpu=cortex-m4',
                'LINKFLAGS': '-Wl,-Map=Build/scons/rt-thread.map -T linker.ld',
                'CPPPATH': [],
                'CPPDEFINES': [],
                'BUILD_DIR': os.path.join('Build', 'scons'),
            }

            previous_directory = os.getcwd()
            try:
                os.chdir(temp_root)
                with mock.patch.object(cmake.os.path, 'exists', return_value=True), \
                        mock.patch.object(cmake.rtconfig, 'CPU', 'cortex-m4', create=True), \
                        mock.patch.object(cmake.rtconfig, 'SIZE', 'size', create=True), \
                        mock.patch.object(cmake.rtconfig, 'OBJDUMP', 'objdump', create=True), \
                        mock.patch.object(cmake.rtconfig, 'OBJCPY', 'objcopy', create=True), \
                        mock.patch.object(
                            cmake.rtconfig,
                            'POST_ACTION',
                            'objcopy $TARGET Build/scons/rtthread.bin',
                            create=True,
                        ):
                    cmake.GenerateCFiles(env, project, 'project')

                with open('CMakeLists.txt', 'r', encoding='utf-8') as cmake_file:
                    generated_cmake = cmake_file.read()
            finally:
                os.chdir(previous_directory)

            self.assertIn('SET(RT_STM32F4_HAL_LOCAL_INCLUDE_DIRS', generated_cmake)
            self.assertIn(
                'TARGET_INCLUDE_DIRECTORIES('
                'rtt_STM32F4_HAL PRIVATE ${RT_STM32F4_HAL_LOCAL_INCLUDE_DIRS})',
                generated_cmake,
            )
            self.assertIn('${CMAKE_BINARY_DIR}/rt-thread.map', generated_cmake)
            self.assertIn('${CMAKE_BINARY_DIR}/rtthread.bin', generated_cmake)
            self.assertNotIn('Build/scons', generated_cmake)


if __name__ == '__main__':
    unittest.main()
