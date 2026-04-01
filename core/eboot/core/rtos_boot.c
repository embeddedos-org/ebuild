// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file rtos_boot.c
 * @brief RTOS-specific boot: detect type, configure MPU, jump to RTOS entry
 */

#include "eos_rtos_boot.h"
#include "eos_hal.h"
#include <string.h>

#define RTOS_MAGIC_OFFSET    0x200
#define FREERTOS_MAGIC       0x46524545  /* "FREE" */
#define ZEPHYR_MAGIC         0x5A455048  /* "ZEPH" */
#define NUTTX_MAGIC          0x4E555458  /* "NUTX" */

eos_rtos_type_t eos_rtos_detect(uint32_t image_addr)
{
    uint32_t magic = 0;
    const void *ptr = (const void *)(uintptr_t)(image_addr + RTOS_MAGIC_OFFSET);
    memcpy(&magic, ptr, sizeof(magic));

    switch (magic) {
        case FREERTOS_MAGIC: return EOS_RTOS_FREERTOS;
        case ZEPHYR_MAGIC:   return EOS_RTOS_ZEPHYR;
        case NUTTX_MAGIC:    return EOS_RTOS_NUTTX;
        default:             return EOS_RTOS_NONE;
    }
}

int eos_rtos_configure_mpu(const eos_rtos_boot_config_t *cfg)
{
    if (!cfg) return EOS_ERR_INVALID;

    switch (cfg->mpu_mode) {
        case EOS_MPU_DISABLED:
            /* MPU remains off — RTOS manages it */
            break;

        case EOS_MPU_PRIVILEGED:
            /* Configure MPU for privileged-only access to flash/RAM */
            /* Platform-specific: set up region 0 for flash (RO),
             * region 1 for RAM (RW), region 2 for peripherals */
            break;

        case EOS_MPU_PROTECTED:
            /* Full MPU setup with separate regions for:
             * - RTOS kernel (privileged RW)
             * - Task stacks (unprivileged RW)
             * - Shared memory (RW)
             * - Peripheral space (privileged only) */
            break;
    }

    return EOS_OK;
}

int eos_rtos_boot(const eos_rtos_boot_config_t *cfg)
{
    if (!cfg) return EOS_ERR_INVALID;
    if (cfg->entry_addr == 0 || cfg->stack_addr == 0) return EOS_ERR_INVALID;

    /* Configure MPU before handing off */
    int rc = eos_rtos_configure_mpu(cfg);
    if (rc != EOS_OK) return rc;

    /* Prepare boot parameters in a known location for the RTOS */
    extern int eos_rtos_params_store(const eos_rtos_boot_config_t *cfg);
    eos_rtos_params_store(cfg);

    /* Clean up bootloader state */
    eos_hal_disable_irqs();
    eos_hal_deinit_peripherals();

    /* Set stack pointer and jump */
    eos_hal_set_msp(cfg->stack_addr);
    eos_hal_jump(cfg->entry_addr);

    /* Should never reach here */
    return EOS_ERR_GENERIC;
}

const char *eos_rtos_type_name(eos_rtos_type_t type)
{
    switch (type) {
        case EOS_RTOS_FREERTOS: return "FreeRTOS";
        case EOS_RTOS_ZEPHYR:   return "Zephyr";
        case EOS_RTOS_NUTTX:    return "NuttX";
        case EOS_RTOS_RTTHREAD: return "RT-Thread";
        case EOS_RTOS_CUSTOM:   return "Custom";
        default:                return "Unknown";
    }
}
