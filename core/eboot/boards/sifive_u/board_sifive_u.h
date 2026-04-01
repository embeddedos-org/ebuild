// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_sifive_u.h
 * @brief SiFive HiFive Unmatched board configuration (RISC-V U74, 64-bit)
 *
 * First production RISC-V board for Linux — used in evaluation and development.
 */

#ifndef BOARD_SIFIVE_U_H
#define BOARD_SIFIVE_U_H

#include "eos_hal.h"

#define SIFIVE_UART0_BASE           0x10010000
#define SIFIVE_UART1_BASE           0x10011000
#define SIFIVE_QSPI_BASE           0x20000000
#define SIFIVE_QSPI_SIZE           (32 * 1024 * 1024)
#define SIFIVE_DDR_BASE            0x80000000
#define SIFIVE_DDR_SIZE            (8UL * 1024 * 1024 * 1024)

#define SIFIVE_SLOT_A_ADDR         0x20200000
#define SIFIVE_SLOT_A_SIZE         (8 * 1024 * 1024)
#define SIFIVE_SLOT_B_ADDR         0x20A00000
#define SIFIVE_SLOT_B_SIZE         (8 * 1024 * 1024)
#define SIFIVE_RECOVERY_ADDR       0x21200000
#define SIFIVE_RECOVERY_SIZE       (4 * 1024 * 1024)
#define SIFIVE_BOOTCTL_ADDR        0x21F00000

#define SIFIVE_CPU_HZ              1200000000
#define SIFIVE_BOARD_ID            0x5F74
#define SIFIVE_PLATFORM            EOS_PLATFORM_RISCV64

void board_sifive_u_early_init(void);
const eos_board_ops_t *board_sifive_u_get_ops(void);

#endif /* BOARD_SIFIVE_U_H */
