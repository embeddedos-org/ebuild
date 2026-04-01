// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file hw_init_minimal.c
 * @brief Stage-0 minimal hardware initialization
 *
 * Performs only the absolute minimum to reach a known-good state:
 * clock configuration, flash latency, and memory setup.
 * No policy or complex logic belongs here.
 */

#include "eos_hal.h"
#include <stdint.h>

/* Board-specific init — provided by the board port */
extern void board_early_init(void);
extern const eos_board_ops_t *board_get_ops(void);

void ebldr_hw_init_minimal(void)
{
    /* Register the board HAL */
    const eos_board_ops_t *ops = board_get_ops();
    eos_hal_init(ops);

    /* Board-specific early initialization (clocks, flash latency) */
    board_early_init();
}
