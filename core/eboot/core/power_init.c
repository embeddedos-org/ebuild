// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file power_init.c
 * @brief Power management — reset cause, PMIC, voltage rails
 */

#include "eos_power.h"
#include "eos_hal.h"
#include <string.h>
#include <stdio.h>

eos_reset_cause_t eos_power_get_reset_cause(void)
{
    /* Platform-specific: read reset status register.
     * Each board port implements the actual register read. */
    return EOS_RESET_POWER_ON;
}

int eos_power_init(eos_power_ctx_t *pwr)
{
    if (!pwr) return -1;
    memset(pwr, 0, sizeof(*pwr));
    pwr->last_reset = eos_power_get_reset_cause();
    pwr->state = EOS_POWER_RUN;
    return 0;
}

int eos_power_set_rail(eos_power_ctx_t *pwr, const char *name, uint32_t mv, bool enable)
{
    if (!pwr || !name) return -1;

    for (int i = 0; i < pwr->rail_count; i++) {
        if (pwr->rails[i].name && strcmp(pwr->rails[i].name, name) == 0) {
            pwr->rails[i].voltage_mv = mv;
            pwr->rails[i].enabled = enable;
            return 0;
        }
    }

    if (pwr->rail_count >= EOS_MAX_POWER_RAILS) return -1;
    eos_power_rail_t *r = &pwr->rails[pwr->rail_count++];
    r->name = name;
    r->voltage_mv = mv;
    r->enabled = enable;
    return 0;
}

int eos_power_system_reset(void)
{
    /* Platform-specific system reset.
     * ARM: write to AIRCR register
     * RISC-V: write to mstatus
     * x86: triple fault or reset port */
#if defined(__ARM_ARCH) && (__ARM_ARCH <= 7) && !defined(__aarch64__)
    *((volatile uint32_t *)0xE000ED0C) = 0x05FA0004;
#endif
    while (1) {} /* Should not reach here */
    return -1;
}

int eos_power_shutdown(void)
{
    /* Platform-specific — typically PMIC I2C command */
    return -1;
}

void eos_power_dump(const eos_power_ctx_t *pwr)
{
#if !defined(EOS_BARE_METAL)
    const char *causes[] = {"POWER_ON","WATCHDOG","SOFTWARE","BROWNOUT","PIN","LOCKUP","UNKNOWN"};
    const char *states[] = {"RUN","SLEEP","DEEP_SLEEP","STANDBY","SHUTDOWN"};
    printf("Power: state=%s reset=%s PMIC=%s USB=%s\n",
           states[pwr->state], causes[pwr->last_reset],
           pwr->pmic_present ? "yes" : "no",
           pwr->usb_power ? "yes" : "no");
    for (int i = 0; i < pwr->rail_count; i++) {
        printf("  Rail %-12s %4umV %s\n",
               pwr->rails[i].name, pwr->rails[i].voltage_mv,
               pwr->rails[i].enabled ? "ON" : "OFF");
    }
#else
    (void)pwr;
#endif
}
