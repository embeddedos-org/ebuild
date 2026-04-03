// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file slot_manager.c
 * @brief Slot scanning, selection, and state management
 */

#include "eos_bootctl.h"
#include "eos_image.h"
#include "eos_hal.h"

/* Per-slot cached state */
typedef struct {
    eos_slot_state_t state;
    eos_image_header_t header;
    bool header_valid;
} slot_info_t;

static slot_info_t slots[2];

static int verify_slot(eos_slot_t slot)
{
    uint32_t addr = eos_hal_slot_addr(slot);
    if (addr == 0)
        return EOS_ERR_INVALID;

    slot_info_t *si = &slots[slot];
    si->header_valid = false;
    si->state = EOS_SLOT_STATE_EMPTY;

    int rc = eos_image_parse_header(addr, &si->header);
    if (rc != EOS_OK) {
        si->state = (rc == EOS_ERR_NO_IMAGE) ? EOS_SLOT_STATE_EMPTY : EOS_SLOT_STATE_INVALID;
        return rc;
    }

    uint32_t payload_addr = addr + si->header.hdr_size;
    rc = eos_image_verify_integrity(&si->header, payload_addr);
    if (rc != EOS_OK) {
        si->state = EOS_SLOT_STATE_INVALID;
        return rc;
    }

    rc = eos_image_verify_signature(&si->header);
    if (rc != EOS_OK) {
        si->state = EOS_SLOT_STATE_INVALID;
        return rc;
    }

    si->header_valid = true;
    si->state = EOS_SLOT_STATE_VALID;
    return EOS_OK;
}

int eos_slot_scan_all(void)
{
    verify_slot(EOS_SLOT_A);
    verify_slot(EOS_SLOT_B);
    return EOS_OK;
}

eos_slot_state_t eos_slot_get_state(eos_slot_t slot)
{
    if (slot > EOS_SLOT_B)
        return EOS_SLOT_STATE_EMPTY;
    return slots[slot].state;
}

int eos_slot_get_header(eos_slot_t slot, eos_image_header_t *out)
{
    if (slot > EOS_SLOT_B || !out)
        return EOS_ERR_INVALID;

    if (!slots[slot].header_valid)
        return EOS_ERR_NO_IMAGE;

    *out = slots[slot].header;
    return EOS_OK;
}

bool eos_slot_is_valid(eos_slot_t slot)
{
    if (slot > EOS_SLOT_B)
        return false;
    return slots[slot].state == EOS_SLOT_STATE_VALID ||
           slots[slot].state == EOS_SLOT_STATE_CONFIRMED;
}

int eos_slot_erase(eos_slot_t slot)
{
    uint32_t addr = eos_hal_slot_addr(slot);
    uint32_t size = eos_hal_slot_size(slot);
    if (addr == 0 || size == 0)
        return EOS_ERR_INVALID;

    int rc = eos_hal_flash_erase(addr, size);
    if (rc != EOS_OK)
        return EOS_ERR_FLASH;

    if (slot <= EOS_SLOT_B) {
        slots[slot].state = EOS_SLOT_STATE_EMPTY;
        slots[slot].header_valid = false;
    }

    return EOS_OK;
}

uint32_t eos_slot_get_version(eos_slot_t slot)
{
    if (slot > EOS_SLOT_B)
        return 0;

    if (!slots[slot].header_valid)
        return 0;

    return slots[slot].header.image_version;
}
