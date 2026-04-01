// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file eos_rtos_boot.h
 * @brief RTOS-specific boot support for eBootloader
 *
 * Detects RTOS type, configures MPU before jump, and passes boot
 * parameters to the RTOS entry point.
 */

#ifndef EOS_RTOS_BOOT_H
#define EOS_RTOS_BOOT_H

#include "eos_types.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    EOS_RTOS_NONE      = 0,
    EOS_RTOS_FREERTOS  = 1,
    EOS_RTOS_ZEPHYR    = 2,
    EOS_RTOS_NUTTX     = 3,
    EOS_RTOS_RTTHREAD  = 4,
    EOS_RTOS_CUSTOM    = 0xFF,
} eos_rtos_type_t;

typedef enum {
    EOS_MPU_DISABLED   = 0,
    EOS_MPU_PRIVILEGED = 1,
    EOS_MPU_PROTECTED  = 2,
} eos_mpu_mode_t;

typedef struct {
    eos_rtos_type_t type;
    uint32_t entry_addr;
    uint32_t stack_addr;
    uint32_t heap_start;
    uint32_t heap_size;
    eos_mpu_mode_t mpu_mode;
    uint32_t tick_rate_hz;
    uint32_t num_priorities;
} eos_rtos_boot_config_t;

/**
 * Detect the RTOS type from the firmware image header.
 */
eos_rtos_type_t eos_rtos_detect(uint32_t image_addr);

/**
 * Configure the MPU for the target RTOS before handoff.
 */
int eos_rtos_configure_mpu(const eos_rtos_boot_config_t *cfg);

/**
 * Prepare and jump to the RTOS entry point.
 */
int eos_rtos_boot(const eos_rtos_boot_config_t *cfg);

/**
 * Get a human-readable name for an RTOS type.
 */
const char *eos_rtos_type_name(eos_rtos_type_t type);

#ifdef __cplusplus
}
#endif

#endif /* EOS_RTOS_BOOT_H */
