// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file boot_log.c
 * @brief Boot event logging
 *
 * Circular log stored in a dedicated flash sector.
 * Entries are append-only with a head pointer in the boot control block.
 */

#include "eos_types.h"
#include "eos_hal.h"
#include <string.h>

static uint32_t log_head = 0;
static bool log_initialized = false;

void eos_boot_log_init(uint32_t head)
{
    log_head = head % EOS_BOOT_LOG_MAX;
    log_initialized = true;
}

void eos_boot_log_append(uint32_t event, uint32_t slot, uint32_t detail)
{
    if (!log_initialized)
        return;

    const eos_board_ops_t *ops = eos_hal_get_ops();
    if (!ops)
        return;

    eos_boot_log_entry_t entry;
    entry.timestamp = eos_hal_get_tick_ms();
    entry.event     = event;
    entry.slot      = slot;
    entry.detail    = detail;

    uint32_t offset = log_head * sizeof(eos_boot_log_entry_t);
    uint32_t addr   = ops->log_addr + offset;

    eos_hal_flash_write(addr, &entry, sizeof(entry));

    log_head = (log_head + 1) % EOS_BOOT_LOG_MAX;
}

uint32_t eos_boot_log_get_head(void)
{
    return log_head;
}

int eos_boot_log_read(uint32_t index, eos_boot_log_entry_t *out)
{
    if (!out || index >= EOS_BOOT_LOG_MAX)
        return EOS_ERR_INVALID;

    const eos_board_ops_t *ops = eos_hal_get_ops();
    if (!ops)
        return EOS_ERR_GENERIC;

    uint32_t offset = index * sizeof(eos_boot_log_entry_t);
    uint32_t addr   = ops->log_addr + offset;

    return eos_hal_flash_read(addr, out, sizeof(*out));
}

int eos_boot_log_clear(void)
{
    const eos_board_ops_t *ops = eos_hal_get_ops();
    if (!ops)
        return EOS_ERR_GENERIC;

    size_t log_size = EOS_BOOT_LOG_MAX * sizeof(eos_boot_log_entry_t);
    int rc = eos_hal_flash_erase(ops->log_addr, log_size);
    if (rc != EOS_OK)
        return rc;

    log_head = 0;
    return EOS_OK;
}
