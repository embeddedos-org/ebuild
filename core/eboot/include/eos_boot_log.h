// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file eos_boot_log.h
 * @brief Structured boot logging for eBootloader
 *
 * Provides a persistent, ring-buffer-based boot log stored in a
 * dedicated flash sector. Each boot cycle appends timestamped entries
 * that record slot selection, image validation, rollback events, and
 * firmware update status. The log survives resets and can be read
 * by application firmware via eos_fw_read_boot_log().
 */

#ifndef EOS_BOOT_LOG_H
#define EOS_BOOT_LOG_H

#include "eos_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ---------------- Boot Log Configuration ---------------- */

#define EOS_BOOT_LOG_SECTOR_SIZE   4096
#define EOS_BOOT_LOG_ENTRY_SIZE    sizeof(eos_boot_log_entry_t)

/* ---------------- Boot Log API ---------------- */

/**
 * @brief Initialize the boot log subsystem.
 *
 * Reads the log region from flash, validates the header, and
 * locates the current write position. If the log region is corrupt
 * or uninitialized, it is formatted with a fresh header.
 *
 * @return EOS_OK on success, EOS_ERR_FLASH on read failure.
 */
int eos_boot_log_init(void);

/**
 * @brief Append a log entry to the boot log.
 *
 * Writes a timestamped entry to the next available position in
 * the ring buffer. When the buffer is full, the oldest entry is
 * overwritten. The entry is flushed to flash immediately.
 *
 * @param event   Event code (EOS_LOG_BOOT_START, EOS_LOG_ROLLBACK, etc.)
 * @param slot    Associated slot (EOS_SLOT_A, EOS_SLOT_B, or EOS_SLOT_NONE).
 * @param detail  Event-specific detail value (version, error code, etc.)
 */
void eos_boot_log_append(uint32_t event, uint32_t slot, uint32_t detail);

/**
 * @brief Read all boot log entries into a caller-provided buffer.
 *
 * Entries are returned in chronological order (oldest first).
 *
 * @param entries   Output buffer for log entries.
 * @param max_count Maximum number of entries the buffer can hold.
 * @return Number of entries read, or negative error code.
 */
int eos_boot_log_read(eos_boot_log_entry_t *entries, uint32_t max_count);

/**
 * @brief Get the number of log entries currently stored.
 * @return Entry count (0 to EOS_BOOT_LOG_MAX).
 */
uint32_t eos_boot_log_count(void);

/**
 * @brief Clear all boot log entries and reset the write pointer.
 *
 * Erases the log flash sector and writes a fresh header.
 *
 * @return EOS_OK on success, EOS_ERR_FLASH on erase failure.
 */
int eos_boot_log_clear(void);

/**
 * @brief Flush any buffered log entries to flash.
 *
 * Normally entries are written immediately, but this can be
 * called before a jump to ensure all entries are persisted.
 *
 * @return EOS_OK on success, EOS_ERR_FLASH on write failure.
 */
int eos_boot_log_flush(void);

/**
 * @brief Get the most recent log entry.
 *
 * @param entry  Pointer to structure to populate.
 * @return EOS_OK on success, EOS_ERR_NO_IMAGE if log is empty.
 */
int eos_boot_log_get_latest(eos_boot_log_entry_t *entry);

/**
 * @brief Convert a log event code to a human-readable string.
 *
 * @param event  Event code (EOS_LOG_*).
 * @return Static string describing the event, or "UNKNOWN".
 */
const char *eos_boot_log_event_name(uint32_t event);

#ifdef __cplusplus
}
#endif
#endif /* EOS_BOOT_LOG_H */
