// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_am64x.h
 * @brief TI AM64x Sitara board configuration (Cortex-R5F + Cortex-A53)
 *
 * Used in industrial automation, PLCs, motor drives, and field instruments.
 */

#ifndef BOARD_AM64X_H
#define BOARD_AM64X_H

#include "eos_hal.h"

#define AM64X_OSPI_BASE             0x50000000
#define AM64X_OSPI_SIZE             (64 * 1024 * 1024)
#define AM64X_DDR_BASE              0x80000000
#define AM64X_DDR_SIZE              (2UL * 1024 * 1024 * 1024)
#define AM64X_MSRAM_BASE            0x70000000

#define AM64X_UART0_BASE            0x02800000

#define AM64X_SLOT_A_ADDR           0x50200000
#define AM64X_SLOT_A_SIZE           (16 * 1024 * 1024)
#define AM64X_SLOT_B_ADDR           0x51200000
#define AM64X_SLOT_B_SIZE           (16 * 1024 * 1024)
#define AM64X_RECOVERY_ADDR         0x52200000
#define AM64X_RECOVERY_SIZE         (8 * 1024 * 1024)
#define AM64X_BOOTCTL_ADDR          0x52F00000

#define AM64X_CPU_HZ                1000000000
#define AM64X_BOARD_ID              0xAA64
#define AM64X_PLATFORM              EOS_PLATFORM_ARM_CA53

void board_am64x_early_init(void);
const eos_board_ops_t *board_am64x_get_ops(void);

#endif /* BOARD_AM64X_H */
