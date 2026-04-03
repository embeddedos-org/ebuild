// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file clock_init.c
 * @brief Clock tree initialization — PLL, oscillators, bus dividers
 */

#include "eos_clock.h"
#ifdef EBOOT_ENABLE_PRINTF
#include <stdio.h>
#endif
#include <string.h>

static eos_clock_config_t g_clock_cfg;

int eos_clock_init(const eos_clock_config_t *cfg)
{
    if (!cfg) return -1;

    memcpy(&g_clock_cfg, cfg, sizeof(g_clock_cfg));

    /* Platform-specific clock tree programming:
     * 1. Select HSE/HSI source
     * 2. Configure PLL (M, N, P, Q dividers)
     * 3. Set AHB/APB bus dividers
     * 4. Switch system clock to PLL
     * 5. Update flash wait states for new frequency
     *
     * Each board port provides the actual register programming
     * via the board config macros. */

    g_clock_cfg.configured = true;
    return 0;
}

uint32_t eos_clock_get_sysclk(void) { return g_clock_cfg.sysclk_hz; }
uint32_t eos_clock_get_hclk(void)   { return g_clock_cfg.hclk_hz; }
uint32_t eos_clock_get_pclk1(void)  { return g_clock_cfg.pclk1_hz; }
uint32_t eos_clock_get_pclk2(void)  { return g_clock_cfg.pclk2_hz; }

void eos_clock_dump(const eos_clock_config_t *cfg)
{
#ifdef EBOOT_ENABLE_PRINTF
    const char *sources[] = {"HSI","HSE","PLL","LSI","LSE"};
    printf("Clock: %s SYSCLK=%uMHz HCLK=%uMHz PCLK1=%uMHz PCLK2=%uMHz\n",
           sources[cfg->source],
           cfg->sysclk_hz / 1000000,
           cfg->hclk_hz / 1000000,
           cfg->pclk1_hz / 1000000,
           cfg->pclk2_hz / 1000000);
    if (cfg->use_pll) {
        printf("  PLL: HSE=%uMHz M=%u N=%u P=%u Q=%u\n",
               cfg->hse_hz / 1000000,
               cfg->pll_m, cfg->pll_n, cfg->pll_p, cfg->pll_q);
    }
#else
    (void)cfg;
#endif
}
