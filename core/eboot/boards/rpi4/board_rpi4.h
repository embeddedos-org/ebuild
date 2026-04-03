// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_rpi4.h
 * @brief Raspberry Pi 4 board configuration (BCM2711, Cortex-A72, ARM64)
 */

#ifndef BOARD_RPI4_H
#define BOARD_RPI4_H

#include "eos_hal.h"

#define RPI4_PERI_BASE              0xFE000000
#define RPI4_GPIO_BASE              (RPI4_PERI_BASE + 0x200000)
#define RPI4_UART0_BASE             (RPI4_PERI_BASE + 0x201000)

#define RPI4_RAM_BASE               0x00000000
#define RPI4_RAM_SIZE               (4UL * 1024 * 1024 * 1024)

#define RPI4_SLOT_A_ADDR            0x00080000
#define RPI4_SLOT_A_SIZE            (32 * 1024 * 1024)
#define RPI4_SLOT_B_ADDR            0x02080000
#define RPI4_SLOT_B_SIZE            (32 * 1024 * 1024)
#define RPI4_RECOVERY_ADDR          0x04080000
#define RPI4_RECOVERY_SIZE          (16 * 1024 * 1024)
#define RPI4_BOOTCTL_ADDR           0x06000000

#define RPI4_CPU_HZ                 1500000000
#define RPI4_BOARD_ID               0xB711
#define RPI4_PLATFORM               EOS_PLATFORM_ARM_CA72

void board_rpi4_early_init(void);
const eos_board_ops_t *board_rpi4_get_ops(void);

#endif /* BOARD_RPI4_H */
