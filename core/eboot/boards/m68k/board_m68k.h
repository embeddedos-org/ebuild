// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_m68k.h
 * @brief ColdFire MCF5307 board configuration (ColdFire V3, 2MB flash, 4MB RAM)
 */

#ifndef BOARD_M68K_H
#define BOARD_M68K_H

#include "eos_hal.h"

#define M68K_FLASH_BASE             0xFFE00000
#define M68K_FLASH_SIZE             (2 * 1024 * 1024)
#define M68K_RAM_BASE               0x00000000
#define M68K_RAM_SIZE               (4 * 1024 * 1024)

#define M68K_SLOT_A_ADDR            0xFFE10000
#define M68K_SLOT_A_SIZE            (768 * 1024)
#define M68K_SLOT_B_ADDR            0xFFED0000
#define M68K_SLOT_B_SIZE            (768 * 1024)
#define M68K_RECOVERY_ADDR          0xFFF90000
#define M68K_RECOVERY_SIZE          (384 * 1024)
#define M68K_BOOTCTL_ADDR           0xFFFFF000
#define M68K_BOOTCTL_BACKUP_ADDR    0xFFFFE000
#define M68K_LOG_ADDR               0xFFFFD000

#define M68K_CPU_HZ                 90000000
#define M68K_BOARD_ID               0x1201

void board_m68k_early_init(void);
const eos_board_ops_t *board_m68k_get_ops(void);

#endif /* BOARD_M68K_H */
