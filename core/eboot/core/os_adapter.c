// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file os_adapter.c
 * @brief eboot OS adapter — registry + default bare-metal implementation
 *
 * Default bare-metal adapter uses HAL functions for all operations:
 * - lock/unlock → disable/enable interrupts
 * - delay_ms → busy-wait on eos_hal_get_tick_ms()
 * - log_print → eos_hal_uart_send()
 * - memory_barrier → compiler barrier
 * - atomic → volatile read/write
 */

#include "eos_os_adapter.h"
#include "eos_hal.h"
#include <string.h>
#if defined(_MSC_VER)
#include <intrin.h>
#endif

static const eos_boot_os_adapter_t *g_boot_adapter = NULL;

/* ---- Default bare-metal adapter ---- */

static void default_mutex_lock(void)
{
    eos_hal_disable_interrupts();
}

static void default_mutex_unlock(void)
{
    eos_hal_enable_interrupts();
}

static void default_delay_ms(uint32_t ms)
{
    uint32_t start = eos_hal_get_tick_ms();
    while ((eos_hal_get_tick_ms() - start) < ms) {
        /* busy-wait */
    }
}

static uint32_t default_get_tick_ms(void)
{
    return eos_hal_get_tick_ms();
}

static void default_log_print(const char *msg)
{
    if (msg) {
        size_t len = 0;
        while (msg[len]) len++;
        eos_hal_uart_send(msg, len);
    }
}

static void default_memory_barrier(void)
{
#if defined(_MSC_VER)
    _ReadWriteBarrier();
#elif defined(__GNUC__) || defined(__clang__)
    __asm volatile ("" ::: "memory");
#endif
}

static void default_atomic_flag_set(volatile uint32_t *flag, uint32_t value)
{
    *flag = value;
    default_memory_barrier();
}

static uint32_t default_atomic_flag_get(const volatile uint32_t *flag)
{
    default_memory_barrier();
    return *flag;
}

static void default_disable_interrupts(void)
{
    eos_hal_disable_interrupts();
}

static void default_enable_interrupts(void)
{
    eos_hal_enable_interrupts();
}

static const eos_boot_os_adapter_t default_adapter = {
    .name               = "bare-metal",
    .mutex_lock         = default_mutex_lock,
    .mutex_unlock       = default_mutex_unlock,
    .delay_ms           = default_delay_ms,
    .get_tick_ms        = default_get_tick_ms,
    .log_print          = default_log_print,
    .memory_barrier     = default_memory_barrier,
    .atomic_flag_set    = default_atomic_flag_set,
    .atomic_flag_get    = default_atomic_flag_get,
    .disable_interrupts = default_disable_interrupts,
    .enable_interrupts  = default_enable_interrupts,
};

/* ---- Public API ---- */

void eos_boot_os_adapter_init(const eos_boot_os_adapter_t *adapter)
{
    g_boot_adapter = adapter ? adapter : &default_adapter;
}

const eos_boot_os_adapter_t *eos_boot_os_adapter_get(void)
{
    if (!g_boot_adapter)
        g_boot_adapter = &default_adapter;
    return g_boot_adapter;
}

/* ---- Convenience wrappers ---- */

void eos_boot_lock(void)
{
    const eos_boot_os_adapter_t *a = eos_boot_os_adapter_get();
    if (a->mutex_lock) a->mutex_lock();
}

void eos_boot_unlock(void)
{
    const eos_boot_os_adapter_t *a = eos_boot_os_adapter_get();
    if (a->mutex_unlock) a->mutex_unlock();
}

void eos_boot_delay_ms(uint32_t ms)
{
    const eos_boot_os_adapter_t *a = eos_boot_os_adapter_get();
    if (a->delay_ms) a->delay_ms(ms);
}

uint32_t eos_boot_get_tick_ms(void)
{
    const eos_boot_os_adapter_t *a = eos_boot_os_adapter_get();
    if (a->get_tick_ms) return a->get_tick_ms();
    return 0;
}

void eos_boot_log(const char *msg)
{
    const eos_boot_os_adapter_t *a = eos_boot_os_adapter_get();
    if (a->log_print) a->log_print(msg);
}

void eos_boot_memory_barrier(void)
{
    const eos_boot_os_adapter_t *a = eos_boot_os_adapter_get();
    if (a->memory_barrier) a->memory_barrier();
}

void eos_boot_atomic_set(volatile uint32_t *flag, uint32_t value)
{
    const eos_boot_os_adapter_t *a = eos_boot_os_adapter_get();
    if (a->atomic_flag_set) a->atomic_flag_set(flag, value);
    else { *flag = value; }
}

uint32_t eos_boot_atomic_get(const volatile uint32_t *flag)
{
    const eos_boot_os_adapter_t *a = eos_boot_os_adapter_get();
    if (a->atomic_flag_get) return a->atomic_flag_get(flag);
    return *flag;
}

void eos_boot_disable_interrupts(void)
{
    const eos_boot_os_adapter_t *a = eos_boot_os_adapter_get();
    if (a->disable_interrupts) a->disable_interrupts();
}

void eos_boot_enable_interrupts(void)
{
    const eos_boot_os_adapter_t *a = eos_boot_os_adapter_get();
    if (a->enable_interrupts) a->enable_interrupts();
}
