// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_sparc.c
 * @brief LEON3 SPARC V8 board port (LEON3, APBUART)
 */

#include "eos_hal.h"
#include "eos_types.h"
#include "eos_device_table.h"

#define SPARC_FLASH_BASE    0x00000000
#define SPARC_FLASH_SIZE    (4 * 1024 * 1024)
#define SPARC_RAM_BASE      0x40000000
#define SPARC_RAM_SIZE      (16 * 1024 * 1024)
#define SPARC_SLOT_A        0x00020000
#define SPARC_SLOT_B        0x001A0000
#define SPARC_RECOVERY      0x00320000
#define SPARC_BOOTCTL       0x003FF000

static const eos_board_ops_t sparc_ops = {
    .flash_base       = SPARC_FLASH_BASE,
    .flash_size       = SPARC_FLASH_SIZE,
    .slot_a_addr      = SPARC_SLOT_A,
    .slot_b_addr      = SPARC_SLOT_B,
    .recovery_addr    = SPARC_RECOVERY,
    .bootctl_addr     = SPARC_BOOTCTL,
    .app_vector_offset = 0x00,
    .flash_read       = NULL,
    .flash_write      = NULL,
    .flash_erase      = NULL,
    .jump             = NULL,
};

void board_sparc_init_device_table(eos_device_table_t *table)
{
    eos_device_table_init(table, "LEON3-SPARC");

    table->board_id = 0x1401;
    table->board_revision = 1;
    table->cpu_clock_hz    = 80000000;
    table->bus_clock_hz    = 80000000;
    table->periph_clock_hz = 80000000;

    eos_mem_region_t flash_region = {
        .base = SPARC_FLASH_BASE,
        .size = SPARC_FLASH_SIZE,
        .type = EOS_MEM_FIRMWARE,
        .attributes = 0,
    };
    eos_device_table_add_memory(table, &flash_region);

    eos_mem_region_t ram_region = {
        .base = SPARC_RAM_BASE,
        .size = SPARC_RAM_SIZE,
        .type = EOS_MEM_USABLE,
        .attributes = 0,
    };
    eos_device_table_add_memory(table, &ram_region);

    eos_periph_entry_t uart0 = {
        .type = EOS_PERIPH_UART,
        .instance = 0,
        .base_addr = 0x80000100,
        .irq_num = 2,
        .clock_hz = 80000000,
        .flags = 0,
    };
    eos_device_table_add_peripheral(table, &uart0);
}

const eos_board_ops_t *board_sparc_get_ops(void)
{
    return &sparc_ops;
}
