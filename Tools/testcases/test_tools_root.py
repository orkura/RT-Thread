#!/usr/bin/env python3

import os
import sys
import tempfile
import unittest
from unittest import mock


TESTS_ROOT = os.path.dirname(os.path.abspath(__file__))
EXPECTED_TOOLS_ROOT = os.path.normpath(os.path.dirname(TESTS_ROOT))
sys.path.insert(0, TESTS_ROOT)
sys.path.insert(0, EXPECTED_TOOLS_ROOT)

import mock_rtconfig
sys.modules['rtconfig'] = mock_rtconfig

import building
import mkdist
from targets import makefile as makefile_target
from targets.xmake import XmakeProject
from utils import TOOLS_ROOT, get_tools_root


class ToolsRootTests(unittest.TestCase):
    def test_default_root_is_tools_directory(self):
        self.assertEqual(TOOLS_ROOT, EXPECTED_TOOLS_ROOT)
        self.assertEqual(building.TOOLS_ROOT, EXPECTED_TOOLS_ROOT)
        self.assertEqual(get_tools_root(), EXPECTED_TOOLS_ROOT)

    def test_environment_root_takes_precedence(self):
        configured_root = os.path.join(TESTS_ROOT, '..', 'custom-tools')
        expected_root = os.path.normpath(os.path.abspath(configured_root))

        self.assertEqual(
            get_tools_root({'TOOLS_ROOT': configured_root}),
            expected_root,
        )

    def test_empty_environment_root_uses_default(self):
        self.assertEqual(get_tools_root({'TOOLS_ROOT': ''}), EXPECTED_TOOLS_ROOT)

    def test_makefile_uses_independent_tools_root(self):
        self.assertIn('include $(TOOLS_ROOT)/rtthread.mk', makefile_target.makefile)
        self.assertNotIn('include $(RTT_ROOT)/tools/rtthread.mk', makefile_target.makefile)

    def test_distribution_copies_tools_from_configured_root(self):
        configured_root = os.path.join(TESTS_ROOT, 'configured-tools')
        rtt_root = os.path.join(TESTS_ROOT, 'RT-Thread Kernel')
        destination = os.path.join('dist', 'rt-thread', 'tools')

        with mock.patch.object(mkdist, 'bsp_copy_files'), \
                mock.patch.object(mkdist, 'do_copy_folder') as copy_folder, \
                mock.patch.object(mkdist, 'do_copy_file'), \
                mock.patch.object(mkdist, 'bsp_update_sconstruct'), \
                mock.patch.object(mkdist, 'bsp_update_kconfig'), \
                mock.patch.object(mkdist, 'bsp_update_kconfig_library'), \
                mock.patch.object(mkdist, 'bsp_update_kconfig_testcases'), \
                mock.patch.object(mkdist, 'GetOption', return_value=None), \
                mock.patch.object(mock_rtconfig, 'ARCH', 'arm', create=True), \
                mock.patch('builtins.print'):
            mkdist.MkDist(
                program=None,
                BSP_ROOT='bsp',
                RTT_ROOT=rtt_root,
                Env={'TOOLS_ROOT': configured_root},
                project_name='project',
                project_path='dist',
            )

        copy_folder.assert_any_call(
            os.path.abspath(configured_root),
            destination,
            mock.ANY,
        )
        copy_folder.assert_any_call(
            os.path.join(rtt_root, 'components'),
            os.path.join('dist', 'rt-thread', 'components'),
        )
        self.assertNotEqual(
            os.path.abspath(configured_root),
            os.path.abspath(rtt_root),
        )

    def test_xmake_reads_template_from_tools_and_writes_to_bsp(self):
        with tempfile.TemporaryDirectory() as temp_root:
            tools_root = os.path.join(temp_root, 'Tools')
            targets_root = os.path.join(tools_root, 'targets')
            bsp_root = os.path.join(temp_root, 'BSP with spaces')
            os.makedirs(targets_root)
            os.makedirs(bsp_root)

            template_path = os.path.join(targets_root, 'xmake.lua')
            template = 'set_target("$target")\n'
            with open(template_path, 'w', encoding='utf-8') as template_file:
                template_file.write(template)

            project = XmakeProject(
                {'TOOLS_ROOT': tools_root, 'BSP_ROOT': bsp_root},
                [],
            )
            project.generate_xmake_file()

            output_path = os.path.join(bsp_root, 'xmake.lua')
            with open(output_path, 'r', encoding='utf-8') as output_file:
                self.assertEqual(output_file.read(), 'set_target("rt-thread")\n')
            with open(template_path, 'r', encoding='utf-8') as template_file:
                self.assertEqual(template_file.read(), template)


if __name__ == '__main__':
    unittest.main()
