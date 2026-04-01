// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_config.c
 * @brief Board configuration — apply memory, pins, interrupts, clocks
 *
 * Platform-agnostic orchestration. Actual register writes are
 * delegated to eos_board_config_ops_t provided by the board port.
 */

#include "eos_board_config.h"
#include "eos_hal.h"
#include <string.h>

static const eos_board_config_t *active_config = NULL;
static const eos_board_config_ops_t *config_ops = NULL;

void eos_board_config_set_ops(const eos_board_config_ops_t *ops)
{
    config_ops = ops;
}

int eos_board_config_apply(const eos_board_config_t *cfg)
{
    if (!cfg) return EOS_ERR_INVALID;

    active_config = cfg;

    /* 1. Apply clock configuration first (everything depends on clocks) */
    if (cfg->clocks && config_ops && config_ops->apply_clocks) {
        int rc = config_ops->apply_clocks(cfg->clocks);
        if (rc != EOS_OK) return rc;
    }

    /* 2. Apply memory regions (MPU setup) */
    if (cfg->memory && config_ops && config_ops->apply_memory) {
        for (uint8_t i = 0; i < cfg->mem_count; i++) {
            int rc = config_ops->apply_memory(&cfg->memory[i]);
            if (rc != EOS_OK) return rc;
        }
    }

    /* 3. Apply pin muxing */
    if (cfg->pins && config_ops && config_ops->apply_pin) {
        for (uint8_t i = 0; i < cfg->pin_count; i++) {
            int rc = config_ops->apply_pin(&cfg->pins[i]);
            if (rc != EOS_OK) return rc;
        }
    }

    /* 4. Apply interrupt configuration */
    if (cfg->irqs && config_ops && config_ops->apply_irq) {
        for (uint8_t i = 0; i < cfg->irq_count; i++) {
            int rc = config_ops->apply_irq(&cfg->irqs[i]);
            if (rc != EOS_OK) return rc;
        }
    }

    /* 5. Apply peripheral enables */
    if (cfg->peripherals && config_ops && config_ops->apply_periph) {
        for (uint8_t i = 0; i < cfg->periph_count; i++) {
            int rc = config_ops->apply_periph(&cfg->peripherals[i]);
            if (rc != EOS_OK) return rc;
        }
    }

    return EOS_OK;
}

const eos_board_config_t *eos_board_config_get(void)
{
    return active_config;
}

const eos_pin_config_t *eos_board_config_find_pin(eos_pin_function_t func,
                                                    uint8_t periph_index)
{
    if (!active_config || !active_config->pins) return NULL;

    for (uint8_t i = 0; i < active_config->pin_count; i++) {
        if (active_config->pins[i].function == func &&
            active_config->pins[i].periph_index == periph_index) {
            return &active_config->pins[i];
        }
    }
    return NULL;
}

const eos_mem_config_t *eos_board_config_find_memory(eos_mem_cfg_type_t type)
{
    if (!active_config || !active_config->memory) return NULL;

    for (uint8_t i = 0; i < active_config->mem_count; i++) {
        if (active_config->memory[i].type == type) {
            return &active_config->memory[i];
        }
    }
    return NULL;
}

const eos_periph_config_t *eos_board_config_find_periph(eos_periph_cfg_type_t type,
                                                         uint8_t index)
{
    if (!active_config || !active_config->peripherals) return NULL;

    for (uint8_t i = 0; i < active_config->periph_count; i++) {
        if (active_config->peripherals[i].type == type &&
            active_config->peripherals[i].index == index) {
            return &active_config->peripherals[i];
        }
    }
    return NULL;
}

uint32_t eos_board_config_total_ram(void)
{
    if (!active_config || !active_config->memory) return 0;

    uint32_t total = 0;
    for (uint8_t i = 0; i < active_config->mem_count; i++) {
        if (active_config->memory[i].type == EOS_MEM_TYPE_RAM ||
            active_config->memory[i].type == EOS_MEM_TYPE_CCMRAM ||
            active_config->memory[i].type == EOS_MEM_TYPE_DTCM) {
            total += active_config->memory[i].size;
        }
    }
    return total;
}

uint32_t eos_board_config_total_flash(void)
{
    if (!active_config || !active_config->memory) return 0;

    uint32_t total = 0;
    for (uint8_t i = 0; i < active_config->mem_count; i++) {
        if (active_config->memory[i].type == EOS_MEM_TYPE_FLASH) {
            total += active_config->memory[i].size;
        }
    }
    return total;
}

void eos_board_config_dump(void)
{
    if (!active_config) return;

    /* Board info — printed via HAL UART if available */
    (void)active_config->name;
    (void)active_config->mcu;

    /* In a real implementation, this would format and print
     * the config summary through eos_hal_uart_send() */
}
