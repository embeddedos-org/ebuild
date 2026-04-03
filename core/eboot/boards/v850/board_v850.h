// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_v850.h
 * @brief Renesas V850E board configuration (V850E, 1MB flash, 128KB RAM)
 */

#ifndef BOARD_V850_H
#define BOARD_V850_H

#include "eos_hal.h"

#define V850_FLASH_BASE             0x00000000
#define V850_FLASH_SIZE             (1024 * 1024)
#define V850_RAM_BASE               0x03FF0000
#define V850_RAM_SIZE               (128 * 1024)

#define V850_SLOT_A_ADDR            0x00008000
#define V850_SLOT_A_SIZE            (384 * 1024)
#define V850_SLOT_B_ADDR            0x00068000
#define V850_SLOT_B_SIZE            (384 * 1024)
#define V850_RECOVERY_ADDR          0x000C8000
#define V850_RECOVERY_SIZE          (96 * 1024)
#define V850_BOOTCTL_ADDR           0x000FF000
#define V850_BOOTCTL_BACKUP_ADDR    0x000FE000
#define V850_LOG_ADDR               0x000FD000

#define V850_CPU_HZ                 32000000
#define V850_BOARD_ID               0x1301

void board_v850_early_init(void);
const eos_board_ops_t *board_v850_get_ops(void);

#endif /* BOARD_V850_H */
