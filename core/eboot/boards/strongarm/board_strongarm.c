// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_strongarm.c
 * @brief Intel StrongARM SA-1110 board port
 */

#include "eos_hal.h"
#include "eos_types.h"
#include "eos_device_table.h"

#define SA1110_FLASH_BASE   0x00000000
#define SA1110_FLASH_SIZE   (16 * 1024 * 1024)
#define SA1110_RAM_BASE     0xC0000000
#define SA1110_RAM_SIZE     (32 * 1024 * 1024)
#define SA1110_SLOT_A       0x00040000
#define SA1110_SLOT_B       0x00640000
#define SA1110_RECOVERY     0x00C40000
#define SA1110_BOOTCTL      0x00FF0000

#define SA1110_UART_BASE    0x80050000

static const eos_board_ops_t strongarm_ops = {
    .flash_base       = SA1110_FLASH_BASE,
    .flash_size       = SA1110_FLASH_SIZE,
    .slot_a_addr      = SA1110_SLOT_A,
    .slot_b_addr      = SA1110_SLOT_B,
    .recovery_addr    = SA1110_RECOVERY,
    .bootctl_addr     = SA1110_BOOTCTL,
    .app_vector_offset = 0x00,
    .flash_read       = NULL,
    .flash_write      = NULL,
    .flash_erase      = NULL,
    .jump             = NULL,
};

void board_strongarm_init_device_table(eos_device_table_t *table)
{
    eos_device_table_init(table, "StrongARM-SA1110");
    table->board_id = 0x0A01;
    table->board_revision = 1;
    table->cpu_clock_hz    = 206000000;
    table->bus_clock_hz    = 103000000;
    table->periph_clock_hz = 3686400;

    eos_mem_region_t flash_region = {
        .base = SA1110_FLASH_BASE, .size = SA1110_FLASH_SIZE,
        .type = EOS_MEM_FIRMWARE, .attributes = 0,
    };
    eos_device_table_add_memory(table, &flash_region);

    eos_mem_region_t ram_region = {
        .base = SA1110_RAM_BASE, .size = SA1110_RAM_SIZE,
        .type = EOS_MEM_USABLE, .attributes = 0,
    };
    eos_device_table_add_memory(table, &ram_region);

    eos_periph_entry_t uart0 = {
        .type = EOS_PERIPH_UART, .instance = 0,
        .base_addr = SA1110_UART_BASE, .irq_num = 15,
        .clock_hz = 3686400, .flags = 0,
    };
    eos_device_table_add_peripheral(table, &uart0);
}

const eos_board_ops_t *board_strongarm_get_ops(void)
{
    return &strongarm_ops;
}
