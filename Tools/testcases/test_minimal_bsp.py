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


KEIL_TEMPLATE = '''<?xml version="1.0" encoding="UTF-8"?>
<Project>
  <Targets>
    <Target>
      <TargetName>rt-thread</TargetName>
      <pCCUsed>5060750::V5.06 update 7 (build 960)::ARMCC</pCCUsed>
      <uAC6>0</uAC6>
      <TargetOption>
        <TargetArmAds>
          <Cads>
            <uC99>0</uC99>
            <uGnu>0</uGnu>
            <VariousControls>
              <IncludePath/>
              <Define/>
            </VariousControls>
          </Cads>
          <LDads><Misc/></LDads>
        </TargetArmAds>
      </TargetOption>
      <Groups/>
    </Target>
  </Targets>
</Project>
'''


class SourceNode:
    def __init__(self, path):
        self.abspath = path
        self.name = os.path.basename(path)

    def rfile(self):
        return self


class MinimalBspTests(unittest.TestCase):
    def test_minimal_bsp_generates_mdk5_mdk6_and_iar_projects(self):
        with tempfile.TemporaryDirectory(prefix='RT Thread Minimal BSP ') as temp_root:
            bsp_root = os.path.join(temp_root, 'BSP Root')
            source_root = os.path.join(bsp_root, 'applications')
            include_root = os.path.join(bsp_root, 'include')
            os.makedirs(source_root)
            os.makedirs(include_root)

            source_path = os.path.join(source_root, 'main.c')
            with open(source_path, 'w', encoding='utf-8') as source_file:
                source_file.write('int main(void) { return 0; }\n')
            with open(os.path.join(bsp_root, 'template.uvprojx'), 'w', encoding='utf-8') as template:
                template.write(KEIL_TEMPLATE)
            with open(os.path.join(bsp_root, 'template.ewp'), 'w', encoding='utf-8') as template:
                template.write('<project/>\n')

            env = {
                'CPPDEFINES': ['RT_USING_MINIMAL_BSP'],
                'CPPPATH': [include_root],
                'CFLAGS': '',
                'CXXFLAGS': '',
                'CCFLAGS': '',
                'LINKFLAGS': '',
            }
            projects = [
                {
                    'name': 'Applications',
                    'src': [SourceNode(source_path)],
                    'CPPPATH': [include_root],
                },
            ]

            previous_directory = os.getcwd()
            try:
                os.chdir(bsp_root)
                self._generate_target('mdk5', 'armcc', env, projects)
                self._generate_target('mdk6', 'armclang', env, projects)
                self._generate_target('iar', 'iccarm', env, projects)
            finally:
                os.chdir(previous_directory)

            mdk5_path = os.path.join(bsp_root, 'MDK5-ARM', 'project.uvprojx')
            mdk6_path = os.path.join(bsp_root, 'MDK6-ARM', 'project.uvprojx')
            iar_path = os.path.join(bsp_root, 'EWARM', 'project.ewp')
            workspace_path = os.path.join(bsp_root, 'EWARM', 'project.eww')

            for project_path in (mdk5_path, mdk6_path, iar_path, workspace_path):
                with self.subTest(project_path=project_path):
                    self.assertTrue(os.path.isfile(project_path))

            self.assertEqual(
                etree.parse(mdk5_path).findtext('Targets/Target/uAC6'),
                '0',
            )
            self.assertEqual(
                etree.parse(mdk6_path).findtext('Targets/Target/uAC6'),
                '1',
            )

            with open(mdk5_path, 'r', encoding='utf-8') as project_file:
                mdk5_xml = project_file.read()
            with open(iar_path, 'r', encoding='utf-8') as project_file:
                iar_xml = project_file.read()
            self.assertIn('main.c', mdk5_xml)
            self.assertIn('main.c', iar_xml)
            self.assertNotIn(temp_root, mdk5_xml)
            self.assertNotIn(temp_root, iar_xml)

    def _generate_target(self, target_name, platform, env, projects):
        def get_option(option_name):
            if option_name == 'target':
                return target_name
            return None

        with mock.patch.object(building, 'GetOption', side_effect=get_option), \
                mock.patch.object(building, 'Env', env), \
                mock.patch.object(building, 'Projects', projects), \
                mock.patch.object(mock_rtconfig, 'PLATFORM', platform), \
                mock.patch.object(mock_rtconfig, 'EXEC_PATH', os.path.join('missing', 'toolchain')), \
                mock.patch('builtins.print'):
            building.GenTargetProject()


if __name__ == '__main__':
    unittest.main()
