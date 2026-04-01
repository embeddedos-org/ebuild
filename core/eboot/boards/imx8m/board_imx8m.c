// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_imx8m.c
 * @brief NXP i.MX 8M Mini board port (Cortex-A53, ARM64)
 */

#include "board_imx8m.h"
#include "eos_types.h"
#include <string.h>

/* i.MX8M UART registers (UART1) */
#define UART_URXD   (*(volatile uint32_t *)(IMX8M_UART1_BASE + 0x00))
#define UART_UTXD   (*(volatile uint32_t *)(IMX8M_UART1_BASE + 0x40))
#define UART_UCR1   (*(volatile uint32_t *)(IMX8M_UART1_BASE + 0x80))
#define UART_UCR2   (*(volatile uint32_t *)(IMX8M_UART1_BASE + 0x84))
#define UART_USR1   (*(volatile uint32_t *)(IMX8M_UART1_BASE + 0x94))
#define UART_USR2   (*(volatile uint32_t *)(IMX8M_UART1_BASE + 0x98))
#define UART_UBIR   (*(volatile uint32_t *)(IMX8M_UART1_BASE + 0xA4))
#define UART_UBMR   (*(volatile uint32_t *)(IMX8M_UART1_BASE + 0xA8))

/* Watchdog (WDOG1) */
#define WDOG1_BASE  0x30280000
#define WDOG_WCR    (*(volatile uint16_t *)(WDOG1_BASE + 0x00))
#define WDOG_WSR    (*(volatile uint16_t *)(WDOG1_BASE + 0x02))

/* SRC for reset reason */
#define SRC_BASE    0x30390000
#define SRC_SRSR    (*(volatile uint32_t *)(SRC_BASE + 0x08))

static volatile uint32_t tick_ms = 0;

static int imx8m_flash_read(uint32_t addr, void *buf, size_t len)
{
    memcpy(buf, (const void *)(uintptr_t)addr, len);
    return EOS_OK;
}

static int imx8m_flash_write(uint32_t addr, const void *buf, size_t len)
{
    (void)addr; (void)buf; (void)len;
    return EOS_OK;
}

static int imx8m_flash_erase(uint32_t addr, size_t len)
{
    (void)addr; (void)len;
    return EOS_OK;
}

static int imx8m_uart_init(uint32_t baud)
{
    (void)baud;
    UART_UCR1 = (1 << 0);
    UART_UCR2 = (1 << 1) | (1 << 2) | (1 << 5) | (1 << 14);
    return EOS_OK;
}

static int imx8m_uart_send(const void *buf, size_t len)
{
    const uint8_t *p = (const uint8_t *)buf;
    for (size_t i = 0; i < len; i++) {
        while (!(UART_USR1 & (1 << 13))) {}  /* TRDY */
        UART_UTXD = p[i];
    }
    return EOS_OK;
}

static int imx8m_uart_recv(void *buf, size_t len, uint32_t timeout_ms)
{
    uint8_t *p = (uint8_t *)buf;
    uint32_t start = tick_ms;
    for (size_t i = 0; i < len; i++) {
        while (!(UART_USR2 & (1 << 0))) {
            if ((tick_ms - start) >= timeout_ms) return EOS_ERR_TIMEOUT;
        }
        p[i] = (uint8_t)(UART_URXD & 0xFF);
    }
    return EOS_OK;
}

static void imx8m_watchdog_init(uint32_t timeout_ms)
{
    uint16_t wt = (uint16_t)(timeout_ms / 500);
    if (wt > 255) wt = 255;
    WDOG_WCR = (wt << 8) | (1 << 2) | (1 << 3) | (1 << 4); /* WT, WDE, WDT, SRS */
}

static void imx8m_watchdog_feed(void)
{
    WDOG_WSR = 0x5555;
    WDOG_WSR = 0xAAAA;
}

static eos_reset_reason_t imx8m_get_reset_reason(void)
{
    uint32_t srsr = SRC_SRSR;
    SRC_SRSR = srsr;
    if (srsr & (1 << 4)) return EOS_RESET_WATCHDOG;
    if (srsr & (1 << 3)) return EOS_RESET_SOFTWARE;
    if (srsr & (1 << 0)) return EOS_RESET_POWER_ON;
    return EOS_RESET_UNKNOWN;
}

static void imx8m_system_reset(void)
{
    WDOG_WCR = (1 << 2); /* Assert SRS */
    while (1) {}
}

static void imx8m_jump(uint32_t vector_addr)
{
    typedef void (*entry_fn)(void);
    entry_fn entry = (entry_fn)(uintptr_t)vector_addr;
    entry();
}

static uint32_t imx8m_get_tick_ms(void) { return tick_ms; }

static void imx8m_disable_interrupts(void)
{
#if defined(__aarch64__)
    __asm volatile ("msr daifset, #0xf" ::: "memory");
#endif
}

static void imx8m_enable_interrupts(void)
{
#if defined(__aarch64__)
    __asm volatile ("msr daifclr, #0xf" ::: "memory");
#endif
}

static void imx8m_deinit_peripherals(void) { UART_UCR1 = 0; }
static bool imx8m_recovery_pin_asserted(void) { return false; }

static const eos_board_ops_t imx8m_ops = {
    .flash_base = IMX8M_QSPI_BASE, .flash_size = IMX8M_QSPI_SIZE,
    .slot_a_addr = IMX8M_SLOT_A_ADDR, .slot_a_size = IMX8M_SLOT_A_SIZE,
    .slot_b_addr = IMX8M_SLOT_B_ADDR, .slot_b_size = IMX8M_SLOT_B_SIZE,
    .recovery_addr = IMX8M_RECOVERY_ADDR, .recovery_size = IMX8M_RECOVERY_SIZE,
    .bootctl_addr = IMX8M_BOOTCTL_ADDR,
    .flash_read = imx8m_flash_read, .flash_write = imx8m_flash_write,
    .flash_erase = imx8m_flash_erase,
    .watchdog_init = imx8m_watchdog_init, .watchdog_feed = imx8m_watchdog_feed,
    .get_reset_reason = imx8m_get_reset_reason, .system_reset = imx8m_system_reset,
    .recovery_pin_asserted = imx8m_recovery_pin_asserted, .jump = imx8m_jump,
    .uart_init = imx8m_uart_init, .uart_send = imx8m_uart_send, .uart_recv = imx8m_uart_recv,
    .get_tick_ms = imx8m_get_tick_ms,
    .disable_interrupts = imx8m_disable_interrupts, .enable_interrupts = imx8m_enable_interrupts,
    .deinit_peripherals = imx8m_deinit_peripherals,
};

const eos_board_ops_t *board_imx8m_get_ops(void) { return &imx8m_ops; }
