// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_registry.c
 * @brief Board registry — runtime multi-hardware management
 */

#include "eos_board_registry.h"
#include <string.h>

static const eos_board_info_t *registry[EOS_MAX_BOARDS];
static uint32_t board_count = 0;

int eos_board_register(const eos_board_info_t *info)
{
    if (!info || !info->name || !info->get_ops) return EOS_ERR_INVALID;
    if (board_count >= EOS_MAX_BOARDS) return EOS_ERR_FULL;

    /* Check for duplicate */
    for (uint32_t i = 0; i < board_count; i++) {
        if (strcmp(registry[i]->name, info->name) == 0) {
            return EOS_ERR_INVALID;
        }
    }

    registry[board_count++] = info;
    return EOS_OK;
}

const eos_board_info_t *eos_board_find(const char *name)
{
    if (!name) return NULL;

    for (uint32_t i = 0; i < board_count; i++) {
        if (strcmp(registry[i]->name, name) == 0) {
            return registry[i];
        }
    }
    return NULL;
}

const eos_board_info_t *eos_board_detect(void)
{
    for (uint32_t i = 0; i < board_count; i++) {
        if (registry[i]->detect && registry[i]->detect()) {
            return registry[i];
        }
    }

    /* Fallback: return first registered board */
    if (board_count > 0) return registry[0];
    return NULL;
}

uint32_t eos_board_count(void)
{
    return board_count;
}

const eos_board_info_t *eos_board_get(uint32_t index)
{
    if (index >= board_count) return NULL;
    return registry[index];
}

int eos_board_activate(const char *name)
{
    const eos_board_info_t *info = eos_board_find(name);
    if (!info) return EOS_ERR_NO_IMAGE;

    const eos_board_ops_t *ops = info->get_ops();
    if (!ops) return EOS_ERR_GENERIC;

    eos_hal_init(ops);
    return EOS_OK;
}

int eos_board_activate_auto(void)
{
    const eos_board_info_t *info = eos_board_detect();
    if (!info) return EOS_ERR_NO_IMAGE;

    const eos_board_ops_t *ops = info->get_ops();
    if (!ops) return EOS_ERR_GENERIC;

    eos_hal_init(ops);
    return EOS_OK;
}
