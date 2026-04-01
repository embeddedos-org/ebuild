// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_qemu_arm64.c
 * @brief QEMU ARM64 virt board operations
 */

#include "board_qemu_arm64.h"
#include "eos_board_registry.h"
#include <string.h>

static int qemu_flash_read(uint32_t addr, void *buf, size_t len)
{
    memcpy(buf, (const void *)(uintptr_t)addr, len);
    return 0;
}

static int qemu_flash_write(uint32_t addr, const void *buf, size_t len)
{
    (void)addr; (void)buf; (void)len;
    return 0;
}

static int qemu_flash_erase(uint32_t addr, size_t len)
{
    (void)addr; (void)len;
    return 0;
}

static void qemu_watchdog_init(uint32_t timeout_ms) { (void)timeout_ms; }
static void qemu_watchdog_feed(void) {}

static eos_reset_reason_t qemu_get_reset_reason(void)
{
    return EOS_RESET_POWER_ON;
}

static void qemu_system_reset(void)
{
    while (1) {}
}

static bool qemu_recovery_pin(void) { return false; }

static void qemu_jump(uint32_t vector_addr)
{
    void (*entry)(void) = (void (*)(void))vector_addr;
    entry();
}

static uint32_t qemu_get_tick_ms(void) { return 0; }

static const eos_board_ops_t qemu_arm64_ops = {
    .flash_base          = QEMU_ARM64_FLASH_BASE,
    .flash_size          = QEMU_ARM64_FLASH_SIZE,
    .slot_a_addr         = QEMU_ARM64_SLOT_A_ADDR,
    .slot_a_size         = QEMU_ARM64_SLOT_A_SIZE,
    .slot_b_addr         = QEMU_ARM64_SLOT_B_ADDR,
    .slot_b_size         = QEMU_ARM64_SLOT_B_SIZE,
    .bootctl_addr        = QEMU_ARM64_BOOTCTL_ADDR,
    .flash_read          = qemu_flash_read,
    .flash_write         = qemu_flash_write,
    .flash_erase         = qemu_flash_erase,
    .watchdog_init       = qemu_watchdog_init,
    .watchdog_feed       = qemu_watchdog_feed,
    .get_reset_reason    = qemu_get_reset_reason,
    .system_reset        = qemu_system_reset,
    .recovery_pin_asserted = qemu_recovery_pin,
    .jump                = qemu_jump,
    .get_tick_ms         = qemu_get_tick_ms,
};

const eos_board_ops_t *board_qemu_arm64_get_ops(void) { return &qemu_arm64_ops; }

void board_qemu_arm64_early_init(void) {}

static bool qemu_arm64_detect(void) { return false; }

EBOOT_REGISTER_BOARD("qemu-arm64", EOS_PLATFORM_ARM_CA53, QEMU_ARM64_BOARD_ID,
                      board_qemu_arm64_get_ops, qemu_arm64_detect);
