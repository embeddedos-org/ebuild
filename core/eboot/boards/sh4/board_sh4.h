// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_sh4.h
 * @brief SH7750 board configuration (SuperH SH-4, 4MB flash, 16MB RAM)
 */

#ifndef BOARD_SH4_H
#define BOARD_SH4_H

#include "eos_hal.h"

#define SH7750_FLASH_BASE            0x00000000
#define SH7750_FLASH_SIZE            (4 * 1024 * 1024)
#define SH7750_RAM_BASE              0x0C000000
#define SH7750_RAM_SIZE              (16 * 1024 * 1024)

#define SH7750_SLOT_A_ADDR           0x00020000
#define SH7750_SLOT_A_SIZE           (1536 * 1024)
#define SH7750_SLOT_B_ADDR           0x001A0000
#define SH7750_SLOT_B_SIZE           (1536 * 1024)
#define SH7750_RECOVERY_ADDR         0x00320000
#define SH7750_RECOVERY_SIZE         (384 * 1024)
#define SH7750_BOOTCTL_ADDR          0x003FF000
#define SH7750_BOOTCTL_BACKUP_ADDR   0x003FE000
#define SH7750_LOG_ADDR              0x003FD000

#define SH7750_CPU_HZ                200000000
#define SH7750_BOARD_ID              0x0C01

void board_sh4_early_init(void);
const eos_board_ops_t *board_sh4_get_ops(void);

#endif /* BOARD_SH4_H */
