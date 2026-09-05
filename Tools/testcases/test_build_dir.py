#!/usr/bin/env python3

import json
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

import mkdist
from targets import vsc
from utils import get_build_dir, get_compile_commands_path


class BuildDirectoryTests(unittest.TestCase):
    def test_default_build_directory_is_backward_compatible(self):
        self.assertEqual(get_build_dir(), 'build')
        self.assertEqual(get_build_dir({}), 'build')
        self.assertEqual(get_build_dir({'BUILD_DIR': ''}), 'build')
        self.assertEqual(
            get_compile_commands_path({}),
            os.path.join('build', 'compile_commands.json'),
        )

    def test_custom_build_directory_is_preserved(self):
        env = {'BUILD_DIR': os.path.join('Build', 'scons')}

        self.assertEqual(get_build_dir(env), os.path.normpath('Build/scons'))
        self.assertEqual(
            get_compile_commands_path(env),
            os.path.normpath('Build/scons/compile_commands.json'),
        )

    def test_distribution_excludes_configured_build_tree(self):
        with tempfile.TemporaryDirectory() as temp_root:
            bsp_root = os.path.join(temp_root, 'bsp')
            dist_root = os.path.join(temp_root, 'dist-output')
            build_root = os.path.join(bsp_root, 'Build', 'scons')
            os.makedirs(build_root)

            source_path = os.path.join(bsp_root, 'SConstruct')
            artifact_path = os.path.join(build_root, 'artifact.o')
            with open(source_path, 'w', encoding='utf-8') as source_file:
                source_file.write('# test\n')
            with open(artifact_path, 'w', encoding='utf-8') as artifact_file:
                artifact_file.write('object\n')

            mkdist.bsp_copy_files(bsp_root, dist_root, os.path.join('Build', 'scons'))

            self.assertTrue(os.path.isfile(os.path.join(dist_root, 'SConstruct')))
            self.assertFalse(os.path.exists(os.path.join(dist_root, 'Build')))

    def test_vscode_uses_configured_compile_database(self):
        with tempfile.TemporaryDirectory() as temp_root:
            previous_directory = os.getcwd()
            try:
                os.chdir(temp_root)
                project_info = {
                    'CPPDEFINES': [],
                    'CPPPATH': [temp_root],
                    'DIRS': [temp_root],
                }
                env = {
                    'BUILD_DIR': os.path.join('Build', 'scons'),
                    'RTT_ROOT': temp_root,
                }

                with mock.patch.object(vsc.utils, 'ProjectInfo', return_value=project_info):
                    vsc.GenerateCFiles(env)

                properties_path = os.path.join(temp_root, '.vscode', 'c_cpp_properties.json')
                with open(properties_path, 'r', encoding='utf-8') as properties_file:
                    properties = json.load(properties_file)

                compile_commands = properties['configurations'][0]['compileCommands']
                self.assertEqual(compile_commands, 'Build/scons/compile_commands.json')
            finally:
                os.chdir(previous_directory)

    def test_vscode_reads_compile_database_from_requested_path(self):
        with tempfile.TemporaryDirectory() as temp_root:
            root_path = os.path.join(temp_root, 'RT-Thread')
            database_path = os.path.join(temp_root, 'Build', 'scons', 'compile_commands.json')
            os.makedirs(root_path)
            os.makedirs(os.path.dirname(database_path))
            with open(database_path, 'w', encoding='utf-8') as database_file:
                json.dump([], database_file)

            filtered_tree = {os.path.basename(root_path): {}}
            with mock.patch.object(vsc, 'extract_source_dirs', return_value=[]), \
                    mock.patch.object(vsc, 'build_tree', return_value={}), \
                    mock.patch.object(vsc, 'filt_tree', return_value=filtered_tree), \
                    mock.patch.object(vsc, 'is_path_in_tree', return_value=True), \
                    mock.patch.object(vsc, 'generate_code_workspace_file') as generate_workspace, \
                    mock.patch('builtins.print'):
                vsc.command_json_to_workspace(root_path, database_path)

            generate_workspace.assert_called_once_with(set(), database_path, root_path)


if __name__ == '__main__':
    unittest.main()
