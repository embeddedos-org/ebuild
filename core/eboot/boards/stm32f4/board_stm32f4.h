// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_stm32f4.h
 * @brief STM32F4 reference board configuration
 */

#ifndef BOARD_STM32F4_H
#define BOARD_STM32F4_H

#include "eos_hal.h"

/*
 * STM32F407 Flash Memory Map (1MB total)
 *
 * 0x08000000 - 0x08003FFF  (16K)   Stage-0 (eBootloader)
 * 0x08004000 - 0x0800FFFF  (48K)   Stage-1 (E-Boot)
 * 0x08010000 - 0x0807FFFF  (448K)  Slot A (application firmware)
 * 0x08080000 - 0x080EFFFF  (448K)  Slot B (candidate firmware)
 * 0x080F0000 - 0x080F3FFF  (16K)   Recovery image (golden)
 * 0x080F4000 - 0x080F5FFF  (8K)    Boot control (primary)
 * 0x080F6000 - 0x080F7FFF  (8K)    Boot control (backup)
 * 0x080F8000 - 0x080F9FFF  (8K)    Boot log
 * 0x080FA000 - 0x080FFFFF  (24K)   Device config / reserved
 */

#define STM32F4_FLASH_BASE          0x08000000
#define STM32F4_FLASH_SIZE          (1024 * 1024)  /* 1MB */

#define STM32F4_STAGE0_ADDR         0x08000000
#define STM32F4_STAGE0_SIZE         (16 * 1024)

#define STM32F4_STAGE1_ADDR         0x08004000
#define STM32F4_STAGE1_SIZE         (48 * 1024)

#define STM32F4_SLOT_A_ADDR         0x08010000
#define STM32F4_SLOT_A_SIZE         (448 * 1024)

#define STM32F4_SLOT_B_ADDR         0x08080000
#define STM32F4_SLOT_B_SIZE         (448 * 1024)

#define STM32F4_RECOVERY_ADDR       0x080F0000
#define STM32F4_RECOVERY_SIZE       (16 * 1024)

#define STM32F4_BOOTCTL_ADDR        0x080F4000
#define STM32F4_BOOTCTL_BACKUP_ADDR 0x080F6000

#define STM32F4_LOG_ADDR            0x080F8000

#define STM32F4_VECTOR_OFFSET       (STM32F4_STAGE1_ADDR - STM32F4_FLASH_BASE)

/* UART for recovery */
#define STM32F4_UART_INSTANCE       2  /* USART2 on PA2/PA3 */

/* Recovery GPIO */
#define STM32F4_RECOVERY_PORT       'C'
#define STM32F4_RECOVERY_PIN        13  /* PC13 — user button on Nucleo */

/* Board entry points */
void board_early_init(void);
const eos_board_ops_t *board_get_ops(void);

#endif /* BOARD_STM32F4_H */
