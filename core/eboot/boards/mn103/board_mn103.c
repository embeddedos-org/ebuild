// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_mn103.c
 * @brief Panasonic AM33 (MN103) board port (Matsushita MN103)
 */

#include "eos_hal.h"
#include "eos_types.h"
#include "eos_device_table.h"

#define MN103_FLASH_BASE    0x00000000
#define MN103_FLASH_SIZE    (2 * 1024 * 1024)
#define MN103_RAM_BASE      0x48000000
#define MN103_RAM_SIZE      (8 * 1024 * 1024)
#define MN103_SLOT_A        0x00010000
#define MN103_SLOT_B        0x000D0000
#define MN103_RECOVERY      0x00190000
#define MN103_BOOTCTL       0x001FF000

static const eos_board_ops_t mn103_ops = {
    .flash_base       = MN103_FLASH_BASE,
    .flash_size       = MN103_FLASH_SIZE,
    .slot_a_addr      = MN103_SLOT_A,
    .slot_b_addr      = MN103_SLOT_B,
    .recovery_addr    = MN103_RECOVERY,
    .bootctl_addr     = MN103_BOOTCTL,
    .app_vector_offset = 0x00,
    .flash_read       = NULL,
    .flash_write      = NULL,
    .flash_erase      = NULL,
    .jump             = NULL,
};

void board_mn103_init_device_table(eos_device_table_t *table)
{
    eos_device_table_init(table, "Panasonic-AM33");

    table->board_id = 0x1001;
    table->board_revision = 1;
    table->cpu_clock_hz    = 200000000;
    table->bus_clock_hz    = 200000000;
    table->periph_clock_hz = 25000000;

    eos_mem_region_t flash_region = {
        .base = MN103_FLASH_BASE,
        .size = MN103_FLASH_SIZE,
        .type = EOS_MEM_FIRMWARE,
        .attributes = 0,
    };
    eos_device_table_add_memory(table, &flash_region);

    eos_mem_region_t ram_region = {
        .base = MN103_RAM_BASE,
        .size = MN103_RAM_SIZE,
        .type = EOS_MEM_USABLE,
        .attributes = 0,
    };
    eos_device_table_add_memory(table, &ram_region);

    eos_periph_entry_t uart0 = {
        .type = EOS_PERIPH_UART,
        .instance = 0,
        .base_addr = 0xD4002000,
        .irq_num = 9,
        .clock_hz = 25000000,
        .flags = 0,
    };
    eos_device_table_add_peripheral(table, &uart0);
}

const eos_board_ops_t *board_mn103_get_ops(void)
{
    return &mn103_ops;
}
