// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_stm32mp1.c
 * @brief STM32MP1 board operations (Cortex-A7 + Cortex-M4)
 */

#include "board_stm32mp1.h"
#include "eos_board_registry.h"
#include <string.h>

static int stm32mp1_flash_read(uint32_t addr, void *buf, size_t len)
{
    memcpy(buf, (const void *)(uintptr_t)addr, len);
    return 0;
}

static int stm32mp1_flash_write(uint32_t addr, const void *buf, size_t len)
{
    (void)addr; (void)buf; (void)len;
    return 0;
}

static int stm32mp1_flash_erase(uint32_t addr, size_t len)
{
    (void)addr; (void)len;
    return 0;
}

static void stm32mp1_watchdog_init(uint32_t timeout_ms) { (void)timeout_ms; }
static void stm32mp1_watchdog_feed(void) {}

static eos_reset_reason_t stm32mp1_get_reset_reason(void)
{
    return EOS_RESET_POWER_ON;
}

static void stm32mp1_system_reset(void)
{
    while (1) {}
}

static bool stm32mp1_recovery_pin(void) { return false; }

static void stm32mp1_jump(uint32_t vector_addr)
{
    void (*entry)(void) = (void (*)(void))vector_addr;
    entry();
}

static uint32_t stm32mp1_get_tick_ms(void) { return 0; }

static const eos_board_ops_t stm32mp1_ops = {
    .flash_base          = STM32MP1_EMMC_BASE,
    .flash_size          = STM32MP1_EMMC_SIZE,
    .slot_a_addr         = STM32MP1_SLOT_A_ADDR,
    .slot_a_size         = STM32MP1_SLOT_A_SIZE,
    .slot_b_addr         = STM32MP1_SLOT_B_ADDR,
    .slot_b_size         = STM32MP1_SLOT_B_SIZE,
    .bootctl_addr        = STM32MP1_BOOTCTL_ADDR,
    .flash_read          = stm32mp1_flash_read,
    .flash_write         = stm32mp1_flash_write,
    .flash_erase         = stm32mp1_flash_erase,
    .watchdog_init       = stm32mp1_watchdog_init,
    .watchdog_feed       = stm32mp1_watchdog_feed,
    .get_reset_reason    = stm32mp1_get_reset_reason,
    .system_reset        = stm32mp1_system_reset,
    .recovery_pin_asserted = stm32mp1_recovery_pin,
    .jump                = stm32mp1_jump,
    .get_tick_ms         = stm32mp1_get_tick_ms,
};

const eos_board_ops_t *board_stm32mp1_get_ops(void) { return &stm32mp1_ops; }

void board_stm32mp1_early_init(void) {}

static bool stm32mp1_detect(void) { return false; }

EBOOT_REGISTER_BOARD("stm32mp1", EOS_PLATFORM_ARM_CA72, STM32MP1_BOARD_ID,
                      board_stm32mp1_get_ops, stm32mp1_detect);
