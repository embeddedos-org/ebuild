// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include <stdio.h>
#include <string.h>
#include "eni/common.h"
#include "eni_fw/stream_bus.h"
#include "eni_fw/router.h"

static int tests_run = 0, tests_passed = 0, tests_failed = 0;
#define TEST(name) do { tests_run++; printf("  TEST %-40s ", #name); } while(0)
#define PASS() do { tests_passed++; printf("[PASS]\n"); } while(0)
#define FAIL(msg) do { tests_failed++; printf("[FAIL] %s\n", msg); } while(0)

static eni_fw_stream_bus_t g_bus;

static void test_stream_bus_empty(void)
{
    TEST(stream_bus_empty);
    eni_fw_stream_bus_init(&g_bus);
    if (!eni_fw_stream_bus_empty(&g_bus)) { FAIL("should be empty"); return; }
    PASS();
}

static void test_stream_bus_push_pop(void)
{
    TEST(stream_bus_push_pop);
    eni_fw_stream_bus_init(&g_bus);
    eni_event_t ev;
    eni_event_init(&ev, ENI_EVENT_INTENT, "test");
    eni_event_set_intent(&ev, "move_left", 0.9f);
    eni_fw_stream_bus_push(&g_bus, &ev);
    eni_event_t popped;
    eni_fw_stream_bus_pop(&g_bus, &popped);
    if (popped.type != ENI_EVENT_INTENT) { FAIL("wrong type"); return; }
    PASS();
}

static void test_router_classify(void)
{
    TEST(router_classify);
    eni_fw_router_t router;
    eni_fw_router_init(&router);
    eni_fw_router_add_rule(&router, ENI_EVENT_CONTROL, ENI_ROUTE_CRITICAL, 10, true);
    eni_event_t ev;
    eni_event_init(&ev, ENI_EVENT_CONTROL, "test");
    eni_route_priority_t pri = eni_fw_router_classify(&router, &ev);
    if (pri != ENI_ROUTE_CRITICAL) { FAIL("should be critical"); return; }
    PASS();
}

int main(void)
{
    printf("=== ENI Framework Tests ===\n\n");
    test_stream_bus_empty();
    test_stream_bus_push_pop();
    test_router_classify();
    printf("\n=== Results: %d/%d passed, %d failed ===\n",
           tests_passed, tests_run, tests_failed);
    return tests_failed > 0 ? 1 : 0;
}
