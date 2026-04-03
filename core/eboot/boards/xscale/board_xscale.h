// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_xscale.h
 * @brief PXA270 board configuration (XScale, 32MB flash, 64MB RAM)
 */

#ifndef BOARD_XSCALE_H
#define BOARD_XSCALE_H

#include "eos_hal.h"

#define PXA270_FLASH_BASE            0x00000000
#define PXA270_FLASH_SIZE            (32 * 1024 * 1024)
#define PXA270_RAM_BASE              0xA0000000
#define PXA270_RAM_SIZE              (64 * 1024 * 1024)

#define PXA270_SLOT_A_ADDR           0x00040000
#define PXA270_SLOT_A_SIZE           (12 * 1024 * 1024)
#define PXA270_SLOT_B_ADDR           0x00C40000
#define PXA270_SLOT_B_SIZE           (12 * 1024 * 1024)
#define PXA270_RECOVERY_ADDR         0x01840000
#define PXA270_RECOVERY_SIZE         (3 * 1024 * 1024)
#define PXA270_BOOTCTL_ADDR          0x01FFF000
#define PXA270_BOOTCTL_BACKUP_ADDR   0x01FFE000
#define PXA270_LOG_ADDR              0x01FFD000

#define PXA270_CPU_HZ                624000000
#define PXA270_BOARD_ID              0x0A02

void board_xscale_early_init(void);
const eos_board_ops_t *board_xscale_get_ops(void);

#endif /* BOARD_XSCALE_H */
