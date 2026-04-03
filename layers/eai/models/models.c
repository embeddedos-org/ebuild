// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "models.h"
#include <string.h>
#include <stdio.h>

const eai_model_info_t EAI_MODELS[] = {
    /* ============================================================ */
    /* MICRO TIER — < 100MB, runs on MCUs (Cortex-M7, ESP32-S3)    */
    /* ============================================================ */
    {
        .name = "tinyllama-1.1b-q2k",
        .family = "TinyLlama",
        .description = "Smallest usable LLM — basic Q&A and command parsing",
        .quant = EAI_QUANT_Q2_K, .runtime = EAI_RUNTIME_LLAMA_CPP,
        .tier = EAI_MODEL_TIER_MICRO,
        .param_count_m = 1100, .context_len = 512,
        .ram_mb = 80, .storage_mb = 60,
        .tokens_per_sec = 2,
        .target_hardware = "STM32H7, ESP32-S3, RPi Pico W",
        .license = "Apache-2.0",
        .gguf_file = "tinyllama-1.1b.Q2_K.gguf"
    },

    /* ============================================================ */
    /* TINY TIER — 100-500MB, low-end SBCs (RPi3, BeagleBone)      */
    /* ============================================================ */
    {
        .name = "phi-1.5-q4",
        .family = "Phi",
        .description = "Microsoft Phi-1.5 — strong reasoning for size, code generation",
        .quant = EAI_QUANT_Q4_0, .runtime = EAI_RUNTIME_LLAMA_CPP,
        .tier = EAI_MODEL_TIER_TINY,
        .param_count_m = 1300, .context_len = 2048,
        .ram_mb = 200, .storage_mb = 150,
        .tokens_per_sec = 5,
        .target_hardware = "RPi3, BeagleBone AI, nRF5340",
        .license = "MIT",
        .gguf_file = "phi-1_5.Q4_0.gguf"
    },
    {
        .name = "qwen2-0.5b-q4",
        .family = "Qwen2",
        .description = "Alibaba Qwen2 0.5B — multilingual, tool calling",
        .quant = EAI_QUANT_Q4_0, .runtime = EAI_RUNTIME_LLAMA_CPP,
        .tier = EAI_MODEL_TIER_TINY,
        .param_count_m = 500, .context_len = 4096,
        .ram_mb = 120, .storage_mb = 90,
        .tokens_per_sec = 10,
        .target_hardware = "RPi3, ESP32-P4, AM64x",
        .license = "Apache-2.0",
        .gguf_file = "qwen2-0_5b.Q4_0.gguf"
    },
    {
        .name = "smollm-360m-q5",
        .family = "SmolLM",
        .description = "HuggingFace SmolLM — optimized for embedded command parsing",
        .quant = EAI_QUANT_Q5_1, .runtime = EAI_RUNTIME_LLAMA_CPP,
        .tier = EAI_MODEL_TIER_TINY,
        .param_count_m = 360, .context_len = 2048,
        .ram_mb = 100, .storage_mb = 75,
        .tokens_per_sec = 15,
        .target_hardware = "RPi3, nRF5340, AM64x",
        .license = "Apache-2.0",
        .gguf_file = "smollm-360m.Q5_1.gguf"
    },

    /* ============================================================ */
    /* SMALL TIER — 500MB-2GB, mid SBCs (RPi4, i.MX8M)             */
    /* ============================================================ */
    {
        .name = "phi-2-q4",
        .family = "Phi",
        .description = "Microsoft Phi-2 — strong reasoning, code, math",
        .quant = EAI_QUANT_Q4_0, .runtime = EAI_RUNTIME_LLAMA_CPP,
        .tier = EAI_MODEL_TIER_SMALL,
        .param_count_m = 2700, .context_len = 2048,
        .ram_mb = 600, .storage_mb = 500,
        .tokens_per_sec = 8,
        .target_hardware = "RPi4 (4GB), i.MX8M, SiFive U74",
        .license = "MIT",
        .gguf_file = "phi-2.Q4_0.gguf"
    },
    {
        .name = "gemma-2b-q4",
        .family = "Gemma",
        .description = "Google Gemma 2B — instruction following, safe outputs",
        .quant = EAI_QUANT_Q4_0, .runtime = EAI_RUNTIME_LLAMA_CPP,
        .tier = EAI_MODEL_TIER_SMALL,
        .param_count_m = 2000, .context_len = 8192,
        .ram_mb = 800, .storage_mb = 650,
        .tokens_per_sec = 6,
        .target_hardware = "RPi4 (8GB), i.MX8M Plus, Jetson Nano",
        .license = "Apache-2.0",
        .gguf_file = "gemma-2b-it.Q4_0.gguf"
    },
    {
        .name = "phi-mini-q4",
        .family = "Phi",
        .description = "Default EoS model — Microsoft Phi-3-mini quantized",
        .quant = EAI_QUANT_Q4_0, .runtime = EAI_RUNTIME_LLAMA_CPP,
        .tier = EAI_MODEL_TIER_SMALL,
        .param_count_m = 3800, .context_len = 4096,
        .ram_mb = 2048, .storage_mb = 2300,
        .tokens_per_sec = 5,
        .target_hardware = "RPi4 (8GB), i.MX8M Plus, AM64x",
        .license = "MIT",
        .gguf_file = "phi-3-mini.Q4_0.gguf"
    },
    {
        .name = "qwen2-1.5b-q4",
        .family = "Qwen2",
        .description = "Qwen2 1.5B — tool calling, function routing, multilingual",
        .quant = EAI_QUANT_Q4_0, .runtime = EAI_RUNTIME_LLAMA_CPP,
        .tier = EAI_MODEL_TIER_SMALL,
        .param_count_m = 1500, .context_len = 4096,
        .ram_mb = 500, .storage_mb = 400,
        .tokens_per_sec = 10,
        .target_hardware = "RPi4 (4GB), i.MX8M, SiFive U74",
        .license = "Apache-2.0",
        .gguf_file = "qwen2-1_5b-instruct.Q4_0.gguf"
    },

    /* ============================================================ */
    /* MEDIUM TIER — 2-4GB, high SBCs (Jetson Nano, RPi5, x86)     */
    /* ============================================================ */
    {
        .name = "llama-3.2-3b-q4",
        .family = "Llama",
        .description = "Meta Llama 3.2 3B — state-of-art small model, tool use",
        .quant = EAI_QUANT_Q4_0, .runtime = EAI_RUNTIME_LLAMA_CPP,
        .tier = EAI_MODEL_TIER_MEDIUM,
        .param_count_m = 3000, .context_len = 8192,
        .ram_mb = 2500, .storage_mb = 2000,
        .tokens_per_sec = 15,
        .target_hardware = "RPi5, Jetson Nano, x86 edge",
        .license = "Llama 3.2 Community",
        .gguf_file = "llama-3.2-3b-instruct.Q4_0.gguf"
    },
    {
        .name = "mistral-7b-q3k",
        .family = "Mistral",
        .description = "Mistral 7B aggressively quantized — general assistant",
        .quant = EAI_QUANT_Q3_K, .runtime = EAI_RUNTIME_LLAMA_CPP,
        .tier = EAI_MODEL_TIER_MEDIUM,
        .param_count_m = 7000, .context_len = 8192,
        .ram_mb = 3500, .storage_mb = 3000,
        .tokens_per_sec = 8,
        .target_hardware = "Jetson Nano (4GB), x86 edge, RPi5 (8GB)",
        .license = "Apache-2.0",
        .gguf_file = "mistral-7b-instruct.Q3_K_M.gguf"
    },

    /* ============================================================ */
    /* LARGE TIER — 4GB+, edge servers (x86, Jetson Orin)           */
    /* ============================================================ */
    {
        .name = "llama-3.2-8b-q4",
        .family = "Llama",
        .description = "Meta Llama 3.2 8B — full-capability edge assistant",
        .quant = EAI_QUANT_Q4_0, .runtime = EAI_RUNTIME_LLAMA_CPP,
        .tier = EAI_MODEL_TIER_LARGE,
        .param_count_m = 8000, .context_len = 8192,
        .ram_mb = 6000, .storage_mb = 5000,
        .tokens_per_sec = 20,
        .target_hardware = "x86 edge server, Jetson Orin, workstation",
        .license = "Llama 3.2 Community",
        .gguf_file = "llama-3.2-8b-instruct.Q4_0.gguf"
    },
    {
        .name = "qwen2.5-7b-q4",
        .family = "Qwen2.5",
        .description = "Qwen2.5 7B — best multilingual, tool calling, coding",
        .quant = EAI_QUANT_Q4_0, .runtime = EAI_RUNTIME_LLAMA_CPP,
        .tier = EAI_MODEL_TIER_LARGE,
        .param_count_m = 7000, .context_len = 32768,
        .ram_mb = 5500, .storage_mb = 4500,
        .tokens_per_sec = 15,
        .target_hardware = "x86 edge, Jetson Orin, workstation",
        .license = "Apache-2.0",
        .gguf_file = "qwen2.5-7b-instruct.Q4_0.gguf"
    },
};

