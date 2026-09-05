#
# File      : keil.py
# This file is part of RT-Thread RTOS
# COPYRIGHT (C) 2006 - 2015, RT-Thread Development Team
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along
#  with this program; if not, write to the Free Software Foundation, Inc.,
#  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Change Logs:
# Date           Author       Notes
# 2015-01-20     Bernard      Add copyright information
#

import os
import re
import sys
import string
import shutil
import subprocess

import xml.etree.ElementTree as etree
from xml.etree.ElementTree import SubElement
from utils import _make_path_relative
from utils import xml_indent

fs_encoding = sys.getfilesystemencoding()


def _read_arm_compiler_info(platform, exec_path):
    """Read the product, component and tool versions from an Arm compiler."""
    if platform == 'armcc':
        command = [os.path.join(exec_path, 'armcc.exe')]
    elif platform == 'armclang':
        command = [os.path.join(exec_path, 'armclang.exe'), '--version']
    else:
        return None

    if not os.path.isfile(command[0]):
        return None

    try:
        child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = child.communicate()
    except OSError:
        return None

    output = stdout if stdout else stderr
    if not isinstance(output, str):
        output = output.decode('utf-8', errors='replace')

    info = {}
    for field in ('Product', 'Component', 'Tool'):
        match = re.search(r'^%s:\s*(.+?)\s*$' % field, output, re.MULTILINE | re.IGNORECASE)
        if match is None:
            return None
        info[field.lower()] = match.group(1).strip()

    return info


def _format_arm_compiler_descriptor(platform, compiler_info):
    """Convert compiler output to the descriptor stored in a uvprojx file."""
    component = compiler_info['component']
    version_match = re.search(r'(\d+)\.(\d+)', component)
    if version_match is None:
        return None

    major, minor = version_match.groups()
    version_match = re.search(
        r'(\d+\.\d+(?:\s+update\s+\d+)?(?:\s+\(build\s+\d+\))?)',
        component,
        re.IGNORECASE,
    )
    version_text = version_match.group(1) if version_match else '%s.%s' % (major, minor)

    if platform == 'armclang':
        version_code = '%d%02d0000' % (int(major), int(minor))
        compiler_name = 'ARMCLANG'
    elif platform == 'armcc':
        build_match = re.search(r'\(build\s+(\d+)\)', component, re.IGNORECASE)
        build = int(build_match.group(1)) if build_match else 0
        version_code = '%d%02d%04d' % (int(major), int(minor), build)
        compiler_name = 'ARMCC'
    else:
        return None

    return '%s::V%s::%s' % (version_code, version_text, compiler_name)


def ConfigureMDKCompiler(tree, platform, compiler_info=None):
    """Keep the uvprojx compiler selection consistent with the SCons target."""
    target = tree.find('Targets/Target')
    if target is None:
        raise ValueError('Invalid Keil project: Targets/Target is missing')

    use_armclang = platform == 'armclang'
    if not use_armclang and platform != 'armcc':
        return

    uac6 = target.find('uAC6')
    if uac6 is None:
        uac6 = SubElement(target, 'uAC6')
    uac6.text = '1' if use_armclang else '0'

    compiler_nodes = [
        node for node in (target.find('pCCUsed'), target.find('pArmCC'))
        if node is not None
    ]

    if compiler_info is None:
        import rtconfig
        compiler_info = _read_arm_compiler_info(platform, rtconfig.EXEC_PATH)

    if compiler_info is None:
        expected_compiler = 'ARMCLANG' if use_armclang else 'ARMCC'
        for compiler_node in compiler_nodes:
            compiler_family = (compiler_node.text or '').rsplit('::', 1)[-1].upper()
            if compiler_family in ('ARMCC', 'ARMCLANG') and compiler_family != expected_compiler:
                target.remove(compiler_node)
        return

    descriptor = _format_arm_compiler_descriptor(platform, compiler_info)
    if descriptor is None:
        return

    if not compiler_nodes:
        compiler_nodes.append(SubElement(target, 'pCCUsed'))
    for compiler_node in compiler_nodes:
        compiler_node.text = descriptor

