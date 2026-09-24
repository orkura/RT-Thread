#ifndef RT_CONFIG_H__
#define RT_CONFIG_H__

#define SOC_FAMILY_STM32
#define SOC_SERIES_STM32H7
#define SOC_STM32H743VI

/* Application */

/* Debug */

#define BSP_USING_FDCAN2_DEBUG
/* end of Debug */

/* RT-Thread Kernel */

/* klibc options */

/* rt_vsnprintf options */

/* end of rt_vsnprintf options */

/* rt_vsscanf options */

/* end of rt_vsscanf options */

/* rt_memset options */

/* end of rt_memset options */

/* rt_memcpy options */

/* end of rt_memcpy options */

/* rt_memmove options */

/* end of rt_memmove options */

/* rt_memcmp options */

/* end of rt_memcmp options */

/* rt_strstr options */

/* end of rt_strstr options */

/* rt_strcasecmp options */

/* end of rt_strcasecmp options */

/* rt_strncpy options */

/* end of rt_strncpy options */

/* rt_strcpy options */

/* end of rt_strcpy options */

/* rt_strncmp options */

/* end of rt_strncmp options */

/* rt_strcmp options */

/* end of rt_strcmp options */

/* rt_strlen options */

/* end of rt_strlen options */

/* rt_strnlen options */

/* end of rt_strnlen options */
/* end of klibc options */
#define RT_NAME_MAX 12
#define RT_CPUS_NR 1
#define RT_ALIGN_SIZE 8
#define RT_THREAD_PRIORITY_32
#define RT_THREAD_PRIORITY_MAX 32
#define RT_TICK_PER_SECOND 1000
#define RT_USING_OVERFLOW_CHECK
#define RT_USING_HOOK
#define RT_HOOK_USING_FUNC_PTR
#define RT_USING_IDLE_HOOK
#define RT_IDLE_HOOK_LIST_SIZE 4
#define IDLE_THREAD_STACK_SIZE 1024
#define RT_USING_TIMER_SOFT
#define RT_TIMER_THREAD_PRIO 4
#define RT_TIMER_THREAD_STACK_SIZE 1024

/* kservice options */

/* end of kservice options */
#define RT_USING_DEBUG
#define RT_DEBUGING_ASSERT
#define RT_DEBUGING_COLOR
#define RT_DEBUGING_CONTEXT

/* Inter-Thread communication */

#define RT_USING_SEMAPHORE
#define RT_USING_MUTEX
#define RT_USING_EVENT
#define RT_USING_MAILBOX
#define RT_USING_MESSAGEQUEUE
/* end of Inter-Thread communication */

/* Memory Management */

#define RT_USING_MEMPOOL
#define RT_USING_SMALL_MEM
#define RT_USING_SMALL_MEM_AS_HEAP
#define RT_USING_HEAP
/* end of Memory Management */
#define RT_USING_DEVICE
#define RT_USING_CONSOLE
#define RT_CONSOLEBUF_SIZE 128
#define RT_CONSOLE_DEVICE_NAME "uart2"
#define RT_VER_NUM 0x50201
#define RT_BACKTRACE_LEVEL_MAX_NR 32
/* end of RT-Thread Kernel */
#define RT_USING_CACHE
#define RT_USING_HW_ATOMIC
#define RT_USING_CPU_FFS
#define ARCH_ARM
#define ARCH_ARM_CORTEX_M
#define ARCH_ARM_CORTEX_M7

/* RT-Thread Components */

#define RT_USING_COMPONENTS_INIT
#define RT_USING_USER_MAIN
#define RT_MAIN_THREAD_STACK_SIZE 2048
#define RT_MAIN_THREAD_PRIORITY 10
#define RT_USING_MSH
#define RT_USING_FINSH
#define FINSH_USING_MSH
#define FINSH_THREAD_NAME "tshell"
#define FINSH_THREAD_PRIORITY 20
#define FINSH_THREAD_STACK_SIZE 4096
#define FINSH_USING_HISTORY
#define FINSH_HISTORY_LINES 5
#define FINSH_USING_SYMTAB
#define FINSH_CMD_SIZE 80
#define MSH_USING_BUILT_IN_COMMANDS
#define FINSH_USING_DESCRIPTION
#define FINSH_ARG_MAX 12
#define FINSH_USING_OPTION_COMPLETION

/* DFS: device virtual file system */

#define RT_USING_DFS
#define DFS_USING_POSIX
#define DFS_USING_WORKDIR
#define DFS_FD_MAX 16
#define RT_USING_DFS_V1
#define DFS_FILESYSTEMS_MAX 4
#define DFS_FILESYSTEM_TYPES_MAX 4
#define RT_USING_DFS_DEVFS
/* end of DFS: device virtual file system */

