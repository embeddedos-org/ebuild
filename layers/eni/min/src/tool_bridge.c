// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eni_min/tool_bridge.h"
#include "eni/log.h"
#include <string.h>

eni_status_t eni_min_tool_bridge_init(eni_min_tool_bridge_t *bridge,
                                       eni_policy_engine_t *policy)
{
    if (!bridge) return ENI_ERR_INVALID;
    memset(bridge, 0, sizeof(*bridge));
    bridge->policy = policy;
    return eni_tool_registry_init(&bridge->registry);
}

eni_status_t eni_min_tool_bridge_register(eni_min_tool_bridge_t *bridge,
                                            const eni_tool_entry_t *entry)
{
    if (!bridge || !entry) return ENI_ERR_INVALID;
    return eni_tool_register(&bridge->registry, entry);
}

eni_status_t eni_min_tool_bridge_exec(eni_min_tool_bridge_t *bridge,
                                        const eni_tool_call_t *call,
                                        eni_tool_result_t *result)
{
    if (!bridge || !call || !result) return ENI_ERR_INVALID;

    /* Policy check */
    if (bridge->policy) {
        eni_policy_verdict_t v = eni_policy_evaluate(bridge->policy, call->tool);
        if (v == ENI_POLICY_DENY) {
            ENI_LOG_WARN("min.bridge", "policy denied: %s", call->tool);
            result->status = ENI_ERR_POLICY_DENIED;
            return ENI_ERR_POLICY_DENIED;
        }
        if (v == ENI_POLICY_CONFIRM) {
            ENI_LOG_INFO("min.bridge", "confirmation required for: %s (auto-skipping in min mode)",
                         call->tool);
        }
    }

    return eni_tool_exec(&bridge->registry, call, result);
}
