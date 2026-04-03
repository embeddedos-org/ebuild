// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_x86_64_efi.h
 * @brief x86_64 UEFI board configuration
 */

#ifndef BOARD_X86_64_EFI_H
#define BOARD_X86_64_EFI_H

#include "eos_hal.h"

#define X86_COM1_BASE               0x3F8
#define X86_COM2_BASE               0x2F8

#define X86_SLOT_A_ADDR             0x00100000
#define X86_SLOT_A_SIZE             (64 * 1024 * 1024)
#define X86_SLOT_B_ADDR             0x04100000
#define X86_SLOT_B_SIZE             (64 * 1024 * 1024)
#define X86_RECOVERY_ADDR           0x08100000
#define X86_RECOVERY_SIZE           (32 * 1024 * 1024)
#define X86_BOOTCTL_ADDR            0x0A100000

#define X86_PLATFORM                EOS_PLATFORM_X86_64

void board_x86_64_efi_early_init(void);
const eos_board_ops_t *board_x86_64_efi_get_ops(void);

#endif /* BOARD_X86_64_EFI_H */
