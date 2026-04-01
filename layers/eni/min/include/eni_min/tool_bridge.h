// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef ENI_MIN_TOOL_BRIDGE_H
#define ENI_MIN_TOOL_BRIDGE_H

#include "eni/common.h"

typedef struct {
    eni_tool_registry_t  registry;
    eni_policy_engine_t *policy;
} eni_min_tool_bridge_t;

eni_status_t eni_min_tool_bridge_init(eni_min_tool_bridge_t *bridge,
                                       eni_policy_engine_t *policy);
eni_status_t eni_min_tool_bridge_register(eni_min_tool_bridge_t *bridge,
                                            const eni_tool_entry_t *entry);
eni_status_t eni_min_tool_bridge_exec(eni_min_tool_bridge_t *bridge,
                                        const eni_tool_call_t *call,
                                        eni_tool_result_t *result);

#endif /* ENI_MIN_TOOL_BRIDGE_H */
