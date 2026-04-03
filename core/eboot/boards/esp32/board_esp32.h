// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_esp32.h
 * @brief ESP32 board configuration (Xtensa LX6, Wi-Fi/BLE, 4MB flash)
 */

#ifndef BOARD_ESP32_H
#define BOARD_ESP32_H

#include "eos_hal.h"

#define ESP32_FLASH_BASE            0x00000000
#define ESP32_FLASH_SIZE            (4 * 1024 * 1024)
#define ESP32_IRAM_BASE             0x40080000
#define ESP32_DRAM_BASE             0x3FFB0000

#define ESP32_SLOT_A_ADDR           0x00010000
#define ESP32_SLOT_A_SIZE           (1536 * 1024)
#define ESP32_SLOT_B_ADDR           0x00190000
#define ESP32_SLOT_B_SIZE           (1536 * 1024)
#define ESP32_RECOVERY_ADDR         0x00310000
#define ESP32_RECOVERY_SIZE         (512 * 1024)
#define ESP32_BOOTCTL_ADDR          0x003F0000

#define ESP32_CPU_HZ                240000000
#define ESP32_BOARD_ID              0xE532
#define ESP32_PLATFORM              EOS_PLATFORM_XTENSA

void board_esp32_early_init(void);
const eos_board_ops_t *board_esp32_get_ops(void);

#endif /* BOARD_ESP32_H */
