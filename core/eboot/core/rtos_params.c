// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file rtos_params.c
 * @brief Boot parameter block passed from bootloader to RTOS
 *
 * Stores clock configuration, memory map, peripheral state, and
 * boot metadata in a known shared memory location.
 */

#include "eos_rtos_boot.h"
#include "eos_types.h"
#include <string.h>

#define EOS_BOOT_PARAMS_MAGIC   0x45425041  /* "EBPA" */
#define EOS_BOOT_PARAMS_VERSION 1

typedef struct {
    uint32_t magic;
    uint32_t version;

    /* Clock configuration */
    uint32_t sysclk_hz;
    uint32_t hclk_hz;
    uint32_t pclk1_hz;
    uint32_t pclk2_hz;

    /* Memory map */
    uint32_t ram_start;
    uint32_t ram_size;
    uint32_t flash_start;
    uint32_t flash_size;
    uint32_t heap_start;
    uint32_t heap_size;

    /* RTOS info */
    eos_rtos_type_t rtos_type;
    uint32_t tick_rate_hz;
    uint32_t num_priorities;

    /* Boot metadata */
    eos_slot_t boot_slot;
    uint32_t firmware_version;
    uint32_t boot_count;
    eos_reset_reason_t reset_reason;

    /* Peripheral state flags */
    uint32_t uart_initialized;
    uint32_t spi_initialized;
    uint32_t i2c_initialized;
    uint32_t watchdog_active;

    uint32_t reserved[8];
    uint32_t crc32;
} eos_boot_params_t;

/* Shared memory location — linker script places this at a known address */
#if defined(__APPLE__)
static eos_boot_params_t boot_params __attribute__((section("__DATA,.shared_params")));
#elif defined(__GNUC__) || defined(__clang__)
static eos_boot_params_t boot_params __attribute__((section(".shared_params")));
#elif defined(_MSC_VER)
#pragma section(".shared_params", read, write)
static __declspec(allocate(".shared_params")) eos_boot_params_t boot_params;
#else
static eos_boot_params_t boot_params;
#endif

static uint32_t compute_params_crc(const eos_boot_params_t *p)
{
    const uint8_t *data = (const uint8_t *)p;
    size_t len = sizeof(eos_boot_params_t) - sizeof(uint32_t);
    uint32_t crc = 0xFFFFFFFF;

    for (size_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (int bit = 0; bit < 8; bit++) {
            if (crc & 1) {
                crc = (crc >> 1) ^ 0xEDB88320;
            } else {
                crc >>= 1;
            }
        }
    }
    return ~crc;
}

int eos_rtos_params_store(const eos_rtos_boot_config_t *cfg)
{
    if (!cfg) return EOS_ERR_INVALID;

    memset(&boot_params, 0, sizeof(boot_params));
    boot_params.magic = EOS_BOOT_PARAMS_MAGIC;
    boot_params.version = EOS_BOOT_PARAMS_VERSION;

    boot_params.rtos_type = cfg->type;
    boot_params.tick_rate_hz = cfg->tick_rate_hz;
    boot_params.num_priorities = cfg->num_priorities;
    boot_params.heap_start = cfg->heap_start;
    boot_params.heap_size = cfg->heap_size;

    boot_params.crc32 = compute_params_crc(&boot_params);

    return EOS_OK;
}

int eos_rtos_params_validate(void)
{
    if (boot_params.magic != EOS_BOOT_PARAMS_MAGIC) {
        return EOS_ERR_INVALID;
    }

    uint32_t expected = compute_params_crc(&boot_params);
    if (boot_params.crc32 != expected) {
        return EOS_ERR_CRC;
    }

    return EOS_OK;
}

const eos_boot_params_t *eos_rtos_params_get(void)
{
    if (eos_rtos_params_validate() != EOS_OK) {
        return NULL;
    }
    return &boot_params;
}
