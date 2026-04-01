// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include <stdio.h>
#include <string.h>
#include "eni/common.h"
#include "eni_min/filter.h"
#include "eni_min/mapper.h"
#include "eni_min/normalizer.h"

static int tests_run    = 0;
static int tests_passed = 0;

#define TEST(name) do { \
    tests_run++; \
    printf("  [TEST] %s ... ", #name); \
} while (0)

#define PASS() do { \
    tests_passed++; \
    printf("PASS\n"); \
} while (0)

#define FAIL(msg) do { \
    printf("FAIL: %s\n", msg); \
} while (0)

/* ── Filter tests ───────────────────────────────────────────── */

static void test_filter_init(void)
{
    TEST(filter_init);
    eni_min_filter_t filter;
    eni_min_filter_init(&filter, 0.75f, 200);
    if (filter.min_confidence != 0.75f) { FAIL("min_confidence mismatch"); return; }
    if (filter.debounce_ms != 200)      { FAIL("debounce_ms mismatch"); return; }
    PASS();
}

static void test_filter_accept_high_confidence(void)
{
    TEST(filter_accept_high_confidence);
    eni_min_filter_t filter;
    eni_min_filter_init(&filter, 0.50f, 100);

    eni_event_t ev;
    memset(&ev, 0, sizeof(ev));
    ev.type = ENI_EVENT_INTENT;
    strncpy(ev.payload.intent.name, "high_conf", ENI_EVENT_INTENT_MAX - 1);
    ev.payload.intent.confidence = 0.90f;

    if (!eni_min_filter_accept(&filter, &ev)) { FAIL("should accept high confidence"); return; }
    PASS();
}

static void test_filter_reject_low_confidence(void)
{
    TEST(filter_reject_low_confidence);
    eni_min_filter_t filter;
    eni_min_filter_init(&filter, 0.80f, 100);

    eni_event_t ev;
    memset(&ev, 0, sizeof(ev));
    ev.type = ENI_EVENT_INTENT;
    ev.payload.intent.confidence = 0.30f;

    if (eni_min_filter_accept(&filter, &ev)) { FAIL("should reject low confidence"); return; }
    PASS();
}

/* ── Mapper tests ───────────────────────────────────────────── */

static void test_mapper_add_and_resolve(void)
{
    TEST(mapper_add_and_resolve);
    eni_min_mapper_t mapper;
    eni_min_mapper_init(&mapper);

    eni_status_t st = eni_min_mapper_add(&mapper, "play_music", "media_play");
    if (st != ENI_OK) { FAIL("mapper add failed"); return; }

    eni_event_t ev;
    memset(&ev, 0, sizeof(ev));
    ev.type = ENI_EVENT_INTENT;
    strncpy(ev.payload.intent.name, "play_music", ENI_EVENT_INTENT_MAX - 1);
    ev.payload.intent.confidence = 0.95f;

    eni_tool_call_t call;
    memset(&call, 0, sizeof(call));

    st = eni_min_mapper_resolve(&mapper, &ev, &call);
    if (st != ENI_OK) { FAIL("mapper resolve failed"); return; }
    if (strcmp(call.tool, "media_play") != 0) { FAIL("wrong tool resolved"); return; }
    PASS();
}

static void test_mapper_resolve_unknown(void)
{
    TEST(mapper_resolve_unknown);
    eni_min_mapper_t mapper;
    eni_min_mapper_init(&mapper);

    eni_event_t ev;
    memset(&ev, 0, sizeof(ev));
    ev.type = ENI_EVENT_INTENT;
    strncpy(ev.payload.intent.name, "unknown_intent", ENI_EVENT_INTENT_MAX - 1);
    ev.payload.intent.confidence = 0.95f;

    eni_tool_call_t call;
    memset(&call, 0, sizeof(call));

    eni_status_t st = eni_min_mapper_resolve(&mapper, &ev, &call);
    if (st == ENI_OK) { FAIL("should fail for unknown intent"); return; }
    PASS();
}

/* ── Normalizer tests ───────────────────────────────────────── */

static void test_normalizer_passthrough(void)
{
    TEST(normalizer_passthrough);
    eni_min_normalizer_t norm;
    eni_min_normalizer_init(&norm, ENI_MODE_INTENT);

    eni_event_t raw;
    memset(&raw, 0, sizeof(raw));
    raw.type = ENI_EVENT_INTENT;
    strncpy(raw.payload.intent.name, "test_intent", ENI_EVENT_INTENT_MAX - 1);
    raw.payload.intent.confidence = 0.85f;

    eni_event_t normalized;
    memset(&normalized, 0, sizeof(normalized));

    eni_status_t st = eni_min_normalizer_process(&norm, &raw, &normalized);
    if (st != ENI_OK) { FAIL("normalizer process failed"); return; }
    if (normalized.type != ENI_EVENT_INTENT) { FAIL("type mismatch after normalize"); return; }
    if (strcmp(normalized.payload.intent.name, "test_intent") != 0) { FAIL("intent name mismatch"); return; }
    PASS();
}

/* ── Main ───────────────────────────────────────────────────── */

int main(void)
{
    printf("=== ENI Min Variant Tests ===\n");

    test_filter_init();
    test_filter_accept_high_confidence();
    test_filter_reject_low_confidence();
    test_mapper_add_and_resolve();
    test_mapper_resolve_unknown();
    test_normalizer_passthrough();

    printf("\nResults: %d/%d passed\n", tests_passed, tests_run);
    return (tests_passed == tests_run) ? 0 : 1;
}
