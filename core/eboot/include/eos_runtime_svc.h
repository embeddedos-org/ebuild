// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file eos_runtime_svc.h
 * @brief Runtime services callable after boot (UEFI-inspired)
 */

#ifndef EOS_RUNTIME_SVC_H
#define EOS_RUNTIME_SVC_H

#include "eos_types.h"

#ifdef __cplusplus
extern "C" {
#endif

#define EOS_RTSVC_MAX_VAR_NAME  32
#define EOS_RTSVC_MAX_VAR_SIZE  256
#define EOS_RTSVC_MAX_VARS      16

typedef enum {
    EOS_RESET_COLD   = 0,
    EOS_RESET_WARM   = 1,
    EOS_RESET_HALT   = 2,
} eos_reset_type_t;

typedef struct {
    char name[EOS_RTSVC_MAX_VAR_NAME];
    uint8_t data[EOS_RTSVC_MAX_VAR_SIZE];
    uint32_t size;
    uint32_t attributes;
} eos_runtime_var_t;

/**
 * Initialize runtime services. Called once during boot.
 */
int eos_rtsvc_init(void);

/**
 * Get a runtime variable by name.
 */
int eos_rtsvc_get_variable(const char *name, void *data, uint32_t *size);

/**
 * Set a runtime variable.
 */
int eos_rtsvc_set_variable(const char *name, const void *data, uint32_t size);

/**
 * Delete a runtime variable.
 */
int eos_rtsvc_delete_variable(const char *name);

/**
 * Request a system reset.
 */
void eos_rtsvc_reset_system(eos_reset_type_t type);

/**
 * Get system time (seconds since epoch, or uptime).
 */
uint32_t eos_rtsvc_get_time(void);

/**
 * Get the next boot slot preference.
 */
eos_slot_t eos_rtsvc_get_next_boot(void);

/**
 * Set the next boot slot preference.
 */
int eos_rtsvc_set_next_boot(eos_slot_t slot);

#ifdef __cplusplus
}
#endif

#endif /* EOS_RUNTIME_SVC_H */