def _get_filetype(fn):
    if fn.rfind('.cpp') != -1 or fn.rfind('.cxx') != -1:
        return 8

    if fn.rfind('.c') != -1 or fn.rfind('.C') != -1:
        return 1

    # assemble file type
    if fn.rfind('.s') != -1 or fn.rfind('.S') != -1:
        return 2

    # header type
    if fn.rfind('.h') != -1:
        return 5

    if fn.rfind('.lib') != -1:
        return 4

    if fn.rfind('.o') != -1:
        return 3

    # other filetype
    return 5

def MDK4AddGroupForFN(ProjectFiles, parent, name, filename, project_path):
    group = SubElement(parent, 'Group')
    group_name = SubElement(group, 'GroupName')
    group_name.text = name

    name = os.path.basename(filename)
    path = os.path.dirname (filename)

    basename = os.path.basename(path)
    path = _make_path_relative(project_path, path)
    path = os.path.join(path, name)
    files = SubElement(group, 'Files')
    file = SubElement(files, 'File')
    file_name = SubElement(file, 'FileName')
    name = os.path.basename(path)

    if name.find('.cpp') != -1:
        obj_name = name.replace('.cpp', '.o')
    elif name.find('.c') != -1:
        obj_name = name.replace('.c', '.o')
    elif name.find('.s') != -1:
        obj_name = name.replace('.s', '.o')
    elif name.find('.S') != -1:
        obj_name = name.replace('.s', '.o')
    else:
        obj_name = name

    if ProjectFiles.count(obj_name):
        name = basename + '_' + name
    ProjectFiles.append(obj_name)
    try: # python 2
        file_name.text = name.decode(fs_encoding)
    except: # python 3
        file_name.text = name
    file_type = SubElement(file, 'FileType')
    file_type.text = '%d' % _get_filetype(name)
    file_path = SubElement(file, 'FilePath')
    try: # python 2
        file_path.text = path.decode(fs_encoding)
    except: # python 3
        file_path.text = path


    return group

def MDK4AddLibToGroup(ProjectFiles, group, name, filename, project_path):
    name = os.path.basename(filename)
    path = os.path.dirname (filename)

    basename = os.path.basename(path)
    path = _make_path_relative(project_path, path)
    path = os.path.join(path, name)
    files = SubElement(group, 'Files')
    file = SubElement(files, 'File')
    file_name = SubElement(file, 'FileName')
    name = os.path.basename(path)

    if name.find('.cpp') != -1:
        obj_name = name.replace('.cpp', '.o')
    elif name.find('.c') != -1:
        obj_name = name.replace('.c', '.o')
    elif name.find('.s') != -1:
        obj_name = name.replace('.s', '.o')
    elif name.find('.S') != -1:
        obj_name = name.replace('.s', '.o')
    else:
        obj_name = name

    if ProjectFiles.count(obj_name):
        name = basename + '_' + name
    ProjectFiles.append(obj_name)
    try:
        file_name.text = name.decode(fs_encoding)
    except:
        file_name.text = name
    file_type = SubElement(file, 'FileType')
    file_type.text = '%d' % _get_filetype(name)
    file_path = SubElement(file, 'FilePath')

    try:
        file_path.text = path.decode(fs_encoding)
    except:
        file_path.text = path

    return group

