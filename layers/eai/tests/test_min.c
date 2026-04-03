// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include <stdio.h>
#include <string.h>
#include "eai/common.h"
#include "eai_min/eai_min.h"

static int tests_run = 0, tests_passed = 0, tests_failed = 0;
#define TEST(name) do { tests_run++; printf("  TEST %-40s ", #name); } while(0)
#define PASS() do { tests_passed++; printf("[PASS]\n"); } while(0)
#define FAIL(msg) do { tests_failed++; printf("[FAIL] %s\n", msg); } while(0)

static void test_memory_lite(void)
{
    TEST(memory_lite);
    eai_mem_lite_t mem;
    eai_status_t st = eai_mem_lite_init(&mem, NULL);
    if (st != EAI_OK) { FAIL("init failed"); return; }

    eai_mem_lite_set(&mem, "x", "hello", false);

    const char *val = eai_mem_lite_get(&mem, "x");
    if (!val || strcmp(val, "hello") != 0) {
        FAIL("expected 'hello' for key 'x'");
        return;
    }

    const char *unknown = eai_mem_lite_get(&mem, "nonexistent");
    if (unknown != NULL) {
        FAIL("expected NULL for unknown key");
        return;
    }
    PASS();
}

static void test_router_mode(void)
{
    TEST(router_mode);
    eai_min_router_t router;
    eai_min_router_init(&router, EAI_ROUTE_LOCAL);

    eai_inference_input_t input = {0};
    input.text = "test input";
    input.text_len = 10;

    eai_route_target_t decision = eai_min_router_decide(&router, &input);
    if (decision != EAI_ROUTE_LOCAL) {
        FAIL("expected EAI_ROUTE_LOCAL for local mode");
        return;
    }
    PASS();
}

int main(void)
{
    printf("=== EAI Min Tests ===\n");

    test_memory_lite();
    test_router_mode();

    printf("\nResults: %d/%d passed, %d failed\n", tests_passed, tests_run, tests_failed);
    return tests_failed > 0 ? 1 : 0;
}
