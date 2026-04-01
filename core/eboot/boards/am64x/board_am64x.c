// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_am64x.c
 * @brief TI AM64x Sitara board port (Cortex-R5F + Cortex-A53)
 */

#include "board_am64x.h"
#include "eos_types.h"
#include <string.h>

/* TI 16550-compatible UART */
#define UART_THR    (*(volatile uint32_t *)(AM64X_UART0_BASE + 0x00))
#define UART_RBR    (*(volatile uint32_t *)(AM64X_UART0_BASE + 0x00))
#define UART_LSR    (*(volatile uint32_t *)(AM64X_UART0_BASE + 0x14))

/* Watchdog (RTI) */
#define RTI0_BASE   0x02200000
#define RTIGCTRL    (*(volatile uint32_t *)(RTI0_BASE + 0x00))
#define RTIWDCTRL   (*(volatile uint32_t *)(RTI0_BASE + 0x90))
#define RTIWDKEY    (*(volatile uint32_t *)(RTI0_BASE + 0x98))

static volatile uint32_t tick_ms = 0;

static int am64x_flash_read(uint32_t addr, void *buf, size_t len)
{
    memcpy(buf, (const void *)(uintptr_t)addr, len);
    return EOS_OK;
}

static int am64x_flash_write(uint32_t addr, const void *buf, size_t len)
{
    (void)addr; (void)buf; (void)len;
    return EOS_OK;
}

static int am64x_flash_erase(uint32_t addr, size_t len)
{
    (void)addr; (void)len;
    return EOS_OK;
}

static int am64x_uart_init(uint32_t baud)
{
    (void)baud;
    return EOS_OK;
}

static int am64x_uart_send(const void *buf, size_t len)
{
    const uint8_t *p = (const uint8_t *)buf;
    for (size_t i = 0; i < len; i++) {
        while (!(UART_LSR & 0x20)) {}
        UART_THR = p[i];
    }
    return EOS_OK;
}

static int am64x_uart_recv(void *buf, size_t len, uint32_t timeout_ms)
{
    uint8_t *p = (uint8_t *)buf;
    uint32_t start = tick_ms;
    for (size_t i = 0; i < len; i++) {
        while (!(UART_LSR & 0x01)) {
            if ((tick_ms - start) >= timeout_ms) return EOS_ERR_TIMEOUT;
        }
        p[i] = (uint8_t)(UART_RBR & 0xFF);
    }
    return EOS_OK;
}

static void am64x_watchdog_init(uint32_t timeout_ms)
{
    (void)timeout_ms;
    RTIWDCTRL = 0xA98559DA;  /* Enable DWWD */
}

static void am64x_watchdog_feed(void)
{
    RTIWDKEY = 0xE51A;
    RTIWDKEY = 0xA35C;
}

static eos_reset_reason_t am64x_get_reset_reason(void) { return EOS_RESET_POWER_ON; }

static void am64x_system_reset(void)
{
    /* Use CTRL_MMR for warm reset */
    while (1) {}
}

static void am64x_jump(uint32_t vector_addr)
{
    typedef void (*entry_fn)(void);
    entry_fn entry = (entry_fn)(uintptr_t)vector_addr;
    entry();
}

static uint32_t am64x_get_tick_ms(void) { return tick_ms; }
static void am64x_disable_interrupts(void)
{
#if defined(__aarch64__)
    __asm volatile ("msr daifset, #0xf" ::: "memory");
#endif
}
static void am64x_enable_interrupts(void)
{
#if defined(__aarch64__)
    __asm volatile ("msr daifclr, #0xf" ::: "memory");
#endif
}
static void am64x_deinit_peripherals(void) {}
static bool am64x_recovery_pin_asserted(void) { return false; }

static const eos_board_ops_t am64x_ops = {
    .flash_base = AM64X_OSPI_BASE, .flash_size = AM64X_OSPI_SIZE,
    .slot_a_addr = AM64X_SLOT_A_ADDR, .slot_a_size = AM64X_SLOT_A_SIZE,
    .slot_b_addr = AM64X_SLOT_B_ADDR, .slot_b_size = AM64X_SLOT_B_SIZE,
    .recovery_addr = AM64X_RECOVERY_ADDR, .recovery_size = AM64X_RECOVERY_SIZE,
    .bootctl_addr = AM64X_BOOTCTL_ADDR,
    .flash_read = am64x_flash_read, .flash_write = am64x_flash_write,
    .flash_erase = am64x_flash_erase,
    .watchdog_init = am64x_watchdog_init, .watchdog_feed = am64x_watchdog_feed,
    .get_reset_reason = am64x_get_reset_reason, .system_reset = am64x_system_reset,
    .recovery_pin_asserted = am64x_recovery_pin_asserted, .jump = am64x_jump,
    .uart_init = am64x_uart_init, .uart_send = am64x_uart_send, .uart_recv = am64x_uart_recv,
    .get_tick_ms = am64x_get_tick_ms,
    .disable_interrupts = am64x_disable_interrupts, .enable_interrupts = am64x_enable_interrupts,
    .deinit_peripherals = am64x_deinit_peripherals,
};

const eos_board_ops_t *board_am64x_get_ops(void) { return &am64x_ops; }
