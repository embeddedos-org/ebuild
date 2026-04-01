// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_qemu_arm64.h
 * @brief QEMU ARM64 virt board configuration (Cortex-A57, for development)
 */

#ifndef BOARD_QEMU_ARM64_H
#define BOARD_QEMU_ARM64_H

#include "eos_hal.h"

#define QEMU_ARM64_FLASH_BASE       0x00000000
#define QEMU_ARM64_FLASH_SIZE       (64 * 1024 * 1024)
#define QEMU_ARM64_RAM_BASE         0x40000000
#define QEMU_ARM64_RAM_SIZE         (512 * 1024 * 1024)

#define QEMU_ARM64_SLOT_A_ADDR      0x00200000
#define QEMU_ARM64_SLOT_A_SIZE      (24 * 1024 * 1024)
#define QEMU_ARM64_SLOT_B_ADDR      0x01A00000
#define QEMU_ARM64_SLOT_B_SIZE      (24 * 1024 * 1024)
#define QEMU_ARM64_RECOVERY_ADDR    0x03200000
#define QEMU_ARM64_RECOVERY_SIZE    (8 * 1024 * 1024)
#define QEMU_ARM64_BOOTCTL_ADDR     0x03F00000

#define QEMU_ARM64_CPU_HZ           1000000000
#define QEMU_ARM64_BOARD_ID         0xA064
#define QEMU_ARM64_PLATFORM         EOS_PLATFORM_ARM_CA53

void board_qemu_arm64_early_init(void);
const eos_board_ops_t *board_qemu_arm64_get_ops(void);

#endif /* BOARD_QEMU_ARM64_H */