const int EAI_MODEL_COUNT = sizeof(EAI_MODELS) / sizeof(EAI_MODELS[0]);

const eai_model_info_t *eai_model_find(const char *name) {
    if (!name) return NULL;
    for (int i = 0; i < EAI_MODEL_COUNT; i++) {
        if (strcmp(EAI_MODELS[i].name, name) == 0)
            return &EAI_MODELS[i];
    }
    return NULL;
}

const eai_model_info_t *eai_model_find_by_tier(eai_model_tier_t tier) {
    for (int i = 0; i < EAI_MODEL_COUNT; i++) {
        if (EAI_MODELS[i].tier == tier)
            return &EAI_MODELS[i];
    }
    return NULL;
}

const eai_model_info_t *eai_model_find_best_fit(uint32_t ram_mb, uint32_t storage_mb) {
    const eai_model_info_t *best = NULL;
    for (int i = 0; i < EAI_MODEL_COUNT; i++) {
        if (EAI_MODELS[i].ram_mb <= ram_mb && EAI_MODELS[i].storage_mb <= storage_mb) {
            if (!best || EAI_MODELS[i].param_count_m > best->param_count_m)
                best = &EAI_MODELS[i];
        }
    }
    return best;
}

static const char *tier_str(eai_model_tier_t t) {
    switch (t) {
    case EAI_MODEL_TIER_MICRO:  return "micro";
    case EAI_MODEL_TIER_TINY:   return "tiny";
    case EAI_MODEL_TIER_SMALL:  return "small";
    case EAI_MODEL_TIER_MEDIUM: return "medium";
    case EAI_MODEL_TIER_LARGE:  return "large";
    default:                    return "?";
    }
}

void eai_model_list(void) {
    fprintf(stderr, "EAI Model Registry (%d models)\n\n", EAI_MODEL_COUNT);
    fprintf(stderr, "%-25s %-8s %-6s %-6s %-8s %-6s %s\n",
            "Model", "Family", "Params", "RAM", "Storage", "Tier", "Hardware");
    fprintf(stderr, "%-25s %-8s %-6s %-6s %-8s %-6s %s\n",
            "-------------------------", "--------", "------", "------",
            "--------", "------", "--------------------");
    for (int i = 0; i < EAI_MODEL_COUNT; i++) {
        const eai_model_info_t *m = &EAI_MODELS[i];
        fprintf(stderr, "%-25s %-8s %4uM %4uMB %5uMB %-6s %s\n",
                m->name, m->family, m->param_count_m, m->ram_mb,
                m->storage_mb, tier_str(m->tier), m->target_hardware);
    }
}