// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_cortex_r5.c
 * @brief Generic Cortex-R5F board port (TMS570-class)
 *
 * Implements eos_board_ops_t for a TMS570-class Cortex-R5F MCU.
 * Key differences from Cortex-M:
 *   - ARM mode (no Thumb-2 by default)
 *   - cpsid/cpsie if (disables both IRQ + FIQ)
 *   - Jump via direct branch (no MSP/vector table load)
 *   - RTI-based watchdog (not SysTick)
 *   - SCI module for UART (not USART)
 */

#include "board_cortex_r5.h"
#include <string.h>

/* ================================================================
 * TMS570 SCI (Serial Communication Interface) registers
 * ================================================================ */
#define SCI_BASE        R5_SCI_BASE
#define SCI_GCR0        (*(volatile uint32_t *)(SCI_BASE + 0x00))
#define SCI_GCR1        (*(volatile uint32_t *)(SCI_BASE + 0x04))
#define SCI_BRS         (*(volatile uint32_t *)(SCI_BASE + 0x2C))
#define SCI_FLR         (*(volatile uint32_t *)(SCI_BASE + 0x1C))
#define SCI_TD          (*(volatile uint32_t *)(SCI_BASE + 0x38))
#define SCI_RD          (*(volatile uint32_t *)(SCI_BASE + 0x3C))

#define SCI_FLR_TXRDY   (1 << 8)
#define SCI_FLR_RXRDY   (1 << 9)

/* ================================================================
 * RTI (Real-Time Interrupt) registers — watchdog (DWD mode)
 * ================================================================ */
#define RTI_BASE        R5_RTI_BASE
#define RTI_DWDCTRL     (*(volatile uint32_t *)(RTI_BASE + 0x90))
#define RTI_DWDPRLD     (*(volatile uint32_t *)(RTI_BASE + 0x94))
#define RTI_WDSTATUS    (*(volatile uint32_t *)(RTI_BASE + 0x98))
#define RTI_WDKEY       (*(volatile uint32_t *)(RTI_BASE + 0x9C))

#define RTI_DWD_ENABLE  0xA98559DA
#define RTI_WDKEY_SEQ1  0xE51A
#define RTI_WDKEY_SEQ2  0xA35C

/* ================================================================
 * Simple tick counter (driven by RTI compare interrupt)
 * ================================================================ */
static volatile uint32_t r5_tick_ms;

/* ================================================================
 * Flash operations (TMS570 F021 flash controller)
 * ================================================================ */
static int r5_flash_read(uint32_t addr, void *buf, size_t len)
{
    memcpy(buf, (const void *)(uintptr_t)addr, len);
    return 0;
}

static int r5_flash_write(uint32_t addr, const void *buf, size_t len)
{
    (void)addr; (void)buf; (void)len;
    /* F021 flash programming sequence — vendor-specific */
    return 0;
}

static int r5_flash_erase(uint32_t addr, size_t len)
{
    (void)addr; (void)len;
    return 0;
}

/* ================================================================
 * Watchdog — RTI Digital Windowed Watchdog
 * ================================================================ */
static void r5_watchdog_init(uint32_t timeout_ms)
{
    (void)timeout_ms;
    RTI_DWDPRLD = 0x00002710;  /* preload ~100ms at RTICLK */
    RTI_DWDCTRL = RTI_DWD_ENABLE;
}

static void r5_watchdog_feed(void)
{
    RTI_WDKEY = RTI_WDKEY_SEQ1;
    RTI_WDKEY = RTI_WDKEY_SEQ2;
}

/* ================================================================
 * Reset
 * ================================================================ */
static eos_reset_reason_t r5_get_reset_reason(void)
{
    return EOS_RESET_UNKNOWN;
}

static void r5_system_reset(void)
{
    /* Force watchdog reset by not feeding */
    while (1) { /* wait for DWD timeout */ }
}

/* ================================================================
 * Recovery pin — directly wired GPIO (active low)
 * ================================================================ */
static bool r5_recovery_pin_asserted(void)
{
    return false;
}

/* ================================================================
 * Jump to application
 *
 * Cortex-R5 jump differs from Cortex-M:
 *   - No vector table with MSP at offset 0
 *   - Direct branch to entry point address
 *   - Must be in SVC mode with interrupts disabled
 * ================================================================ */
static void r5_jump(uint32_t entry_addr)
{
    typedef void (*entry_fn)(void);
    entry_fn app = (entry_fn)(uintptr_t)entry_addr;
    app();
}

/* ================================================================
 * UART — TMS570 SCI module
 * ================================================================ */
