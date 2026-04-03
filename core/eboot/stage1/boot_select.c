// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file boot_select.c
 * @brief Stage-1 boot slot selection wrapper
 */

#include "eos_bootctl.h"
#include "eos_image.h"
#include "eos_hal.h"

/* Forward declaration from boot_policy */
extern int eos_boot_policy_select(eos_bootctl_t *bctl, eos_slot_t *selected);
extern bool eos_boot_policy_should_recover(const eos_bootctl_t *bctl);

int eboot_select_slot(eos_bootctl_t *bctl, eos_slot_t *out)
{
    return eos_boot_policy_select(bctl, out);
}

bool eboot_should_recover(const eos_bootctl_t *bctl)
{
    return eos_boot_policy_should_recover(bctl);
}
