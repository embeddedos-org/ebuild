// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file bootctl.c
 * @brief Boot control block load/save/validate operations
 */

#include "eos_bootctl.h"
#include "eos_hal.h"
#include "eos_image.h"
#include <string.h>

/* Compute CRC32 over a byte buffer (software implementation) */
static uint32_t crc32_buf(const void *data, size_t len)
{
    const uint8_t *p = (const uint8_t *)data;
    uint32_t crc = 0xFFFFFFFF;

    for (size_t i = 0; i < len; i++) {
        crc ^= p[i];
        for (int j = 0; j < 8; j++) {
            if (crc & 1)
                crc = (crc >> 1) ^ 0xEDB88320;
            else
                crc >>= 1;
        }
    }
    return ~crc;
}

static void bootctl_update_crc(eos_bootctl_t *bctl)
{
    bctl->crc32 = crc32_buf(bctl, offsetof(eos_bootctl_t, crc32));
}

bool eos_bootctl_validate(const eos_bootctl_t *bctl)
{
    if (bctl->magic != EOS_BOOTCTL_MAGIC)
        return false;

    uint32_t computed = crc32_buf(bctl, offsetof(eos_bootctl_t, crc32));
    return computed == bctl->crc32;
}

void eos_bootctl_init_defaults(eos_bootctl_t *bctl)
{
    memset(bctl, 0, sizeof(*bctl));
    bctl->magic          = EOS_BOOTCTL_MAGIC;
    bctl->version        = EOS_BOOTCTL_VERSION;
    bctl->active_slot    = EOS_SLOT_A;
    bctl->pending_slot   = EOS_SLOT_NONE;
    bctl->confirmed_slot = EOS_SLOT_NONE;
    bctl->boot_attempts  = 0;
    bctl->max_attempts   = EOS_MAX_BOOT_ATTEMPTS;
    bctl->flags          = 0;
    bctl->log_head       = 0;
    bctl->boot_count     = 0;
    bootctl_update_crc(bctl);
}

int eos_bootctl_load(eos_bootctl_t *bctl)
{
    const eos_board_ops_t *ops = eos_hal_get_ops();
    if (!ops)
        return EOS_ERR_GENERIC;

    /* Try primary copy */
    int rc = eos_hal_flash_read(ops->bootctl_addr, bctl, sizeof(*bctl));
    if (rc == EOS_OK && eos_bootctl_validate(bctl))
        return EOS_OK;

    /* Try backup copy */
    rc = eos_hal_flash_read(ops->bootctl_backup_addr, bctl, sizeof(*bctl));
    if (rc == EOS_OK && eos_bootctl_validate(bctl))
        return EOS_OK;

    /* Both copies corrupt — initialize defaults */
    eos_bootctl_init_defaults(bctl);
    return EOS_ERR_CRC;
}

int eos_bootctl_save(eos_bootctl_t *bctl)
{
    const eos_board_ops_t *ops = eos_hal_get_ops();
    if (!ops)
        return EOS_ERR_GENERIC;

    bootctl_update_crc(bctl);

    /* Erase and write primary */
    int rc = eos_hal_flash_erase(ops->bootctl_addr, sizeof(*bctl));
    if (rc != EOS_OK)
        return EOS_ERR_FLASH;

    rc = eos_hal_flash_write(ops->bootctl_addr, bctl, sizeof(*bctl));
    if (rc != EOS_OK)
        return EOS_ERR_FLASH;

    /* Erase and write backup */
    rc = eos_hal_flash_erase(ops->bootctl_backup_addr, sizeof(*bctl));
    if (rc != EOS_OK)
        return EOS_ERR_FLASH;

    rc = eos_hal_flash_write(ops->bootctl_backup_addr, bctl, sizeof(*bctl));
    if (rc != EOS_OK)
        return EOS_ERR_FLASH;

    return EOS_OK;
}

int eos_bootctl_increment_attempts(eos_bootctl_t *bctl)
{
    bctl->boot_attempts++;
    bctl->boot_count++;
    return eos_bootctl_save(bctl);
}

int eos_bootctl_reset_attempts(eos_bootctl_t *bctl)
{
    bctl->boot_attempts = 0;
    return eos_bootctl_save(bctl);
}

int eos_bootctl_set_pending(eos_bootctl_t *bctl, eos_slot_t slot)
{
    bctl->pending_slot = slot;
    bctl->flags |= EOS_FLAG_UPGRADE_PENDING;
    return eos_bootctl_save(bctl);
}

int eos_bootctl_clear_pending(eos_bootctl_t *bctl)
{
    bctl->pending_slot = EOS_SLOT_NONE;
    bctl->flags &= ~EOS_FLAG_UPGRADE_PENDING;
    return eos_bootctl_save(bctl);
}

int eos_bootctl_confirm(eos_bootctl_t *bctl)
{
    bctl->confirmed_slot = bctl->active_slot;
    bctl->flags |= EOS_FLAG_CONFIRMED;
    bctl->flags &= ~EOS_FLAG_TEST_BOOT;
    bctl->boot_attempts = 0;
    return eos_bootctl_save(bctl);
}

int eos_bootctl_request_recovery(eos_bootctl_t *bctl)
{
    bctl->flags |= EOS_FLAG_FORCE_RECOVERY;
    return eos_bootctl_save(bctl);
}

int eos_bootctl_request_factory_reset(eos_bootctl_t *bctl)
{
    bctl->flags |= EOS_FLAG_FACTORY_RESET;
    return eos_bootctl_save(bctl);
}

eos_slot_t eos_bootctl_other_slot(eos_slot_t slot)
{
    switch (slot) {
    case EOS_SLOT_A: return EOS_SLOT_B;
    case EOS_SLOT_B: return EOS_SLOT_A;
    default:         return EOS_SLOT_NONE;
    }
}
