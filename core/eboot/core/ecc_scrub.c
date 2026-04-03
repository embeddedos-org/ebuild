// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file ecc_scrub.c
 * @brief ECC memory scrubbing during boot
 */

#include "eos_ecc.h"
#include <string.h>
#include <stdio.h>

int eos_ecc_init(eos_ecc_ctx_t *ctx, uint32_t base, uint32_t size)
{
    if (!ctx) return -1;
    memset(ctx, 0, sizeof(*ctx));
    ctx->base_addr = base;
    ctx->size_bytes = size;
    ctx->total_pages = size / 4096;
    ctx->scrub_interval_ms = 100;
    ctx->enabled = 1;
    return 0;
}

int eos_ecc_scrub(eos_ecc_ctx_t *ctx)
{
    if (!ctx || !ctx->enabled) return -1;

    volatile uint32_t *p = (volatile uint32_t *)(uintptr_t)ctx->base_addr;
    uint32_t words = ctx->size_bytes / 4;

    for (uint32_t i = 0; i < words; i++) {
        volatile uint32_t val = p[i];
        (void)val;
    }

    ctx->pages_scrubbed = ctx->total_pages;
    ctx->scrub_complete = 1;
    return 0;
}

int eos_ecc_check_region(eos_ecc_ctx_t *ctx, uint32_t addr, uint32_t len)
{
    if (!ctx) return -1;
    volatile uint32_t *p = (volatile uint32_t *)(uintptr_t)addr;
    uint32_t words = len / 4;

    for (uint32_t i = 0; i < words; i++) {
        volatile uint32_t val = p[i];
        (void)val;
    }
    return 0;
}

void eos_ecc_dump(const eos_ecc_ctx_t *ctx)
{
#if !defined(EOS_BARE_METAL)
    printf("ECC: base=0x%08x size=%uMB pages=%u/%u CE=%u UE=%u %s\n",
           ctx->base_addr, ctx->size_bytes / (1024*1024),
           ctx->pages_scrubbed, ctx->total_pages,
           ctx->correctable_errors, ctx->uncorrectable_errors,
           ctx->scrub_complete ? "complete" : "in-progress");
#else
    (void)ctx;
#endif
}