def MDK4AddGroup(ProjectFiles, parent, name, files, project_path, group_scons):
    # don't add an empty group
    if len(files) == 0:
        return

    group = SubElement(parent, 'Group')
    group_name = SubElement(group, 'GroupName')
    group_name.text = name

    for f in files:
        fn = f.rfile()
        name = fn.name
        path = os.path.dirname(fn.abspath)

        basename = os.path.basename(path)
        path = _make_path_relative(project_path, path)
        path = os.path.join(path, name)

        files = SubElement(group, 'Files')
        file = SubElement(files, 'File')
        file_name = SubElement(file, 'FileName')
        name = os.path.basename(path)

        if name.find('.cpp') != -1:
            obj_name = name.replace('.cpp', '.o')
        elif name.find('.c') != -1:
            obj_name = name.replace('.c', '.o')
        elif name.find('.s') != -1:
            obj_name = name.replace('.s', '.o')
        elif name.find('.S') != -1:
            obj_name = name.replace('.s', '.o')

        if ProjectFiles.count(obj_name):
            name = basename + '_' + name
        ProjectFiles.append(obj_name)
        file_name.text = name # name.decode(fs_encoding)
        file_type = SubElement(file, 'FileType')
        file_type.text = '%d' % _get_filetype(name)
        file_path = SubElement(file, 'FilePath')
        file_path.text = path # path.decode(fs_encoding)

        # for local LOCAL_CFLAGS/LOCAL_CXXFLAGS/LOCAL_CCFLAGS/LOCAL_CPPPATH/LOCAL_CPPDEFINES
        MiscControls_text = ' '
        if file_type.text == '1' and 'LOCAL_CFLAGS' in group_scons:
            MiscControls_text = MiscControls_text + group_scons['LOCAL_CFLAGS']
        elif file_type.text == '8' and 'LOCAL_CXXFLAGS' in group_scons:
            MiscControls_text = MiscControls_text + group_scons['LOCAL_CXXFLAGS']
        if 'LOCAL_CCFLAGS' in group_scons:
            MiscControls_text = MiscControls_text + group_scons['LOCAL_CCFLAGS']
        if (MiscControls_text != ' '
                or 'LOCAL_CPPDEFINES' in group_scons
                or 'LOCAL_CPPPATH' in group_scons):
            FileOption     = SubElement(file,  'FileOption')
            FileArmAds     = SubElement(FileOption, 'FileArmAds')
            Cads            = SubElement(FileArmAds, 'Cads')
            VariousControls = SubElement(Cads, 'VariousControls')
            MiscControls    = SubElement(VariousControls, 'MiscControls')
            MiscControls.text = MiscControls_text
            Define          = SubElement(VariousControls, 'Define')
            if 'LOCAL_CPPDEFINES' in group_scons:
                Define.text     = ', '.join(set(group_scons['LOCAL_CPPDEFINES']))
            else:
                Define.text     = ' '
            Undefine        = SubElement(VariousControls, 'Undefine')
            Undefine.text   = ' '
            IncludePath     = SubElement(VariousControls, 'IncludePath')
            if 'LOCAL_CPPPATH' in group_scons:
                IncludePath.text = ';'.join([_make_path_relative(project_path, os.path.normpath(i)) for i in group_scons['LOCAL_CPPPATH']])
            else:
                IncludePath.text = ' '

    return group

