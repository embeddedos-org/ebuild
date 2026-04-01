// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef EAI_MIN_RUNTIME_LLAMA_H
#define EAI_MIN_RUNTIME_LLAMA_H

#include "eai/runtime_contract.h"

#ifdef EAI_LLAMA_CPP_ENABLED

extern const eai_runtime_ops_t eai_runtime_llama_ops;

int eai_llama_load_model(const char *model_path);
int eai_llama_infer(const char *prompt, char *output, size_t output_size);
void eai_llama_unload(void);

#endif

#endif
