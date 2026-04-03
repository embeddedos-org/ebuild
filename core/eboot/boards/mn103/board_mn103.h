// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_mn103.h
 * @brief Panasonic AM33 (MN103) board configuration (AM33, 2MB flash, 8MB RAM)
 */

#ifndef BOARD_MN103_H
#define BOARD_MN103_H

#include "eos_hal.h"

#define MN103_FLASH_BASE            0x00000000
#define MN103_FLASH_SIZE            (2 * 1024 * 1024)
#define MN103_RAM_BASE              0x48000000
#define MN103_RAM_SIZE              (8 * 1024 * 1024)

#define MN103_SLOT_A_ADDR           0x00010000
#define MN103_SLOT_A_SIZE           (768 * 1024)
#define MN103_SLOT_B_ADDR           0x000D0000
#define MN103_SLOT_B_SIZE           (768 * 1024)
#define MN103_RECOVERY_ADDR         0x00190000
#define MN103_RECOVERY_SIZE         (192 * 1024)
#define MN103_BOOTCTL_ADDR          0x001FF000
#define MN103_BOOTCTL_BACKUP_ADDR   0x001FE000
#define MN103_LOG_ADDR              0x001FD000

#define MN103_CPU_HZ                200000000
#define MN103_BOARD_ID              0x1001

void board_mn103_early_init(void);
const eos_board_ops_t *board_mn103_get_ops(void);

#endif /* BOARD_MN103_H */
