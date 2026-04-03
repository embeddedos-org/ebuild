// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file device_table.c
 * @brief Device/resource table — memory map, peripherals, board info
 */

#include "eos_device_table.h"
#include <string.h>

static uint32_t compute_table_crc(const eos_device_table_t *t)
{
    const uint8_t *data = (const uint8_t *)t;
    size_t len = sizeof(eos_device_table_t) - sizeof(uint32_t);
    uint32_t crc = 0xFFFFFFFF;

    for (size_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (int bit = 0; bit < 8; bit++) {
            if (crc & 1) crc = (crc >> 1) ^ 0xEDB88320;
            else         crc >>= 1;
        }
    }
    return ~crc;
}

int eos_device_table_init(eos_device_table_t *table, const char *board_name)
{
    if (!table) return EOS_ERR_INVALID;

    memset(table, 0, sizeof(eos_device_table_t));
    table->magic = EOS_DEVTABLE_MAGIC;
    table->version = EOS_DEVTABLE_VERSION;
    table->table_size = sizeof(eos_device_table_t);

    if (board_name) {
        size_t len = strlen(board_name);
        if (len >= sizeof(table->board_name)) len = sizeof(table->board_name) - 1;
        memcpy(table->board_name, board_name, len);
    }

    return EOS_OK;
}

int eos_device_table_add_memory(eos_device_table_t *table, const eos_mem_region_t *region)
{
    if (!table || !region) return EOS_ERR_INVALID;
    if (table->mem_region_count >= EOS_MAX_MEM_REGIONS) return EOS_ERR_FULL;

    table->mem_regions[table->mem_region_count++] = *region;
    return EOS_OK;
}

int eos_device_table_add_peripheral(eos_device_table_t *table, const eos_periph_entry_t *periph)
{
    if (!table || !periph) return EOS_ERR_INVALID;
    if (table->periph_count >= EOS_MAX_PERIPHERALS) return EOS_ERR_FULL;

    table->peripherals[table->periph_count++] = *periph;
    return EOS_OK;
}

int eos_device_table_finalize(eos_device_table_t *table)
{
    if (!table) return EOS_ERR_INVALID;

    table->crc32 = compute_table_crc(table);
    return EOS_OK;
}

int eos_device_table_validate(const eos_device_table_t *table)
{
    if (!table) return EOS_ERR_INVALID;
    if (table->magic != EOS_DEVTABLE_MAGIC) return EOS_ERR_INVALID;
    if (table->version != EOS_DEVTABLE_VERSION) return EOS_ERR_VERSION;

    uint32_t expected = compute_table_crc(table);
    if (table->crc32 != expected) return EOS_ERR_CRC;

    return EOS_OK;
}
