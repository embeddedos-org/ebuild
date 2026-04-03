// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include <stdio.h>
#include <string.h>
#include "eai/common.h"
#include "eai_fw/eai_framework.h"

static int tests_run = 0, tests_passed = 0, tests_failed = 0;
#define TEST(name) do { tests_run++; printf("  TEST %-40s ", #name); } while(0)
#define PASS() do { tests_passed++; printf("[PASS]\n"); } while(0)
#define FAIL(msg) do { tests_failed++; printf("[FAIL] %s\n", msg); } while(0)

static void test_policy_init(void)
{
    TEST(policy_init);
    eai_fw_policy_t pol;
    eai_status_t st = eai_fw_policy_init(&pol);
    if (st != EAI_OK) { FAIL("init failed"); return; }
    if (pol.rule_count != 0) { FAIL("expected 0 rules"); return; }
    PASS();
}

static void test_policy_check(void)
{
    TEST(policy_check);
    eai_fw_policy_t pol;
    eai_fw_policy_init(&pol);

    eai_policy_rule_t rule = {
        .subject   = "orchestrator",
        .resource  = "tool1",
        .operation = "exec",
        .action    = EAI_POLICY_ALLOW,
    };
    eai_fw_policy_add_rule(&pol, &rule);

    eai_policy_action_t act = eai_fw_policy_check(&pol, "orchestrator", "tool1", "exec");
    if (act != EAI_POLICY_ALLOW) { FAIL("should allow orchestrator/tool1/exec"); return; }

    act = eai_fw_policy_check(&pol, "orchestrator", "tool2", "exec");
    if (act != EAI_POLICY_ALLOW) { FAIL("default policy should allow unregistered resource"); return; }
    PASS();
}

static void test_observability_counters(void)
{
    TEST(observability_counters);
    eai_fw_observability_t obs;
    eai_status_t st = eai_fw_obs_init(&obs, true);
    if (st != EAI_OK) { FAIL("obs init failed"); return; }

    eai_fw_obs_counter_inc(&obs, "events", 1.0);
    eai_fw_obs_counter_inc(&obs, "events", 1.0);
    eai_fw_obs_counter_inc(&obs, "events", 1.0);

    PASS();
}

int main(void)
{
    printf("=== EAI Framework Tests ===\n\n");

    test_policy_init();
    test_policy_check();
    test_observability_counters();

    printf("\n=== Results: %d/%d passed, %d failed ===\n",
           tests_passed, tests_run, tests_failed);
    return tests_failed > 0 ? 1 : 0;
}
