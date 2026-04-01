// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file watchdog.c
 * @brief Stage-0 watchdog initialization
 */

#include "eos_hal.h"

#define EBLDR_WATCHDOG_TIMEOUT_MS  8000

void ebldr_watchdog_init(void)
{
    eos_hal_watchdog_init(EBLDR_WATCHDOG_TIMEOUT_MS);
}

void ebldr_watchdog_feed(void)
{
    eos_hal_watchdog_feed();
}
