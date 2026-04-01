// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_rpi4.c
 * @brief Raspberry Pi 4 board port (BCM2711, Cortex-A72, ARM64)
 *
 * Bootloader port for ARM64 Cortex-A application processors.
 * Uses MMIO for peripherals, UART via PL011 (mini UART).
 */

#include "eos_hal.h"
#include "eos_types.h"

/* BCM2711 peripheral base (low-peripheral mode) */
#define BCM2711_PERI_BASE       0xFE000000
#define BCM2711_GPIO_BASE       (BCM2711_PERI_BASE + 0x200000)
#define BCM2711_UART0_BASE      (BCM2711_PERI_BASE + 0x201000)
#define BCM2711_AUX_BASE        (BCM2711_PERI_BASE + 0x215000)

/* Memory map */
#define RPI4_FLASH_BASE         0x00000000
#define RPI4_FLASH_SIZE         0x00000000  /* SD card, not memory-mapped */
#define RPI4_RAM_BASE           0x00000000
#define RPI4_RAM_SIZE           (4UL * 1024 * 1024 * 1024)  /* 4GB */

/* Slot layout — using SD card partitions conceptually */
#define RPI4_SLOT_A_ADDR        0x00080000  /* kernel8.img load address */
#define RPI4_SLOT_A_SIZE        (32 * 1024 * 1024)
#define RPI4_SLOT_B_ADDR        0x02080000
#define RPI4_SLOT_B_SIZE        (32 * 1024 * 1024)
#define RPI4_RECOVERY_ADDR      0x04080000
#define RPI4_RECOVERY_SIZE      (16 * 1024 * 1024)
#define RPI4_BOOTCTL_ADDR       0x06000000

/* PL011 UART registers */
#define UART0_DR    (*(volatile uint32_t *)(BCM2711_UART0_BASE + 0x00))
#define UART0_FR    (*(volatile uint32_t *)(BCM2711_UART0_BASE + 0x18))
#define UART0_IBRD  (*(volatile uint32_t *)(BCM2711_UART0_BASE + 0x24))
#define UART0_FBRD  (*(volatile uint32_t *)(BCM2711_UART0_BASE + 0x28))
#define UART0_LCRH  (*(volatile uint32_t *)(BCM2711_UART0_BASE + 0x2C))
#define UART0_CR    (*(volatile uint32_t *)(BCM2711_UART0_BASE + 0x30))
#define UART0_ICR   (*(volatile uint32_t *)(BCM2711_UART0_BASE + 0x44))

static volatile uint32_t tick_ms = 0;

/* ---- Flash (stub — RPi boots from SD/eMMC) ---- */

static int rpi4_flash_read(uint32_t addr, void *buf, size_t len)
{
    /* On RPi4, "flash" is actually SD card or eMMC */
    /* In a real impl, this would use the EMMC2 controller */
    (void)addr; (void)buf; (void)len;
    return EOS_ERR_GENERIC;
}

static int rpi4_flash_write(uint32_t addr, const void *buf, size_t len)
{
    (void)addr; (void)buf; (void)len;
    return EOS_ERR_GENERIC;
}

static int rpi4_flash_erase(uint32_t addr, size_t len)
{
    (void)addr; (void)len;
    return EOS_ERR_GENERIC;
}

/* ---- UART (PL011) ---- */

static int rpi4_uart_init(uint32_t baud)
{
    UART0_CR = 0;           /* Disable UART */
    UART0_ICR = 0x7FF;      /* Clear all interrupts */

    /* Baud rate: 48MHz UART clock / (16 * baud) */
    uint32_t divider = 48000000 / (16 * baud);
    uint32_t frac = ((48000000 % (16 * baud)) * 64 + (16 * baud) / 2) / (16 * baud);
    UART0_IBRD = divider;
    UART0_FBRD = frac;

    UART0_LCRH = (3 << 5);  /* 8-bit, FIFO enabled */
    UART0_CR = (1 << 0) | (1 << 8) | (1 << 9);  /* Enable, TX, RX */

    return EOS_OK;
}

