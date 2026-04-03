// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file fw_services.c
 * @brief Firmware services API implementation
 *
 * Runtime API for application firmware to query boot state,
 * request upgrades, confirm images, and trigger recovery.
 */

#include "eos_fwsvc.h"
#include "eos_bootctl.h"
#include "eos_hal.h"
#include <string.h>

/* Shared boot control block — initialized by bootloader before jump */
static eos_bootctl_t fw_bctl;
static bool fw_bctl_loaded = false;

static int ensure_loaded(void)
{
    if (fw_bctl_loaded)
        return EOS_OK;

    int rc = eos_bootctl_load(&fw_bctl);
    if (rc == EOS_OK || rc == EOS_ERR_CRC) {
        fw_bctl_loaded = true;
        return EOS_OK;
    }
    return rc;
}

int eos_fw_get_status(eos_fw_status_t *out)
{
    if (!out)
        return EOS_ERR_INVALID;

    int rc = ensure_loaded();
    if (rc != EOS_OK)
        return rc;

    out->active           = (eos_slot_t)fw_bctl.active_slot;
    out->confirmed        = (eos_slot_t)fw_bctl.confirmed_slot;
    out->pending          = (eos_slot_t)fw_bctl.pending_slot;
    out->active_version   = (fw_bctl.active_slot == EOS_SLOT_A) ?
                            fw_bctl.img_a_version : fw_bctl.img_b_version;
    out->previous_version = (fw_bctl.active_slot == EOS_SLOT_A) ?
                            fw_bctl.img_b_version : fw_bctl.img_a_version;
    out->boot_count       = fw_bctl.boot_count;
    out->reset_reason     = fw_bctl.last_reset_reason;
    out->security_flags   = 0; /* Phase 2 */
    out->boot_attempts    = fw_bctl.boot_attempts;
    out->max_attempts     = fw_bctl.max_attempts;

    return EOS_OK;
}

int eos_fw_request_upgrade(eos_slot_t slot, eos_upgrade_mode_t mode)
{
    int rc = ensure_loaded();
    if (rc != EOS_OK)
        return rc;

    if (slot != EOS_SLOT_A && slot != EOS_SLOT_B)
        return EOS_ERR_INVALID;

    if ((eos_slot_t)fw_bctl.active_slot == slot)
        return EOS_ERR_INVALID;

    if (mode == EOS_UPGRADE_TEST) {
        fw_bctl.pending_slot = slot;
        fw_bctl.flags |= EOS_FLAG_UPGRADE_PENDING;
        fw_bctl.flags |= EOS_FLAG_TEST_BOOT;
    } else {
        fw_bctl.active_slot = slot;
        fw_bctl.confirmed_slot = slot;
        fw_bctl.pending_slot = EOS_SLOT_NONE;
        fw_bctl.flags |= EOS_FLAG_CONFIRMED;
        fw_bctl.flags &= ~EOS_FLAG_TEST_BOOT;
        fw_bctl.flags &= ~EOS_FLAG_UPGRADE_PENDING;
        fw_bctl.boot_attempts = 0;
    }

    return eos_bootctl_save(&fw_bctl);
}

int eos_fw_confirm_running_image(void)
{
    int rc = ensure_loaded();
    if (rc != EOS_OK)
        return rc;

    return eos_bootctl_confirm(&fw_bctl);
}

int eos_fw_request_recovery(void)
{
    int rc = ensure_loaded();
    if (rc != EOS_OK)
        return rc;

    return eos_bootctl_request_recovery(&fw_bctl);
}

int eos_fw_factory_reset(void)
{
    int rc = ensure_loaded();
    if (rc != EOS_OK)
        return rc;

    return eos_bootctl_request_factory_reset(&fw_bctl);
}

int eos_fw_read_boot_log(void *buf, size_t len)
{
    if (!buf || len == 0)
        return EOS_ERR_INVALID;

    const eos_board_ops_t *ops = eos_hal_get_ops();
    if (!ops)
        return EOS_ERR_GENERIC;

    size_t max_bytes = EOS_BOOT_LOG_MAX * sizeof(eos_boot_log_entry_t);
    size_t read_len = (len < max_bytes) ? len : max_bytes;

    return eos_hal_flash_read(ops->log_addr, buf, read_len);
}

int eos_fw_get_slot_version(eos_slot_t slot, uint32_t *version)
{
    if (!version)
        return EOS_ERR_INVALID;

    int rc = ensure_loaded();
    if (rc != EOS_OK)
        return rc;

    switch (slot) {
    case EOS_SLOT_A:
        *version = fw_bctl.img_a_version;
        break;
    case EOS_SLOT_B:
        *version = fw_bctl.img_b_version;
        break;
    default:
        return EOS_ERR_INVALID;
    }

    if (*version == 0)
        return EOS_ERR_NO_IMAGE;

    return EOS_OK;
}

bool eos_fw_is_test_boot(void)
{
    if (ensure_loaded() != EOS_OK)
        return false;

    return (fw_bctl.flags & EOS_FLAG_TEST_BOOT) != 0;
}

uint32_t eos_fw_remaining_attempts(void)
{
    if (ensure_loaded() != EOS_OK)
        return 0;

    if (!(fw_bctl.flags & EOS_FLAG_TEST_BOOT))
        return 0;

    if (fw_bctl.boot_attempts >= fw_bctl.max_attempts)
        return 0;

    return fw_bctl.max_attempts - fw_bctl.boot_attempts;
}
