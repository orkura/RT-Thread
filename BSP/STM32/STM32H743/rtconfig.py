import os

from toolchain_config import TOOLCHAIN_PATHS

# toolchains options
ARCH='arm'
# STM32H743 uses a Cortex-M7 core with an FPv5 double-precision FPU.
CPU='cortex-m7'
CROSS_TOOL='gcc'

# bsp lib config
BSP_LIBRARY_TYPE = None

if os.getenv('RTT_CC'):
    CROSS_TOOL = os.getenv('RTT_CC')

# cross_tool provides the cross compiler
# EXEC_PATH is the compiler execute path, for example, CodeSourcery, Keil MDK, IAR
if CROSS_TOOL == 'gcc':
    PLATFORM    = 'gcc'
elif CROSS_TOOL == 'keil':
    PLATFORM    = 'armcc'
elif CROSS_TOOL == 'armclang':
    PLATFORM    = 'armclang'
elif CROSS_TOOL == 'iar':
    PLATFORM    = 'iccarm'
else:
    raise ValueError('Unsupported toolchain: ' + CROSS_TOOL)

EXEC_PATH = os.getenv('RTT_EXEC_PATH', TOOLCHAIN_PATHS.get(PLATFORM, ''))

LINK_SCRIPT = {
    'gcc': 'Board/LinkerScripts/GCC/LinkerScripts.ld',
    'armcc': 'Board/LinkerScripts/MDK-ARM/LinkerScripts.sct',
    'armclang': 'Board/LinkerScripts/MDK-ARM/LinkerScripts.sct',
    'iccarm': 'Board/LinkerScripts/EWARM/LinkerScripts.icf',
}[PLATFORM]

# Keep artifacts from different build systems isolated and easy to identify.
BUILD_OUTPUT_DIR = os.path.join('Build', 'scons')
MAP_FILE = os.path.join(BUILD_OUTPUT_DIR, 'rt-thread.map').replace(os.sep, '/')
BINARY_FILE = os.path.join(BUILD_OUTPUT_DIR, 'rtthread.bin').replace(os.sep, '/')

BUILD = 'debug'

if PLATFORM == 'gcc':
    # toolchains
    PREFIX = 'arm-none-eabi-'
    CC = PREFIX + 'gcc'
    AS = PREFIX + 'gcc'
    AR = PREFIX + 'ar'
    CXX = PREFIX + 'g++'
    LINK = PREFIX + 'gcc'
    TARGET_EXT = 'elf'
    SIZE = PREFIX + 'size'
    OBJDUMP = PREFIX + 'objdump'
    OBJCPY = PREFIX + 'objcopy'

     # Keep the CPU, FPU, and hard-float ABI consistent across all build stages.
    DEVICE = ' -mcpu=cortex-m7 -mthumb -mfpu=fpv5-d16 -mfloat-abi=hard -ffunction-sections -fdata-sections'
    CFLAGS = DEVICE
    CFLAGS += ' -Wall'
    AFLAGS = ' -c' + DEVICE + ' -x assembler-with-cpp -Wa,-mimplicit-it=thumb '
    LFLAGS = DEVICE + ' -Wl,--gc-sections,-Map=' + MAP_FILE + ',-cref,-u,Reset_Handler -T "' + LINK_SCRIPT + '"'

    CPATH = ''
    LPATH = ''

    if BUILD == 'debug':
        CFLAGS += ' -O0 -gdwarf-2 -g'
        AFLAGS += ' -gdwarf-2'
    else:
        CFLAGS += ' -O2'

    CXXFLAGS = CFLAGS
    # A missing declaration in C can silently select an invalid ABI; always
    # reject it even while other warnings remain non-fatal.
    CFLAGS += ' -Werror=implicit-function-declaration'

    POST_ACTION = OBJCPY + ' -O binary $TARGET "' + BINARY_FILE + '"\n' + SIZE + ' $TARGET \n'

