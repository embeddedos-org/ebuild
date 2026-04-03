// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_sh4.c
 * @brief SH-4 board port (SH7750, Hitachi SuperH)
 */

#include "eos_hal.h"
#include "eos_types.h"
#include "eos_device_table.h"

#define SH7750_FLASH_BASE    0x00000000
#define SH7750_FLASH_SIZE    (4 * 1024 * 1024)
#define SH7750_RAM_BASE      0x0C000000
#define SH7750_RAM_SIZE      (16 * 1024 * 1024)
#define SH7750_SLOT_A        0x00020000
#define SH7750_SLOT_B        0x001A0000
#define SH7750_RECOVERY      0x00320000
#define SH7750_BOOTCTL       0x003FF000

static const eos_board_ops_t sh4_ops = {
    .flash_base       = SH7750_FLASH_BASE,
    .flash_size       = SH7750_FLASH_SIZE,
    .slot_a_addr      = SH7750_SLOT_A,
    .slot_b_addr      = SH7750_SLOT_B,
    .recovery_addr    = SH7750_RECOVERY,
    .bootctl_addr     = SH7750_BOOTCTL,
    .app_vector_offset = 0x00,
    .flash_read       = NULL,
    .flash_write      = NULL,
    .flash_erase      = NULL,
    .jump             = NULL,
};

void board_sh4_init_device_table(eos_device_table_t *table)
{
    eos_device_table_init(table, "SH7750-DevBoard");

    table->board_id = 0x0C01;
    table->board_revision = 1;
    table->cpu_clock_hz    = 200000000;
    table->bus_clock_hz    = 100000000;
    table->periph_clock_hz = 33333333;

    eos_mem_region_t flash_region = {
        .base = SH7750_FLASH_BASE,
        .size = SH7750_FLASH_SIZE,
        .type = EOS_MEM_FIRMWARE,
        .attributes = 0,
    };
    eos_device_table_add_memory(table, &flash_region);

    eos_mem_region_t ram_region = {
        .base = SH7750_RAM_BASE,
        .size = SH7750_RAM_SIZE,
        .type = EOS_MEM_USABLE,
        .attributes = 0,
    };
    eos_device_table_add_memory(table, &ram_region);

    eos_periph_entry_t uart0 = {
        .type = EOS_PERIPH_UART,
        .instance = 0,
        .base_addr = 0xFFE80000,
        .irq_num = 40,
        .clock_hz = 33333333,
        .flags = 0,
    };
    eos_device_table_add_peripheral(table, &uart0);
}

const eos_board_ops_t *board_sh4_get_ops(void)
{
    return &sh4_ops;
}
