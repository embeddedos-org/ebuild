// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef ENI_PROVIDER_SIMULATOR_H
#define ENI_PROVIDER_SIMULATOR_H

#include "eni/provider_contract.h"

extern const eni_provider_ops_t eni_provider_simulator_ops;

typedef struct {
    uint32_t event_interval_ms;
    uint32_t tick_count;
} eni_simulator_config_t;

#endif /* ENI_PROVIDER_SIMULATOR_H */
