// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef EAI_FW_ORCHESTRATOR_H
#define EAI_FW_ORCHESTRATOR_H

#include "eai/types.h"
#include "eai/tool.h"
#include "eai_fw/runtime_manager.h"
#include "eai_fw/connector.h"
#include "eai_fw/policy.h"

#define EAI_FW_MAX_WORKFLOW_STEPS 32

typedef enum {
    EAI_STEP_INFER,
    EAI_STEP_TOOL_CALL,
    EAI_STEP_CONNECTOR_READ,
    EAI_STEP_CONNECTOR_WRITE,
    EAI_STEP_CONDITION,
    EAI_STEP_DELAY,
} eai_step_type_t;

typedef struct {
    eai_step_type_t type;
    const char     *name;
    const char     *target;      /* tool name, connector id, or model */
    eai_kv_t        params[8];
    int             param_count;
    int             next_on_success;
    int             next_on_failure;
} eai_workflow_step_t;

typedef struct {
    const char         *name;
    eai_workflow_step_t steps[EAI_FW_MAX_WORKFLOW_STEPS];
    int                 step_count;
    bool                repeat;
    uint32_t            interval_ms;
} eai_workflow_t;

typedef enum {
    EAI_ORCH_IDLE,
    EAI_ORCH_RUNNING,
    EAI_ORCH_PAUSED,
    EAI_ORCH_ERROR,
} eai_orch_state_t;

typedef struct {
    eai_fw_runtime_manager_t *rt_mgr;
    eai_tool_registry_t      *tools;
    eai_fw_connector_mgr_t   *connectors;
    eai_fw_policy_t          *policy;
    eai_workflow_t           *active_workflow;
    int                       current_step;
    eai_orch_state_t          state;
} eai_fw_orchestrator_t;

eai_status_t eai_fw_orch_init(eai_fw_orchestrator_t *orch,
                               eai_fw_runtime_manager_t *rt_mgr,
                               eai_tool_registry_t *tools,
                               eai_fw_connector_mgr_t *connectors,
                               eai_fw_policy_t *policy);
eai_status_t eai_fw_orch_load_workflow(eai_fw_orchestrator_t *orch, eai_workflow_t *wf);
eai_status_t eai_fw_orch_run(eai_fw_orchestrator_t *orch);
eai_status_t eai_fw_orch_step(eai_fw_orchestrator_t *orch);
eai_status_t eai_fw_orch_pause(eai_fw_orchestrator_t *orch);
eai_status_t eai_fw_orch_resume(eai_fw_orchestrator_t *orch);
void         eai_fw_orch_reset(eai_fw_orchestrator_t *orch);

#endif /* EAI_FW_ORCHESTRATOR_H */
