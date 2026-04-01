// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef ENI_PROVIDER_GENERIC_H
#define ENI_PROVIDER_GENERIC_H

#include "eni/provider_contract.h"

extern const eni_provider_ops_t eni_provider_generic_ops;

typedef struct {
    eni_transport_t transport;
    const char     *endpoint;
    uint32_t        timeout_ms;
} eni_generic_config_t;

#endif /* ENI_PROVIDER_GENERIC_H */
