// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_esp32.c
 * @brief ESP32 board port (Xtensa LX6 dual-core, Wi-Fi/BLE SoC)
 *
 * Bootloader port for Espressif ESP32. Uses ROM UART functions
 * and flash via SPI interface. ESP-IDF bootloader conventions.
 */

#include "eos_hal.h"
#include "eos_types.h"
#include <string.h>

/* ESP32 memory map */
#define ESP32_FLASH_BASE    0x00000000  /* Accessed via SPI, mapped at 0x3F400000 */
#define ESP32_FLASH_SIZE    (4 * 1024 * 1024)
#define ESP32_IRAM_BASE     0x40080000
#define ESP32_DRAM_BASE     0x3FFB0000

/* Flash partitions (OTA scheme) */
#define ESP32_SLOT_A_ADDR   0x00010000  /* ota_0 */
#define ESP32_SLOT_A_SIZE   (1536 * 1024)
#define ESP32_SLOT_B_ADDR   0x00190000  /* ota_1 */
#define ESP32_SLOT_B_SIZE   (1536 * 1024)
#define ESP32_RECOVERY_ADDR 0x00310000  /* factory */
#define ESP32_RECOVERY_SIZE (512 * 1024)
#define ESP32_BOOTCTL_ADDR  0x003F0000  /* otadata */

/* UART0 registers */
#define UART0_BASE          0x3FF40000
#define UART0_FIFO          (*(volatile uint32_t *)(UART0_BASE + 0x00))
#define UART0_STATUS        (*(volatile uint32_t *)(UART0_BASE + 0x1C))
#define UART0_CONF0         (*(volatile uint32_t *)(UART0_BASE + 0x20))

/* RTC_CNTL for reset reason */
#define RTC_CNTL_BASE       0x3FF48000
#define RTC_CNTL_RESET_STATE (*(volatile uint32_t *)(RTC_CNTL_BASE + 0x34))

static volatile uint32_t tick_ms = 0;

/* ---- Flash (SPI flash) ---- */

static int esp32_flash_read(uint32_t addr, void *buf, size_t len)
{
    /* In real impl: use esp_rom_spiflash_read() */
    (void)addr; (void)buf; (void)len;
    return EOS_OK;
}

static int esp32_flash_write(uint32_t addr, const void *buf, size_t len)
{
    /* In real impl: use esp_rom_spiflash_write() */
    (void)addr; (void)buf; (void)len;
    return EOS_OK;
}

static int esp32_flash_erase(uint32_t addr, size_t len)
{
    /* In real impl: use esp_rom_spiflash_erase_sector() */
    (void)addr; (void)len;
    return EOS_OK;
}

/* ---- UART ---- */

static int esp32_uart_init(uint32_t baud)
{
    (void)baud;
    /* ESP32 ROM already initializes UART0 at 115200 */
    return EOS_OK;
}

static int esp32_uart_send(const void *buf, size_t len)
{
    const uint8_t *p = (const uint8_t *)buf;
    for (size_t i = 0; i < len; i++) {
        while ((UART0_STATUS >> 16) & 0xFF) {}  /* TX FIFO count */
        UART0_FIFO = p[i];
    }
    return EOS_OK;
}

static int esp32_uart_recv(void *buf, size_t len, uint32_t timeout_ms)
{
    uint8_t *p = (uint8_t *)buf;
    uint32_t start = tick_ms;

    for (size_t i = 0; i < len; i++) {
        while (!((UART0_STATUS >> 0) & 0xFF)) {  /* RX FIFO count */
            if ((tick_ms - start) >= timeout_ms) return EOS_ERR_TIMEOUT;
        }
        p[i] = (uint8_t)(UART0_FIFO & 0xFF);
    }
    return EOS_OK;
}

/* ---- Reset ---- */

static eos_reset_reason_t esp32_get_reset_reason(void)
{
    uint32_t reason = RTC_CNTL_RESET_STATE & 0x3F;
    switch (reason) {
        case 1:  return EOS_RESET_POWER_ON;
        case 3:  return EOS_RESET_SOFTWARE;
        case 5:  return EOS_RESET_PIN;
        case 7:
        case 8:  return EOS_RESET_WATCHDOG;
        case 15: return EOS_RESET_BROWNOUT;
        default: return EOS_RESET_UNKNOWN;
    }
}

static void esp32_system_reset(void)
{
    /* Software reset via RTC_CNTL */
    *(volatile uint32_t *)(RTC_CNTL_BASE + 0x00) = 0x80000000;
    while (1) {}
}

/* ---- Jump ---- */

static void esp32_jump(uint32_t vector_addr)
{
    typedef void (*entry_fn)(void);
    entry_fn entry = (entry_fn)(uintptr_t)vector_addr;
    entry();
}

/* ---- Timing ---- */

static uint32_t esp32_get_tick_ms(void)
{
    return tick_ms;
}

/* ---- Interrupt control ---- */

static void esp32_disable_interrupts(void)
{
#if defined(__XTENSA__)
    uint32_t ps;
    __asm volatile ("rsil %0, 15" : "=a"(ps));
#endif
}

static void esp32_enable_interrupts(void)
{
#if defined(__XTENSA__)
    __asm volatile ("rsil a0, 0" ::: "a0");
#endif
}

static void esp32_deinit_peripherals(void)
{
    /* Disable UART interrupts */
}

static void esp32_watchdog_init(uint32_t timeout_ms)
{
    (void)timeout_ms;
}

static void esp32_watchdog_feed(void)
{
    /* Feed TIMG0 watchdog */
}

static bool esp32_recovery_pin_asserted(void)
{
    /* GPIO0 — held low for flash/recovery mode */
    return false;
}

/* ---- Board Ops ---- */

static const eos_board_ops_t esp32_ops = {
    .flash_base          = ESP32_FLASH_BASE,
    .flash_size          = ESP32_FLASH_SIZE,
    .slot_a_addr         = ESP32_SLOT_A_ADDR,
    .slot_a_size         = ESP32_SLOT_A_SIZE,
    .slot_b_addr         = ESP32_SLOT_B_ADDR,
    .slot_b_size         = ESP32_SLOT_B_SIZE,
    .recovery_addr       = ESP32_RECOVERY_ADDR,
    .recovery_size       = ESP32_RECOVERY_SIZE,
    .bootctl_addr        = ESP32_BOOTCTL_ADDR,

    .flash_read          = esp32_flash_read,
    .flash_write         = esp32_flash_write,
    .flash_erase         = esp32_flash_erase,

    .watchdog_init       = esp32_watchdog_init,
    .watchdog_feed       = esp32_watchdog_feed,

    .get_reset_reason    = esp32_get_reset_reason,
    .system_reset        = esp32_system_reset,
    .recovery_pin_asserted = esp32_recovery_pin_asserted,
    .jump                = esp32_jump,

    .uart_init           = esp32_uart_init,
    .uart_send           = esp32_uart_send,
    .uart_recv           = esp32_uart_recv,

    .get_tick_ms         = esp32_get_tick_ms,
    .disable_interrupts  = esp32_disable_interrupts,
    .enable_interrupts   = esp32_enable_interrupts,
    .deinit_peripherals  = esp32_deinit_peripherals,
};

const eos_board_ops_t *board_esp32_get_ops(void)
{
    return &esp32_ops;
}
