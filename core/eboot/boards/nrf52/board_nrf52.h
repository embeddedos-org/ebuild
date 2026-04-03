// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_nrf52.h
 * @brief nRF52840 board configuration (Cortex-M4F, BLE, 1MB flash, 256K RAM)
 */

#ifndef BOARD_NRF52_H
#define BOARD_NRF52_H

#include "eos_hal.h"

#define NRF52_FLASH_BASE            0x00000000
#define NRF52_FLASH_SIZE            (1024 * 1024)
#define NRF52_RAM_BASE              0x20000000
#define NRF52_RAM_SIZE              (256 * 1024)

#define NRF52_SLOT_A_ADDR           0x00026000
#define NRF52_SLOT_A_SIZE           (360 * 1024)
#define NRF52_SLOT_B_ADDR           0x00080000
#define NRF52_SLOT_B_SIZE           (360 * 1024)
#define NRF52_RECOVERY_ADDR         0x000E0000
#define NRF52_RECOVERY_SIZE         (64 * 1024)
#define NRF52_BOOTCTL_ADDR          0x000FF000
#define NRF52_BOOTCTL_BACKUP_ADDR   0x000FE000
#define NRF52_LOG_ADDR              0x000FD000

#define NRF52_CPU_HZ                64000000
#define NRF52_BOARD_ID              0x0152

void board_nrf52_early_init(void);
const eos_board_ops_t *board_nrf52_get_ops(void);

#endif /* BOARD_NRF52_H */
