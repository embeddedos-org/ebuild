// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_x86.c
 * @brief x86 board port (i486/Pentium, legacy PC)
 */

#include "eos_hal.h"
#include "eos_types.h"
#include "eos_device_table.h"

#define X86_FLASH_BASE    0xFFF00000
#define X86_FLASH_SIZE    (16 * 1024 * 1024)
#define X86_RAM_BASE      0x00100000
#define X86_RAM_SIZE      (64 * 1024 * 1024)
#define X86_SLOT_A        0xFF040000
#define X86_SLOT_B        0xFF640000
#define X86_RECOVERY      0xFFC40000
#define X86_BOOTCTL       0xFFEFF000

static const eos_board_ops_t x86_ops = {
    .flash_base       = X86_FLASH_BASE,
    .flash_size       = X86_FLASH_SIZE,
    .slot_a_addr      = X86_SLOT_A,
    .slot_b_addr      = X86_SLOT_B,
    .recovery_addr    = X86_RECOVERY,
    .bootctl_addr     = X86_BOOTCTL,
    .app_vector_offset = 0x00,
    .flash_read       = NULL,
    .flash_write      = NULL,
    .flash_erase      = NULL,
    .jump             = NULL,
};

void board_x86_init_device_table(eos_device_table_t *table)
{
    eos_device_table_init(table, "x86-GenericPC");

    table->board_id = 0x0E01;
    table->board_revision = 1;
    table->cpu_clock_hz    = 100000000;
    table->bus_clock_hz    = 33333333;
    table->periph_clock_hz = 1843200;

    eos_mem_region_t flash_region = {
        .base = X86_FLASH_BASE,
        .size = X86_FLASH_SIZE,
        .type = EOS_MEM_FIRMWARE,
        .attributes = 0,
    };
    eos_device_table_add_memory(table, &flash_region);

    eos_mem_region_t ram_region = {
        .base = X86_RAM_BASE,
        .size = X86_RAM_SIZE,
        .type = EOS_MEM_USABLE,
        .attributes = 0,
    };
    eos_device_table_add_memory(table, &ram_region);

    eos_periph_entry_t uart0 = {
        .type = EOS_PERIPH_UART,
        .instance = 0,
        .base_addr = 0x3F8,
        .irq_num = 4,
        .clock_hz = 1843200,
        .flags = 0,
    };
    eos_device_table_add_peripheral(table, &uart0);
}

const eos_board_ops_t *board_x86_get_ops(void)
{
    return &x86_ops;
}
