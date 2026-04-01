// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_sifive_u.c
 * @brief SiFive HiFive Unmatched board port (RISC-V U74, 64-bit)
 */

#include "board_sifive_u.h"
#include "eos_types.h"
#include <string.h>

/* SiFive UART registers */
#define UART_TXDATA (*(volatile uint32_t *)(SIFIVE_UART0_BASE + 0x00))
#define UART_RXDATA (*(volatile uint32_t *)(SIFIVE_UART0_BASE + 0x04))
#define UART_TXCTRL (*(volatile uint32_t *)(SIFIVE_UART0_BASE + 0x08))
#define UART_RXCTRL (*(volatile uint32_t *)(SIFIVE_UART0_BASE + 0x0C))
#define UART_DIV    (*(volatile uint32_t *)(SIFIVE_UART0_BASE + 0x18))

static volatile uint32_t tick_ms = 0;

static int sifive_flash_read(uint32_t addr, void *buf, size_t len)
{
    memcpy(buf, (const void *)(uintptr_t)addr, len);
    return EOS_OK;
}

static int sifive_flash_write(uint32_t addr, const void *buf, size_t len)
{
    (void)addr; (void)buf; (void)len;
    return EOS_OK;
}

static int sifive_flash_erase(uint32_t addr, size_t len)
{
    (void)addr; (void)len;
    return EOS_OK;
}

static int sifive_uart_init(uint32_t baud)
{
    UART_DIV = SIFIVE_CPU_HZ / baud - 1;
    UART_TXCTRL = 0x01;
    UART_RXCTRL = 0x01;
    return EOS_OK;
}

static int sifive_uart_send(const void *buf, size_t len)
{
    const uint8_t *p = (const uint8_t *)buf;
    for (size_t i = 0; i < len; i++) {
        while (UART_TXDATA & 0x80000000) {}  /* TX full */
        UART_TXDATA = p[i];
    }
    return EOS_OK;
}

static int sifive_uart_recv(void *buf, size_t len, uint32_t timeout_ms)
{
    uint8_t *p = (uint8_t *)buf;
    uint32_t start = tick_ms;
    for (size_t i = 0; i < len; i++) {
        uint32_t data;
        do {
            data = UART_RXDATA;
            if ((tick_ms - start) >= timeout_ms) return EOS_ERR_TIMEOUT;
        } while (data & 0x80000000);
        p[i] = (uint8_t)(data & 0xFF);
    }
    return EOS_OK;
}

static eos_reset_reason_t sifive_get_reset_reason(void) { return EOS_RESET_POWER_ON; }

static void sifive_system_reset(void)
{
#if defined(__riscv)
    register unsigned long a7 __asm("a7") = 0x53525354;
    register unsigned long a6 __asm("a6") = 0;
    register unsigned long a0 __asm("a0") = 0;
    register unsigned long a1 __asm("a1") = 0;
    __asm volatile ("ecall" : "+r"(a0) : "r"(a1), "r"(a6), "r"(a7));
#endif
    while (1) {}
}

static void sifive_jump(uint32_t vector_addr)
{
    typedef void (*entry_fn)(void);
    entry_fn entry = (entry_fn)(uintptr_t)vector_addr;
    entry();
}

static uint32_t sifive_get_tick_ms(void) { return tick_ms; }
static void sifive_disable_interrupts(void)
{
#if defined(__riscv)
    __asm volatile ("csrci mstatus, 0x8" ::: "memory");
#endif
}
static void sifive_enable_interrupts(void)
{
#if defined(__riscv)
    __asm volatile ("csrsi mstatus, 0x8" ::: "memory");
#endif
}
static void sifive_deinit_peripherals(void) { UART_TXCTRL = 0; }
static bool sifive_recovery_pin_asserted(void) { return false; }

static const eos_board_ops_t sifive_u_ops = {
    .flash_base = SIFIVE_QSPI_BASE, .flash_size = SIFIVE_QSPI_SIZE,
    .slot_a_addr = SIFIVE_SLOT_A_ADDR, .slot_a_size = SIFIVE_SLOT_A_SIZE,
    .slot_b_addr = SIFIVE_SLOT_B_ADDR, .slot_b_size = SIFIVE_SLOT_B_SIZE,
    .recovery_addr = SIFIVE_RECOVERY_ADDR, .recovery_size = SIFIVE_RECOVERY_SIZE,
    .bootctl_addr = SIFIVE_BOOTCTL_ADDR,
    .flash_read = sifive_flash_read, .flash_write = sifive_flash_write,
    .flash_erase = sifive_flash_erase,
    .get_reset_reason = sifive_get_reset_reason, .system_reset = sifive_system_reset,
    .recovery_pin_asserted = sifive_recovery_pin_asserted, .jump = sifive_jump,
    .uart_init = sifive_uart_init, .uart_send = sifive_uart_send, .uart_recv = sifive_uart_recv,
    .get_tick_ms = sifive_get_tick_ms,
    .disable_interrupts = sifive_disable_interrupts, .enable_interrupts = sifive_enable_interrupts,
    .deinit_peripherals = sifive_deinit_peripherals,
};

const eos_board_ops_t *board_sifive_u_get_ops(void) { return &sifive_u_ops; }
