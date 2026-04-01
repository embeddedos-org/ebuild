// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef EOS_SLOT_MANAGER_H
#define EOS_SLOT_MANAGER_H

#include "eos_types.h"
#include "eos_image.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Scan all firmware slots and cache their state.
 * @return Number of valid slots found, or negative error code.
 */
int eos_slot_scan_all(void);

/**
 * @brief Check if a slot contains a valid firmware image.
 * @param slot  Slot identifier.
 * @return true if the slot has a valid image.
 */
bool eos_slot_is_valid(eos_slot_t slot);

/**
 * @brief Get the firmware version from a slot's image header.
 * @param slot  Slot identifier.
 * @return Version number, or 0 if slot is empty/invalid.
 */
uint32_t eos_slot_get_version(eos_slot_t slot);

/**
 * @brief Read the image header from a slot.
 * @param slot  Slot identifier.
 * @param out   Pointer to header structure to populate.
 * @return EOS_OK on success, EOS_ERR_NO_IMAGE if empty.
 */
int eos_slot_get_header(eos_slot_t slot, eos_image_header_t *out);

/**
 * @brief Get the state of a firmware slot.
 * @param slot  Slot identifier.
 * @return Slot state enum value.
 */
eos_slot_state_t eos_slot_get_state(eos_slot_t slot);

/**
 * @brief Erase a firmware slot.
 * @param slot  Slot identifier.
 * @return EOS_OK on success, EOS_ERR_FLASH on failure.
 */
int eos_slot_erase(eos_slot_t slot);

#ifdef __cplusplus
}
#endif
#endif /* EOS_SLOT_MANAGER_H */
