// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file boot_menu.c
 * @brief Interactive UART-based boot menu
 */

#include "eos_boot_menu.h"
#include "eos_hal.h"
#include "eos_bootctl.h"
#include <string.h>

static void uart_puts(uint8_t port, const char *str)
{
    eos_hal_uart_write(port, (const uint8_t *)str, strlen(str));
}

static int uart_getc(uint8_t port, uint32_t timeout_ms)
{
    uint8_t ch;
    int rc = eos_hal_uart_read(port, &ch, 1, timeout_ms);
    return (rc == EOS_OK) ? (int)ch : -1;
}

void eos_boot_menu_print_status(uint8_t uart_port)
{
    uart_puts(uart_port, "\r\n=== eBootloader Status ===\r\n");
    uart_puts(uart_port, "  Firmware: eBootloader v0.3.0\r\n");
    uart_puts(uart_port, "==========================\r\n");
}

eos_menu_choice_t eos_boot_menu_run(const eos_boot_menu_config_t *cfg)
{
    if (!cfg) return EOS_MENU_TIMEOUT;

    uint8_t port = cfg->uart_port;

    uart_puts(port, "\r\n");
    uart_puts(port, "╔══════════════════════════════╗\r\n");
    uart_puts(port, "║      eBootloader Menu        ║\r\n");
    uart_puts(port, "╠══════════════════════════════╣\r\n");
    uart_puts(port, "║  1. Boot Default             ║\r\n");
    uart_puts(port, "║  2. Boot Slot A              ║\r\n");
    uart_puts(port, "║  3. Boot Slot B              ║\r\n");
    uart_puts(port, "║  4. Recovery Mode            ║\r\n");
    uart_puts(port, "║  5. Run Diagnostics          ║\r\n");
    uart_puts(port, "║  6. View Boot Log            ║\r\n");
    uart_puts(port, "║  7. Reboot                   ║\r\n");
    uart_puts(port, "╚══════════════════════════════╝\r\n");
    uart_puts(port, "Select [1-7]: ");

    int ch = uart_getc(port, cfg->timeout_ms);

    switch (ch) {
        case '1': return EOS_MENU_BOOT_DEFAULT;
        case '2': return EOS_MENU_BOOT_SLOT_A;
        case '3': return EOS_MENU_BOOT_SLOT_B;
        case '4': return EOS_MENU_RECOVERY;
        case '5': return EOS_MENU_DIAGNOSTICS;
        case '6': return EOS_MENU_VIEW_LOG;
        case '7': return EOS_MENU_REBOOT;
        default:  return EOS_MENU_TIMEOUT;
    }
}
