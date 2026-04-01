// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file eos_device_table.h
 * @brief Device/resource table passed to OS (UEFI system table inspired)
 */

#ifndef EOS_DEVICE_TABLE_H
#define EOS_DEVICE_TABLE_H

#include "eos_types.h"

#ifdef __cplusplus
extern "C" {
#endif

#define EOS_DEVTABLE_MAGIC      0x45445654  /* "EDVT" */
#define EOS_DEVTABLE_VERSION    1
#define EOS_MAX_MEM_REGIONS     8
#define EOS_MAX_PERIPHERALS     16

typedef enum {
    EOS_MEM_USABLE     = 0,
    EOS_MEM_RESERVED   = 1,
    EOS_MEM_BOOTLOADER = 2,
    EOS_MEM_FIRMWARE   = 3,
    EOS_MEM_DMA        = 4,
    EOS_MEM_PERIPHERAL = 5,
} eos_mem_type_t;

typedef struct {
    uint32_t base;
    uint32_t size;
    eos_mem_type_t type;
    uint32_t attributes;
} eos_mem_region_t;

typedef enum {
    EOS_PERIPH_UART  = 0,
    EOS_PERIPH_SPI   = 1,
    EOS_PERIPH_I2C   = 2,
    EOS_PERIPH_GPIO  = 3,
    EOS_PERIPH_TIMER = 4,
    EOS_PERIPH_USB   = 5,
    EOS_PERIPH_CAN   = 6,
    EOS_PERIPH_ETH   = 7,
    EOS_PERIPH_ADC   = 8,
} eos_periph_type_t;

typedef struct {
    eos_periph_type_t type;
    uint8_t instance;
    uint32_t base_addr;
    uint16_t irq_num;
    uint32_t clock_hz;
    uint32_t flags;
} eos_periph_entry_t;

typedef struct {
    uint32_t magic;
    uint32_t version;
    uint32_t table_size;

    /* Board identification */
    uint32_t board_id;
    uint32_t board_revision;
    char board_name[32];

    /* Memory map */
    uint32_t mem_region_count;
    eos_mem_region_t mem_regions[EOS_MAX_MEM_REGIONS];

    /* Peripheral list */
    uint32_t periph_count;
    eos_periph_entry_t peripherals[EOS_MAX_PERIPHERALS];

    /* System clocks */
    uint32_t cpu_clock_hz;
    uint32_t bus_clock_hz;
    uint32_t periph_clock_hz;

    uint32_t crc32;
} eos_device_table_t;

int eos_device_table_init(eos_device_table_t *table, const char *board_name);
int eos_device_table_add_memory(eos_device_table_t *table, const eos_mem_region_t *region);
int eos_device_table_add_peripheral(eos_device_table_t *table, const eos_periph_entry_t *periph);
int eos_device_table_finalize(eos_device_table_t *table);
int eos_device_table_validate(const eos_device_table_t *table);

#ifdef __cplusplus
}
#endif

#endif /* EOS_DEVICE_TABLE_H */
