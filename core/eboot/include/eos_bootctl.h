// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file eos_bootctl.h
 * @brief Boot control block management for eBootloader
 *
 * The boot control block stores persistent state required to make
 * deterministic boot decisions across reset cycles. It is stored
 * in a dedicated flash sector with CRC protection and optional
 * redundancy.
 */

#ifndef EOS_BOOTCTL_H
#define EOS_BOOTCTL_H

#include "eos_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ---------------- Boot Control Block ---------------- */

typedef struct {
    uint32_t magic;               /* EOS_BOOTCTL_MAGIC */
    uint32_t version;             /* Control block format version */
    uint32_t active_slot;         /* Currently active slot (eos_slot_t) */
    uint32_t pending_slot;        /* Slot pending test boot (eos_slot_t) */
    uint32_t confirmed_slot;      /* Last confirmed-good slot (eos_slot_t) */
    uint32_t boot_attempts;       /* Current consecutive boot attempt count */
    uint32_t max_attempts;        /* Maximum allowed boot attempts */
    uint32_t last_reset_reason;   /* Last reset cause (eos_reset_reason_t) */
    uint32_t flags;               /* EOS_FLAG_* */
    uint32_t img_a_version;       /* Version of image in Slot A */
    uint32_t img_b_version;       /* Version of image in Slot B */
    uint32_t img_a_crc;           /* CRC32 of image in Slot A */
    uint32_t img_b_crc;           /* CRC32 of image in Slot B */
    uint32_t log_head;            /* Index of next log entry to write */
    uint32_t boot_count;          /* Total boot count since factory */
    uint32_t reserved[7];         /* Reserved for future use */
    uint32_t crc32;               /* CRC32 of this structure (excluding this field) */
} eos_bootctl_t;

#define EOS_BOOTCTL_VERSION  1

/* ---------------- Boot Control API ---------------- */

/**
 * @brief Load the boot control block from flash.
 * Reads the primary copy; falls back to the backup copy if the primary
 * is corrupt.
 * @param bctl  Pointer to structure to populate.
 * @return EOS_OK on success, EOS_ERR_CRC if both copies are corrupt.
 */
int eos_bootctl_load(eos_bootctl_t *bctl);

/**
 * @brief Save the boot control block to flash.
 * Writes both primary and backup copies atomically with CRC.
 * @param bctl  Pointer to structure to save.
 * @return EOS_OK on success, EOS_ERR_FLASH on write failure.
 */
int eos_bootctl_save(eos_bootctl_t *bctl);

/**
 * @brief Initialize a fresh boot control block with defaults.
 * Used on first boot or after factory reset.
 * @param bctl  Pointer to structure to initialize.
 */
void eos_bootctl_init_defaults(eos_bootctl_t *bctl);

/**
 * @brief Validate the CRC of a boot control block.
 * @param bctl  Pointer to structure to validate.
 * @return true if CRC matches, false otherwise.
 */
bool eos_bootctl_validate(const eos_bootctl_t *bctl);

/**
 * @brief Increment the boot attempt counter and save.
 * @param bctl  Pointer to active boot control block.
 * @return EOS_OK on success.
 */
int eos_bootctl_increment_attempts(eos_bootctl_t *bctl);

/**
 * @brief Reset boot attempt counter to zero and save.
 * @param bctl  Pointer to active boot control block.
 * @return EOS_OK on success.
 */
int eos_bootctl_reset_attempts(eos_bootctl_t *bctl);

/**
 * @brief Set the pending slot for test boot.
 * @param bctl  Pointer to active boot control block.
 * @param slot  Target slot.
 * @return EOS_OK on success.
 */
int eos_bootctl_set_pending(eos_bootctl_t *bctl, eos_slot_t slot);

/**
 * @brief Clear the pending slot after a failed verification.
 * @param bctl  Pointer to active boot control block.
 * @return EOS_OK on success.
 */
int eos_bootctl_clear_pending(eos_bootctl_t *bctl);

/**
 * @brief Confirm the active slot as known-good.
 * Clears the test boot flag and marks the active slot as confirmed.
 * @param bctl  Pointer to active boot control block.
 * @return EOS_OK on success.
 */
int eos_bootctl_confirm(eos_bootctl_t *bctl);

/**
 * @brief Set the force-recovery flag.
 * @param bctl  Pointer to active boot control block.
 * @return EOS_OK on success.
 */
int eos_bootctl_request_recovery(eos_bootctl_t *bctl);

/**
 * @brief Set the factory reset flag.
 * @param bctl  Pointer to active boot control block.
 * @return EOS_OK on success.
 */
int eos_bootctl_request_factory_reset(eos_bootctl_t *bctl);

/**
 * @brief Get the alternate slot.
 * @param slot  Current slot.
 * @return The other slot (A→B, B→A), or EOS_SLOT_NONE.
 */
eos_slot_t eos_bootctl_other_slot(eos_slot_t slot);

#ifdef __cplusplus
}
#endif
#endif /* EOS_BOOTCTL_H */
