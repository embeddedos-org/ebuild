// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_nrf52.c
 * @brief nRF52 board port (BLE SoC, Cortex-M4F)
 */

#include "eos_hal.h"
#include "eos_types.h"
#include "eos_device_table.h"

#define NRF52_FLASH_BASE    0x00000000
#define NRF52_FLASH_SIZE    (1024 * 1024)
#define NRF52_RAM_BASE      0x20000000
#define NRF52_RAM_SIZE      (256 * 1024)
#define NRF52_SLOT_A        0x00026000
#define NRF52_SLOT_B        0x00080000
#define NRF52_RECOVERY      0x000E0000
#define NRF52_BOOTCTL       0x000FF000

static const eos_board_ops_t nrf52_ops = {
    .flash_base       = NRF52_FLASH_BASE,
    .flash_size       = NRF52_FLASH_SIZE,
    .slot_a_addr      = NRF52_SLOT_A,
    .slot_b_addr      = NRF52_SLOT_B,
    .recovery_addr    = NRF52_RECOVERY,
    .bootctl_addr     = NRF52_BOOTCTL,
    .app_vector_offset = 0x00,
    .flash_read       = NULL,
    .flash_write      = NULL,
    .flash_erase      = NULL,
    .jump             = NULL,
};

void board_nrf52_init_device_table(eos_device_table_t *table)
{
    eos_device_table_init(table, "nRF52840-DK");

    table->board_id = 0x0152;
    table->board_revision = 1;
    table->cpu_clock_hz    = 64000000;
    table->bus_clock_hz    = 64000000;
    table->periph_clock_hz = 16000000;

    eos_mem_region_t flash_region = {
        .base = NRF52_FLASH_BASE,
        .size = NRF52_FLASH_SIZE,
        .type = EOS_MEM_FIRMWARE,
        .attributes = 0,
    };
    eos_device_table_add_memory(table, &flash_region);

    eos_mem_region_t ram_region = {
        .base = NRF52_RAM_BASE,
        .size = NRF52_RAM_SIZE,
        .type = EOS_MEM_USABLE,
        .attributes = 0,
    };
    eos_device_table_add_memory(table, &ram_region);

    eos_periph_entry_t uart0 = {
        .type = EOS_PERIPH_UART,
        .instance = 0,
        .base_addr = 0x40002000,
        .irq_num = 2,
        .clock_hz = 16000000,
        .flags = 0,
    };
    eos_device_table_add_peripheral(table, &uart0);
}

const eos_board_ops_t *board_nrf52_get_ops(void)
{
    return &nrf52_ops;
}
