// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file boot_policy.c
 * @brief Boot decision logic — slot selection, rollback, test boot
 */

#include "eos_bootctl.h"
#include "eos_image.h"
#include "eos_hal.h"

/* Forward declarations from slot_manager */
extern int  eos_slot_scan_all(void);
extern bool eos_slot_is_valid(eos_slot_t slot);

/* Forward declarations from boot_log */
extern void eos_boot_log_append(uint32_t event, uint32_t slot, uint32_t detail);

int eos_boot_policy_select(eos_bootctl_t *bctl, eos_slot_t *selected)
{
    *selected = EOS_SLOT_NONE;

    /* Check if maximum boot attempts exceeded — trigger rollback */
    if (bctl->boot_attempts >= bctl->max_attempts) {
        eos_slot_t alt = eos_bootctl_other_slot((eos_slot_t)bctl->active_slot);
        if (eos_slot_is_valid(alt)) {
            bctl->active_slot = alt;
            bctl->boot_attempts = 0;
            bctl->flags |= EOS_FLAG_ROLLBACK;
            bctl->flags &= ~EOS_FLAG_TEST_BOOT;
            eos_bootctl_clear_pending(bctl);
            eos_boot_log_append(EOS_LOG_ROLLBACK, alt, 0);
            *selected = alt;
            return EOS_OK;
        }
        /* No valid alternate — will fall through to recovery */
        return EOS_ERR_NO_IMAGE;
    }

    /* Handle pending upgrade (test boot) */
    if (bctl->pending_slot != EOS_SLOT_NONE &&
        (bctl->flags & EOS_FLAG_UPGRADE_PENDING)) {
        eos_slot_t pending = (eos_slot_t)bctl->pending_slot;
        if (eos_slot_is_valid(pending)) {
            bctl->active_slot = pending;
            bctl->flags |= EOS_FLAG_TEST_BOOT;
            bctl->flags &= ~EOS_FLAG_UPGRADE_PENDING;
            bctl->pending_slot = EOS_SLOT_NONE;
            eos_boot_log_append(EOS_LOG_SLOT_SELECTED, pending, 1);
            *selected = pending;
            return EOS_OK;
        }
        /* Pending image invalid — clear and continue */
        eos_bootctl_clear_pending(bctl);
        eos_boot_log_append(EOS_LOG_IMAGE_INVALID, pending, 0);
    }

    /* Try the active slot */
    eos_slot_t active = (eos_slot_t)bctl->active_slot;
    if (eos_slot_is_valid(active)) {
        eos_boot_log_append(EOS_LOG_SLOT_SELECTED, active, 0);
        *selected = active;
        return EOS_OK;
    }

    /* Active image invalid — try the alternate slot */
    eos_slot_t alt = eos_bootctl_other_slot(active);
    if (eos_slot_is_valid(alt)) {
        bctl->active_slot = alt;
        bctl->flags |= EOS_FLAG_ROLLBACK;
        eos_boot_log_append(EOS_LOG_ROLLBACK, alt, 0);
        *selected = alt;
        return EOS_OK;
    }

    /* No bootable image found */
    eos_boot_log_append(EOS_LOG_BOOT_FAIL, EOS_SLOT_NONE, 0);
    return EOS_ERR_NO_IMAGE;
}

bool eos_boot_policy_should_recover(const eos_bootctl_t *bctl)
{
    if (bctl->flags & EOS_FLAG_FORCE_RECOVERY)
        return true;

    if (bctl->flags & EOS_FLAG_FACTORY_RESET)
        return true;

    return false;
}

bool eos_boot_policy_is_test_boot(const eos_bootctl_t *bctl)
{
    return (bctl->flags & EOS_FLAG_TEST_BOOT) != 0;
}

bool eos_boot_policy_is_confirmed(const eos_bootctl_t *bctl)
{
    return (bctl->flags & EOS_FLAG_CONFIRMED) != 0;
}
