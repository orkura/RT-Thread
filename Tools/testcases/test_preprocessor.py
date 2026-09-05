#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# File      : test_preprocessor.py
# This file is part of RT-Thread RTOS
# COPYRIGHT (C) 2006 - 2025, RT-Thread Development Team
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import sys
import unittest


TESTS_ROOT = os.path.dirname(os.path.abspath(__file__))
TOOLS_ROOT = os.path.normpath(os.path.dirname(TESTS_ROOT))
sys.path.insert(0, TESTS_ROOT)
sys.path.insert(0, TOOLS_ROOT)

import mock_rtconfig
sys.modules['rtconfig'] = mock_rtconfig

import building
from preprocessor import SConsPreProcessorPatch, create_preprocessor_instance


class PreProcessorTests(unittest.TestCase):
    def test_patch_returns_scons_preprocessor_class(self):
        patch = SConsPreProcessorPatch()

        patched_class = patch.get_patched_preprocessor()

        self.assertTrue(hasattr(patched_class, 'start_handling_includes'))
        self.assertTrue(hasattr(patched_class, 'stop_handling_includes'))

    def test_preprocessor_handles_conditional_defines(self):
        preprocessor = create_preprocessor_instance()
        preprocessor.process_contents(
            '''
#define TEST_MACRO 1
#ifdef TEST_MACRO
#define ENABLED_FEATURE 1
#else
#define DISABLED_FEATURE 1
#endif
'''
        )

        namespace = preprocessor.cpp_namespace
        self.assertIn('TEST_MACRO', namespace)
        self.assertIn('ENABLED_FEATURE', namespace)
        self.assertNotIn('DISABLED_FEATURE', namespace)

    def test_building_uses_shared_preprocessor_factory(self):
        self.assertIs(building.create_preprocessor_instance, create_preprocessor_instance)


if __name__ == '__main__':
    unittest.main()
