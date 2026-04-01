// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file recovery_entry.c
 * @brief Stage-0 recovery trigger detection
 */

#include "eos_hal.h"
#include "eos_bootctl.h"

bool ebldr_recovery_triggered(const eos_bootctl_t *bctl)
{
    /* GPIO pin held low during reset */
    if (eos_hal_recovery_pin_asserted())
        return true;

    /* Explicit recovery flag set by firmware or bootloader */
    if (bctl->flags & EOS_FLAG_FORCE_RECOVERY)
        return true;

    /* Factory reset requested */
    if (bctl->flags & EOS_FLAG_FACTORY_RESET)
        return true;

    /* Watchdog reset with too many boot attempts */
    eos_reset_reason_t reason = eos_hal_get_reset_reason();
    if (reason == EOS_RESET_WATCHDOG &&
        bctl->boot_attempts >= bctl->max_attempts)
        return true;

    return false;
}
