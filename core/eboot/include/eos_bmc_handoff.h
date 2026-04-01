// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file eos_bmc_handoff.h
 * @brief BMC/IPMI handoff interface for bootloader
 *
 * Communicates with the Baseboard Management Controller during boot
 * to report status, errors, and receive management commands.
 */

#ifndef EOS_BMC_HANDOFF_H
#define EOS_BMC_HANDOFF_H

#include "eos_types.h"

typedef enum {
    EOS_BMC_BOOT_START,
    EOS_BMC_BOOT_STAGE0,
    EOS_BMC_BOOT_STAGE1,
    EOS_BMC_BOOT_OS_LOADING,
    EOS_BMC_BOOT_COMPLETE,
    EOS_BMC_BOOT_FAILED
} eos_bmc_boot_phase_t;

typedef struct {
    uint32_t i2c_addr;
    int connected;
    eos_bmc_boot_phase_t phase;
    uint32_t error_code;
    uint32_t boot_count;
} eos_bmc_handoff_t;

int  eos_bmc_handoff_init(eos_bmc_handoff_t *bmc, uint32_t i2c_addr);
int  eos_bmc_handoff_report_phase(eos_bmc_handoff_t *bmc, eos_bmc_boot_phase_t phase);
int  eos_bmc_handoff_report_error(eos_bmc_handoff_t *bmc, uint32_t error_code);
int  eos_bmc_handoff_check_override(eos_bmc_handoff_t *bmc);
void eos_bmc_handoff_dump(const eos_bmc_handoff_t *bmc);

#endif /* EOS_BMC_HANDOFF_H */
