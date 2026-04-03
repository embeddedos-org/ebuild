// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_strongarm.h
 * @brief Intel StrongARM SA-1110 board configuration
 */

#ifndef BOARD_STRONGARM_H
#define BOARD_STRONGARM_H

#include "eos_hal.h"

#define SA1110_FLASH_BASE           0x00000000
#define SA1110_FLASH_SIZE           (16 * 1024 * 1024)
#define SA1110_RAM_BASE             0xC0000000
#define SA1110_RAM_SIZE             (32 * 1024 * 1024)

#define SA1110_SLOT_A_ADDR          0x00040000
#define SA1110_SLOT_A_SIZE          (6 * 1024 * 1024)
#define SA1110_SLOT_B_ADDR          0x00640000
#define SA1110_SLOT_B_SIZE          (6 * 1024 * 1024)
#define SA1110_RECOVERY_ADDR        0x00C40000
#define SA1110_RECOVERY_SIZE        (2 * 1024 * 1024)
#define SA1110_BOOTCTL_ADDR         0x00FF0000
#define SA1110_BOOTCTL_BACKUP_ADDR  0x00FE0000

#define SA1110_CPU_HZ               206000000
#define SA1110_BOARD_ID             0x0A01

void board_strongarm_early_init(void);
const eos_board_ops_t *board_strongarm_get_ops(void);

#endif /* BOARD_STRONGARM_H */
