// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file test_multicore.c
 * @brief Unit tests for multicore boot management
 */

#include "eos_multicore.h"
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

/* Mock multicore ops */
static eos_core_state_t mock_states[EOS_MAX_CORES];
static int mock_start_count = 0;

static int mock_start_core(const eos_core_config_t *cfg)
{
    if (cfg->core_id >= EOS_MAX_CORES) return EOS_ERR_INVALID;
    mock_states[cfg->core_id] = EOS_CORE_STATE_RUNNING;
    mock_start_count++;
    return EOS_OK;
}

static int mock_stop_core(uint8_t core_id)
{
    if (core_id >= EOS_MAX_CORES) return EOS_ERR_INVALID;
    mock_states[core_id] = EOS_CORE_STATE_STOPPED;
    return EOS_OK;
}

static eos_core_state_t mock_get_state(uint8_t core_id)
{
    if (core_id >= EOS_MAX_CORES) return EOS_CORE_STATE_OFF;
    return mock_states[core_id];
}

static uint8_t mock_get_count(void) { return 4; }
static uint8_t mock_get_current(void) { return 0; }

static const eos_multicore_ops_t mock_mc_ops = {
    .start_core = mock_start_core,
    .stop_core = mock_stop_core,
    .reset_core = NULL,
    .get_core_state = mock_get_state,
    .send_ipi = NULL,
    .get_core_count = mock_get_count,
    .get_current_core = mock_get_current,
};

static void mc_setup(void)
{
    memset(mock_states, 0, sizeof(mock_states));
    mock_states[0] = EOS_CORE_STATE_RUNNING;  /* primary core is running */
    mock_start_count = 0;
    eos_multicore_init(&mock_mc_ops);
}

TEST(test_init)
{
    mc_setup();
    ASSERT(eos_multicore_count() == 4);
    ASSERT(eos_multicore_current() == 0);
    ASSERT(eos_multicore_get_state(0) == EOS_CORE_STATE_RUNNING);
}

TEST(test_init_null)
{
    ASSERT(eos_multicore_init(NULL) == EOS_ERR_INVALID);
}

TEST(test_start_smp)
{
    mc_setup();
    int rc = eos_multicore_start_smp(1, 0x08020000, 0x20010000);
    ASSERT(rc == EOS_OK);
    ASSERT(mock_start_count == 1);
    ASSERT(eos_multicore_get_state(1) == EOS_CORE_STATE_RUNNING);
}

TEST(test_cannot_restart_primary)
{
    mc_setup();
    eos_core_config_t cfg;
    memset(&cfg, 0, sizeof(cfg));
    cfg.core_id = 0;
    cfg.entry_addr = 0x08000000;
    ASSERT(eos_multicore_start(&cfg) == EOS_ERR_INVALID);
}

TEST(test_stop_core)
{
    mc_setup();
    eos_multicore_start_smp(1, 0x08020000, 0x20010000);
    ASSERT(eos_multicore_get_state(1) == EOS_CORE_STATE_RUNNING);

    int rc = eos_multicore_stop(1);
    ASSERT(rc == EOS_OK);
    ASSERT(eos_multicore_get_state(1) == EOS_CORE_STATE_STOPPED);
}

TEST(test_cannot_stop_primary)
{
    mc_setup();
    ASSERT(eos_multicore_stop(0) == EOS_ERR_INVALID);
}

TEST(test_start_requires_entry_addr)
{
    mc_setup();
    eos_core_config_t cfg;
    memset(&cfg, 0, sizeof(cfg));
    cfg.core_id = 1;
    cfg.entry_addr = 0;  /* invalid */
    ASSERT(eos_multicore_start(&cfg) == EOS_ERR_INVALID);
}

TEST(test_boot_all)
{
    mc_setup();
    eos_core_config_t configs[3];
    memset(configs, 0, sizeof(configs));

    configs[0].core_id = 0;  /* primary — will be skipped */
    configs[0].entry_addr = 0x08000000;

    configs[1].core_id = 1;
    configs[1].entry_addr = 0x08020000;
    configs[1].mode = EOS_CORE_SMP;

    configs[2].core_id = 2;
    configs[2].entry_addr = 0x08040000;
    configs[2].mode = EOS_CORE_SMP;

    int rc = eos_multicore_boot_all(configs, 3);
    ASSERT(rc == EOS_OK);
    ASSERT(mock_start_count == 2);  /* only cores 1 and 2 */
}

TEST(test_invalid_core_id)
{
    mc_setup();
    ASSERT(eos_multicore_get_state(EOS_MAX_CORES) == EOS_CORE_STATE_OFF);
    ASSERT(eos_multicore_stop(EOS_MAX_CORES) == EOS_ERR_INVALID);
}

int main(void)
{
    printf("=== eBootloader: Multicore Unit Tests ===\n\n");

    run_test_init();
    run_test_init_null();
    run_test_start_smp();
    run_test_cannot_restart_primary();
    run_test_stop_core();
    run_test_cannot_stop_primary();
    run_test_start_requires_entry_addr();
    run_test_boot_all();
    run_test_invalid_core_id();

    tests_run = 9;
    printf("\n%d/%d tests passed\n", tests_passed, tests_run);
    return (tests_passed == tests_run) ? 0 : 1;
}