static int rpi4_uart_send(const void *buf, size_t len)
{
    const uint8_t *p = (const uint8_t *)buf;
    for (size_t i = 0; i < len; i++) {
        while (UART0_FR & (1 << 5)) {}  /* Wait TX FIFO not full */
        UART0_DR = p[i];
    }
    return EOS_OK;
}

static int rpi4_uart_recv(void *buf, size_t len, uint32_t timeout_ms)
{
    uint8_t *p = (uint8_t *)buf;
    uint32_t start = tick_ms;

    for (size_t i = 0; i < len; i++) {
        while (UART0_FR & (1 << 4)) {  /* RX FIFO empty */
            if ((tick_ms - start) >= timeout_ms) return EOS_ERR_TIMEOUT;
        }
        p[i] = (uint8_t)(UART0_DR & 0xFF);
    }
    return EOS_OK;
}

/* ---- Reset ---- */

#define PM_BASE         (BCM2711_PERI_BASE + 0x100000)
#define PM_RSTC         (*(volatile uint32_t *)(PM_BASE + 0x1C))
#define PM_WDOG         (*(volatile uint32_t *)(PM_BASE + 0x24))
#define PM_PASSWORD     0x5A000000

static void rpi4_system_reset(void)
{
    PM_WDOG = PM_PASSWORD | 1;
    PM_RSTC = PM_PASSWORD | 0x20;
    while (1) {}
}

static eos_reset_reason_t rpi4_get_reset_reason(void)
{
    return EOS_RESET_POWER_ON;
}

/* ---- Jump (ARM64) ---- */

static void rpi4_jump(uint32_t vector_addr)
{
    typedef void (*entry_fn)(void);
    entry_fn entry = (entry_fn)(uintptr_t)vector_addr;
    entry();
}

/* ---- Timing ---- */

static uint32_t rpi4_get_tick_ms(void)
{
    /* ARM generic timer: CNTPCT_EL0 / CNTFRQ_EL0 */
    return tick_ms;
}

/* ---- Interrupt control ---- */

static void rpi4_disable_interrupts(void)
{
#if defined(__aarch64__)
    __asm volatile ("msr daifset, #0xf" ::: "memory");
#endif
}

static void rpi4_enable_interrupts(void)
{
#if defined(__aarch64__)
    __asm volatile ("msr daifclr, #0xf" ::: "memory");
#endif
}

static void rpi4_deinit_peripherals(void)
{
    UART0_CR = 0;
}

static bool rpi4_recovery_pin_asserted(void)
{
    return false;
}

/* ---- Board Ops ---- */

static const eos_board_ops_t rpi4_ops = {
    .flash_base          = RPI4_FLASH_BASE,
    .flash_size          = RPI4_FLASH_SIZE,
    .slot_a_addr         = RPI4_SLOT_A_ADDR,
    .slot_a_size         = RPI4_SLOT_A_SIZE,
    .slot_b_addr         = RPI4_SLOT_B_ADDR,
    .slot_b_size         = RPI4_SLOT_B_SIZE,
    .recovery_addr       = RPI4_RECOVERY_ADDR,
    .recovery_size       = RPI4_RECOVERY_SIZE,
    .bootctl_addr        = RPI4_BOOTCTL_ADDR,
    .bootctl_backup_addr = 0x3FF80000,
    .log_addr            = 0x3FFC0000,
    .app_vector_offset   = 0x80000,

    .flash_read          = rpi4_flash_read,
    .flash_write         = rpi4_flash_write,
    .flash_erase         = rpi4_flash_erase,

    .get_reset_reason    = rpi4_get_reset_reason,
    .system_reset        = rpi4_system_reset,
    .recovery_pin_asserted = rpi4_recovery_pin_asserted,
    .jump                = rpi4_jump,

    .uart_init           = rpi4_uart_init,
    .uart_send           = rpi4_uart_send,
    .uart_recv           = rpi4_uart_recv,

    .get_tick_ms         = rpi4_get_tick_ms,
    .disable_interrupts  = rpi4_disable_interrupts,
    .enable_interrupts   = rpi4_enable_interrupts,
    .deinit_peripherals  = rpi4_deinit_peripherals,
};

const eos_board_ops_t *board_rpi4_get_ops(void)
{
    return &rpi4_ops;
}
