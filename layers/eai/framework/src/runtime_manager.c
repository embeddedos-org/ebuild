// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eai_fw/runtime_manager.h"
#include "eai/log.h"
#include <string.h>

#define LOG_MOD "fw-rtmgr"

eai_status_t eai_fw_rtmgr_init(eai_fw_runtime_manager_t *mgr)
{
    if (!mgr) return EAI_ERR_INVALID;
    memset(mgr, 0, sizeof(*mgr));
    mgr->active_index = -1;
    return EAI_OK;
}

eai_status_t eai_fw_rtmgr_add(eai_fw_runtime_manager_t *mgr, const eai_runtime_ops_t *ops)
{
    if (!mgr || !ops) return EAI_ERR_INVALID;
    if (mgr->count >= EAI_FW_MAX_RUNTIMES) return EAI_ERR_NOMEM;

    eai_runtime_t *rt = &mgr->runtimes[mgr->count];
    eai_status_t s = eai_runtime_init(rt, ops);
    if (s != EAI_OK) return s;

    EAI_LOG_INFO(LOG_MOD, "added runtime [%d]: %s", mgr->count, ops->name);
    mgr->count++;

    if (mgr->active_index < 0) mgr->active_index = 0;
    return EAI_OK;
}

eai_status_t eai_fw_rtmgr_load_model(eai_fw_runtime_manager_t *mgr, int index,
                                      const eai_model_manifest_t *manifest,
                                      const char *model_path)
{
    if (!mgr || index < 0 || index >= mgr->count) return EAI_ERR_INVALID;
    return eai_runtime_load(&mgr->runtimes[index], manifest, model_path);
}

eai_status_t eai_fw_rtmgr_infer(eai_fw_runtime_manager_t *mgr, int index,
                                 const eai_inference_input_t *in,
                                 eai_inference_output_t *out)
{
    if (!mgr) return EAI_ERR_INVALID;
    int idx = index >= 0 ? index : mgr->active_index;
    if (idx < 0 || idx >= mgr->count) return EAI_ERR_INVALID;

    return eai_runtime_infer(&mgr->runtimes[idx], in, out);
}

eai_status_t eai_fw_rtmgr_select(eai_fw_runtime_manager_t *mgr, int index)
{
    if (!mgr || index < 0 || index >= mgr->count) return EAI_ERR_INVALID;
    mgr->active_index = index;
    EAI_LOG_INFO(LOG_MOD, "selected runtime [%d]: %s", index, mgr->runtimes[index].ops->name);
    return EAI_OK;
}

void eai_fw_rtmgr_shutdown(eai_fw_runtime_manager_t *mgr)
{
    if (!mgr) return;
    for (int i = 0; i < mgr->count; i++) {
        if (mgr->runtimes[i].loaded)
            eai_runtime_unload(&mgr->runtimes[i]);
        eai_runtime_shutdown(&mgr->runtimes[i]);
    }
    mgr->count = 0;
    mgr->active_index = -1;
    EAI_LOG_INFO(LOG_MOD, "all runtimes shut down");
}
