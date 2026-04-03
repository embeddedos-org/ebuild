// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file bmc_handoff.c
 * @brief BMC/IPMI boot handoff
 */

#include "eos_bmc_handoff.h"
#include <string.h>
#include <stdio.h>

int eos_bmc_handoff_init(eos_bmc_handoff_t *bmc, uint32_t i2c_addr)
{
    if (!bmc) return -1;
    memset(bmc, 0, sizeof(*bmc));
    bmc->i2c_addr = i2c_addr;
    bmc->phase = EOS_BMC_BOOT_START;
    /* I2C probe to check if BMC is present — platform-specific */
    bmc->connected = 1;
    return 0;
}

int eos_bmc_handoff_report_phase(eos_bmc_handoff_t *bmc, eos_bmc_boot_phase_t phase)
{
    if (!bmc || !bmc->connected) return -1;
    bmc->phase = phase;
    /* Send IPMI OEM command to BMC: boot phase update
     * Actual I2C/IPMB transaction is board-specific */
    return 0;
}

int eos_bmc_handoff_report_error(eos_bmc_handoff_t *bmc, uint32_t error_code)
{
    if (!bmc || !bmc->connected) return -1;
    bmc->error_code = error_code;
    bmc->phase = EOS_BMC_BOOT_FAILED;
    /* Send IPMI SEL entry to BMC */
    return 0;
}

int eos_bmc_handoff_check_override(eos_bmc_handoff_t *bmc)
{
    if (!bmc || !bmc->connected) return 0;
    /* Check if BMC wants to override boot (e.g., force recovery, PXE boot)
     * Read IPMI OEM variable from BMC */
    return 0;
}

void eos_bmc_handoff_dump(const eos_bmc_handoff_t *bmc)
{
#if !defined(EOS_BARE_METAL)
    const char *phases[] = {"START","STAGE0","STAGE1","OS_LOADING","COMPLETE","FAILED"};
    printf("BMC Handoff: addr=0x%x %s phase=%s err=0x%x boots=%u\n",
           bmc->i2c_addr, bmc->connected ? "connected" : "disconnected",
           phases[bmc->phase], bmc->error_code, bmc->boot_count);
#else
    (void)bmc;
#endif
}
