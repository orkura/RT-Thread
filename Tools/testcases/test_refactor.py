#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import unittest


TESTS_ROOT = os.path.dirname(os.path.abspath(__file__))
TOOLS_ROOT = os.path.normpath(os.path.dirname(TESTS_ROOT))
sys.path.insert(0, TESTS_ROOT)
sys.path.insert(0, TOOLS_ROOT)

import mock_rtconfig
sys.modules['rtconfig'] = mock_rtconfig


class RefactorTests(unittest.TestCase):
    def test_target_modules_can_be_imported(self):
        import targets

        target_modules = [
            'keil', 'iar', 'vs', 'vs2012', 'codeblocks', 'ua',
            'vsc', 'cdk', 'ses', 'eclipse', 'codelite',
            'cmake', 'xmake', 'esp_idf', 'zigbuild', 'makefile', 'rt_studio',
        ]
        for module_name in target_modules:
            with self.subTest(module=module_name):
                self.assertTrue(hasattr(targets, module_name))

    def test_building_exports_project_generator(self):
        import building

        self.assertTrue(callable(building.GenTargetProject))

    def test_target_entry_points_are_callable(self):
        from targets.cmake import CMakeProject
        from targets.eclipse import TargetEclipse
        from targets.iar import IARProject
        from targets.keil import MDK4Project, MDK5Project

        for entry_point in (
                CMakeProject, TargetEclipse, IARProject, MDK4Project, MDK5Project):
            with self.subTest(entry_point=entry_point.__name__):
                self.assertTrue(callable(entry_point))


if __name__ == '__main__':
    unittest.main()
