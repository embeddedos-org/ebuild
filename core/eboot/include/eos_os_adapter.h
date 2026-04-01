// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file eos_os_adapter.h
 * @brief eboot Minimal OS Adapter — boot-time OS primitives
 *
 * Provides a lightweight vtable for boot-time operations (locking, delays,
 * logging, memory barriers). Follows the same pattern as eos_board_ops_t
 * in eos_hal.h — function pointer struct + init/get + convenience wrappers.
 *
 * eboot does NOT need full POSIX/VxWorks compatibility — it needs only
 * the minimal OS primitives required during the boot sequence.
 */

#ifndef EOS_BOOT_OS_ADAPTER_H
#define EOS_BOOT_OS_ADAPTER_H

#include "eos_types.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    const char *name;

    /* Mutual exclusion for shared boot state */
    void (*mutex_lock)(void);
    void (*mutex_unlock)(void);

    /* Boot timing */
    void (*delay_ms)(uint32_t ms);
    uint32_t (*get_tick_ms)(void);

    /* Boot logging */
    void (*log_print)(const char *msg);

    /* Memory barriers (multicore boot synchronization) */
    void (*memory_barrier)(void);

    /* Atomic boot handoff flags */
    void (*atomic_flag_set)(volatile uint32_t *flag, uint32_t value);
    uint32_t (*atomic_flag_get)(const volatile uint32_t *flag);

    /* Interrupt control */
    void (*disable_interrupts)(void);
    void (*enable_interrupts)(void);

} eos_boot_os_adapter_t;

/**
 * Initialize the boot OS adapter. If NULL, uses the default bare-metal adapter.
 */
void eos_boot_os_adapter_init(const eos_boot_os_adapter_t *adapter);

/**
 * Get the active boot OS adapter.
 */
const eos_boot_os_adapter_t *eos_boot_os_adapter_get(void);

/* ---- Convenience wrappers ---- */

void     eos_boot_lock(void);
void     eos_boot_unlock(void);
void     eos_boot_delay_ms(uint32_t ms);
uint32_t eos_boot_get_tick_ms(void);
void     eos_boot_log(const char *msg);
void     eos_boot_memory_barrier(void);
void     eos_boot_atomic_set(volatile uint32_t *flag, uint32_t value);
uint32_t eos_boot_atomic_get(const volatile uint32_t *flag);
void     eos_boot_disable_interrupts(void);
void     eos_boot_enable_interrupts(void);

#ifdef __cplusplus
}
#endif

#endif /* EOS_BOOT_OS_ADAPTER_H */
