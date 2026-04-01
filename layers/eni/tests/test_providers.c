// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include <stdio.h>
#include <string.h>
#include "eni/common.h"

static int tests_run = 0, tests_passed = 0, tests_failed = 0;
#define TEST(name) do { tests_run++; printf("  TEST %-40s ", #name); } while(0)
#define PASS() do { tests_passed++; printf("[PASS]\n"); } while(0)
#define FAIL(msg) do { tests_failed++; printf("[FAIL] %s\n", msg); } while(0)

extern const eni_provider_ops_t eni_provider_simulator_ops;

static void test_simulator_ops_exist(void)
{
    TEST(simulator_ops_exist);
    if (!eni_provider_simulator_ops.name) { FAIL("name is NULL"); return; }
    if (!eni_provider_simulator_ops.init) { FAIL("init is NULL"); return; }
    if (!eni_provider_simulator_ops.poll) { FAIL("poll is NULL"); return; }
    PASS();
}

static void test_provider_init(void)
{
    TEST(provider_init);
    eni_provider_t prov;
    eni_status_t st = eni_provider_init(&prov, &eni_provider_simulator_ops, "sim0", NULL);
    if (st != ENI_OK) { FAIL("init failed"); return; }
    if (strcmp(prov.name, "sim0") != 0) { FAIL("wrong name"); return; }
    PASS();
}

int main(void)
{
    printf("=== ENI Provider Tests ===\n\n");
    test_simulator_ops_exist();
    test_provider_init();
    printf("\n=== Results: %d/%d passed, %d failed ===\n",
           tests_passed, tests_run, tests_failed);
    return tests_failed > 0 ? 1 : 0;
}
