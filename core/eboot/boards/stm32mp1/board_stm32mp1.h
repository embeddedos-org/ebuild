// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_stm32mp1.h
 * @brief STM32MP1 board configuration (Cortex-A7 + Cortex-M4 hybrid)
 *
 * Used in industrial HMI, gateways, and Linux+RTOS hybrid applications.
 */

#ifndef BOARD_STM32MP1_H
#define BOARD_STM32MP1_H

#include "eos_hal.h"

#define STM32MP1_DDR_BASE           0xC0000000
#define STM32MP1_DDR_SIZE           (512 * 1024 * 1024)
#define STM32MP1_SRAM_BASE          0x10000000
#define STM32MP1_SRAM_SIZE          (256 * 1024)
#define STM32MP1_EMMC_BASE          0x00000000
#define STM32MP1_EMMC_SIZE          (4UL * 1024 * 1024 * 1024)

#define STM32MP1_SLOT_A_ADDR        0x00100000
#define STM32MP1_SLOT_A_SIZE        (64 * 1024 * 1024)
#define STM32MP1_SLOT_B_ADDR        0x04100000
#define STM32MP1_SLOT_B_SIZE        (64 * 1024 * 1024)
#define STM32MP1_RECOVERY_ADDR      0x08100000
#define STM32MP1_RECOVERY_SIZE      (16 * 1024 * 1024)
#define STM32MP1_BOOTCTL_ADDR       0x09100000

#define STM32MP1_CPU_HZ             650000000
#define STM32MP1_BOARD_ID           0xA7C4
#define STM32MP1_PLATFORM           EOS_PLATFORM_ARM_CA72

void board_stm32mp1_early_init(void);
const eos_board_ops_t *board_stm32mp1_get_ops(void);

#endif /* BOARD_STM32MP1_H */
