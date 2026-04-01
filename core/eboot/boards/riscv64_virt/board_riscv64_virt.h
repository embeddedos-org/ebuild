// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_riscv64_virt.h
 * @brief RISC-V 64-bit QEMU virt machine board configuration
 */

#ifndef BOARD_RISCV64_VIRT_H
#define BOARD_RISCV64_VIRT_H

#include "eos_hal.h"

#define RISCV64_UART0_BASE          0x10000000
#define RISCV64_FLASH_BASE          0x20000000
#define RISCV64_FLASH_SIZE          (32 * 1024 * 1024)
#define RISCV64_RAM_BASE            0x80000000
#define RISCV64_RAM_SIZE            (128 * 1024 * 1024)

#define RISCV64_SLOT_A_ADDR         0x20100000
#define RISCV64_SLOT_A_SIZE         (8 * 1024 * 1024)
#define RISCV64_SLOT_B_ADDR         0x20900000
#define RISCV64_SLOT_B_SIZE         (8 * 1024 * 1024)
#define RISCV64_RECOVERY_ADDR       0x21100000
#define RISCV64_RECOVERY_SIZE       (4 * 1024 * 1024)
#define RISCV64_BOOTCTL_ADDR        0x21F00000

#define RISCV64_PLATFORM            EOS_PLATFORM_RISCV64

void board_riscv64_virt_early_init(void);
const eos_board_ops_t *board_riscv64_virt_get_ops(void);

#endif /* BOARD_RISCV64_VIRT_H */
