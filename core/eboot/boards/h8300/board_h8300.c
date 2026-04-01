// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_h8300.c
 * @brief H8/300H board port (H83069, Renesas H8)
 */

#include "eos_hal.h"
#include "eos_types.h"
#include "eos_device_table.h"

#define H83069_FLASH_BASE    0x00000000
#define H83069_FLASH_SIZE    (512 * 1024)
#define H83069_RAM_BASE      0x00400000
#define H83069_RAM_SIZE      (128 * 1024)
#define H83069_SLOT_A        0x00008000
#define H83069_SLOT_B        0x00038000
#define H83069_RECOVERY      0x00068000
#define H83069_BOOTCTL       0x0007F000

static const eos_board_ops_t h8300_ops = {
    .flash_base       = H83069_FLASH_BASE,
    .flash_size       = H83069_FLASH_SIZE,
    .slot_a_addr      = H83069_SLOT_A,
    .slot_b_addr      = H83069_SLOT_B,
    .recovery_addr    = H83069_RECOVERY,
    .bootctl_addr     = H83069_BOOTCTL,
    .app_vector_offset = 0x00,
    .flash_read       = NULL,
    .flash_write      = NULL,
    .flash_erase      = NULL,
    .jump             = NULL,
};

void board_h8300_init_device_table(eos_device_table_t *table)
{
    eos_device_table_init(table, "H83069-DevBoard");

    table->board_id = 0x0D01;
    table->board_revision = 1;
    table->cpu_clock_hz    = 25000000;
    table->bus_clock_hz    = 25000000;
    table->periph_clock_hz = 12500000;

    eos_mem_region_t flash_region = {
        .base = H83069_FLASH_BASE,
        .size = H83069_FLASH_SIZE,
        .type = EOS_MEM_FIRMWARE,
        .attributes = 0,
    };
    eos_device_table_add_memory(table, &flash_region);

    eos_mem_region_t ram_region = {
        .base = H83069_RAM_BASE,
        .size = H83069_RAM_SIZE,
        .type = EOS_MEM_USABLE,
        .attributes = 0,
    };
    eos_device_table_add_memory(table, &ram_region);

    eos_periph_entry_t uart0 = {
        .type = EOS_PERIPH_UART,
        .instance = 0,
        .base_addr = 0xFFFFB0,
        .irq_num = 52,
        .clock_hz = 12500000,
        .flags = 0,
    };
    eos_device_table_add_peripheral(table, &uart0);
}

const eos_board_ops_t *board_h8300_get_ops(void)
{
    return &h8300_ops;
}