/* Device Drivers */

#define RT_USING_DEVICE_IPC
#define RT_UNAMED_PIPE_NUMBER 64
#define RT_USING_SERIAL
#define RT_USING_SERIAL_V1
#define RT_SERIAL_USING_DMA
#define RT_SERIAL_RB_BUFSZ 64
#define RT_USING_CAN
#define RT_CAN_USING_CANFD
#define RT_CANMSG_BOX_SZ 16
#define RT_CANSND_BOX_NUM 1
#define RT_CANSND_MSG_TIMEOUT 100
#define RT_CAN_NB_TX_FIFO_SIZE 256
#define RT_USING_PIN
/* end of Device Drivers */

/* C/C++ and POSIX layer */

/* ISO-ANSI C layer */

/* Timezone and Daylight Saving Time */

#define RT_LIBC_USING_LIGHT_TZ_DST
#define RT_LIBC_TZ_DEFAULT_HOUR 8
#define RT_LIBC_TZ_DEFAULT_MIN 0
#define RT_LIBC_TZ_DEFAULT_SEC 0
/* end of Timezone and Daylight Saving Time */
/* end of ISO-ANSI C layer */

/* POSIX (Portable Operating System Interface) layer */


/* Interprocess Communication (IPC) */


/* Socket is in the 'Network' category */

/* end of Interprocess Communication (IPC) */
/* end of POSIX (Portable Operating System Interface) layer */
/* end of C/C++ and POSIX layer */

/* Network */

/* end of Network */

/* Memory protection */

/* end of Memory protection */

/* Utilities */

/* end of Utilities */

/* Using USB legacy version */

/* end of Using USB legacy version */
/* end of RT-Thread Components */

/* RT-Thread Utestcases */

/* end of RT-Thread Utestcases */

/* Hardware Drivers */

/* On-chip Peripheral Drivers */

#define BSP_USING_GPIO
#define BSP_USING_FDCAN
#define BSP_USING_FDCAN2
#define BSP_USING_UART
#define BSP_STM32_UART_V1_TX_TIMEOUT 2000
#define BSP_USING_UART2
/* end of On-chip Peripheral Drivers */
/* end of Hardware Drivers */

/* BSP Components */

#define PKG_USING_CANOPENNODE

/* RT-Thread integration */

#define PKG_CANOPENNODE_CAN_DEV_NAME "fdcan2"
#define PKG_CANOPENNODE_CAN_BINDING_COUNT 1

/* RT-Thread runtime options */

/* CAN RX helper thread */

#define PKG_CANOPENNODE_RX_THREAD_STACK_SIZE 2048
#define PKG_CANOPENNODE_RX_THREAD_PRIORITY 2
#define PKG_CANOPENNODE_RX_THREAD_TICK 10
#define PKG_CANOPENNODE_RX_BATCH_SIZE 8
/* end of CAN RX helper thread */

/* CANopen mainline thread */

#define PKG_CANOPENNODE_MAIN_THREAD_STACK_SIZE 2048
#define PKG_CANOPENNODE_MAIN_THREAD_PRIORITY 10
#define PKG_CANOPENNODE_MAIN_THREAD_TICK 10
/* end of CANopen mainline thread */

/* CANopen realtime thread */

#define PKG_CANOPENNODE_RT_THREAD_STACK_SIZE 2048
#define PKG_CANOPENNODE_RT_THREAD_PRIORITY 3
#define PKG_CANOPENNODE_RT_THREAD_TICK 10
#define PKG_CANOPENNODE_TIMER_PERIOD_US 1000
/* end of CANopen realtime thread */

/* CANopen application runtime */

#define PKG_CANOPENNODE_APP_FIRST_HB_TIME_MS 500
#define PKG_CANOPENNODE_APP_SDO_SRV_TIMEOUT_MS 1000
#define PKG_CANOPENNODE_APP_SDO_CLI_TIMEOUT_MS 500
/* end of CANopen application runtime */
#define PKG_CANOPENNODE_APP_AUTO_INIT
#define PKG_CANOPENNODE_AUTO_INIT_NODE_ID 2
#define PKG_CANOPENNODE_AUTO_INIT_BITRATE_250
#define PKG_CANOPENNODE_AUTO_INIT_BITRATE 250
#define PKG_CANOPENNODE_GATEWAY_RTT_CONSOLE
/* end of RT-Thread runtime options */
/* end of RT-Thread integration */

/* CANopenNode CO_CONFIG groups */

/* Common flags */

