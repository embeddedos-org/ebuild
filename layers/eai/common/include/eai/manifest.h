// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef EAI_MANIFEST_H
#define EAI_MANIFEST_H

#include "eai/types.h"

#define EAI_MANIFEST_MAX_INPUTS   8
#define EAI_MANIFEST_MAX_OUTPUTS  8
#define EAI_MANIFEST_MAX_ARCH     4

typedef enum {
    EAI_MODEL_LLM,
    EAI_MODEL_VISION,
    EAI_MODEL_ANOMALY,
    EAI_MODEL_CLASSIFICATION,
    EAI_MODEL_CUSTOM,
} eai_model_kind_t;

typedef enum {
    EAI_RUNTIME_LLAMA_CPP,
    EAI_RUNTIME_ONNX,
    EAI_RUNTIME_TFLITE,
    EAI_RUNTIME_CUSTOM,
} eai_runtime_type_t;

typedef enum {
    EAI_ARCH_ARM64,
    EAI_ARCH_X86_64,
    EAI_ARCH_RISCV64,
    EAI_ARCH_ARM32,
} eai_arch_t;

typedef struct {
    uint32_t ram_mb;
    uint32_t storage_mb;
} eai_footprint_t;

typedef struct {
    char              name[64];
    eai_model_kind_t  kind;
    eai_runtime_type_t runtime;
    char              version[16];

    const char       *inputs[EAI_MANIFEST_MAX_INPUTS];
    int               input_count;
    const char       *outputs[EAI_MANIFEST_MAX_OUTPUTS];
    int               output_count;

    eai_footprint_t   footprint;

    eai_arch_t        compat_arch[EAI_MANIFEST_MAX_ARCH];
    int               compat_arch_count;

    char              hash[72];  /* sha256:... */
} eai_model_manifest_t;

eai_status_t eai_manifest_load(eai_model_manifest_t *m, const char *path);
eai_status_t eai_manifest_validate(const eai_model_manifest_t *m);
void         eai_manifest_print(const eai_model_manifest_t *m);

#endif /* EAI_MANIFEST_H */
