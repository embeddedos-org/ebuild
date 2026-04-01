// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_m68k.c
 * @brief ColdFire MCF5307 board port (ColdFire V3)
 */

#include "eos_hal.h"
#include "eos_types.h"
#include "eos_device_table.h"

#define M68K_FLASH_BASE     0xFFE00000
#define M68K_FLASH_SIZE     (2 * 1024 * 1024)
#define M68K_RAM_BASE       0x00000000
#define M68K_RAM_SIZE       (4 * 1024 * 1024)
#define M68K_SLOT_A         0xFFE10000
#define M68K_SLOT_B         0xFFED0000
#define M68K_RECOVERY       0xFFF90000
#define M68K_BOOTCTL        0xFFFFF000

static const eos_board_ops_t m68k_ops = {
    .flash_base       = M68K_FLASH_BASE,
    .flash_size       = M68K_FLASH_SIZE,
    .slot_a_addr      = M68K_SLOT_A,
    .slot_b_addr      = M68K_SLOT_B,
    .recovery_addr    = M68K_RECOVERY,
    .bootctl_addr     = M68K_BOOTCTL,
    .app_vector_offset = 0x08,
    .flash_read       = NULL,
    .flash_write      = NULL,
    .flash_erase      = NULL,
    .jump             = NULL,
};

void board_m68k_init_device_table(eos_device_table_t *table)
{
    eos_device_table_init(table, "ColdFire-MCF5307");

    table->board_id = 0x1201;
    table->board_revision = 1;
    table->cpu_clock_hz    = 90000000;
    table->bus_clock_hz    = 90000000;
    table->periph_clock_hz = 45000000;

    eos_mem_region_t flash_region = {
        .base = M68K_FLASH_BASE,
        .size = M68K_FLASH_SIZE,
        .type = EOS_MEM_FIRMWARE,
        .attributes = 0,
    };
    eos_device_table_add_memory(table, &flash_region);

    eos_mem_region_t ram_region = {
        .base = M68K_RAM_BASE,
        .size = M68K_RAM_SIZE,
        .type = EOS_MEM_USABLE,
        .attributes = 0,
    };
    eos_device_table_add_memory(table, &ram_region);

    eos_periph_entry_t uart0 = {
        .type = EOS_PERIPH_UART,
        .instance = 0,
        .base_addr = 0x10000140,
        .irq_num = 73,
        .clock_hz = 45000000,
        .flags = 0,
    };
    eos_device_table_add_peripheral(table, &uart0);
}

const eos_board_ops_t *board_m68k_get_ops(void)
{
    return &m68k_ops;
}
