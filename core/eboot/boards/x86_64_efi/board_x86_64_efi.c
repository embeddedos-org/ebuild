// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_x86_64_efi.c
 * @brief x86_64 UEFI board port
 *
 * Bootloader port for x86_64 targets using UEFI boot services.
 * Uses UEFI console protocol for I/O and UEFI runtime services.
 */

#include "eos_hal.h"
#include "eos_types.h"
#include <string.h>

/* x86_64 memory map (UEFI-based) */
#define X86_FLASH_BASE      0x00000000
#define X86_FLASH_SIZE      0x00000000  /* No direct flash — use UEFI block I/O */

/* Slot layout — partitions on disk */
#define X86_SLOT_A_ADDR     0x00100000
#define X86_SLOT_A_SIZE     (64 * 1024 * 1024)
#define X86_SLOT_B_ADDR     0x04100000
#define X86_SLOT_B_SIZE     (64 * 1024 * 1024)
#define X86_RECOVERY_ADDR   0x08100000
#define X86_RECOVERY_SIZE   (32 * 1024 * 1024)
#define X86_BOOTCTL_ADDR    0x0A100000

/* COM1 16550 UART for legacy serial */
#define COM1_BASE           0x3F8

static volatile uint32_t tick_ms = 0;

/* ---- I/O port access (x86) ---- */

#if defined(__x86_64__) || defined(_M_X64)
static inline void outb(uint16_t port, uint8_t val)
{
#if defined(__GNUC__)
    __asm volatile ("outb %0, %1" : : "a"(val), "Nd"(port));
#endif
}

static inline uint8_t inb(uint16_t port)
{
    uint8_t val;
#if defined(__GNUC__)
    __asm volatile ("inb %1, %0" : "=a"(val) : "Nd"(port));
#endif
    return val;
}
#else
static inline void outb(uint16_t port, uint8_t val) { (void)port; (void)val; }
static inline uint8_t inb(uint16_t port) { (void)port; return 0; }
#endif

/* ---- Flash (stub — UEFI block I/O) ---- */

static int x86_flash_read(uint32_t addr, void *buf, size_t len)
{
    (void)addr; (void)buf; (void)len;
    return EOS_ERR_GENERIC;
}

static int x86_flash_write(uint32_t addr, const void *buf, size_t len)
{
    (void)addr; (void)buf; (void)len;
    return EOS_ERR_GENERIC;
}

static int x86_flash_erase(uint32_t addr, size_t len)
{
    (void)addr; (void)len;
    return EOS_ERR_GENERIC;
}

/* ---- UART (COM1 16550) ---- */

static int x86_uart_init(uint32_t baud)
{
    uint16_t divisor = 115200 / baud;
    outb(COM1_BASE + 1, 0x00);             /* Disable interrupts */
    outb(COM1_BASE + 3, 0x80);             /* DLAB enable */
    outb(COM1_BASE + 0, divisor & 0xFF);   /* Divisor low */
    outb(COM1_BASE + 1, (divisor >> 8));    /* Divisor high */
    outb(COM1_BASE + 3, 0x03);             /* 8N1 */
    outb(COM1_BASE + 2, 0xC7);             /* Enable & clear FIFOs */
    outb(COM1_BASE + 4, 0x0B);             /* DTR, RTS, OUT2 */
    return EOS_OK;
}

static int x86_uart_send(const void *buf, size_t len)
{
    const uint8_t *p = (const uint8_t *)buf;
    for (size_t i = 0; i < len; i++) {
        while (!(inb(COM1_BASE + 5) & 0x20)) {}  /* Wait THR empty */
        outb(COM1_BASE, p[i]);
    }
    return EOS_OK;
}

static int x86_uart_recv(void *buf, size_t len, uint32_t timeout_ms)
{
    uint8_t *p = (uint8_t *)buf;
    uint32_t start = tick_ms;

    for (size_t i = 0; i < len; i++) {
        while (!(inb(COM1_BASE + 5) & 0x01)) {
            if ((tick_ms - start) >= timeout_ms) return EOS_ERR_TIMEOUT;
        }
        p[i] = inb(COM1_BASE);
    }
    return EOS_OK;
}

/* ---- Reset ---- */

static eos_reset_reason_t x86_get_reset_reason(void)
{
    return EOS_RESET_POWER_ON;
}

static void x86_system_reset(void)
{
    /* Triple fault or keyboard controller reset */
    outb(0x64, 0xFE);
    while (1) {}
}

/* ---- Jump ---- */

static void x86_jump(uint32_t vector_addr)
{
    typedef void (*entry_fn)(void);
    entry_fn entry = (entry_fn)(uintptr_t)vector_addr;
    entry();
}

/* ---- Timing ---- */

static uint32_t x86_get_tick_ms(void)
{
    return tick_ms;
}

/* ---- Interrupt control ---- */

static void x86_disable_interrupts(void)
{
#if defined(__x86_64__) || defined(_M_X64)
#if defined(__GNUC__)
    __asm volatile ("cli" ::: "memory");
#endif
#endif
}

static void x86_enable_interrupts(void)
{
#if defined(__x86_64__) || defined(_M_X64)
#if defined(__GNUC__)
    __asm volatile ("sti" ::: "memory");
#endif
#endif
}

static void x86_deinit_peripherals(void)
{
    /* Disable COM1 interrupts */
    outb(COM1_BASE + 1, 0x00);
}

static bool x86_recovery_pin_asserted(void)
{
    return false;
}

/* ---- Board Ops ---- */

static const eos_board_ops_t x86_64_efi_ops = {
    .flash_base          = X86_FLASH_BASE,
    .flash_size          = X86_FLASH_SIZE,
    .slot_a_addr         = X86_SLOT_A_ADDR,
    .slot_a_size         = X86_SLOT_A_SIZE,
    .slot_b_addr         = X86_SLOT_B_ADDR,
    .slot_b_size         = X86_SLOT_B_SIZE,
    .recovery_addr       = X86_RECOVERY_ADDR,
    .recovery_size       = X86_RECOVERY_SIZE,
    .bootctl_addr        = X86_BOOTCTL_ADDR,

    .flash_read          = x86_flash_read,
    .flash_write         = x86_flash_write,
    .flash_erase         = x86_flash_erase,

    .get_reset_reason    = x86_get_reset_reason,
    .system_reset        = x86_system_reset,
    .recovery_pin_asserted = x86_recovery_pin_asserted,
    .jump                = x86_jump,

    .uart_init           = x86_uart_init,
    .uart_send           = x86_uart_send,
    .uart_recv           = x86_uart_recv,

    .get_tick_ms         = x86_get_tick_ms,
    .disable_interrupts  = x86_disable_interrupts,
    .enable_interrupts   = x86_enable_interrupts,
    .deinit_peripherals  = x86_deinit_peripherals,
};

const eos_board_ops_t *board_x86_64_efi_get_ops(void)
{
    return &x86_64_efi_ops;
}
