// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file hal_core.c
 * @brief HAL core — board ops registration and convenience wrappers
 */

#include "eos_hal.h"

static const eos_board_ops_t *g_ops = NULL;

void eos_hal_init(const eos_board_ops_t *ops)
{
    g_ops = ops;
}

const eos_board_ops_t *eos_hal_get_ops(void)
{
    return g_ops;
}

int eos_hal_flash_read(uint32_t addr, void *buf, size_t len)
{
    if (!g_ops || !g_ops->flash_read)
        return EOS_ERR_GENERIC;
    return g_ops->flash_read(addr, buf, len);
}

int eos_hal_flash_write(uint32_t addr, const void *buf, size_t len)
{
    if (!g_ops || !g_ops->flash_write)
        return EOS_ERR_GENERIC;
    return g_ops->flash_write(addr, buf, len);
}

int eos_hal_flash_erase(uint32_t addr, size_t len)
{
    if (!g_ops || !g_ops->flash_erase)
        return EOS_ERR_GENERIC;
    return g_ops->flash_erase(addr, len);
}

void eos_hal_watchdog_init(uint32_t timeout_ms)
{
    if (g_ops && g_ops->watchdog_init)
        g_ops->watchdog_init(timeout_ms);
}

void eos_hal_watchdog_feed(void)
{
    if (g_ops && g_ops->watchdog_feed)
        g_ops->watchdog_feed();
}

eos_reset_reason_t eos_hal_get_reset_reason(void)
{
    if (g_ops && g_ops->get_reset_reason)
        return g_ops->get_reset_reason();
    return EOS_RESET_UNKNOWN;
}

void eos_hal_system_reset(void)
{
    if (g_ops && g_ops->system_reset)
        g_ops->system_reset();
    while (1); /* fallback halt */
}

bool eos_hal_recovery_pin_asserted(void)
{
    if (g_ops && g_ops->recovery_pin_asserted)
        return g_ops->recovery_pin_asserted();
    return false;
}

void eos_hal_jump(uint32_t vector_addr)
{
    if (g_ops && g_ops->jump)
        g_ops->jump(vector_addr);
}

int eos_hal_uart_init(uint32_t baud)
{
    if (!g_ops || !g_ops->uart_init)
        return EOS_ERR_GENERIC;
    return g_ops->uart_init(baud);
}

int eos_hal_uart_send(const void *buf, size_t len)
{
    if (!g_ops || !g_ops->uart_send)
        return EOS_ERR_GENERIC;
    return g_ops->uart_send(buf, len);
}

int eos_hal_uart_recv(void *buf, size_t len, uint32_t timeout_ms)
{
    if (!g_ops || !g_ops->uart_recv)
        return EOS_ERR_GENERIC;
    return g_ops->uart_recv(buf, len, timeout_ms);
}

uint32_t eos_hal_get_tick_ms(void)
{
    if (g_ops && g_ops->get_tick_ms)
        return g_ops->get_tick_ms();
    return 0;
}

void eos_hal_disable_interrupts(void)
{
    if (g_ops && g_ops->disable_interrupts)
        g_ops->disable_interrupts();
}

void eos_hal_enable_interrupts(void)
{
    if (g_ops && g_ops->enable_interrupts)
        g_ops->enable_interrupts();
}

void eos_hal_deinit_peripherals(void)
{
    if (g_ops && g_ops->deinit_peripherals)
        g_ops->deinit_peripherals();
}

uint32_t eos_hal_slot_addr(eos_slot_t slot)
{
    if (!g_ops)
        return 0;

    switch (slot) {
    case EOS_SLOT_A:        return g_ops->slot_a_addr;
    case EOS_SLOT_B:        return g_ops->slot_b_addr;
    case EOS_SLOT_RECOVERY: return g_ops->recovery_addr;
    default:                return 0;
    }
}

uint32_t eos_hal_slot_size(eos_slot_t slot)
{
    if (!g_ops)
        return 0;

    switch (slot) {
    case EOS_SLOT_A:        return g_ops->slot_a_size;
    case EOS_SLOT_B:        return g_ops->slot_b_size;
    case EOS_SLOT_RECOVERY: return g_ops->recovery_size;
    default:                return 0;
    }
}
