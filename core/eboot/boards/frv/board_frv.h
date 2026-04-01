// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_frv.h
 * @brief FR450 board configuration (Fujitsu FR-V, 4MB flash, 16MB RAM)
 */

#ifndef BOARD_FRV_H
#define BOARD_FRV_H

#include "eos_hal.h"

#define FR450_FLASH_BASE            0x00000000
#define FR450_FLASH_SIZE            (4 * 1024 * 1024)
#define FR450_RAM_BASE              0x20000000
#define FR450_RAM_SIZE              (16 * 1024 * 1024)

#define FR450_SLOT_A_ADDR           0x00020000
#define FR450_SLOT_A_SIZE           (1536 * 1024)
#define FR450_SLOT_B_ADDR           0x001A0000
#define FR450_SLOT_B_SIZE           (1536 * 1024)
#define FR450_RECOVERY_ADDR         0x00320000
#define FR450_RECOVERY_SIZE         (384 * 1024)
#define FR450_BOOTCTL_ADDR          0x003FF000
#define FR450_BOOTCTL_BACKUP_ADDR   0x003FE000
#define FR450_LOG_ADDR              0x003FD000

#define FR450_CPU_HZ                400000000
#define FR450_BOARD_ID              0x0B01

void board_frv_early_init(void);
const eos_board_ops_t *board_frv_get_ops(void);

#endif /* BOARD_FRV_H */
