// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_mips.c
 * @brief MIPS32 generic board port (MIPS32, kseg1 flash, kseg0 RAM)
 */

#include "eos_hal.h"
#include "eos_types.h"
#include "eos_device_table.h"

#define MIPS_FLASH_BASE     0x1FC00000
#define MIPS_FLASH_SIZE     (8 * 1024 * 1024)
#define MIPS_RAM_BASE       0x80000000
#define MIPS_RAM_SIZE       (32 * 1024 * 1024)
#define MIPS_SLOT_A         0x1FC40000
#define MIPS_SLOT_B         0x1FF40000
#define MIPS_RECOVERY       0x20240000
#define MIPS_BOOTCTL        0x203FF000

static const eos_board_ops_t mips_ops = {
    .flash_base       = MIPS_FLASH_BASE,
    .flash_size       = MIPS_FLASH_SIZE,
    .slot_a_addr      = MIPS_SLOT_A,
    .slot_b_addr      = MIPS_SLOT_B,
    .recovery_addr    = MIPS_RECOVERY,
    .bootctl_addr     = MIPS_BOOTCTL,
    .app_vector_offset = 0x00,
    .flash_read       = NULL,
    .flash_write      = NULL,
    .flash_erase      = NULL,
    .jump             = NULL,
};

void board_mips_init_device_table(eos_device_table_t *table)
{
    eos_device_table_init(table, "MIPS32-Generic");

    table->board_id = 0x0F01;
    table->board_revision = 1;
    table->cpu_clock_hz    = 400000000;
    table->bus_clock_hz    = 400000000;
    table->periph_clock_hz = 50000000;

    eos_mem_region_t flash_region = {
        .base = MIPS_FLASH_BASE,
        .size = MIPS_FLASH_SIZE,
        .type = EOS_MEM_FIRMWARE,
        .attributes = 0,
    };
    eos_device_table_add_memory(table, &flash_region);

    eos_mem_region_t ram_region = {
        .base = MIPS_RAM_BASE,
        .size = MIPS_RAM_SIZE,
        .type = EOS_MEM_USABLE,
        .attributes = 0,
    };
    eos_device_table_add_memory(table, &ram_region);

    eos_periph_entry_t uart0 = {
        .type = EOS_PERIPH_UART,
        .instance = 0,
        .base_addr = 0x180003F8,
        .irq_num = 4,
        .clock_hz = 50000000,
        .flags = 0,
    };
    eos_device_table_add_peripheral(table, &uart0);
}

const eos_board_ops_t *board_mips_get_ops(void)
{
    return &mips_ops;
}