# The common part of making MDK4/5 project
def MDK45Project(env, tree, target, script):
    project_path = os.path.dirname(os.path.abspath(target))

    root = tree.getroot()
    out = open(target, 'w')
    out.write('<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n')

    CPPPATH = []
    CPPDEFINES = env.get('CPPDEFINES', [])
    LINKFLAGS = ''
    CXXFLAGS = ''
    CCFLAGS = ''
    CFLAGS = ''
    ProjectFiles = []

    # add group
    groups = tree.find('Targets/Target/Groups')
    if groups is None:
        groups = SubElement(tree.find('Targets/Target'), 'Groups')
    groups.clear() # clean old groups
    for group in script:
        group_tree = MDK4AddGroup(ProjectFiles, groups, group['name'], group['src'], project_path, group)

        # get each include path
        if 'CPPPATH' in group and group['CPPPATH']:
            if CPPPATH:
                CPPPATH += group['CPPPATH']
            else:
                CPPPATH += group['CPPPATH']

        # get each group's link flags
        if 'LINKFLAGS' in group and group['LINKFLAGS']:
            if LINKFLAGS:
                LINKFLAGS += ' ' + group['LINKFLAGS']
            else:
                LINKFLAGS += group['LINKFLAGS']

        # get each group's CXXFLAGS flags
        if 'CXXFLAGS' in group and group['CXXFLAGS']:
            if CXXFLAGS:
                CXXFLAGS += ' ' + group['CXXFLAGS']
            else:
                CXXFLAGS += group['CXXFLAGS']

        # get each group's CCFLAGS flags
        if 'CCFLAGS' in group and group['CCFLAGS']:
            if CCFLAGS:
                CCFLAGS += ' ' + group['CCFLAGS']
            else:
                CCFLAGS += group['CCFLAGS']

        # get each group's CFLAGS flags
        if 'CFLAGS' in group and group['CFLAGS']:
            if CFLAGS:
                CFLAGS += ' ' + group['CFLAGS']
            else:
                CFLAGS += group['CFLAGS']

        # get each group's LIBS flags
        if 'LIBS' in group and group['LIBS']:
            for item in group['LIBPATH']:
                full_path = os.path.join(item, group['name'] + '.lib')
                if os.path.isfile(full_path): # has this library
                    if group_tree != None:
                        MDK4AddLibToGroup(ProjectFiles, group_tree, group['name'], full_path, project_path)
                    else:
                        group_tree = MDK4AddGroupForFN(ProjectFiles, groups, group['name'], full_path, project_path)

    # write include path, definitions and link flags
    IncludePath = tree.find('Targets/Target/TargetOption/TargetArmAds/Cads/VariousControls/IncludePath')
    IncludePath.text = ';'.join([_make_path_relative(project_path, os.path.normpath(i)) for i in set(CPPPATH)])

    Define = tree.find('Targets/Target/TargetOption/TargetArmAds/Cads/VariousControls/Define')
    Define.text = ', '.join(set(CPPDEFINES))

    if 'c99' in CXXFLAGS or 'c99' in CCFLAGS or 'c99' in CFLAGS:
        uC99 = tree.find('Targets/Target/TargetOption/TargetArmAds/Cads/uC99')
        uC99.text = '1'

    if 'gnu' in CXXFLAGS or 'gnu' in CCFLAGS or 'gnu' in CFLAGS:
        uGnu = tree.find('Targets/Target/TargetOption/TargetArmAds/Cads/uGnu')
        uGnu.text = '1'

    Misc = tree.find('Targets/Target/TargetOption/TargetArmAds/LDads/Misc')
    Misc.text = LINKFLAGS

    xml_indent(root)
    out.write(etree.tostring(root, encoding='utf-8').decode())
    out.close()

def MDK4Project(env, target, script):

    if os.path.isfile('template.uvproj') is False:
        print ('Warning: The template project file [template.uvproj] not found!')
        return

    template_tree = etree.parse('template.uvproj')

    MDK45Project(env, template_tree, target, script)

    # remove project.uvopt file
    project_uvopt = os.path.abspath(target).replace('uvproj', 'uvopt')
    if os.path.isfile(project_uvopt):
        os.unlink(project_uvopt)

    # copy uvopt file
    if os.path.exists('template.uvopt'):
        import shutil
        shutil.copy2('template.uvopt', '{}.uvopt'.format(os.path.splitext(target)[0]))
import threading
import time
def monitor_log_file(log_file_path):
    if not os.path.exists(log_file_path):
        open(log_file_path, 'w').close()
    empty_line_count = 0
    with open(log_file_path, 'r') as log_file:
        while True:
            line = log_file.readline()
            if line:
                print(line.strip())
                if 'Build Time Elapsed' in line:
                    break
                empty_line_count = 0
            else:
                empty_line_count += 1
                time.sleep(1)
            if empty_line_count > 30:
                print("Timeout reached or too many empty lines, exiting log monitoring thread.")
                break