elif PLATFORM == 'armcc':
    # toolchains
    CC = 'armcc'
    CXX = 'armcc'
    AS = 'armasm'
    AR = 'armar'
    LINK = 'armlink'
    TARGET_EXT = 'axf'

    DEVICE = ' --cpu Cortex-M7.fp.dp '
    CFLAGS = '-c ' + DEVICE + ' --apcs=interwork --c99'
    AFLAGS = DEVICE + ' --apcs=interwork '
    LFLAGS = DEVICE + ' --scatter "' + LINK_SCRIPT + '" --info sizes --info totals --info unused --info veneers --list "' + MAP_FILE + '" --strict'
    if EXEC_PATH:
        ARMCC_ROOT = os.path.dirname(os.path.normpath(EXEC_PATH))
        CFLAGS += ' -I' + os.path.join(ARMCC_ROOT, 'include')
        LFLAGS += ' --libpath=' + os.path.join(ARMCC_ROOT, 'lib')

    CFLAGS += ' -D__MICROLIB '
    AFLAGS += ' --pd "__MICROLIB SETA 1" '
    LFLAGS += ' --library_type=microlib '
    if BUILD == 'debug':
        CFLAGS += ' -g -O0'
        AFLAGS += ' -g'
    else:
        CFLAGS += ' -O2'

    CXXFLAGS = CFLAGS 
    CFLAGS += ' -std=c99'

    POST_ACTION = 'fromelf --bin $TARGET --output "' + BINARY_FILE + '" \nfromelf -z $TARGET'

elif PLATFORM == 'armclang':
    # toolchains
    CC = 'armclang'
    CXX = 'armclang'
    AS = 'armasm'
    AR = 'armar'
    LINK = 'armlink'
    TARGET_EXT = 'axf'

    DEVICE = ' --cpu Cortex-M7.fp.dp '
    CFLAGS = ' --target=arm-arm-none-eabi -mcpu=cortex-m7 '
    CFLAGS += ' -mfpu=fpv5-d16 '
    CFLAGS += ' -mfloat-abi=hard -c -fno-rtti -funsigned-char -fshort-enums -fshort-wchar '
    CFLAGS += ' -gdwarf-3 -ffunction-sections '
    AFLAGS = DEVICE + ' --apcs=interwork '
    LFLAGS = DEVICE + ' --info sizes --info totals --info unused --info veneers '
    LFLAGS += ' --list "' + MAP_FILE + '" '
    LFLAGS += ' --strict --scatter "' + LINK_SCRIPT + '" '
    if EXEC_PATH:
        ARMCLANG_ROOT = os.path.dirname(os.path.normpath(EXEC_PATH))
        CFLAGS += ' -I' + os.path.join(ARMCLANG_ROOT, 'include')
        LFLAGS += ' --libpath=' + os.path.join(ARMCLANG_ROOT, 'lib')

    if BUILD == 'debug':
        CFLAGS += ' -g -O1' # armclang recommend
        AFLAGS += ' -g'
    else:
        CFLAGS += ' -O2'
        
    CXXFLAGS = CFLAGS
    CFLAGS += ' -std=c99'

    POST_ACTION = 'fromelf --bin $TARGET --output "' + BINARY_FILE + '" \nfromelf -z $TARGET'

elif PLATFORM == 'iccarm':
    # toolchains
    CC = 'iccarm'
    CXX = 'iccarm'
    AS = 'iasmarm'
    AR = 'iarchive'
    LINK = 'ilinkarm'
    TARGET_EXT = 'out'

    DEVICE = '-Dewarm'

    CFLAGS = DEVICE
    CFLAGS += ' --diag_suppress Pa050'
    CFLAGS += ' --no_cse'
    CFLAGS += ' --no_unroll'
    CFLAGS += ' --no_inline'
    CFLAGS += ' --no_code_motion'
    CFLAGS += ' --no_tbaa'
    CFLAGS += ' --no_clustering'
    CFLAGS += ' --no_scheduling'
    CFLAGS += ' --endian=little'
    CFLAGS += ' --cpu=Cortex-M7'
    CFLAGS += ' -e'
    CFLAGS += ' --fpu=VFPv5_d16'
    if EXEC_PATH:
        IAR_ARM_ROOT = os.path.dirname(os.path.normpath(EXEC_PATH))
        CFLAGS += ' --dlib_config "' + os.path.join(IAR_ARM_ROOT, 'INC', 'c', 'DLib_Config_Normal.h') + '"'
    CFLAGS += ' --silent'

    AFLAGS = DEVICE
    AFLAGS += ' -s+'
    AFLAGS += ' -w+'
    AFLAGS += ' -r'
    AFLAGS += ' --cpu Cortex-M7'
    AFLAGS += ' --fpu VFPv5_d16'
    AFLAGS += ' -S'

    if BUILD == 'debug':
        CFLAGS += ' --debug'
        CFLAGS += ' -On'
    else:
        CFLAGS += ' -Oh'

    LFLAGS = ' --config "' + LINK_SCRIPT + '"'
    LFLAGS += ' --entry __iar_program_start'

    CXXFLAGS = CFLAGS
    
    POST_ACTION = 'ielftool --bin $TARGET "' + BINARY_FILE + '"'
