// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file eos_ecc.h
 * @brief ECC memory scrubbing and error reporting during boot
 *
 * Performs background scrubbing of ECC-protected DRAM to detect
 * and correct single-bit errors before they accumulate into
 * uncorrectable multi-bit errors. Reports errors to BMC.
 */

#ifndef EOS_ECC_H
#define EOS_ECC_H

#include "eos_types.h"

typedef struct {
    uint32_t base_addr;
    uint32_t size_bytes;
    uint32_t scrub_interval_ms;
    uint32_t correctable_errors;
    uint32_t uncorrectable_errors;
    uint32_t pages_scrubbed;
    uint32_t total_pages;
    int enabled;
    int scrub_complete;
} eos_ecc_ctx_t;

int  eos_ecc_init(eos_ecc_ctx_t *ctx, uint32_t base, uint32_t size);
int  eos_ecc_scrub(eos_ecc_ctx_t *ctx);
int  eos_ecc_check_region(eos_ecc_ctx_t *ctx, uint32_t addr, uint32_t len);
void eos_ecc_dump(const eos_ecc_ctx_t *ctx);

#endif /* EOS_ECC_H */
