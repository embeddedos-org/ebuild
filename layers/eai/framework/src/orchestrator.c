// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eai_fw/orchestrator.h"
#include "eai/log.h"
#include <string.h>
#include <stdio.h>

#define LOG_MOD "fw-orch"

eai_status_t eai_fw_orch_init(eai_fw_orchestrator_t *orch,
                               eai_fw_runtime_manager_t *rt_mgr,
                               eai_tool_registry_t *tools,
                               eai_fw_connector_mgr_t *connectors,
                               eai_fw_policy_t *policy)
{
    if (!orch) return EAI_ERR_INVALID;
    memset(orch, 0, sizeof(*orch));
    orch->rt_mgr     = rt_mgr;
    orch->tools      = tools;
    orch->connectors = connectors;
    orch->policy     = policy;
    orch->state      = EAI_ORCH_IDLE;
    orch->current_step = 0;
    return EAI_OK;
}

eai_status_t eai_fw_orch_load_workflow(eai_fw_orchestrator_t *orch, eai_workflow_t *wf)
{
    if (!orch || !wf) return EAI_ERR_INVALID;
    orch->active_workflow = wf;
    orch->current_step = 0;
    EAI_LOG_INFO(LOG_MOD, "loaded workflow: %s (%d steps)", wf->name, wf->step_count);
    return EAI_OK;
}

static eai_status_t exec_step(eai_fw_orchestrator_t *orch, const eai_workflow_step_t *step)
{
    EAI_LOG_DEBUG(LOG_MOD, "executing step: %s (type=%d)", step->name, step->type);

    /* policy check */
    if (orch->policy) {
        const char *subject = "orchestrator";
        const char *op = "exec";
        eai_policy_action_t act = eai_fw_policy_check(orch->policy, subject, step->target, op);
        if (act == EAI_POLICY_DENY) {
            EAI_LOG_WARN(LOG_MOD, "policy denied step: %s -> %s", step->name, step->target);
            return EAI_ERR_PERMISSION;
        }
    }

    switch (step->type) {
    case EAI_STEP_INFER: {
        if (!orch->rt_mgr) return EAI_ERR_INVALID;
        eai_inference_input_t in = {0};
        /* find text param */
        for (int i = 0; i < step->param_count; i++) {
            if (strcmp(step->params[i].key, "text") == 0) {
                in.text = step->params[i].value;
                in.text_len = strlen(step->params[i].value);
            }
        }
        eai_inference_output_t out = {0};
        return eai_fw_rtmgr_infer(orch->rt_mgr, -1, &in, &out);
    }

    case EAI_STEP_TOOL_CALL: {
        if (!orch->tools) return EAI_ERR_INVALID;
        eai_tool_t *tool = eai_tool_find(orch->tools, step->target);
        if (!tool) return EAI_ERR_NOT_FOUND;
        eai_tool_result_t result;
        return eai_tool_exec(tool, step->params, step->param_count, &result);
    }

    case EAI_STEP_CONNECTOR_READ: {
        if (!orch->connectors) return EAI_ERR_INVALID;
        eai_fw_connector_t *conn = eai_fw_conn_find(orch->connectors, step->target);
        if (!conn || !conn->ops->read) return EAI_ERR_NOT_FOUND;
        char buf[EAI_CONNECTOR_BUF_MAX];
        size_t bytes_read = 0;
        const char *addr = NULL;
        for (int i = 0; i < step->param_count; i++) {
            if (strcmp(step->params[i].key, "address") == 0) addr = step->params[i].value;
        }
        return conn->ops->read(conn, addr, buf, sizeof(buf), &bytes_read);
    }

    case EAI_STEP_CONNECTOR_WRITE: {
        if (!orch->connectors) return EAI_ERR_INVALID;
        eai_fw_connector_t *conn = eai_fw_conn_find(orch->connectors, step->target);
        if (!conn || !conn->ops->write) return EAI_ERR_NOT_FOUND;
        const char *addr = NULL, *data = NULL;
        for (int i = 0; i < step->param_count; i++) {
            if (strcmp(step->params[i].key, "address") == 0) addr = step->params[i].value;
            if (strcmp(step->params[i].key, "data") == 0)    data = step->params[i].value;
        }
        return conn->ops->write(conn, addr, data, data ? strlen(data) : 0);
    }

    case EAI_STEP_DELAY:
        EAI_LOG_DEBUG(LOG_MOD, "delay step (no-op in sync mode)");
        return EAI_OK;

    case EAI_STEP_CONDITION:
        EAI_LOG_DEBUG(LOG_MOD, "condition step (defaulting to success path)");
        return EAI_OK;

    default:
        return EAI_ERR_UNSUPPORTED;
    }
}

