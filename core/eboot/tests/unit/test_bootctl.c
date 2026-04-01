// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file test_bootctl.c
 * @brief Unit tests for boot control block operations
 *
 * Tests run on the host using a simulated flash backend.
 */

#include "eos_bootctl.h"
#include "eos_hal.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <assert.h>

/* ---- Simulated Flash ---- */

#define SIM_FLASH_SIZE  (64 * 1024)
static uint8_t sim_flash[SIM_FLASH_SIZE];

#define SIM_BOOTCTL_ADDR        0x0000
#define SIM_BOOTCTL_BACKUP_ADDR 0x1000
#define SIM_LOG_ADDR            0x2000
#define SIM_SLOT_A_ADDR         0x4000
#define SIM_SLOT_A_SIZE         0x8000
#define SIM_SLOT_B_ADDR         0xC000
#define SIM_SLOT_B_SIZE         0x8000

static int sim_flash_read(uint32_t addr, void *buf, size_t len)
{
    if (addr + len > SIM_FLASH_SIZE) return EOS_ERR_FLASH;
    memcpy(buf, &sim_flash[addr], len);
    return EOS_OK;
}

static int sim_flash_write(uint32_t addr, const void *buf, size_t len)
{
    if (addr + len > SIM_FLASH_SIZE) return EOS_ERR_FLASH;
    memcpy(&sim_flash[addr], buf, len);
    return EOS_OK;
}

static int sim_flash_erase(uint32_t addr, size_t len)
{
    if (addr + len > SIM_FLASH_SIZE) return EOS_ERR_FLASH;
    memset(&sim_flash[addr], 0xFF, len);
    return EOS_OK;
}

static uint32_t sim_tick = 0;
static uint32_t sim_get_tick(void) { return sim_tick++; }
static void sim_noop(void) {}
static void sim_noop_u32(uint32_t x) { (void)x; }
static void sim_jump(uint32_t addr) { (void)addr; }
static eos_reset_reason_t sim_reset_reason(void) { return EOS_RESET_POWER_ON; }
static bool sim_recovery_pin(void) { return false; }
static void sim_system_reset(void) {}

static const eos_board_ops_t sim_ops = {
    .flash_base          = 0,
    .flash_size          = SIM_FLASH_SIZE,
    .slot_a_addr         = SIM_SLOT_A_ADDR,
    .slot_a_size         = SIM_SLOT_A_SIZE,
    .slot_b_addr         = SIM_SLOT_B_ADDR,
    .slot_b_size         = SIM_SLOT_B_SIZE,
    .recovery_addr       = 0,
    .recovery_size       = 0,
    .bootctl_addr        = SIM_BOOTCTL_ADDR,
    .bootctl_backup_addr = SIM_BOOTCTL_BACKUP_ADDR,
    .log_addr            = SIM_LOG_ADDR,
    .app_vector_offset   = 0,

    .flash_read          = sim_flash_read,
    .flash_write         = sim_flash_write,
    .flash_erase         = sim_flash_erase,

    .watchdog_init       = sim_noop_u32,
    .watchdog_feed       = sim_noop,
    .get_reset_reason    = sim_reset_reason,
    .system_reset        = sim_system_reset,
    .recovery_pin_asserted = sim_recovery_pin,
    .jump                = sim_jump,
    .uart_init           = NULL,
    .uart_send           = NULL,
    .uart_recv           = NULL,
    .get_tick_ms         = sim_get_tick,
    .disable_interrupts  = sim_noop,
    .enable_interrupts   = sim_noop,
    .deinit_peripherals  = sim_noop,
};

static void setup(void)
{
    memset(sim_flash, 0xFF, sizeof(sim_flash));
    sim_tick = 0;
    eos_hal_init(&sim_ops);
}

/* ---- Tests ---- */

static int tests_run = 0;
static int tests_passed = 0;

#define TEST(name) \
    static void name(void); \
    static void run_##name(void) { \
        setup(); \
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

TEST(test_init_defaults)
{
    eos_bootctl_t bctl;
    eos_bootctl_init_defaults(&bctl);

    ASSERT(bctl.magic == EOS_BOOTCTL_MAGIC);
    ASSERT(bctl.version == EOS_BOOTCTL_VERSION);
    ASSERT(bctl.active_slot == EOS_SLOT_A);
    ASSERT(bctl.pending_slot == EOS_SLOT_NONE);
    ASSERT(bctl.confirmed_slot == EOS_SLOT_NONE);
    ASSERT(bctl.boot_attempts == 0);
    ASSERT(bctl.max_attempts == EOS_MAX_BOOT_ATTEMPTS);
    ASSERT(bctl.flags == 0);
    ASSERT(eos_bootctl_validate(&bctl));
}

TEST(test_save_and_load)
{
    eos_bootctl_t bctl, loaded;
    eos_bootctl_init_defaults(&bctl);
    bctl.active_slot = EOS_SLOT_B;
    bctl.img_a_version = EOS_VERSION_MAKE(1, 2, 3);

    int rc = eos_bootctl_save(&bctl);
    ASSERT(rc == EOS_OK);

    rc = eos_bootctl_load(&loaded);
    ASSERT(rc == EOS_OK);
    ASSERT(loaded.active_slot == EOS_SLOT_B);
    ASSERT(loaded.img_a_version == EOS_VERSION_MAKE(1, 2, 3));
    ASSERT(eos_bootctl_validate(&loaded));
}

