// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file eos_boot_menu.h
 * @brief Interactive UART-based boot menu
 */

#ifndef EOS_BOOT_MENU_H
#define EOS_BOOT_MENU_H

#include "eos_types.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    EOS_MENU_BOOT_DEFAULT = 0,
    EOS_MENU_BOOT_SLOT_A  = 1,
    EOS_MENU_BOOT_SLOT_B  = 2,
    EOS_MENU_RECOVERY     = 3,
    EOS_MENU_DIAGNOSTICS  = 4,
    EOS_MENU_VIEW_LOG     = 5,
    EOS_MENU_REBOOT       = 6,
    EOS_MENU_TIMEOUT      = 0xFF,
} eos_menu_choice_t;

typedef struct {
    uint32_t timeout_ms;
    uint8_t uart_port;
    uint32_t baudrate;
    bool show_version;
    bool show_slot_info;
} eos_boot_menu_config_t;

/**
 * Display the boot menu and wait for user selection.
 */
eos_menu_choice_t eos_boot_menu_run(const eos_boot_menu_config_t *cfg);

/**
 * Print boot status information to UART.
 */
void eos_boot_menu_print_status(uint8_t uart_port);

#ifdef __cplusplus
}
#endif

#endif /* EOS_BOOT_MENU_H */
