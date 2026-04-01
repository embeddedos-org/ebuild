// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file test_device_table.c
 * @brief Unit tests for UEFI-style device table
 */

#include "eos_device_table.h"
#include "eos_types.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static int tests_run = 0;
static int tests_passed = 0;

#define TEST(name) \
    static void name(void); \
    static void run_##name(void) { \
        printf("  %-50s ", #name); \
        name(); \
        tests_passed++; \
        printf("[PASS]\n"); \
    } \
    static void name(void)

#define ASSERT(cond) do { \
    if (!(cond)) { \
        printf("[FAIL] %s:%d: %s\n", __FILE__, __LINE__, #cond); \
        exit(1); \
    } \
} while(0)

TEST(test_init)
{
    eos_device_table_t table;
    int rc = eos_device_table_init(&table, "TestBoard");
    ASSERT(rc == EOS_OK);
    ASSERT(table.magic == EOS_DEVTABLE_MAGIC);
    ASSERT(table.version == EOS_DEVTABLE_VERSION);
    ASSERT(strcmp(table.board_name, "TestBoard") == 0);
    ASSERT(table.mem_region_count == 0);
    ASSERT(table.periph_count == 0);
}

TEST(test_init_null)
{
    ASSERT(eos_device_table_init(NULL, "X") == EOS_ERR_INVALID);
}

TEST(test_add_memory)
{
    eos_device_table_t table;
    eos_device_table_init(&table, "Test");

    eos_mem_region_t flash = { .base = 0x08000000, .size = 1024*1024,
                                .type = EOS_MEM_FIRMWARE, .attributes = 0 };
    eos_mem_region_t ram = { .base = 0x20000000, .size = 128*1024,
                              .type = EOS_MEM_USABLE, .attributes = 0 };

    ASSERT(eos_device_table_add_memory(&table, &flash) == EOS_OK);
    ASSERT(eos_device_table_add_memory(&table, &ram) == EOS_OK);
    ASSERT(table.mem_region_count == 2);
    ASSERT(table.mem_regions[0].base == 0x08000000);
    ASSERT(table.mem_regions[1].size == 128*1024);
}

TEST(test_add_peripheral)
{
    eos_device_table_t table;
    eos_device_table_init(&table, "Test");

    eos_periph_entry_t uart = { .type = EOS_PERIPH_UART, .instance = 0,
                                 .base_addr = 0x40004400, .irq_num = 38,
                                 .clock_hz = 42000000 };

    ASSERT(eos_device_table_add_peripheral(&table, &uart) == EOS_OK);
    ASSERT(table.periph_count == 1);
    ASSERT(table.peripherals[0].base_addr == 0x40004400);
}

TEST(test_memory_overflow)
{
    eos_device_table_t table;
    eos_device_table_init(&table, "Test");

    eos_mem_region_t region = { .base = 0, .size = 4096, .type = EOS_MEM_USABLE };
    for (int i = 0; i < EOS_MAX_MEM_REGIONS; i++) {
        ASSERT(eos_device_table_add_memory(&table, &region) == EOS_OK);
    }
    ASSERT(eos_device_table_add_memory(&table, &region) == EOS_ERR_FULL);
}

TEST(test_finalize_and_validate)
{
    eos_device_table_t table;
    eos_device_table_init(&table, "CRCTest");

    eos_mem_region_t ram = { .base = 0x20000000, .size = 64*1024, .type = EOS_MEM_USABLE };
    eos_device_table_add_memory(&table, &ram);

    ASSERT(eos_device_table_finalize(&table) == EOS_OK);
    ASSERT(table.crc32 != 0);
    ASSERT(eos_device_table_validate(&table) == EOS_OK);
}

TEST(test_corrupt_crc_fails)
{
    eos_device_table_t table;
    eos_device_table_init(&table, "Corrupt");
    eos_device_table_finalize(&table);

    table.board_id = 0xDEAD;  /* corrupt after finalize */
    ASSERT(eos_device_table_validate(&table) == EOS_ERR_CRC);
}

int main(void)
{
    printf("=== eBootloader: Device Table Unit Tests ===\n\n");

    run_test_init();
    run_test_init_null();
    run_test_add_memory();
    run_test_add_peripheral();
    run_test_memory_overflow();
    run_test_finalize_and_validate();
    run_test_corrupt_crc_fails();

    tests_run = 7;
    printf("\n%d/%d tests passed\n", tests_passed, tests_run);
    return (tests_passed == tests_run) ? 0 : 1;
}
