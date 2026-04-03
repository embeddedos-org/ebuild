// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_cortex_r5.h
 * @brief Generic Cortex-R5F board configuration (TMS570-class)
 */

#ifndef BOARD_CORTEX_R5_H
#define BOARD_CORTEX_R5_H

#include "eos_hal.h"

/*
 * Cortex-R5F Memory Map (TMS570-class, 2MB Flash + 256K RAM)
 *
 * 0x00000000 - 0x0000FFFF  (64K)   ATCM — vectors + stage-0 code
 * 0x00080000 - 0x0008FFFF  (64K)   BTCM — fast data / stack
 * 0x00200000 - 0x00203FFF  (16K)   Flash: Stage-0 (eBootloader)
 * 0x00204000 - 0x0020FFFF  (48K)   Flash: Stage-1 (E-Boot)
 * 0x00210000 - 0x0027FFFF  (448K)  Flash: Slot A (application firmware)
 * 0x00280000 - 0x002EFFFF  (448K)  Flash: Slot B (candidate firmware)
 * 0x002F0000 - 0x002F3FFF  (16K)   Flash: Recovery image (golden)
 * 0x002F4000 - 0x002F5FFF  (8K)    Flash: Boot control (primary)
 * 0x002F6000 - 0x002F7FFF  (8K)    Flash: Boot control (backup)
 * 0x002F8000 - 0x002F9FFF  (8K)    Flash: Boot log
 * 0x002FA000 - 0x003FFFFF  (1M)    Flash: Reserved
 * 0x08000000 - 0x0803FFFF  (256K)  RAM (SRAM)
 */

#define R5_ATCM_BASE              0x00000000
#define R5_ATCM_SIZE              (64 * 1024)
#define R5_BTCM_BASE              0x00080000
#define R5_BTCM_SIZE              (64 * 1024)

#define R5_FLASH_BASE             0x00200000
#define R5_FLASH_SIZE             (2 * 1024 * 1024)

#define R5_STAGE0_ADDR            0x00200000
#define R5_STAGE0_SIZE            (16 * 1024)

#define R5_STAGE1_ADDR            0x00204000
#define R5_STAGE1_SIZE            (48 * 1024)

#define R5_SLOT_A_ADDR            0x00210000
#define R5_SLOT_A_SIZE            (448 * 1024)

#define R5_SLOT_B_ADDR            0x00280000
#define R5_SLOT_B_SIZE            (448 * 1024)

#define R5_RECOVERY_ADDR          0x002F0000
#define R5_RECOVERY_SIZE          (16 * 1024)

#define R5_BOOTCTL_ADDR           0x002F4000
#define R5_BOOTCTL_BACKUP_ADDR    0x002F6000

#define R5_LOG_ADDR               0x002F8000

#define R5_RAM_BASE               0x08000000
#define R5_RAM_SIZE               (256 * 1024)

#define R5_VECTOR_OFFSET          (R5_STAGE1_ADDR - R5_FLASH_BASE)

/* TMS570 SCI (UART) base — SCI/LIN module 1 */
#define R5_SCI_BASE               0xFFF7E400

/* RTI (Real-Time Interrupt) timer base */
#define R5_RTI_BASE               0xFFFFFC00

/* ESM (Error Signaling Module) base */
#define R5_ESM_BASE               0xFFFFF500

/* Board identification */
#define R5_BOARD_ID               0xCE05  /* Cortex-R5 */
#define R5_CPU_HZ                 300000000  /* 300 MHz */

/* Platform enum (from eos_hal.h) */
#define R5_PLATFORM               EOS_PLATFORM_ARM_R5F

/* Board entry points */
void board_early_init(void);
const eos_board_ops_t *board_get_ops(void);

#endif /* BOARD_CORTEX_R5_H */
