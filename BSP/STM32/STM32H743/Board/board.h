#ifndef __BOARD_H__
#define __BOARD_H__

#include <rtconfig.h>
#include "stm32h7xx_hal.h"

#ifdef __cplusplus
extern "C" {
#endif

#define STM32_SRAM_SIZE               512U
#define STM32_SRAM_END                (0x24000000UL + STM32_SRAM_SIZE * 1024UL)

#define STM32_FLASH_START_ADRESS      ((uint32_t)0x08000000UL)
#define STM32_FLASH_SIZE              (2048U * 1024U)
#define STM32_FLASH_END_ADDRESS       (STM32_FLASH_START_ADRESS + STM32_FLASH_SIZE)

#if defined(__ARMCC_VERSION)
extern int Image$$RW_IRAM1$$ZI$$Limit;
extern int Image$$ARM_LIB_STACK$$Base;
#define HEAP_BEGIN                    ((void *)&Image$$RW_IRAM1$$ZI$$Limit)
#define HEAP_END                      ((void *)&Image$$ARM_LIB_STACK$$Base)
#elif defined(__ICCARM__)
#pragma section="HEAP"
#pragma section="CSTACK"
#define HEAP_BEGIN                    (__segment_end("HEAP"))
#define HEAP_END                      (__segment_begin("CSTACK"))
#else
extern int __bss_end;
extern int _sstack;
#define HEAP_BEGIN                    ((void *)&__bss_end)
#define HEAP_END                      ((void *)&_sstack)
#endif

void SystemClock_Config(void);
void Error_Handler(void);

#ifdef __cplusplus
}
#endif

#endif
