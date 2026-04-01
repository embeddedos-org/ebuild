// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_sparc.h
 * @brief LEON3 SPARC V8 board configuration (LEON3, 4MB flash, 16MB RAM)
 */

#ifndef BOARD_SPARC_H
#define BOARD_SPARC_H

#include "eos_hal.h"

#define SPARC_FLASH_BASE            0x00000000
#define SPARC_FLASH_SIZE            (4 * 1024 * 1024)
#define SPARC_RAM_BASE              0x40000000
#define SPARC_RAM_SIZE              (16 * 1024 * 1024)

#define SPARC_SLOT_A_ADDR           0x00020000
#define SPARC_SLOT_A_SIZE           (1536 * 1024)
#define SPARC_SLOT_B_ADDR           0x001A0000
#define SPARC_SLOT_B_SIZE           (1536 * 1024)
#define SPARC_RECOVERY_ADDR         0x00320000
#define SPARC_RECOVERY_SIZE         (384 * 1024)
#define SPARC_BOOTCTL_ADDR          0x003FF000
#define SPARC_BOOTCTL_BACKUP_ADDR   0x003FE000
#define SPARC_LOG_ADDR              0x003FD000

#define SPARC_CPU_HZ                80000000
#define SPARC_BOARD_ID              0x1401

void board_sparc_early_init(void);
const eos_board_ops_t *board_sparc_get_ops(void);

#endif /* BOARD_SPARC_H */
