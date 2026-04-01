// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_samd51.c
 * @brief Microchip SAMD51 board port (Cortex-M4F, 120MHz)
 */

#include "board_samd51.h"
#include "eos_types.h"
#include <string.h>

#define SERCOM_BASE(n)  (0x40003000 + (n) * 0x400)
#define NVMCTRL_BASE    0x41004000

static volatile uint32_t tick_ms = 0;

static int samd51_flash_read(uint32_t addr, void *buf, size_t len)
{
    memcpy(buf, (const void *)(uintptr_t)addr, len);
    return EOS_OK;
}

static int samd51_flash_write(uint32_t addr, const void *buf, size_t len)
{
    (void)addr; (void)buf; (void)len;
    return EOS_OK;
}

static int samd51_flash_erase(uint32_t addr, size_t len)
{
    (void)addr; (void)len;
    return EOS_OK;
}

static int samd51_uart_init(uint32_t baud) { (void)baud; return EOS_OK; }
static int samd51_uart_send(const void *buf, size_t len) { (void)buf; (void)len; return EOS_OK; }
static int samd51_uart_recv(void *buf, size_t len, uint32_t timeout_ms)
{
    (void)buf; (void)len; (void)timeout_ms;
    return EOS_ERR_TIMEOUT;
}

static void samd51_watchdog_init(uint32_t timeout_ms) { (void)timeout_ms; }
static void samd51_watchdog_feed(void) {}
static eos_reset_reason_t samd51_get_reset_reason(void) { return EOS_RESET_POWER_ON; }

static void samd51_system_reset(void)
{
#if defined(__ARM_ARCH) && (__ARM_ARCH <= 7) && !defined(__aarch64__)
    *((volatile uint32_t *)0xE000ED0C) = 0x05FA0004;
#endif
    while (1) {}
}

static void samd51_jump(uint32_t vector_addr)
{
#if defined(__ARM_ARCH) && (__ARM_ARCH <= 7) && !defined(__aarch64__)
    uint32_t new_msp = *(volatile uint32_t *)(vector_addr);
    uint32_t reset_pc = *(volatile uint32_t *)(vector_addr + 4);
    *(volatile uint32_t *)0xE000ED08 = vector_addr;
    __asm volatile ("MSR MSP, %0" : : "r" (new_msp));
    __asm volatile ("BX %0" : : "r" (reset_pc));
#else
    (void)vector_addr;
#endif
}

static uint32_t samd51_get_tick_ms(void) { return tick_ms; }
static void samd51_disable_interrupts(void)
{
#if defined(__ARM_ARCH) && (__ARM_ARCH <= 7) && !defined(__aarch64__)
    __asm volatile ("CPSID i");
#endif
}
static void samd51_enable_interrupts(void)
{
#if defined(__ARM_ARCH) && (__ARM_ARCH <= 7) && !defined(__aarch64__)
    __asm volatile ("CPSIE i");
#endif
}
static void samd51_deinit_peripherals(void) {}
static bool samd51_recovery_pin_asserted(void) { return false; }

static const eos_board_ops_t samd51_ops = {
    .flash_base = SAMD51_FLASH_BASE, .flash_size = SAMD51_FLASH_SIZE,
    .slot_a_addr = SAMD51_SLOT_A_ADDR, .slot_a_size = SAMD51_SLOT_A_SIZE,
    .slot_b_addr = SAMD51_SLOT_B_ADDR, .slot_b_size = SAMD51_SLOT_B_SIZE,
    .recovery_addr = SAMD51_RECOVERY_ADDR, .recovery_size = SAMD51_RECOVERY_SIZE,
    .bootctl_addr = SAMD51_BOOTCTL_ADDR,
    .flash_read = samd51_flash_read, .flash_write = samd51_flash_write,
    .flash_erase = samd51_flash_erase,
    .watchdog_init = samd51_watchdog_init, .watchdog_feed = samd51_watchdog_feed,
    .get_reset_reason = samd51_get_reset_reason, .system_reset = samd51_system_reset,
    .recovery_pin_asserted = samd51_recovery_pin_asserted, .jump = samd51_jump,
    .uart_init = samd51_uart_init, .uart_send = samd51_uart_send, .uart_recv = samd51_uart_recv,
    .get_tick_ms = samd51_get_tick_ms,
    .disable_interrupts = samd51_disable_interrupts, .enable_interrupts = samd51_enable_interrupts,
    .deinit_peripherals = samd51_deinit_peripherals,
};

const eos_board_ops_t *board_samd51_get_ops(void) { return &samd51_ops; }
