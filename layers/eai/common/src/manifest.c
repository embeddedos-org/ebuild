// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eai/manifest.h"
#include "eai/log.h"
#include <string.h>
#include <stdio.h>

#define LOG_MOD "manifest"

eai_status_t eai_manifest_load(eai_model_manifest_t *m, const char *path)
{
    if (!m || !path) return EAI_ERR_INVALID;

    FILE *fp = fopen(path, "r");
    if (!fp) {
        EAI_LOG_ERROR(LOG_MOD, "cannot open manifest: %s", path);
        return EAI_ERR_IO;
    }

    memset(m, 0, sizeof(*m));

    char line[512];
    while (fgets(line, sizeof(line), fp)) {
        char val[256];
        if (sscanf(line, "name: %63s", m->name) == 1) continue;
        if (sscanf(line, "version: %15s", m->version) == 1) continue;
        if (sscanf(line, "hash: %71s", m->hash) == 1) continue;

        if (sscanf(line, "kind: %255s", val) == 1) {
            if (strcmp(val, "llm") == 0)             m->kind = EAI_MODEL_LLM;
            else if (strcmp(val, "vision") == 0)      m->kind = EAI_MODEL_VISION;
            else if (strcmp(val, "anomaly") == 0)      m->kind = EAI_MODEL_ANOMALY;
            else if (strcmp(val, "classification") == 0) m->kind = EAI_MODEL_CLASSIFICATION;
            else m->kind = EAI_MODEL_CUSTOM;
        }
        if (sscanf(line, "runtime: %255s", val) == 1) {
            if (strcmp(val, "llama.cpp") == 0)     m->runtime = EAI_RUNTIME_LLAMA_CPP;
            else if (strcmp(val, "onnx") == 0)     m->runtime = EAI_RUNTIME_ONNX;
            else if (strcmp(val, "tflite") == 0)   m->runtime = EAI_RUNTIME_TFLITE;
            else m->runtime = EAI_RUNTIME_CUSTOM;
        }

        uint32_t uval;
        if (sscanf(line, " ram_mb: %u", &uval) == 1) m->footprint.ram_mb = uval;
        if (sscanf(line, " storage_mb: %u", &uval) == 1) m->footprint.storage_mb = uval;
    }

    fclose(fp);
    EAI_LOG_INFO(LOG_MOD, "loaded manifest: %s (%s)", m->name, m->version);
    return EAI_OK;
}

eai_status_t eai_manifest_validate(const eai_model_manifest_t *m)
{
    if (!m) return EAI_ERR_INVALID;
    if (m->name[0] == '\0') {
        EAI_LOG_ERROR(LOG_MOD, "manifest missing name");
        return EAI_ERR_INVALID;
    }
    if (m->version[0] == '\0') {
        EAI_LOG_ERROR(LOG_MOD, "manifest missing version");
        return EAI_ERR_INVALID;
    }
    if (m->footprint.ram_mb == 0) {
        EAI_LOG_WARN(LOG_MOD, "manifest missing RAM footprint");
    }
    return EAI_OK;
}

void eai_manifest_print(const eai_model_manifest_t *m)
{
    if (!m) return;

    static const char *kind_names[] = {"llm", "vision", "anomaly", "classification", "custom"};
    static const char *rt_names[]   = {"llama.cpp", "onnx", "tflite", "custom"};

    printf("Model Manifest:\n");
    printf("  name:       %s\n", m->name);
    printf("  kind:       %s\n", kind_names[m->kind]);
    printf("  runtime:    %s\n", rt_names[m->runtime]);
    printf("  version:    %s\n", m->version);
    printf("  RAM:        %u MB\n", m->footprint.ram_mb);
    printf("  storage:    %u MB\n", m->footprint.storage_mb);
    if (m->hash[0]) printf("  hash:       %s\n", m->hash);
}