TEST(test_corrupt_primary_falls_back_to_backup)
{
    eos_bootctl_t bctl, loaded;
    eos_bootctl_init_defaults(&bctl);
    bctl.active_slot = EOS_SLOT_B;

    eos_bootctl_save(&bctl);

    /* Corrupt primary copy */
    sim_flash[SIM_BOOTCTL_ADDR] = 0x00;
    sim_flash[SIM_BOOTCTL_ADDR + 1] = 0x00;

    int rc = eos_bootctl_load(&loaded);
    ASSERT(rc == EOS_OK);
    ASSERT(loaded.active_slot == EOS_SLOT_B);
}

TEST(test_both_corrupt_returns_defaults)
{
    eos_bootctl_t loaded;

    /* Flash is all 0xFF — no valid control block */
    int rc = eos_bootctl_load(&loaded);
    ASSERT(rc == EOS_ERR_CRC);
    ASSERT(loaded.magic == EOS_BOOTCTL_MAGIC);
    ASSERT(loaded.active_slot == EOS_SLOT_A);
}

TEST(test_increment_attempts)
{
    eos_bootctl_t bctl;
    eos_bootctl_init_defaults(&bctl);
    eos_bootctl_save(&bctl);

    ASSERT(bctl.boot_attempts == 0);
    eos_bootctl_increment_attempts(&bctl);
    ASSERT(bctl.boot_attempts == 1);
    eos_bootctl_increment_attempts(&bctl);
    ASSERT(bctl.boot_attempts == 2);

    /* Verify persisted */
    eos_bootctl_t loaded;
    eos_bootctl_load(&loaded);
    ASSERT(loaded.boot_attempts == 2);
}

TEST(test_set_and_clear_pending)
{
    eos_bootctl_t bctl;
    eos_bootctl_init_defaults(&bctl);

    eos_bootctl_set_pending(&bctl, EOS_SLOT_B);
    ASSERT(bctl.pending_slot == EOS_SLOT_B);
    ASSERT(bctl.flags & EOS_FLAG_UPGRADE_PENDING);

    eos_bootctl_clear_pending(&bctl);
    ASSERT(bctl.pending_slot == EOS_SLOT_NONE);
    ASSERT(!(bctl.flags & EOS_FLAG_UPGRADE_PENDING));
}

TEST(test_confirm)
{
    eos_bootctl_t bctl;
    eos_bootctl_init_defaults(&bctl);
    bctl.flags |= EOS_FLAG_TEST_BOOT;
    bctl.boot_attempts = 2;

    eos_bootctl_confirm(&bctl);
    ASSERT(bctl.confirmed_slot == EOS_SLOT_A);
    ASSERT(bctl.flags & EOS_FLAG_CONFIRMED);
    ASSERT(!(bctl.flags & EOS_FLAG_TEST_BOOT));
    ASSERT(bctl.boot_attempts == 0);
}

TEST(test_other_slot)
{
    ASSERT(eos_bootctl_other_slot(EOS_SLOT_A) == EOS_SLOT_B);
    ASSERT(eos_bootctl_other_slot(EOS_SLOT_B) == EOS_SLOT_A);
    ASSERT(eos_bootctl_other_slot(EOS_SLOT_RECOVERY) == EOS_SLOT_NONE);
    ASSERT(eos_bootctl_other_slot(EOS_SLOT_NONE) == EOS_SLOT_NONE);
}

TEST(test_request_recovery)
{
    eos_bootctl_t bctl;
    eos_bootctl_init_defaults(&bctl);

    eos_bootctl_request_recovery(&bctl);
    ASSERT(bctl.flags & EOS_FLAG_FORCE_RECOVERY);
}

TEST(test_request_factory_reset)
{
    eos_bootctl_t bctl;
    eos_bootctl_init_defaults(&bctl);

    eos_bootctl_request_factory_reset(&bctl);
    ASSERT(bctl.flags & EOS_FLAG_FACTORY_RESET);
}

TEST(test_version_encoding)
{
    uint32_t v = EOS_VERSION_MAKE(1, 2, 3);
    ASSERT(EOS_VERSION_MAJOR(v) == 1);
    ASSERT(EOS_VERSION_MINOR(v) == 2);
    ASSERT(EOS_VERSION_PATCH(v) == 3);

    v = EOS_VERSION_MAKE(255, 255, 65535);
    ASSERT(EOS_VERSION_MAJOR(v) == 255);
    ASSERT(EOS_VERSION_MINOR(v) == 255);
    ASSERT(EOS_VERSION_PATCH(v) == 65535);
}

/* ---- Main ---- */

int main(void)
{
    printf("=== eBootloader: Boot Control Unit Tests ===\n\n");

    run_test_init_defaults();
    run_test_save_and_load();
    run_test_corrupt_primary_falls_back_to_backup();
    run_test_both_corrupt_returns_defaults();
    run_test_increment_attempts();
    run_test_set_and_clear_pending();
    run_test_confirm();
    run_test_other_slot();
    run_test_request_recovery();
    run_test_request_factory_reset();
    run_test_version_encoding();

    tests_run = 11;
    printf("\n%d/%d tests passed\n", tests_passed, tests_run);
    return (tests_passed == tests_run) ? 0 : 1;
}