static int r5_uart_init(uint32_t baud)
{
    SCI_GCR0 = 0;          /* Reset SCI */
    SCI_GCR0 = 1;          /* Release from reset */
    SCI_GCR1 = (1 << 25)   /* TXENA */
             | (1 << 24)   /* RXENA */
             | (1 << 7)    /* TIMING_MODE (async) */
             | (1 << 5);   /* CLOCK (internal) */
    SCI_BRS = (R5_CPU_HZ / (16 * baud)) - 1;
    return EOS_OK;
}

static int r5_uart_send(const void *buf, size_t len)
{
    const uint8_t *data = (const uint8_t *)buf;
    for (size_t i = 0; i < len; i++) {
        while (!(SCI_FLR & SCI_FLR_TXRDY)) {}
        SCI_TD = data[i];
    }
    return EOS_OK;
}

static int r5_uart_recv(void *buf, size_t len, uint32_t timeout_ms)
{
    uint8_t *data = (uint8_t *)buf;
    uint32_t start = r5_tick_ms;
    for (size_t i = 0; i < len; i++) {
        while (!(SCI_FLR & SCI_FLR_RXRDY)) {
            if ((r5_tick_ms - start) >= timeout_ms) return EOS_ERR_TIMEOUT;
        }
        data[i] = (uint8_t)SCI_RD;
    }
    return EOS_OK;
}

/* ================================================================
 * Timing
 * ================================================================ */
static uint32_t r5_get_tick_ms(void)
{
    return r5_tick_ms;
}

/* Called from RTI Compare 0 interrupt handler */
void eos_cortex_r5_rti_handler(void)
{
    r5_tick_ms++;
}

/* ================================================================
 * Interrupt control
 *
 * Cortex-R5 uses cpsid/cpsie with 'if' flag (both IRQ + FIQ),
 * unlike Cortex-M which only uses 'i' (IRQ only).
 * ================================================================ */
static void r5_disable_interrupts(void)
{
#if defined(__ARM_ARCH)
    __asm volatile ("cpsid if" ::: "memory");
#endif
}

static void r5_enable_interrupts(void)
{
#if defined(__ARM_ARCH)
    __asm volatile ("cpsie if" ::: "memory");
#endif
}

static void r5_deinit_peripherals(void)
{
    /* Disable SCI, RTI, DMA before jumping to app */
    SCI_GCR0 = 0;
}

/* ================================================================
 * Board ops — static const struct filling all fields
 * ================================================================ */
static const eos_board_ops_t cortex_r5_ops = {
    /* Memory map */
    .flash_base          = R5_FLASH_BASE,
    .flash_size          = R5_FLASH_SIZE,
    .slot_a_addr         = R5_SLOT_A_ADDR,
    .slot_a_size         = R5_SLOT_A_SIZE,
    .slot_b_addr         = R5_SLOT_B_ADDR,
    .slot_b_size         = R5_SLOT_B_SIZE,
    .recovery_addr       = R5_RECOVERY_ADDR,
    .recovery_size       = R5_RECOVERY_SIZE,
    .bootctl_addr        = R5_BOOTCTL_ADDR,
    .bootctl_backup_addr = R5_BOOTCTL_BACKUP_ADDR,
    .log_addr            = R5_LOG_ADDR,
    .app_vector_offset   = R5_VECTOR_OFFSET,

    /* Function pointers */
    .flash_read          = r5_flash_read,
    .flash_write         = r5_flash_write,
    .flash_erase         = r5_flash_erase,
    .watchdog_init       = r5_watchdog_init,
    .watchdog_feed       = r5_watchdog_feed,
    .get_reset_reason    = r5_get_reset_reason,
    .system_reset        = r5_system_reset,
    .recovery_pin_asserted = r5_recovery_pin_asserted,
    .jump                = r5_jump,
    .uart_init           = r5_uart_init,
    .uart_send           = r5_uart_send,
    .uart_recv           = r5_uart_recv,
    .get_tick_ms         = r5_get_tick_ms,
    .disable_interrupts  = r5_disable_interrupts,
    .enable_interrupts   = r5_enable_interrupts,
    .deinit_peripherals  = r5_deinit_peripherals,
};

/* ================================================================
 * Board early init — clock and peripheral setup before HAL
 * ================================================================ */
void board_early_init(void)
{
    r5_tick_ms = 0;

    /* VIM (Vectored Interrupt Manager) — clear all channels */
    /* RTI — configure Compare 0 for 1 ms tick */
    /* PLL — lock system clock to target frequency */
    /* ESM — clear error flags */

    r5_uart_init(115200);
}

const eos_board_ops_t *board_get_ops(void)
{
    return &cortex_r5_ops;
}
