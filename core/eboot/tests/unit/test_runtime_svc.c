// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file test_runtime_svc.c
 * @brief Unit tests for runtime services (variable store)
 */

#include "eos_runtime_svc.h"
#include "eos_types.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static int tests_run = 0;
static int tests_passed = 0;

#define TEST(name) \
    static void name(void); \
    static void run_##name(void) { \
        eos_rtsvc_init(); \
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

TEST(test_set_get_variable)
{
    uint32_t value = 42;
    ASSERT(eos_rtsvc_set_variable("count", &value, sizeof(value)) == EOS_OK);

    uint32_t out = 0;
    uint32_t size = sizeof(out);
    ASSERT(eos_rtsvc_get_variable("count", &out, &size) == EOS_OK);
    ASSERT(out == 42);
    ASSERT(size == sizeof(uint32_t));
}

TEST(test_overwrite_variable)
{
    uint32_t v1 = 10, v2 = 20;
    eos_rtsvc_set_variable("x", &v1, sizeof(v1));
    eos_rtsvc_set_variable("x", &v2, sizeof(v2));

    uint32_t out = 0;
    uint32_t size = sizeof(out);
    eos_rtsvc_get_variable("x", &out, &size);
    ASSERT(out == 20);
}

TEST(test_delete_variable)
{
    uint32_t v = 99;
    eos_rtsvc_set_variable("temp", &v, sizeof(v));
    ASSERT(eos_rtsvc_delete_variable("temp") == EOS_OK);

    uint32_t out = 0;
    uint32_t size = sizeof(out);
    ASSERT(eos_rtsvc_get_variable("temp", &out, &size) != EOS_OK);
}

TEST(test_get_nonexistent)
{
    uint32_t out = 0;
    uint32_t size = sizeof(out);
    ASSERT(eos_rtsvc_get_variable("nope", &out, &size) != EOS_OK);
}

TEST(test_null_args)
{
    ASSERT(eos_rtsvc_set_variable(NULL, "x", 1) == EOS_ERR_INVALID);
    ASSERT(eos_rtsvc_get_variable(NULL, NULL, NULL) == EOS_ERR_INVALID);
    ASSERT(eos_rtsvc_delete_variable(NULL) == EOS_ERR_INVALID);
}

TEST(test_string_variable)
{
    const char *msg = "hello boot";
    eos_rtsvc_set_variable("msg", msg, (uint32_t)(strlen(msg) + 1));

    char out[64] = {0};
    uint32_t size = sizeof(out);
    ASSERT(eos_rtsvc_get_variable("msg", out, &size) == EOS_OK);
    ASSERT(strcmp(out, "hello boot") == 0);
}

TEST(test_next_boot_slot)
{
    ASSERT(eos_rtsvc_get_next_boot() == EOS_SLOT_NONE);
    ASSERT(eos_rtsvc_set_next_boot(EOS_SLOT_B) == EOS_OK);
    ASSERT(eos_rtsvc_get_next_boot() == EOS_SLOT_B);
    ASSERT(eos_rtsvc_set_next_boot(EOS_SLOT_A) == EOS_OK);
    ASSERT(eos_rtsvc_get_next_boot() == EOS_SLOT_A);
}

TEST(test_time)
{
    ASSERT(eos_rtsvc_get_time() == 0);
}

int main(void)
{
    printf("=== eBootloader: Runtime Services Unit Tests ===\n\n");

    run_test_set_get_variable();
    run_test_overwrite_variable();
    run_test_delete_variable();
    run_test_get_nonexistent();
    run_test_null_args();
    run_test_string_variable();
    run_test_next_boot_slot();
    run_test_time();

    tests_run = 8;
    printf("\n%d/%d tests passed\n", tests_passed, tests_run);
    return (tests_passed == tests_run) ? 0 : 1;
}
