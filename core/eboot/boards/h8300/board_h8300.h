// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_h8300.h
 * @brief H83069 board configuration (H8/300H, 512KB flash, 128KB RAM)
 */

#ifndef BOARD_H8300_H
#define BOARD_H8300_H

#include "eos_hal.h"

#define H83069_FLASH_BASE            0x00000000
#define H83069_FLASH_SIZE            (512 * 1024)
#define H83069_RAM_BASE              0x00400000
#define H83069_RAM_SIZE              (128 * 1024)

#define H83069_SLOT_A_ADDR           0x00008000
#define H83069_SLOT_A_SIZE           (192 * 1024)
#define H83069_SLOT_B_ADDR           0x00038000
#define H83069_SLOT_B_SIZE           (192 * 1024)
#define H83069_RECOVERY_ADDR         0x00068000
#define H83069_RECOVERY_SIZE         (48 * 1024)
#define H83069_BOOTCTL_ADDR          0x0007F000
#define H83069_BOOTCTL_BACKUP_ADDR   0x0007E000
#define H83069_LOG_ADDR              0x0007D000

#define H83069_CPU_HZ                25000000
#define H83069_BOARD_ID              0x0D01

void board_h8300_early_init(void);
const eos_board_ops_t *board_h8300_get_ops(void);

#endif /* BOARD_H8300_H */
