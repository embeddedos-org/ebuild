// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef ENI_FW_ORCHESTRATOR_H
#define ENI_FW_ORCHESTRATOR_H

#include "eni/common.h"
#include "eni_fw/router.h"

typedef struct {
    eni_tool_registry_t   registry;
    eni_policy_engine_t  *policy;
    eni_fw_router_t      *router;
    uint64_t              exec_count;
    uint64_t              denied_count;
} eni_fw_orchestrator_t;

eni_status_t eni_fw_orchestrator_init(eni_fw_orchestrator_t *orch,
                                       eni_policy_engine_t *policy,
                                       eni_fw_router_t *router);
eni_status_t eni_fw_orchestrator_register_tool(eni_fw_orchestrator_t *orch,
                                                const eni_tool_entry_t *entry);
eni_status_t eni_fw_orchestrator_dispatch(eni_fw_orchestrator_t *orch,
                                           const eni_event_t *ev,
                                           const eni_tool_call_t *call,
                                           eni_tool_result_t *result);
void         eni_fw_orchestrator_stats(const eni_fw_orchestrator_t *orch);

#endif /* ENI_FW_ORCHESTRATOR_H */
