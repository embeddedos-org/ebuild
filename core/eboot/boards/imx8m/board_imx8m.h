// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_imx8m.h
 * @brief NXP i.MX 8M Mini board configuration (Cortex-A53, ARM64)
 *
 * Industry-standard applications processor used in IoT gateways,
 * industrial HMIs, and edge computing devices.
 */

#ifndef BOARD_IMX8M_H
#define BOARD_IMX8M_H

#include "eos_hal.h"

#define IMX8M_OCRAM_BASE            0x00900000
#define IMX8M_DDR_BASE              0x40000000
#define IMX8M_DDR_SIZE              (2UL * 1024 * 1024 * 1024)
#define IMX8M_QSPI_BASE            0x08000000
#define IMX8M_QSPI_SIZE            (64 * 1024 * 1024)

#define IMX8M_UART1_BASE            0x30860000
#define IMX8M_UART2_BASE            0x30890000

#define IMX8M_SLOT_A_ADDR           0x08100000
#define IMX8M_SLOT_A_SIZE           (16 * 1024 * 1024)
#define IMX8M_SLOT_B_ADDR           0x09100000
#define IMX8M_SLOT_B_SIZE           (16 * 1024 * 1024)
#define IMX8M_RECOVERY_ADDR         0x0A100000
#define IMX8M_RECOVERY_SIZE         (8 * 1024 * 1024)
#define IMX8M_BOOTCTL_ADDR          0x0AF00000

#define IMX8M_CPU_HZ                1800000000
#define IMX8M_BOARD_ID              0x824D
#define IMX8M_PLATFORM              EOS_PLATFORM_ARM_CA53

void board_imx8m_early_init(void);
const eos_board_ops_t *board_imx8m_get_ops(void);

#endif /* BOARD_IMX8M_H */
