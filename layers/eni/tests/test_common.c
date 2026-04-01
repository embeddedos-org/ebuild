// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include <stdio.h>
#include <string.h>
#include <assert.h>
#include "eni/common.h"

static int tests_run    = 0;
static int tests_passed = 0;
static int tests_failed = 0;

#define TEST(name) \
    do { \
        tests_run++; \
        printf("  TEST %-40s ", #name); \
    } while (0)

#define PASS() \
    do { \
        tests_passed++; \
        printf("[PASS]\n"); \
    } while (0)

#define FAIL(msg) \
    do { \
        tests_failed++; \
        printf("[FAIL] %s\n", msg); \
    } while (0)

static void test_event_init(void)
{
    TEST(event_init);
    eni_event_t ev;
    eni_status_t st = eni_event_init(&ev, ENI_EVENT_INTENT, "test-source");
    if (st != ENI_OK) { FAIL("init returned error"); return; }
    if (ev.type != ENI_EVENT_INTENT) { FAIL("wrong type"); return; }
    if (strcmp(ev.source, "test-source") != 0) { FAIL("wrong source"); return; }
    if (ev.version != 1) { FAIL("wrong version"); return; }
    PASS();
}

static void test_event_set_intent(void)
{
    TEST(event_set_intent);
    eni_event_t ev;
    eni_event_init(&ev, ENI_EVENT_INTENT, "test");
    eni_status_t st = eni_event_set_intent(&ev, "move_left", 0.95f);
    if (st != ENI_OK) { FAIL("set_intent returned error"); return; }
    if (strcmp(ev.payload.intent.name, "move_left") != 0) { FAIL("wrong intent name"); return; }
    if (ev.payload.intent.confidence < 0.94f || ev.payload.intent.confidence > 0.96f) { FAIL("wrong confidence"); return; }
    PASS();
}

static void test_event_add_feature(void)
{
    TEST(event_add_feature);
    eni_event_t ev;
    eni_event_init(&ev, ENI_EVENT_FEATURES, "test");
    eni_status_t st = eni_event_add_feature(&ev, "attention", 0.72f);
    if (st != ENI_OK) { FAIL("add_feature returned error"); return; }
    if (ev.payload.features.count != 1) { FAIL("wrong count"); return; }
    if (strcmp(ev.payload.features.features[0].name, "attention") != 0) { FAIL("wrong feature name"); return; }
    PASS();
}

static void test_event_set_raw(void)
{
    TEST(event_set_raw);
    eni_event_t ev;
    eni_event_init(&ev, ENI_EVENT_RAW, "test");
    uint8_t data[] = {0xDE, 0xAD, 0xBE, 0xEF};
    eni_status_t st = eni_event_set_raw(&ev, data, sizeof(data));
    if (st != ENI_OK) { FAIL("set_raw returned error"); return; }
    if (ev.payload.raw.len != 4) { FAIL("wrong len"); return; }
    if (ev.payload.raw.data[0] != 0xDE) { FAIL("wrong data"); return; }
    PASS();
}

static void test_event_type_mismatch(void)
{
    TEST(event_type_mismatch);
    eni_event_t ev;
    eni_event_init(&ev, ENI_EVENT_RAW, "test");
    eni_status_t st = eni_event_set_intent(&ev, "move", 0.5f);
    if (st != ENI_ERR_INVALID) { FAIL("should reject intent on raw event"); return; }
    PASS();
}

static void test_policy_allow_deny(void)
{
    TEST(policy_allow_deny);
    eni_policy_engine_t pol;
    eni_policy_init(&pol);
    eni_policy_add_rule(&pol, "ui.cursor.move", ENI_POLICY_ALLOW, ENI_ACTION_SAFE);
    eni_policy_add_rule(&pol, "system.shutdown", ENI_POLICY_DENY, ENI_ACTION_RESTRICTED);

    if (eni_policy_evaluate(&pol, "ui.cursor.move") != ENI_POLICY_ALLOW) { FAIL("should allow"); return; }
    if (eni_policy_evaluate(&pol, "system.shutdown") != ENI_POLICY_DENY) { FAIL("should deny"); return; }
    if (eni_policy_evaluate(&pol, "unknown.action") != ENI_POLICY_ALLOW) { FAIL("default should allow"); return; }

    eni_policy_set_default_deny(&pol, true);
    if (eni_policy_evaluate(&pol, "unknown.action") != ENI_POLICY_DENY) { FAIL("default_deny should deny"); return; }
    PASS();
}

static eni_status_t dummy_tool_exec(const eni_tool_call_t *call, eni_tool_result_t *result)
{
    (void)call;
    result->status = ENI_OK;
    const char *msg = "ok";
    memcpy(result->data, msg, 2);
    result->len = 2;
    return ENI_OK;
}

static void test_tool_registry(void)
{
    TEST(tool_registry);
    eni_tool_registry_t reg;
    eni_tool_registry_init(&reg);

    eni_tool_entry_t entry = { .name = "test.tool", .description = "A test tool", .exec = dummy_tool_exec };
    eni_status_t st = eni_tool_register(&reg, &entry);
    if (st != ENI_OK) { FAIL("register failed"); return; }

    eni_tool_entry_t *found = eni_tool_find(&reg, "test.tool");
    if (!found) { FAIL("find returned NULL"); return; }
    if (strcmp(found->name, "test.tool") != 0) { FAIL("wrong name"); return; }

    eni_tool_call_t call = {0};
    memcpy(call.tool, "test.tool", 9);
    eni_tool_result_t result;
    st = eni_tool_exec(&reg, &call, &result);
    if (st != ENI_OK) { FAIL("exec failed"); return; }
    PASS();
}

static void test_config_defaults(void)
{
    TEST(config_defaults);
    eni_config_t cfg;
    eni_config_load_defaults(&cfg, ENI_VARIANT_MIN);
    if (cfg.variant != ENI_VARIANT_MIN) { FAIL("wrong variant"); return; }
    if (cfg.mode != ENI_MODE_INTENT) { FAIL("wrong mode"); return; }
    if (cfg.provider_count != 1) { FAIL("wrong provider count"); return; }

    eni_config_load_defaults(&cfg, ENI_VARIANT_FRAMEWORK);
    if (cfg.variant != ENI_VARIANT_FRAMEWORK) { FAIL("wrong variant"); return; }
    if (cfg.mode != ENI_MODE_FEATURES_INTENT) { FAIL("wrong mode"); return; }
    PASS();
}

static void test_status_strings(void)
{
    TEST(status_strings);
    if (strcmp(eni_status_str(ENI_OK), "OK") != 0) { FAIL("ENI_OK"); return; }
    if (strcmp(eni_status_str(ENI_ERR_POLICY_DENIED), "ERR_POLICY_DENIED") != 0) { FAIL("POLICY_DENIED"); return; }
    if (strcmp(eni_status_str(ENI_ERR_OVERFLOW), "ERR_OVERFLOW") != 0) { FAIL("OVERFLOW"); return; }
    PASS();
}

int main(void)
{
    printf("=== ENI Unit Tests ===\n\n");

    test_event_init();
    test_event_set_intent();
    test_event_add_feature();
    test_event_set_raw();
    test_event_type_mismatch();
    test_policy_allow_deny();
    test_tool_registry();
    test_config_defaults();
    test_status_strings();

    printf("\n=== Results: %d/%d passed, %d failed ===\n",
           tests_passed, tests_run, tests_failed);

    return tests_failed > 0 ? 1 : 0;
}
