// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_stm32h7.h
 * @brief STM32H7 board configuration (Cortex-M7, 2MB flash, 512K RAM)
 */

#ifndef BOARD_STM32H7_H
#define BOARD_STM32H7_H

#include "eos_hal.h"

#define STM32H7_FLASH_BASE          0x08000000
#define STM32H7_FLASH_SIZE          (2 * 1024 * 1024)
#define STM32H7_RAM_BASE            0x20000000
#define STM32H7_RAM_SIZE            (512 * 1024)

#define STM32H7_STAGE0_ADDR         0x08000000
#define STM32H7_STAGE0_SIZE         (32 * 1024)
#define STM32H7_STAGE1_ADDR         0x08008000
#define STM32H7_STAGE1_SIZE         (96 * 1024)

#define STM32H7_SLOT_A_ADDR         0x08020000
#define STM32H7_SLOT_A_SIZE         (896 * 1024)
#define STM32H7_SLOT_B_ADDR         0x08100000
#define STM32H7_SLOT_B_SIZE         (896 * 1024)
#define STM32H7_RECOVERY_ADDR       0x081E0000
#define STM32H7_RECOVERY_SIZE       (64 * 1024)
#define STM32H7_BOOTCTL_ADDR        0x081F0000
#define STM32H7_BOOTCTL_BACKUP_ADDR 0x081F4000
#define STM32H7_LOG_ADDR            0x081F8000

#define STM32H7_CPU_HZ              480000000
#define STM32H7_BOARD_ID            0x0450

void board_stm32h7_early_init(void);
const eos_board_ops_t *board_stm32h7_get_ops(void);

#endif /* BOARD_STM32H7_H */
