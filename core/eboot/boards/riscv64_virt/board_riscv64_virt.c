// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_riscv64_virt.c
 * @brief RISC-V 64-bit QEMU virt machine board port
 *
 * Bootloader port for RISC-V 64-bit targets. Uses QEMU virt
 * machine memory map with 16550-compatible UART.
 */

#include "eos_hal.h"
#include "eos_types.h"
#include <string.h>

/* QEMU virt machine memory map */
#define VIRT_UART0_BASE     0x10000000
#define VIRT_FLASH_BASE     0x20000000
#define VIRT_FLASH_SIZE     (32 * 1024 * 1024)
#define VIRT_RAM_BASE       0x80000000

/* Slot layout in flash */
#define VIRT_SLOT_A_ADDR    0x20100000
#define VIRT_SLOT_A_SIZE    (8 * 1024 * 1024)
#define VIRT_SLOT_B_ADDR    0x20900000
#define VIRT_SLOT_B_SIZE    (8 * 1024 * 1024)
#define VIRT_RECOVERY_ADDR  0x21100000
#define VIRT_RECOVERY_SIZE  (4 * 1024 * 1024)
#define VIRT_BOOTCTL_ADDR   0x21F00000

/* 16550 UART registers */
#define UART_THR    (*(volatile uint8_t *)(VIRT_UART0_BASE + 0x00))
#define UART_RBR    (*(volatile uint8_t *)(VIRT_UART0_BASE + 0x00))
#define UART_IER    (*(volatile uint8_t *)(VIRT_UART0_BASE + 0x01))
#define UART_FCR    (*(volatile uint8_t *)(VIRT_UART0_BASE + 0x02))
#define UART_LCR    (*(volatile uint8_t *)(VIRT_UART0_BASE + 0x03))
#define UART_LSR    (*(volatile uint8_t *)(VIRT_UART0_BASE + 0x05))
#define UART_DLL    (*(volatile uint8_t *)(VIRT_UART0_BASE + 0x00))
#define UART_DLM    (*(volatile uint8_t *)(VIRT_UART0_BASE + 0x01))

static volatile uint32_t tick_ms = 0;

/* ---- Flash (memory-mapped on QEMU virt) ---- */

static int rv64_flash_read(uint32_t addr, void *buf, size_t len)
{
    memcpy(buf, (const void *)(uintptr_t)addr, len);
    return EOS_OK;
}

static int rv64_flash_write(uint32_t addr, const void *buf, size_t len)
{
    /* QEMU pflash: write-through for CFI flash model */
    memcpy((void *)(uintptr_t)addr, buf, len);
    return EOS_OK;
}

static int rv64_flash_erase(uint32_t addr, size_t len)
{
    memset((void *)(uintptr_t)addr, 0xFF, len);
    return EOS_OK;
}

/* ---- UART (16550) ---- */

static int rv64_uart_init(uint32_t baud)
{
    (void)baud;
    UART_IER = 0x00;       /* Disable interrupts */
    UART_LCR = 0x80;       /* DLAB enable */
    UART_DLL = 0x01;       /* Divisor low (115200 @ 1.8432 MHz) */
    UART_DLM = 0x00;       /* Divisor high */
    UART_LCR = 0x03;       /* 8N1 */
    UART_FCR = 0x07;       /* Enable & clear FIFOs */
    return EOS_OK;
}

static int rv64_uart_send(const void *buf, size_t len)
{
    const uint8_t *p = (const uint8_t *)buf;
    for (size_t i = 0; i < len; i++) {
        while (!(UART_LSR & 0x20)) {}  /* Wait THR empty */
        UART_THR = p[i];
    }
    return EOS_OK;
}

static int rv64_uart_recv(void *buf, size_t len, uint32_t timeout_ms)
{
    uint8_t *p = (uint8_t *)buf;
    uint32_t start = tick_ms;

    for (size_t i = 0; i < len; i++) {
        while (!(UART_LSR & 0x01)) {  /* Wait data ready */
            if ((tick_ms - start) >= timeout_ms) return EOS_ERR_TIMEOUT;
        }
        p[i] = UART_RBR;
    }
    return EOS_OK;
}

/* ---- Reset ---- */

static eos_reset_reason_t rv64_get_reset_reason(void)
{
    return EOS_RESET_POWER_ON;
}

static void rv64_system_reset(void)
{
    /* SBI ecall for system reset: EID=0x53525354 (SRST), FID=0 */
#if defined(__riscv)
    register unsigned long a7 __asm ("a7") = 0x53525354;
    register unsigned long a6 __asm ("a6") = 0;
    register unsigned long a0 __asm ("a0") = 0;  /* SHUTDOWN */
    register unsigned long a1 __asm ("a1") = 0;  /* COLD REBOOT */
    __asm volatile ("ecall" : "+r"(a0) : "r"(a1), "r"(a6), "r"(a7));
#endif
    while (1) {}
}

/* ---- Jump ---- */

static void rv64_jump(uint32_t vector_addr)
{
    typedef void (*entry_fn)(void);
    entry_fn entry = (entry_fn)(uintptr_t)vector_addr;
    entry();
}

/* ---- Timing ---- */

static uint32_t rv64_get_tick_ms(void)
{
    /* Read RISC-V mtime register via memory-mapped CLINT */
    return tick_ms;
}

/* ---- Interrupt control ---- */

static void rv64_disable_interrupts(void)
{
#if defined(__riscv)
    __asm volatile ("csrci mstatus, 0x8" ::: "memory");
#endif
}

static void rv64_enable_interrupts(void)
{
#if defined(__riscv)
    __asm volatile ("csrsi mstatus, 0x8" ::: "memory");
#endif
}

static void rv64_deinit_peripherals(void)
{
    UART_IER = 0;
}

static bool rv64_recovery_pin_asserted(void)
{
    return false;
}

/* ---- Board Ops ---- */

static const eos_board_ops_t rv64_virt_ops = {
    .flash_base          = VIRT_FLASH_BASE,
    .flash_size          = VIRT_FLASH_SIZE,
    .slot_a_addr         = VIRT_SLOT_A_ADDR,
    .slot_a_size         = VIRT_SLOT_A_SIZE,
    .slot_b_addr         = VIRT_SLOT_B_ADDR,
    .slot_b_size         = VIRT_SLOT_B_SIZE,
    .recovery_addr       = VIRT_RECOVERY_ADDR,
    .recovery_size       = VIRT_RECOVERY_SIZE,
    .bootctl_addr        = VIRT_BOOTCTL_ADDR,

    .flash_read          = rv64_flash_read,
    .flash_write         = rv64_flash_write,
    .flash_erase         = rv64_flash_erase,

    .get_reset_reason    = rv64_get_reset_reason,
    .system_reset        = rv64_system_reset,
    .recovery_pin_asserted = rv64_recovery_pin_asserted,
    .jump                = rv64_jump,

    .uart_init           = rv64_uart_init,
    .uart_send           = rv64_uart_send,
    .uart_recv           = rv64_uart_recv,

    .get_tick_ms         = rv64_get_tick_ms,
    .disable_interrupts  = rv64_disable_interrupts,
    .enable_interrupts   = rv64_enable_interrupts,
    .deinit_peripherals  = rv64_deinit_peripherals,
};

const eos_board_ops_t *board_riscv64_virt_get_ops(void)
{
    return &rv64_virt_ops;
}
