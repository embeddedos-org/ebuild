// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef ENI_PLATFORM_H
#define ENI_PLATFORM_H

#include "eni/types.h"

typedef struct {
    const char *os_name;
    const char *arch;
    bool        realtime_capable;
    bool        hardware_access;
} eni_platform_info_t;

eni_status_t        eni_platform_init(void);
eni_platform_info_t eni_platform_info(void);
void                eni_platform_sleep_ms(uint32_t ms);
uint64_t            eni_platform_monotonic_ms(void);

#endif /* ENI_PLATFORM_H */
