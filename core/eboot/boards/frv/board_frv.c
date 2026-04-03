// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_frv.c
 * @brief FR-V board port (FR450, Fujitsu FR-V)
 */

#include "eos_hal.h"
#include "eos_types.h"
#include "eos_device_table.h"

#define FR450_FLASH_BASE    0x00000000
#define FR450_FLASH_SIZE    (4 * 1024 * 1024)
#define FR450_RAM_BASE      0x20000000
#define FR450_RAM_SIZE      (16 * 1024 * 1024)
#define FR450_SLOT_A        0x00020000
#define FR450_SLOT_B        0x001A0000
#define FR450_RECOVERY      0x00320000
#define FR450_BOOTCTL       0x003FF000

static const eos_board_ops_t frv_ops = {
    .flash_base       = FR450_FLASH_BASE,
    .flash_size       = FR450_FLASH_SIZE,
    .slot_a_addr      = FR450_SLOT_A,
    .slot_b_addr      = FR450_SLOT_B,
    .recovery_addr    = FR450_RECOVERY,
    .bootctl_addr     = FR450_BOOTCTL,
    .app_vector_offset = 0x00,
    .flash_read       = NULL,
    .flash_write      = NULL,
    .flash_erase      = NULL,
    .jump             = NULL,
};

void board_frv_init_device_table(eos_device_table_t *table)
{
    eos_device_table_init(table, "FR450-DevBoard");

    table->board_id = 0x0B01;
    table->board_revision = 1;
    table->cpu_clock_hz    = 400000000;
    table->bus_clock_hz    = 100000000;
    table->periph_clock_hz = 50000000;

    eos_mem_region_t flash_region = {
        .base = FR450_FLASH_BASE,
        .size = FR450_FLASH_SIZE,
        .type = EOS_MEM_FIRMWARE,
        .attributes = 0,
    };
    eos_device_table_add_memory(table, &flash_region);

    eos_mem_region_t ram_region = {
        .base = FR450_RAM_BASE,
        .size = FR450_RAM_SIZE,
        .type = EOS_MEM_USABLE,
        .attributes = 0,
    };
    eos_device_table_add_memory(table, &ram_region);

    eos_periph_entry_t uart0 = {
        .type = EOS_PERIPH_UART,
        .instance = 0,
        .base_addr = 0xFEFF9600,
        .irq_num = 49,
        .clock_hz = 50000000,
        .flags = 0,
    };
    eos_device_table_add_peripheral(table, &uart0);
}

const eos_board_ops_t *board_frv_get_ops(void)
{
    return &frv_ops;
}
