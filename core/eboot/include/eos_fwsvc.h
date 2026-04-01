// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file eos_fwsvc.h
 * @brief Firmware Services API for eBootloader
 *
 * Runtime-facing API that allows application firmware to interact
 * with boot state safely. Firmware should never write boot metadata
 * directly — it should use this interface.
 */

#ifndef EOS_FWSVC_H
#define EOS_FWSVC_H

#include "eos_types.h"
#include "eos_bootctl.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ---------------- Firmware Status ---------------- */

typedef struct {
    eos_slot_t active;
    eos_slot_t confirmed;
    eos_slot_t pending;
    uint32_t   active_version;
    uint32_t   previous_version;
    uint32_t   boot_count;
    uint32_t   reset_reason;
    uint32_t   security_flags;
    uint32_t   boot_attempts;
    uint32_t   max_attempts;
} eos_fw_status_t;

/* ---------------- Firmware Services API ---------------- */

/**
 * @brief Get current boot status.
 * @param out  Pointer to status structure to populate.
 * @return EOS_OK on success.
 */
int eos_fw_get_status(eos_fw_status_t *out);

/**
 * @brief Request an upgrade to a new image.
 * @param slot  Target slot containing the new image.
 * @param mode  EOS_UPGRADE_TEST for single-try, EOS_UPGRADE_PERMANENT for immediate switch.
 * @return EOS_OK on success, negative error code on failure.
 */
int eos_fw_request_upgrade(eos_slot_t slot, eos_upgrade_mode_t mode);

/**
 * @brief Confirm the currently running image as known-good.
 * Must be called after a successful test boot to prevent rollback.
 * @return EOS_OK on success.
 */
int eos_fw_confirm_running_image(void);

/**
 * @brief Request entry into recovery mode on next reboot.
 * @return EOS_OK on success.
 */
int eos_fw_request_recovery(void);

/**
 * @brief Request factory reset on next reboot.
 * Erases both slots and resets boot control to defaults.
 * @return EOS_OK on success.
 */
int eos_fw_factory_reset(void);

/**
 * @brief Read boot log entries.
 * @param buf  Buffer to receive log entries.
 * @param len  Size of buffer in bytes.
 * @return Number of bytes read, or negative error code.
 */
int eos_fw_read_boot_log(void *buf, size_t len);

/**
 * @brief Get the version of the image in a specific slot.
 * @param slot     Target slot.
 * @param version  Output pointer for version.
 * @return EOS_OK on success, EOS_ERR_NO_IMAGE if slot is empty.
 */
int eos_fw_get_slot_version(eos_slot_t slot, uint32_t *version);

/**
 * @brief Check if the current boot is a test boot.
 * @return true if running in test-boot mode.
 */
bool eos_fw_is_test_boot(void);

/**
 * @brief Get the number of remaining boot attempts before rollback.
 * @return Remaining attempts, or 0 if not in test-boot mode.
 */
uint32_t eos_fw_remaining_attempts(void);

#ifdef __cplusplus
}
#endif
#endif /* EOS_FWSVC_H */
