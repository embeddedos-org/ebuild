// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_v850.c
 * @brief Renesas V850E board port (V850E core)
 */

#include "eos_hal.h"
#include "eos_types.h"
#include "eos_device_table.h"

#define V850_FLASH_BASE     0x00000000
#define V850_FLASH_SIZE     (1024 * 1024)
#define V850_RAM_BASE       0x03FF0000
#define V850_RAM_SIZE       (128 * 1024)
#define V850_SLOT_A         0x00008000
#define V850_SLOT_B         0x00068000
#define V850_RECOVERY       0x000C8000
#define V850_BOOTCTL        0x000FF000

static const eos_board_ops_t v850_ops = {
    .flash_base       = V850_FLASH_BASE,
    .flash_size       = V850_FLASH_SIZE,
    .slot_a_addr      = V850_SLOT_A,
    .slot_b_addr      = V850_SLOT_B,
    .recovery_addr    = V850_RECOVERY,
    .bootctl_addr     = V850_BOOTCTL,
    .app_vector_offset = 0x00,
    .flash_read       = NULL,
    .flash_write      = NULL,
    .flash_erase      = NULL,
    .jump             = NULL,
};

void board_v850_init_device_table(eos_device_table_t *table)
{
    eos_device_table_init(table, "Renesas-V850E");

    table->board_id = 0x1301;
    table->board_revision = 1;
    table->cpu_clock_hz    = 32000000;
    table->bus_clock_hz    = 32000000;
    table->periph_clock_hz = 16000000;

    eos_mem_region_t flash_region = {
        .base = V850_FLASH_BASE,
        .size = V850_FLASH_SIZE,
        .type = EOS_MEM_FIRMWARE,
        .attributes = 0,
    };
    eos_device_table_add_memory(table, &flash_region);

    eos_mem_region_t ram_region = {
        .base = V850_RAM_BASE,
        .size = V850_RAM_SIZE,
        .type = EOS_MEM_USABLE,
        .attributes = 0,
    };
    eos_device_table_add_memory(table, &ram_region);

    eos_periph_entry_t uart0 = {
        .type = EOS_PERIPH_UART,
        .instance = 0,
        .base_addr = 0xFFFFF600,
        .irq_num = 18,
        .clock_hz = 16000000,
        .flags = 0,
    };
    eos_device_table_add_peripheral(table, &uart0);
}

const eos_board_ops_t *board_v850_get_ops(void)
{
    return &v850_ops;
}
