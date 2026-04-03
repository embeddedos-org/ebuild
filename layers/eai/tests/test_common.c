// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include <stdio.h>
#include <string.h>
#include "eai/common.h"

static int tests_run = 0, tests_passed = 0, tests_failed = 0;
#define TEST(name) do { tests_run++; printf("  TEST %-40s ", #name); } while(0)
#define PASS() do { tests_passed++; printf("[PASS]\n"); } while(0)
#define FAIL(msg) do { tests_failed++; printf("[FAIL] %s\n", msg); } while(0)

static eai_status_t dummy_exec(const eai_kv_t *args, int arg_count, eai_tool_result_t *result)
{
    (void)args; (void)arg_count;
    const char *msg = "ok";
    memcpy(result->data, msg, 3);
    result->len = 2;
    result->status = EAI_OK;
    return EAI_OK;
}

static void test_config_init(void)
{
    TEST(config_init);
    eai_config_t cfg;
    eai_status_t st = eai_config_init(&cfg);
    if (st != EAI_OK) { FAIL("init returned error"); return; }
    if (cfg.variant != EAI_VARIANT_MIN) { FAIL("wrong variant"); return; }
    if (cfg.mode != EAI_MODE_LOCAL) { FAIL("wrong mode"); return; }
    PASS();
}

static void test_tool_registry(void)
{
    TEST(tool_registry);
    eai_tool_registry_t reg;
    eai_tool_registry_init(&reg);

    eai_tool_t tool = {0};
    strncpy(tool.name, "test.tool", EAI_TOOL_NAME_MAX - 1);
    tool.description = "A test tool";
    tool.exec = dummy_exec;

    eai_status_t st = eai_tool_register(&reg, &tool);
    if (st != EAI_OK) { FAIL("register failed"); return; }

    eai_tool_t *found = eai_tool_find(&reg, "test.tool");
    if (!found) { FAIL("find returned NULL"); return; }
    if (strcmp(found->name, "test.tool") != 0) { FAIL("wrong name"); return; }
    PASS();
}

static void test_tool_exec(void)
{
    TEST(tool_exec);
    eai_tool_registry_t reg;
    eai_tool_registry_init(&reg);

    eai_tool_t tool = {0};
    strncpy(tool.name, "exec.tool", EAI_TOOL_NAME_MAX - 1);
    tool.exec = dummy_exec;
    eai_tool_register(&reg, &tool);

    eai_tool_t *found = eai_tool_find(&reg, "exec.tool");
    if (!found) { FAIL("find returned NULL"); return; }

    eai_tool_result_t result = {0};
    eai_status_t st = eai_tool_exec(found, NULL, 0, &result);
    if (st != EAI_OK) { FAIL("exec failed"); return; }
    if (result.len != 2) { FAIL("wrong result len"); return; }
    PASS();
}

static void test_security_ctx(void)
{
    TEST(security_ctx);
    eai_security_ctx_t ctx;
    eai_security_ctx_init(&ctx, "test-agent");

    eai_security_grant(&ctx, "tool.read");

    if (!eai_security_check(&ctx, "tool.read")) { FAIL("should allow tool.read"); return; }
    if (eai_security_check(&ctx, "tool.write")) { FAIL("should deny tool.write"); return; }
    PASS();
}

static void test_status_strings(void)
{
    TEST(status_strings);
    const char *ok = eai_status_str(EAI_OK);
    if (!ok) { FAIL("EAI_OK returned NULL"); return; }
    const char *inv = eai_status_str(EAI_ERR_INVALID);
    if (!inv) { FAIL("EAI_ERR_INVALID returned NULL"); return; }
    PASS();
}

int main(void)
{
    printf("=== EAI Common Tests ===\n\n");

    test_config_init();
    test_tool_registry();
    test_tool_exec();
    test_security_ctx();
    test_status_strings();

    printf("\n=== Results: %d/%d passed, %d failed ===\n",
           tests_passed, tests_run, tests_failed);
    return tests_failed > 0 ? 1 : 0;
}
