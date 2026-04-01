// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef EAI_MODELS_H
#define EAI_MODELS_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    EAI_QUANT_F32   = 0,
    EAI_QUANT_F16   = 1,
    EAI_QUANT_Q8_0  = 2,
    EAI_QUANT_Q5_1  = 3,
    EAI_QUANT_Q5_0  = 4,
    EAI_QUANT_Q4_1  = 5,
    EAI_QUANT_Q4_0  = 6,
    EAI_QUANT_Q3_K  = 7,
    EAI_QUANT_Q2_K  = 8,
    EAI_QUANT_IQ2   = 9
} eai_quant_t;

typedef enum {
    EAI_RUNTIME_LLAMA_CPP  = 0,
    EAI_RUNTIME_ONNX       = 1,
    EAI_RUNTIME_TFLITE     = 2,
    EAI_RUNTIME_CUSTOM     = 3
} eai_runtime_t;

typedef enum {
    EAI_MODEL_TIER_MICRO  = 0,   /* < 100MB, MCU-class (Cortex-M7, RP2040) */
    EAI_MODEL_TIER_TINY   = 1,   /* 100-500MB, low-end SBC (RPi3, nRF5340) */
    EAI_MODEL_TIER_SMALL  = 2,   /* 500MB-2GB, mid SBC (RPi4, i.MX8M) */
    EAI_MODEL_TIER_MEDIUM = 3,   /* 2-4GB, high SBC (Jetson Nano, RPi5) */
    EAI_MODEL_TIER_LARGE  = 4    /* 4GB+, edge server (x86, Jetson Orin) */
} eai_model_tier_t;

typedef struct {
    const char     *name;
    const char     *family;
    const char     *description;
    eai_quant_t     quant;
    eai_runtime_t   runtime;
    eai_model_tier_t tier;
    uint32_t        param_count_m;    /* parameters in millions */
    uint32_t        context_len;      /* max context tokens */
    uint32_t        ram_mb;           /* RAM required */
    uint32_t        storage_mb;       /* disk/flash storage */
    uint32_t        tokens_per_sec;   /* approx on target hardware */
    const char     *target_hardware;  /* recommended hardware */
    const char     *license;
    const char     *gguf_file;        /* filename for llama.cpp */
} eai_model_info_t;

/* Model registry — curated embedded LLMs */
extern const eai_model_info_t EAI_MODELS[];
extern const int EAI_MODEL_COUNT;

/* Lookup */
const eai_model_info_t *eai_model_find(const char *name);
const eai_model_info_t *eai_model_find_by_tier(eai_model_tier_t tier);
const eai_model_info_t *eai_model_find_best_fit(uint32_t ram_mb, uint32_t storage_mb);
void eai_model_list(void);

#ifdef __cplusplus
}
#endif

#endif /* EAI_MODELS_H */