def MDK5Project(env, target, script):

    if os.path.isfile('template.uvprojx') is False:
        print ('Warning: The template project file [template.uvprojx] not found!')
        return

    template_tree = etree.parse('template.uvprojx')

    import rtconfig
    ConfigureMDKCompiler(template_tree, rtconfig.PLATFORM)

    MDK45Project(env, template_tree, target, script)

    # remove project.uvopt file
    project_uvopt = os.path.abspath(target).replace('uvprojx', 'uvoptx')
    if os.path.isfile(project_uvopt):
        os.unlink(project_uvopt)
    # copy uvopt file
    if os.path.exists('template.uvoptx'):
        import shutil
        shutil.copy2('template.uvoptx', '{}.uvoptx'.format(os.path.splitext(target)[0]))
        # build with UV4.exe

        if shutil.which('UV4.exe') is not None:
            target_name = template_tree.find('Targets/Target/TargetName')
            print('target_name:', target_name.text)
            log_file_path = 'keil.log'
            if os.path.exists(log_file_path):
                os.remove(log_file_path)
            log_thread = threading.Thread(target=monitor_log_file, args=(log_file_path,))
            log_thread.start()
            cmd = ['UV4.exe', '-b', os.path.abspath(target), '-q', '-j0',
                   '-t', target_name.text, '-o', log_file_path]
            print('Start to build keil project')
            print(subprocess.list2cmdline(cmd))
            subprocess.call(cmd)
        else:
            print('UV4.exe is not available, please check your keil installation')

def MDK2Project(env, target, script):
    template = open(os.path.join(os.path.dirname(__file__), 'template.Uv2'), 'r')
    lines = template.readlines()

    project = open(target, "w")
    project_path = os.path.dirname(os.path.abspath(target))

    line_index = 5
    # write group
    for group in script:
        lines.insert(line_index, 'Group (%s)\r\n' % group['name'])
        line_index += 1

    lines.insert(line_index, '\r\n')
    line_index += 1

    # write file

    ProjectFiles = []
    CPPPATH = []
    CPPDEFINES = env.get('CPPDEFINES', [])
    LINKFLAGS = ''
    CFLAGS = ''

    # number of groups
    group_index = 1
    for group in script:
        # print group['name']

        # get each include path
        if 'CPPPATH' in group and group['CPPPATH']:
            if CPPPATH:
                CPPPATH += group['CPPPATH']
            else:
                CPPPATH += group['CPPPATH']

        # get each group's link flags
        if 'LINKFLAGS' in group and group['LINKFLAGS']:
            if LINKFLAGS:
                LINKFLAGS += ' ' + group['LINKFLAGS']
            else:
                LINKFLAGS += group['LINKFLAGS']

        # generate file items
        for node in group['src']:
            fn = node.rfile()
            name = fn.name
            path = os.path.dirname(fn.abspath)
            basename = os.path.basename(path)
            path = _make_path_relative(project_path, path)
            path = os.path.join(path, name)
            if ProjectFiles.count(name):
                name = basename + '_' + name
            ProjectFiles.append(name)
            lines.insert(line_index, 'File %d,%d,<%s><%s>\r\n'
                % (group_index, _get_filetype(name), path, name))
            line_index += 1

        group_index = group_index + 1

    lines.insert(line_index, '\r\n')
    line_index += 1

    # remove repeat path
    paths = set()
    for path in CPPPATH:
        inc = _make_path_relative(project_path, os.path.normpath(path))
        paths.add(inc) #.replace('\\', '/')

    paths = [i for i in paths]
    CPPPATH = string.join(paths, ';')

    definitions = [i for i in set(CPPDEFINES)]
    CPPDEFINES = string.join(definitions, ', ')

    while line_index < len(lines):
        if lines[line_index].startswith(' ADSCINCD '):
            lines[line_index] = ' ADSCINCD (' + CPPPATH + ')\r\n'

        if lines[line_index].startswith(' ADSLDMC ('):
            lines[line_index] = ' ADSLDMC (' + LINKFLAGS + ')\r\n'

        if lines[line_index].startswith(' ADSCDEFN ('):
            lines[line_index] = ' ADSCDEFN (' + CPPDEFINES + ')\r\n'

        line_index += 1

    # write project
    for line in lines:
        project.write(line)

    project.close()

def ARMCC_Version():
    import rtconfig

    compiler_info = _read_arm_compiler_info(rtconfig.PLATFORM, rtconfig.EXEC_PATH)
    if compiler_info is None:
        return "0.0"

    return '%s/%s/%s' % (
        compiler_info['product'],
        compiler_info['component'],
        compiler_info['tool'],
    )
