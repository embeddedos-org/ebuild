// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eni_fw/orchestrator.h"
#include "eni/log.h"
#include <string.h>
#include <stdio.h>

eni_status_t eni_fw_orchestrator_init(eni_fw_orchestrator_t *orch,
                                       eni_policy_engine_t *policy,
                                       eni_fw_router_t *router)
{
    if (!orch) return ENI_ERR_INVALID;
    memset(orch, 0, sizeof(*orch));
    orch->policy = policy;
    orch->router = router;
    return eni_tool_registry_init(&orch->registry);
}

eni_status_t eni_fw_orchestrator_register_tool(eni_fw_orchestrator_t *orch,
                                                const eni_tool_entry_t *entry)
{
    if (!orch || !entry) return ENI_ERR_INVALID;
    return eni_tool_register(&orch->registry, entry);
}

eni_status_t eni_fw_orchestrator_dispatch(eni_fw_orchestrator_t *orch,
                                           const eni_event_t *ev,
                                           const eni_tool_call_t *call,
                                           eni_tool_result_t *result)
{
    if (!orch || !ev || !call || !result) return ENI_ERR_INVALID;

    /* Route classification */
    eni_route_priority_t pri = ENI_ROUTE_NORMAL;
    if (orch->router) {
        pri = eni_fw_router_classify(orch->router, ev);
    }

    /* Policy check */
    if (orch->policy) {
        eni_policy_verdict_t v = eni_policy_evaluate(orch->policy, call->tool);
        if (v == ENI_POLICY_DENY) {
            ENI_LOG_WARN("fw.orch", "policy denied: %s (priority=%d)", call->tool, pri);
            orch->denied_count++;
            result->status = ENI_ERR_POLICY_DENIED;
            return ENI_ERR_POLICY_DENIED;
        }
        if (v == ENI_POLICY_CONFIRM) {
            ENI_LOG_INFO("fw.orch", "confirmation required: %s", call->tool);
        }
    }

    eni_status_t st = eni_tool_exec(&orch->registry, call, result);
    if (st == ENI_OK) {
        orch->exec_count++;
    }
    return st;
}

void eni_fw_orchestrator_stats(const eni_fw_orchestrator_t *orch)
{
    if (!orch) return;
    printf("[orchestrator] executed=%llu denied=%llu tools=%d\n",
           (unsigned long long)orch->exec_count,
           (unsigned long long)orch->denied_count,
           orch->registry.count);
}
