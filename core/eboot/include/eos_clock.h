// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file eos_clock.h
 * @brief Clock tree initialization — PLL, oscillators, clock distribution
 *
 * Configures the full clock tree early in boot: HSE/HSI selection,
 * PLL configuration, bus dividers, peripheral clocks. Board-specific
 * clock configs are provided via eos_board_config.h macros.
 */

#ifndef EOS_CLOCK_H
#define EOS_CLOCK_H

#include "eos_types.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    EOS_CLK_HSI,        /* Internal high-speed RC */
    EOS_CLK_HSE,        /* External crystal */
    EOS_CLK_PLL,        /* Phase-locked loop */
    EOS_CLK_LSI,        /* Internal low-speed RC (RTC) */
    EOS_CLK_LSE         /* External 32.768kHz crystal */
} eos_clk_source_t;

typedef struct {
    eos_clk_source_t source;
    uint32_t hse_hz;
    uint32_t sysclk_hz;
    uint32_t hclk_hz;       /* AHB bus */
    uint32_t pclk1_hz;      /* APB1 bus */
    uint32_t pclk2_hz;      /* APB2 bus */
    uint32_t pll_m;
    uint32_t pll_n;
    uint32_t pll_p;
    uint32_t pll_q;
    bool     use_pll;
    bool     configured;
} eos_clock_config_t;

int  eos_clock_init(const eos_clock_config_t *cfg);
uint32_t eos_clock_get_sysclk(void);
uint32_t eos_clock_get_hclk(void);
uint32_t eos_clock_get_pclk1(void);
uint32_t eos_clock_get_pclk2(void);
void eos_clock_dump(const eos_clock_config_t *cfg);

#ifdef __cplusplus
}
#endif
#endif /* EOS_CLOCK_H */
