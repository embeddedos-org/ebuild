// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_stm32h7.c
 * @brief STM32H7 board port (Cortex-M7, RTOS-capable)
 */

#include "eos_hal.h"
#include "eos_types.h"
#include "eos_device_table.h"

#define STM32H7_FLASH_BASE  0x08000000
#define STM32H7_FLASH_SIZE  (2 * 1024 * 1024)
#define STM32H7_RAM_BASE    0x20000000
#define STM32H7_RAM_SIZE    (512 * 1024)
#define STM32H7_SLOT_A      0x08020000
#define STM32H7_SLOT_B      0x08100000
#define STM32H7_RECOVERY    0x081E0000
#define STM32H7_BOOTCTL     0x081F0000

static const eos_board_ops_t stm32h7_ops = {
    .flash_base       = STM32H7_FLASH_BASE,
    .flash_size       = STM32H7_FLASH_SIZE,
    .slot_a_addr      = STM32H7_SLOT_A,
    .slot_b_addr      = STM32H7_SLOT_B,
    .recovery_addr    = STM32H7_RECOVERY,
    .bootctl_addr     = STM32H7_BOOTCTL,
    .app_vector_offset = 0x00,
    .flash_read       = NULL,
    .flash_write      = NULL,
    .flash_erase      = NULL,
    .jump             = NULL,
};

void board_stm32h7_init_device_table(eos_device_table_t *table)
{
    eos_device_table_init(table, "STM32H743ZI");

    table->board_id = 0x0450;
    table->board_revision = 1;
    table->cpu_clock_hz   = 480000000;
    table->bus_clock_hz   = 240000000;
    table->periph_clock_hz = 120000000;

    eos_mem_region_t flash_region = {
        .base = STM32H7_FLASH_BASE,
        .size = STM32H7_FLASH_SIZE,
        .type = EOS_MEM_FIRMWARE,
        .attributes = 0,
    };
    eos_device_table_add_memory(table, &flash_region);

    eos_mem_region_t ram_region = {
        .base = STM32H7_RAM_BASE,
        .size = STM32H7_RAM_SIZE,
        .type = EOS_MEM_USABLE,
        .attributes = 0,
    };
    eos_device_table_add_memory(table, &ram_region);

    eos_periph_entry_t uart1 = {
        .type = EOS_PERIPH_UART,
        .instance = 0,
        .base_addr = 0x40011000,
        .irq_num = 37,
        .clock_hz = 120000000,
        .flags = 0,
    };
    eos_device_table_add_peripheral(table, &uart1);
}

const eos_board_ops_t *board_stm32h7_get_ops(void)
{
    return &stm32h7_ops;
}
