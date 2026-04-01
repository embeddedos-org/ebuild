// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_x86.h
 * @brief x86 board configuration (i486/Pentium, 16MB flash, 64MB RAM)
 */

#ifndef BOARD_X86_H
#define BOARD_X86_H

#include "eos_hal.h"

#define X86_FLASH_BASE            0xFFF00000
#define X86_FLASH_SIZE            (16 * 1024 * 1024)
#define X86_RAM_BASE              0x00100000
#define X86_RAM_SIZE              (64 * 1024 * 1024)

#define X86_SLOT_A_ADDR           0xFF040000
#define X86_SLOT_A_SIZE           (6 * 1024 * 1024)
#define X86_SLOT_B_ADDR           0xFF640000
#define X86_SLOT_B_SIZE           (6 * 1024 * 1024)
#define X86_RECOVERY_ADDR         0xFFC40000
#define X86_RECOVERY_SIZE         (1536 * 1024)
#define X86_BOOTCTL_ADDR          0xFFEFF000
#define X86_BOOTCTL_BACKUP_ADDR   0xFFEFE000
#define X86_LOG_ADDR              0xFFEFD000

#define X86_CPU_HZ                100000000
#define X86_BOARD_ID              0x0E01

void board_x86_early_init(void);
const eos_board_ops_t *board_x86_get_ops(void);

#endif /* BOARD_X86_H */
