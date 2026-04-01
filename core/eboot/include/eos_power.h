// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file eos_power.h
 * @brief Power management for bootloader — PMIC, voltage rails, reset
 *
 * Handles early power sequencing, PMIC communication, voltage rail
 * configuration, and system reset control.
 */

#ifndef EOS_BOOT_POWER_H
#define EOS_BOOT_POWER_H

#include "eos_types.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef eos_reset_reason_t eos_reset_cause_t;

typedef enum {
    EOS_POWER_RUN,
    EOS_POWER_SLEEP,
    EOS_POWER_DEEP_SLEEP,
    EOS_POWER_STANDBY,
    EOS_POWER_SHUTDOWN
} eos_power_state_t;

typedef struct {
    const char *name;
    uint32_t voltage_mv;
    uint32_t current_limit_ma;
    bool     enabled;
    bool     adjustable;
} eos_power_rail_t;

#define EOS_MAX_POWER_RAILS 16

typedef struct {
    eos_reset_cause_t last_reset;
    eos_power_state_t state;
    eos_power_rail_t rails[EOS_MAX_POWER_RAILS];
    int rail_count;
    uint32_t vbat_mv;
    bool     pmic_present;
    bool     usb_power;
} eos_power_ctx_t;

eos_reset_cause_t eos_power_get_reset_cause(void);
int  eos_power_init(eos_power_ctx_t *pwr);
int  eos_power_set_rail(eos_power_ctx_t *pwr, const char *name, uint32_t mv, bool enable);
int  eos_power_system_reset(void);
int  eos_power_shutdown(void);
void eos_power_dump(const eos_power_ctx_t *pwr);

#ifdef __cplusplus
}
#endif
#endif /* EOS_BOOT_POWER_H */
