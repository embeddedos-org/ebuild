// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file mpu_boot.c
 * @brief MPU configuration during boot
 */

#include "eos_mpu_boot.h"
#include <string.h>
#ifdef EBOOT_ENABLE_PRINTF
#include <stdio.h>
#endif

int eos_mpu_init(eos_mpu_ctx_t *ctx)
{
    if (!ctx) return -1;
    memset(ctx, 0, sizeof(*ctx));
    ctx->hw_regions = 8; /* Default for Cortex-M4/M7 */
    return 0;
}

int eos_mpu_add_region(eos_mpu_ctx_t *ctx, uint32_t base, uint32_t size,
                       eos_mpu_access_t access, bool exec, bool cache)
{
    if (!ctx || ctx->count >= EOS_MPU_MAX_REGIONS) return -1;
    if (ctx->count >= ctx->hw_regions) return -1;

    eos_mpu_region_t *r = &ctx->regions[ctx->count++];
    r->base_addr = base;
    r->size = size;
    r->access = access;
    r->executable = exec;
    r->cacheable = cache;
    r->bufferable = cache;
    r->shareable = false;
    r->enabled = true;
    return 0;
}

int eos_mpu_set_default(eos_mpu_ctx_t *ctx)
{
    if (!ctx) return -1;
    ctx->count = 0;

    /* Flash — read + execute, cacheable */
    eos_mpu_add_region(ctx, 0x08000000, 0x200000, EOS_MPU_FULL_RO, true, true);
    /* RAM — read + write, no execute, cacheable */
    eos_mpu_add_region(ctx, 0x20000000, 0x100000, EOS_MPU_FULL_RW, false, true);
    /* Peripherals — read + write, no execute, no cache */
    eos_mpu_add_region(ctx, 0x40000000, 0x20000000, EOS_MPU_FULL_RW, false, false);
    /* System — privileged only */
    eos_mpu_add_region(ctx, 0xE0000000, 0x10000, EOS_MPU_PRIV_RW, false, false);

    return 0;
}

int eos_mpu_apply(const eos_mpu_ctx_t *ctx)
{
    if (!ctx) return -1;

    /* ARM Cortex-M MPU programming:
     * 1. Disable MPU
     * 2. Program each region (RBAR + RASR registers)
     * 3. Enable MPU with PRIVDEFENA
     *
     * Actual register writes are platform-specific. */

#if defined(__ARM_ARCH) && (__ARM_ARCH <= 7) && !defined(__aarch64__)
    /* MPU->CTRL disable */
    *((volatile uint32_t *)0xE000ED94) = 0;

    for (int i = 0; i < ctx->count; i++) {
        const eos_mpu_region_t *r = &ctx->regions[i];
        if (!r->enabled) continue;

        /* Calculate region size encoding (log2 - 1) */
        uint32_t size_bits = 0;
        uint32_t sz = r->size;
        while (sz > 1) { sz >>= 1; size_bits++; }

        uint32_t rbar = r->base_addr | (1 << 4) | i;
        uint32_t rasr = (r->access << 24) | (size_bits << 1) | 1;
        if (!r->executable) rasr |= (1 << 28);
        if (r->cacheable) rasr |= (1 << 17);
        if (r->bufferable) rasr |= (1 << 16);
        if (r->shareable) rasr |= (1 << 18);

        *((volatile uint32_t *)0xE000ED9C) = rbar;
        *((volatile uint32_t *)0xE000EDA0) = rasr;
    }

    /* MPU->CTRL enable with PRIVDEFENA */
    *((volatile uint32_t *)0xE000ED94) = 5;

#elif defined(__ARM_ARCH_7R__)
    /* ---- Cortex-R5 PMSAv7 MPU via CP15 ---- */

    /* Disable MPU: clear bit 0 of SCTLR (CP15 c1, c0, 0) */
    uint32_t sctlr;
    __asm volatile ("mrc p15, 0, %0, c1, c0, 0" : "=r"(sctlr));
    sctlr &= ~1u;
    __asm volatile ("mcr p15, 0, %0, c1, c0, 0" :: "r"(sctlr));
    __asm volatile ("isb");

    for (int i = 0; i < ctx->count; i++) {
        const eos_mpu_region_t *r = &ctx->regions[i];
        if (!r->enabled) continue;

        /* Select region (RGNR — CP15 c6, c2, 0) */
        uint32_t rgnr = (uint32_t)i;
        __asm volatile ("mcr p15, 0, %0, c6, c2, 0" :: "r"(rgnr));

        /* Calculate region size encoding (log2 - 1) */
        uint32_t size_bits = 0;
        uint32_t sz = r->size;
        while (sz > 1) { sz >>= 1; size_bits++; }

        /* DRBAR — Region Base Address Register (CP15 c6, c1, 0) */
        __asm volatile ("mcr p15, 0, %0, c6, c1, 0" :: "r"(r->base_addr));

        /* DRSR — Region Size and Enable Register (CP15 c6, c1, 2) */
        uint32_t drsr = (size_bits << 1) | 1;  /* size + enable */
        __asm volatile ("mcr p15, 0, %0, c6, c1, 2" :: "r"(drsr));

        /* DRACR — Region Access Control Register (CP15 c6, c1, 4) */
        uint32_t dracr = (r->access << 8);
        if (!r->executable) dracr |= (1 << 12);  /* XN bit */
        if (r->cacheable)   dracr |= (1 << 1);   /* C bit */
        if (r->bufferable)  dracr |= (1 << 0);   /* B bit */
        if (r->shareable)   dracr |= (1 << 2);   /* S bit */
        __asm volatile ("mcr p15, 0, %0, c6, c1, 4" :: "r"(dracr));
    }

    /* Enable MPU + background region (SCTLR bits 0 and 17) */
    __asm volatile ("mrc p15, 0, %0, c1, c0, 0" : "=r"(sctlr));
    sctlr |= (1 << 0) | (1 << 17);  /* M + BR */
    __asm volatile ("mcr p15, 0, %0, c1, c0, 0" :: "r"(sctlr));
    __asm volatile ("isb");

#endif

    return 0;
}

int eos_mpu_disable(void)
{
#if defined(__ARM_ARCH) && (__ARM_ARCH <= 7) && !defined(__aarch64__) && !defined(__ARM_ARCH_7R__)
    *((volatile uint32_t *)0xE000ED94) = 0;
#elif defined(__ARM_ARCH_7R__)
    uint32_t sctlr;
    __asm volatile ("mrc p15, 0, %0, c1, c0, 0" : "=r"(sctlr));
    sctlr &= ~1u;
    __asm volatile ("mcr p15, 0, %0, c1, c0, 0" :: "r"(sctlr));
    __asm volatile ("isb");
#endif
    return 0;
}

void eos_mpu_dump(const eos_mpu_ctx_t *ctx)
{
#ifdef EBOOT_ENABLE_PRINTF
    const char *access_str[] = {"NONE","P_RW","--","FULL_RW","--","P_RO","FULL_RO"};
    printf("MPU: %d regions (HW supports %d)\n", ctx->count, ctx->hw_regions);
    for (int i = 0; i < ctx->count; i++) {
        const eos_mpu_region_t *r = &ctx->regions[i];
        printf("  [%d] 0x%08x +0x%x %s %s%s%s\n",
               i, r->base_addr, r->size,
               access_str[r->access],
               r->executable ? "X" : "-",
               r->cacheable ? "C" : "-",
               r->enabled ? "" : " (disabled)");
    }
#else
    (void)ctx;
#endif
}
