#!/usr/bin/env python3

import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as etree
from unittest import mock


TESTS_ROOT = os.path.dirname(os.path.abspath(__file__))
TOOLS_ROOT = os.path.normpath(os.path.dirname(TESTS_ROOT))
sys.path.insert(0, TESTS_ROOT)
sys.path.insert(0, TOOLS_ROOT)

import mock_rtconfig
sys.modules['rtconfig'] = mock_rtconfig

import building
from targets import keil


ARMCC_INFO = {
    'product': 'MDK Professional 5.42',
    'component': 'ARM Compiler 5.06 update 7 (build 960)',
    'tool': 'armcc [4d365d]',
}

ARMCLANG_INFO = {
    'product': 'MDK Professional 5.42',
    'component': 'Arm Compiler for Embedded 6.23',
    'tool': 'armclang [5f103000]',
}


class SourceNode:
    def __init__(self, path):
        self.abspath = path
        self.name = os.path.basename(path)

    def rfile(self):
        return self


def make_project_tree(descriptor, use_armclang):
    return etree.ElementTree(etree.fromstring(
        '<Project><Targets><Target>'
        '<pCCUsed>%s</pCCUsed><uAC6>%s</uAC6>'
        '</Target></Targets></Project>' % (descriptor, use_armclang)
    ))


class MDKToolchainTests(unittest.TestCase):
    def test_mdk_targets_select_separate_compiler_families(self):
        self.assertEqual(building.TARGET_TOOLCHAINS['mdk5'], ('keil', 'armcc'))
        self.assertEqual(building.TARGET_TOOLCHAINS['mdk6'], ('armclang', 'armclang'))

    def test_mdk6_converts_an_armcc_template_to_armclang(self):
        tree = make_project_tree(
            '5060750::V5.06 update 6 (build 750)::ARMCC',
            '0',
        )

        keil.ConfigureMDKCompiler(tree, 'armclang', ARMCLANG_INFO)

        self.assertEqual(tree.findtext('Targets/Target/uAC6'), '1')
        self.assertEqual(
            tree.findtext('Targets/Target/pCCUsed'),
            '6230000::V6.23::ARMCLANG',
        )

    def test_mdk5_converts_an_armclang_template_to_armcc(self):
        tree = make_project_tree('6230000::V6.23::ARMCLANG', '1')

        keil.ConfigureMDKCompiler(tree, 'armcc', ARMCC_INFO)

        self.assertEqual(tree.findtext('Targets/Target/uAC6'), '0')
        self.assertEqual(
            tree.findtext('Targets/Target/pCCUsed'),
            '5060960::V5.06 update 7 (build 960)::ARMCC',
        )

    def test_compiler_selection_is_updated_without_version_detection(self):
        tree = make_project_tree(
            '5060750::V5.06 update 6 (build 750)::ARMCC',
            '0',
        )

        with mock.patch.object(keil, '_read_arm_compiler_info', return_value=None):
            keil.ConfigureMDKCompiler(tree, 'armclang')

        self.assertEqual(tree.findtext('Targets/Target/uAC6'), '1')
        self.assertIsNone(tree.find('Targets/Target/pCCUsed'))

    def test_armcc_version_keeps_complete_fields(self):
        with mock.patch.object(keil, '_read_arm_compiler_info', return_value=ARMCC_INFO):
            self.assertEqual(
                keil.ARMCC_Version(),
                'MDK Professional 5.42/'
                'ARM Compiler 5.06 update 7 (build 960)/'
                'armcc [4d365d]',
            )

    def test_armclang_version_keeps_complete_fields(self):
        with mock.patch.object(keil, '_read_arm_compiler_info', return_value=ARMCLANG_INFO):
            self.assertEqual(
                keil.ARMCC_Version(),
                'MDK Professional 5.42/'
                'Arm Compiler for Embedded 6.23/'
                'armclang [5f103000]',
            )

    def test_local_include_path_is_emitted_without_other_local_options(self):
        with tempfile.TemporaryDirectory() as temp_root:
            project_path = os.path.join(temp_root, 'MDK5-ARM')
            source_path = os.path.join(temp_root, 'drivers', 'drv_can.c')
            include_path = os.path.join(temp_root, 'drivers', 'include')
            groups = etree.Element('Groups')

            keil.MDK4AddGroup(
                [],
                groups,
                'Drivers',
                [SourceNode(source_path)],
                project_path,
                {'LOCAL_CPPPATH': [include_path]},
            )

            generated_path = groups.findtext(
                'Group/Files/File/FileOption/FileArmAds/Cads/'
                'VariousControls/IncludePath'
            )
            self.assertEqual(
                os.path.normpath(generated_path),
                os.path.normpath(os.path.relpath(include_path, project_path)),
            )


if __name__ == '__main__':
    unittest.main()
