// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_mips.h
 * @brief MIPS32 generic board configuration (MIPS32, 8MB flash, 32MB RAM)
 */

#ifndef BOARD_MIPS_H
#define BOARD_MIPS_H

#include "eos_hal.h"

#define MIPS_FLASH_BASE             0x1FC00000
#define MIPS_FLASH_SIZE             (8 * 1024 * 1024)
#define MIPS_RAM_BASE               0x80000000
#define MIPS_RAM_SIZE               (32 * 1024 * 1024)

#define MIPS_SLOT_A_ADDR            0x1FC40000
#define MIPS_SLOT_A_SIZE            (3 * 1024 * 1024)
#define MIPS_SLOT_B_ADDR            0x1FF40000
#define MIPS_SLOT_B_SIZE            (3 * 1024 * 1024)
#define MIPS_RECOVERY_ADDR          0x20240000
#define MIPS_RECOVERY_SIZE          (768 * 1024)
#define MIPS_BOOTCTL_ADDR           0x203FF000
#define MIPS_BOOTCTL_BACKUP_ADDR    0x203FE000
#define MIPS_LOG_ADDR               0x203FD000

#define MIPS_CPU_HZ                 400000000
#define MIPS_BOARD_ID               0x0F01

void board_mips_early_init(void);
const eos_board_ops_t *board_mips_get_ops(void);

#endif /* BOARD_MIPS_H */
