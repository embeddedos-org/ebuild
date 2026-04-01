// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef EAI_FW_RUNTIME_MANAGER_H
#define EAI_FW_RUNTIME_MANAGER_H

#include "eai/runtime_contract.h"

#define EAI_FW_MAX_RUNTIMES 8

typedef struct {
    eai_runtime_t runtimes[EAI_FW_MAX_RUNTIMES];
    int           count;
    int           active_index;
} eai_fw_runtime_manager_t;

eai_status_t eai_fw_rtmgr_init(eai_fw_runtime_manager_t *mgr);
eai_status_t eai_fw_rtmgr_add(eai_fw_runtime_manager_t *mgr, const eai_runtime_ops_t *ops);
eai_status_t eai_fw_rtmgr_load_model(eai_fw_runtime_manager_t *mgr, int index,
                                      const eai_model_manifest_t *manifest,
                                      const char *model_path);
eai_status_t eai_fw_rtmgr_infer(eai_fw_runtime_manager_t *mgr, int index,
                                 const eai_inference_input_t *in,
                                 eai_inference_output_t *out);
eai_status_t eai_fw_rtmgr_select(eai_fw_runtime_manager_t *mgr, int index);
void         eai_fw_rtmgr_shutdown(eai_fw_runtime_manager_t *mgr);

#endif /* EAI_FW_RUNTIME_MANAGER_H */
