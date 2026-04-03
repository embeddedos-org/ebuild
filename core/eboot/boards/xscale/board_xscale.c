// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_xscale.c
 * @brief XScale board port (PXA270, Intel XScale)
 */

#include "eos_hal.h"
#include "eos_types.h"
#include "eos_device_table.h"

#define PXA270_FLASH_BASE    0x00000000
#define PXA270_FLASH_SIZE    (32 * 1024 * 1024)
#define PXA270_RAM_BASE      0xA0000000
#define PXA270_RAM_SIZE      (64 * 1024 * 1024)
#define PXA270_SLOT_A        0x00040000
#define PXA270_SLOT_B        0x00C40000
#define PXA270_RECOVERY      0x01840000
#define PXA270_BOOTCTL       0x01FFF000

static const eos_board_ops_t xscale_ops = {
    .flash_base       = PXA270_FLASH_BASE,
    .flash_size       = PXA270_FLASH_SIZE,
    .slot_a_addr      = PXA270_SLOT_A,
    .slot_b_addr      = PXA270_SLOT_B,
    .recovery_addr    = PXA270_RECOVERY,
    .bootctl_addr     = PXA270_BOOTCTL,
    .app_vector_offset = 0x00,
    .flash_read       = NULL,
    .flash_write      = NULL,
    .flash_erase      = NULL,
    .jump             = NULL,
};

void board_xscale_init_device_table(eos_device_table_t *table)
{
    eos_device_table_init(table, "PXA270-DevBoard");

    table->board_id = 0x0A02;
    table->board_revision = 1;
    table->cpu_clock_hz    = 624000000;
    table->bus_clock_hz    = 208000000;
    table->periph_clock_hz = 14745600;

    eos_mem_region_t flash_region = {
        .base = PXA270_FLASH_BASE,
        .size = PXA270_FLASH_SIZE,
        .type = EOS_MEM_FIRMWARE,
        .attributes = 0,
    };
    eos_device_table_add_memory(table, &flash_region);

    eos_mem_region_t ram_region = {
        .base = PXA270_RAM_BASE,
        .size = PXA270_RAM_SIZE,
        .type = EOS_MEM_USABLE,
        .attributes = 0,
    };
    eos_device_table_add_memory(table, &ram_region);

    eos_periph_entry_t uart0 = {
        .type = EOS_PERIPH_UART,
        .instance = 0,
        .base_addr = 0x40100000,
        .irq_num = 22,
        .clock_hz = 14745600,
        .flags = 0,
    };
    eos_device_table_add_peripheral(table, &uart0);
}

const eos_board_ops_t *board_xscale_get_ops(void)
{
    return &xscale_ops;
}
