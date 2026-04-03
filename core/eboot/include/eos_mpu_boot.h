// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file eos_mpu_boot.h
 * @brief MPU configuration during boot — memory protection setup before OS handoff
 *
 * Configures the ARM MPU (Memory Protection Unit) or MMU before
 * jumping to the application. Sets up regions for flash, RAM,
 * peripherals, and stack with appropriate access permissions.
 */

#ifndef EOS_MPU_BOOT_H
#define EOS_MPU_BOOT_H

#include "eos_types.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    EOS_MPU_NO_ACCESS   = 0,
    EOS_MPU_PRIV_RW     = 1,
    EOS_MPU_FULL_RW     = 3,
    EOS_MPU_PRIV_RO     = 5,
    EOS_MPU_FULL_RO     = 6
} eos_mpu_access_t;

typedef struct {
    uint32_t base_addr;
    uint32_t size;
    eos_mpu_access_t access;
    bool     executable;
    bool     cacheable;
    bool     bufferable;
    bool     shareable;
    bool     enabled;
} eos_mpu_region_t;

#define EOS_MPU_MAX_REGIONS 16

typedef struct {
    eos_mpu_region_t regions[EOS_MPU_MAX_REGIONS];
    int count;
    int hw_regions;     /* Number of MPU regions supported by hardware */
    bool enabled;
} eos_mpu_ctx_t;

int  eos_mpu_init(eos_mpu_ctx_t *ctx);
int  eos_mpu_add_region(eos_mpu_ctx_t *ctx, uint32_t base, uint32_t size,
                        eos_mpu_access_t access, bool exec, bool cache);
int  eos_mpu_set_default(eos_mpu_ctx_t *ctx); /* flash RX, RAM RW, periph RW-no-exec */
int  eos_mpu_apply(const eos_mpu_ctx_t *ctx);
int  eos_mpu_disable(void);
void eos_mpu_dump(const eos_mpu_ctx_t *ctx);

#ifdef __cplusplus
}
#endif
#endif /* EOS_MPU_BOOT_H */
