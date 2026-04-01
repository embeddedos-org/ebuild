// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file test_board_registry.c
 * @brief Unit tests for board registry (runtime multi-board selection)
 */

#include "eos_board_registry.h"
#include "eos_hal.h"
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

/* Mock board ops */
static const eos_board_ops_t mock_ops_a = { .flash_base = 0x08000000, .flash_size = 1024*1024 };
static const eos_board_ops_t mock_ops_b = { .flash_base = 0x00000000, .flash_size = 512*1024 };

static const eos_board_ops_t *get_ops_a(void) { return &mock_ops_a; }
static const eos_board_ops_t *get_ops_b(void) { return &mock_ops_b; }
static bool detect_b(void) { return true; }

static const eos_board_info_t board_a = {
    .name = "board-a", .platform = EOS_PLATFORM_ARM_CM4,
    .board_id = 0x0001, .get_ops = get_ops_a, .detect = NULL,
};

static const eos_board_info_t board_b = {
    .name = "board-b", .platform = EOS_PLATFORM_RISCV64,
    .board_id = 0x0002, .get_ops = get_ops_b, .detect = detect_b,
};

TEST(test_register_and_count)
{
    ASSERT(eos_board_register(&board_a) == EOS_OK);
    ASSERT(eos_board_register(&board_b) == EOS_OK);
    ASSERT(eos_board_count() >= 2);
}

TEST(test_find_by_name)
{
    eos_board_register(&board_a);
    eos_board_register(&board_b);

    const eos_board_info_t *found = eos_board_find("board-a");
    ASSERT(found != NULL);
    ASSERT(found->board_id == 0x0001);
    ASSERT(found->platform == EOS_PLATFORM_ARM_CM4);
}

TEST(test_find_nonexistent)
{
    ASSERT(eos_board_find("no-such-board") == NULL);
    ASSERT(eos_board_find(NULL) == NULL);
}

TEST(test_detect)
{
    eos_board_register(&board_a);
    eos_board_register(&board_b);

    const eos_board_info_t *detected = eos_board_detect();
    ASSERT(detected != NULL);
    /* board_b has detect() that returns true */
    ASSERT(strcmp(detected->name, "board-b") == 0);
}

TEST(test_activate)
{
    eos_board_register(&board_a);

    int rc = eos_board_activate("board-a");
    ASSERT(rc == EOS_OK);

    const eos_board_ops_t *ops = eos_hal_get_ops();
    ASSERT(ops != NULL);
    ASSERT(ops->flash_base == 0x08000000);
}

TEST(test_activate_nonexistent)
{
    ASSERT(eos_board_activate("nope") != EOS_OK);
}

TEST(test_get_by_index)
{
    eos_board_register(&board_a);
    eos_board_register(&board_b);

    uint32_t count = eos_board_count();
    ASSERT(count >= 2);

    const eos_board_info_t *b = eos_board_get(0);
    ASSERT(b != NULL);
}

TEST(test_register_null)
{
    ASSERT(eos_board_register(NULL) != EOS_OK);
}

int main(void)
{
    printf("=== eBootloader: Board Registry Unit Tests ===\n\n");

    run_test_register_and_count();
    run_test_find_by_name();
    run_test_find_nonexistent();
    run_test_detect();
    run_test_activate();
    run_test_activate_nonexistent();
    run_test_get_by_index();
    run_test_register_null();

    tests_run = 8;
    printf("\n%d/%d tests passed\n", tests_passed, tests_run);
    return (tests_passed == tests_run) ? 0 : 1;
}
