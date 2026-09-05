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

import building
from targets import cmake
from utils import _make_path_relative, get_build_dir, get_compile_commands_path


class PathCompatibilityTests(unittest.TestCase):
    def test_build_paths_preserve_spaces(self):
        env = {'BUILD_DIR': os.path.join('Build Output', 'scons')}

        self.assertEqual(
            get_build_dir(env),
            os.path.normpath('Build Output/scons'),
        )
        self.assertEqual(
            get_compile_commands_path(env),
            os.path.normpath('Build Output/scons/compile_commands.json'),
        )

    def test_relative_path_works_in_workspace_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix='RT Thread Workspace ') as temp_root:
            project_directory = os.path.join(temp_root, 'BSP Root', 'MDK5-ARM')
            include_directory = os.path.join(temp_root, 'Kernel Root', 'include')
            os.makedirs(project_directory)
            os.makedirs(include_directory)

            relative_path = _make_path_relative(project_directory, include_directory)

            self.assertEqual(
                os.path.normpath(relative_path),
                os.path.normpath(os.path.relpath(include_directory, project_directory)),
            )

    def test_explicit_project_name_with_spaces_is_preserved_and_created(self):
        with tempfile.TemporaryDirectory(prefix='RT Thread BSP ') as temp_root:
            previous_directory = os.getcwd()
            try:
                os.chdir(temp_root)
                requested_name = os.path.join('IDE Output', 'Firmware Project')
                with mock.patch.object(building, 'GetOption', return_value=requested_name):
                    project_file = building.GetProjectFile('mdk5', '.uvprojx')

                self.assertEqual(project_file, requested_name + '.uvprojx')
                self.assertTrue(os.path.isdir(os.path.join(temp_root, 'IDE Output')))
            finally:
                os.chdir(previous_directory)

    def test_cmake_rewrites_windows_and_linux_build_paths(self):
        cases = (
            (
                '-Wl,-Map=C:/RT Thread/Build/scons/rt-thread.map',
                r'C:\RT Thread\Build\scons',
            ),
            (
                '-Wl,-Map=/tmp/RT Thread/Build/scons/rt-thread.map',
                '/tmp/RT Thread/Build/scons',
            ),
        )

        for flags, build_directory in cases:
            with self.subTest(build_directory=build_directory):
                rewritten = cmake._replace_build_directory(flags, build_directory)
                self.assertEqual(
                    rewritten,
                    '-Wl,-Map=${CMAKE_BINARY_DIR}/rt-thread.map',
                )


if __name__ == '__main__':
    unittest.main()
