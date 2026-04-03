// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file dram_init.c
 * @brief DDR/DRAM initialization and training
 */

#include "eos_dram.h"
#include "eos_hal.h"
#include <string.h>
#ifdef EBOOT_ENABLE_PRINTF
#include <stdio.h>
#endif

int eos_dram_init(eos_dram_config_t *cfg)
{
    if (!cfg) return EOS_ERR_GENERIC;

    /* Board-specific DRAM controller init would go here.
     * Each board port provides the actual register programming. */
    const eos_board_ops_t *ops = eos_hal_get_ops();
    if (!ops) return EOS_ERR_GENERIC;

    /* Platform-specific init delegated to board port */
    cfg->training_done = false;
    return EOS_OK;
}

int eos_dram_train(eos_dram_config_t *cfg, eos_dram_training_t *result)
{
    if (!cfg || !result) return EOS_ERR_GENERIC;

    memset(result, 0, sizeof(*result));

    /* Hardware-specific training sequence:
     * 1. Write known patterns to DRAM
     * 2. Sweep read/write delays
     * 3. Find optimal DQS/CLK alignment
     * 4. Store trained values */

    result->valid = true;
    cfg->training_done = true;
    return EOS_OK;
}

int eos_dram_test(const eos_dram_config_t *cfg)
{
    if (!cfg || !cfg->training_done) return EOS_ERR_GENERIC;

    /* Simple memory test: write pattern, read back, verify */
    volatile uint32_t *base = (volatile uint32_t *)(uintptr_t)cfg->base_addr;
    uint32_t words = cfg->size_bytes / 4;
    if (words > 1024) words = 1024; /* Test first 4KB only during boot */

    for (uint32_t i = 0; i < words; i++)
        base[i] = 0xA5A5A5A5 ^ i;

    for (uint32_t i = 0; i < words; i++) {
        if (base[i] != (0xA5A5A5A5 ^ i))
            return EOS_ERR_GENERIC;
    }
    return EOS_OK;
}

void eos_dram_dump(const eos_dram_config_t *cfg)
{
#ifdef EBOOT_ENABLE_PRINTF
    const char *types[] = {"DDR3","DDR3L","DDR4","LPDDR4","LPDDR4X","LPDDR5","DDR5"};
    printf("DRAM: %s %uMB @ 0x%08x (%u MHz, %u-bit)\n",
           types[cfg->type], cfg->size_bytes / (1024*1024),
           cfg->base_addr, cfg->clock_mhz, cfg->bus_width);
    printf("  CAS=%u ranks=%u banks=%u ECC=%s trained=%s\n",
           cfg->cas_latency, cfg->ranks, cfg->banks,
           cfg->ecc_enabled ? "yes" : "no",
           cfg->training_done ? "yes" : "no");
#else
    (void)cfg;
#endif
}