eai_status_t eai_fw_orch_step(eai_fw_orchestrator_t *orch)
{
    if (!orch || !orch->active_workflow) return EAI_ERR_INVALID;
    if (orch->current_step >= orch->active_workflow->step_count) {
        orch->state = EAI_ORCH_IDLE;
        return EAI_OK;
    }

    const eai_workflow_step_t *step = &orch->active_workflow->steps[orch->current_step];
    eai_status_t s = exec_step(orch, step);

    if (s == EAI_OK) {
        orch->current_step = step->next_on_success >= 0
            ? step->next_on_success
            : orch->current_step + 1;
    } else {
        if (step->next_on_failure >= 0) {
            orch->current_step = step->next_on_failure;
        } else {
            orch->state = EAI_ORCH_ERROR;
            return s;
        }
    }

    return EAI_OK;
}

eai_status_t eai_fw_orch_run(eai_fw_orchestrator_t *orch)
{
    if (!orch || !orch->active_workflow) return EAI_ERR_INVALID;

    orch->state = EAI_ORCH_RUNNING;
    orch->current_step = 0;

    EAI_LOG_INFO(LOG_MOD, "running workflow: %s", orch->active_workflow->name);

    while (orch->state == EAI_ORCH_RUNNING &&
           orch->current_step < orch->active_workflow->step_count) {
        eai_status_t s = eai_fw_orch_step(orch);
        if (s != EAI_OK && orch->state == EAI_ORCH_ERROR) {
            EAI_LOG_ERROR(LOG_MOD, "workflow failed at step %d", orch->current_step);
            return s;
        }
    }

    orch->state = EAI_ORCH_IDLE;
    EAI_LOG_INFO(LOG_MOD, "workflow completed: %s", orch->active_workflow->name);
    return EAI_OK;
}

eai_status_t eai_fw_orch_pause(eai_fw_orchestrator_t *orch)
{
    if (!orch || orch->state != EAI_ORCH_RUNNING) return EAI_ERR_INVALID;
    orch->state = EAI_ORCH_PAUSED;
    EAI_LOG_INFO(LOG_MOD, "workflow paused at step %d", orch->current_step);
    return EAI_OK;
}

eai_status_t eai_fw_orch_resume(eai_fw_orchestrator_t *orch)
{
    if (!orch || orch->state != EAI_ORCH_PAUSED) return EAI_ERR_INVALID;
    orch->state = EAI_ORCH_RUNNING;
    EAI_LOG_INFO(LOG_MOD, "workflow resumed at step %d", orch->current_step);

    while (orch->state == EAI_ORCH_RUNNING &&
           orch->current_step < orch->active_workflow->step_count) {
        eai_status_t s = eai_fw_orch_step(orch);
        if (s != EAI_OK && orch->state == EAI_ORCH_ERROR) {
            EAI_LOG_ERROR(LOG_MOD, "workflow failed at step %d", orch->current_step);
            return s;
        }
    }

    orch->state = EAI_ORCH_IDLE;
    EAI_LOG_INFO(LOG_MOD, "workflow completed: %s", orch->active_workflow->name);
    return EAI_OK;
}

void eai_fw_orch_reset(eai_fw_orchestrator_t *orch)
{
    if (!orch) return;
    orch->active_workflow = NULL;
    orch->current_step = 0;
    orch->state = EAI_ORCH_IDLE;
}