#define PKG_CANOPENNODE_GLOBAL_OD_DYNAMIC
/* end of Common flags */

/* CiA 301 NMT and heartbeat */

#define PKG_CANOPENNODE_NMT_MASTER
#define PKG_CANOPENNODE_USING_HB_CONS
#define PKG_CANOPENNODE_HB_CONS_CALLBACK_NONE
/* end of CiA 301 NMT and heartbeat */

/* CiA 301 legacy node guarding */

/* Node guarding is legacy and is not covered by demo CI profiles; prefer heartbeat supervision. */

/* end of CiA 301 legacy node guarding */

/* CiA 301 emergency object */

#define PKG_CANOPENNODE_EM_PRODUCER
#define PKG_CANOPENNODE_EM_HISTORY
#define PKG_CANOPENNODE_EM_ERR_STATUS_BITS_COUNT 80
#define PKG_CANOPENNODE_ERR_CONDITION_GENERIC_STACK
#define PKG_CANOPENNODE_ERR_CONDITION_COMMUNICATION_STACK
#define PKG_CANOPENNODE_ERR_CONDITION_MANUFACTURER_STACK
/* end of CiA 301 emergency object */

/* CiA 301 SDO */

/* SDO provides Object Dictionary upload/download for configuration and diagnostics. */

/* Most slave devices need SDO server; SDO client is for masters/gateways/tools. */

#define PKG_CANOPENNODE_USING_SDO_SERVER
#define PKG_CANOPENNODE_SDO_SRV_SEGMENTED
#define PKG_CANOPENNODE_SDO_SRV_BUFFER_SIZE 32
#define PKG_CANOPENNODE_USING_SDO_CLIENT
#define PKG_CANOPENNODE_SDO_CLI_SEGMENTED
#define PKG_CANOPENNODE_SDO_CLI_LOCAL
#define PKG_CANOPENNODE_SDO_CLI_BUFFER_SIZE 32
/* end of CiA 301 SDO */
#define PKG_CANOPENNODE_USING_TIME

/* CiA 301 SYNC and PDO */

/* SYNC provides a network synchronization event; PDO transfers process data. */

/* RPDO receives process data; TPDO transmits process data. */

#define PKG_CANOPENNODE_USING_SYNC
#define PKG_CANOPENNODE_SYNC_PRODUCER
#define PKG_CANOPENNODE_USING_PDO
#define PKG_CANOPENNODE_RPDO
#define PKG_CANOPENNODE_TPDO
#define PKG_CANOPENNODE_RPDO_TIMERS
#define PKG_CANOPENNODE_TPDO_TIMERS
#define PKG_CANOPENNODE_PDO_SYNC
#define PKG_CANOPENNODE_PDO_OD_IO_ACCESS
/* end of CiA 301 SYNC and PDO */
#define PKG_CANOPENNODE_USING_LEDS

/* CiA 304 safety-related objects */

/* end of CiA 304 safety-related objects */

/* CiA 305 LSS */

/* LSS discovers/configures node ID and bitrate during commissioning. */

/* LSS slave is for configurable devices; LSS master is for tools/gateways/managers. */

#define PKG_CANOPENNODE_USING_LSS_SLAVE
/* end of CiA 305 LSS */
#define PKG_CANOPENNODE_USING_GATEWAY_ASCII
#define PKG_CANOPENNODE_GATEWAY_ASCII_SDO
#define PKG_CANOPENNODE_GATEWAY_ASCII_NMT
#define PKG_CANOPENNODE_GATEWAY_ASCII_ERROR_DESC
#define PKG_CANOPENNODE_GATEWAY_ASCII_PRINT_HELP
#define PKG_CANOPENNODE_GTW_BLOCK_DL_LOOP 1
#define PKG_CANOPENNODE_GTWA_COMM_BUF_SIZE 200
#define PKG_CANOPENNODE_GTWA_LOG_BUF_SIZE 2000

/* Helper and debug objects */

/* FIFO/CRC16 are helpers for optional modules; trace/debug are bring-up aids. */

#define PKG_CANOPENNODE_USING_FIFO
#define PKG_CANOPENNODE_FIFO_ASCII_COMMANDS
#define PKG_CANOPENNODE_FIFO_ASCII_DATATYPES
/* end of Helper and debug objects */
/* end of CANopenNode CO_CONFIG groups */

/* CANopen profiles */

/* end of CANopen profiles */

/* Object Dictionary */

#define PKG_CANOPENNODE_USING_DEMO_OD

/* Optional demo/test modules */

/* end of Optional demo/test modules */
/* end of Object Dictionary */
#define PKG_USING_CANOPENNODE_V100
/* end of BSP Components */

#endif
