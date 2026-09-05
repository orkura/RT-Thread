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
from targets import iar


class ProjectOutputTests(unittest.TestCase):
    def test_ide_targets_use_separate_default_directories(self):
        with mock.patch.object(building, 'GetOption', return_value=None):
            self.assertEqual(
                building.GetProjectName('mdk5'),
                os.path.join('MDK5-ARM', 'project'),
            )
            self.assertEqual(
                building.GetProjectName('mdk6'),
                os.path.join('MDK6-ARM', 'project'),
            )
            self.assertEqual(
                building.GetProjectName('iar'),
                os.path.join('EWARM', 'project'),
            )

    def test_other_targets_keep_project_as_default_name(self):
        with mock.patch.object(building, 'GetOption', return_value=None):
            for target_name in ('mdk', 'mdk4', 'vs', 'eclipse', 'cmake'):
                self.assertEqual(building.GetProjectName(target_name), 'project')

    def test_explicit_project_name_is_preserved_for_every_target(self):
        requested_name = os.path.join('custom-output', 'firmware')
        with mock.patch.object(building, 'GetOption', return_value=requested_name):
            for target_name in ('mdk5', 'mdk6', 'iar', 'vs'):
                self.assertEqual(building.GetProjectName(target_name), requested_name)

    def test_project_output_directory_is_created(self):
        with tempfile.TemporaryDirectory() as temp_root:
            previous_directory = os.getcwd()
            try:
                os.chdir(temp_root)
                with mock.patch.object(building, 'GetOption', return_value=None):
                    project_file = building.GetProjectFile('mdk6', '.uvprojx')

                self.assertEqual(
                    project_file,
                    os.path.join('MDK6-ARM', 'project.uvprojx'),
                )
                self.assertTrue(os.path.isdir(os.path.join(temp_root, 'MDK6-ARM')))
            finally:
                os.chdir(previous_directory)

    def test_iar_workspace_references_project_in_the_same_directory(self):
        with tempfile.TemporaryDirectory() as temp_root:
            project_file = os.path.join(temp_root, 'EWARM', 'project.ewp')
            os.makedirs(os.path.dirname(project_file))

            iar.IARWorkspace(project_file)

            workspace_file = os.path.join(temp_root, 'EWARM', 'project.eww')
            with open(workspace_file, 'r', encoding='utf-8') as workspace:
                workspace_xml = workspace.read()
            self.assertIn(r'$WS_DIR$\project.ewp', workspace_xml)
            self.assertNotIn(r'$WS_DIR$\EWARM\project.ewp', workspace_xml)


if __name__ == '__main__':
    unittest.main()
