// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef EAI_MIN_RUNTIME_H
#define EAI_MIN_RUNTIME_H

#include "eai/runtime_contract.h"

typedef struct {
    eai_runtime_t        base;
    const char          *model_path;
    uint32_t             max_tokens;
    float                temperature;
    bool                 initialized;
} eai_min_runtime_t;

eai_status_t eai_min_runtime_create(eai_min_runtime_t *rt, eai_runtime_type_t type);
eai_status_t eai_min_runtime_load(eai_min_runtime_t *rt, const char *model_path,
                                   const eai_model_manifest_t *manifest);
eai_status_t eai_min_runtime_infer(eai_min_runtime_t *rt,
                                    const char *prompt,
                                    char *output, size_t output_size);
void         eai_min_runtime_destroy(eai_min_runtime_t *rt);

/* Built-in runtime backends */
extern const eai_runtime_ops_t eai_runtime_stub_ops;

#ifdef EAI_LLAMA_CPP_ENABLED
extern const eai_runtime_ops_t eai_runtime_llama_ops;
#endif


#endif /* EAI_MIN_RUNTIME_H */
