// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file runtime_services.c
 * @brief Runtime services — get/set variables, reset, time
 */

#include "eos_runtime_svc.h"
#include <string.h>

static eos_runtime_var_t var_store[EOS_RTSVC_MAX_VARS];
static uint32_t var_count = 0;
static bool rtsvc_initialized = false;
static volatile uint32_t uptime_seconds = 0;
static eos_slot_t next_boot_slot = EOS_SLOT_NONE;

int eos_rtsvc_init(void)
{
    memset(var_store, 0, sizeof(var_store));
    var_count = 0;
    rtsvc_initialized = true;
    uptime_seconds = 0;
    next_boot_slot = EOS_SLOT_NONE;
    return EOS_OK;
}

static eos_runtime_var_t *find_var(const char *name)
{
    for (uint32_t i = 0; i < var_count; i++) {
        if (strcmp(var_store[i].name, name) == 0) {
            return &var_store[i];
        }
    }
    return NULL;
}

int eos_rtsvc_get_variable(const char *name, void *data, uint32_t *size)
{
    if (!name || !data || !size) return EOS_ERR_INVALID;
    if (!rtsvc_initialized) return EOS_ERR_GENERIC;

    eos_runtime_var_t *var = find_var(name);
    if (!var) return EOS_ERR_NOT_FOUND;

    if (*size < var->size) {
        *size = var->size;
        return EOS_ERR_FULL;
    }

    memcpy(data, var->data, var->size);
    *size = var->size;
    return EOS_OK;
}

int eos_rtsvc_set_variable(const char *name, const void *data, uint32_t size)
{
    if (!name || !data || size == 0) return EOS_ERR_INVALID;
    if (!rtsvc_initialized) return EOS_ERR_GENERIC;
    if (size > EOS_RTSVC_MAX_VAR_SIZE) return EOS_ERR_FULL;

    eos_runtime_var_t *var = find_var(name);
    if (!var) {
        if (var_count >= EOS_RTSVC_MAX_VARS) return EOS_ERR_FULL;
        var = &var_store[var_count++];
        size_t nlen = strlen(name);
        if (nlen >= EOS_RTSVC_MAX_VAR_NAME) nlen = EOS_RTSVC_MAX_VAR_NAME - 1;
        memcpy(var->name, name, nlen);
        var->name[nlen] = '\0';
    }

    memcpy(var->data, data, size);
    var->size = size;
    return EOS_OK;
}

int eos_rtsvc_delete_variable(const char *name)
{
    if (!name) return EOS_ERR_INVALID;

    for (uint32_t i = 0; i < var_count; i++) {
        if (strcmp(var_store[i].name, name) == 0) {
            for (uint32_t j = i; j < var_count - 1; j++) {
                var_store[j] = var_store[j + 1];
            }
            memset(&var_store[--var_count], 0, sizeof(eos_runtime_var_t));
            return EOS_OK;
        }
    }
    return EOS_ERR_NOT_FOUND;
}

void eos_rtsvc_reset_system(eos_reset_type_t type)
{
    (void)type;
    /* Platform-specific: trigger system reset via NVIC or watchdog */
#if defined(__ARM_ARCH) && (__ARM_ARCH <= 7) && !defined(__aarch64__)
    /* NVIC_SystemReset() */
    *((volatile uint32_t *)0xE000ED0C) = 0x05FA0004;
#endif
    while (1) { /* wait for reset */ }
}

uint32_t eos_rtsvc_get_time(void)
{
    return uptime_seconds;
}

eos_slot_t eos_rtsvc_get_next_boot(void)
{
    return next_boot_slot;
}

int eos_rtsvc_set_next_boot(eos_slot_t slot)
{
    if (slot != EOS_SLOT_A && slot != EOS_SLOT_B &&
        slot != EOS_SLOT_RECOVERY && slot != EOS_SLOT_NONE) {
        return EOS_ERR_INVALID;
    }
    next_boot_slot = slot;
    return EOS_OK;
}
