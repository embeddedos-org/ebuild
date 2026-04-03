// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eai_min/runtime.h"
#include "eai_min/runtime_llama.h"
#include "eai/log.h"
#include <string.h>
#include <stdio.h>

#define LOG_MOD "min-rt"

/* ---- Stub runtime (for development/testing without real backends) ---- */

static eai_status_t stub_init(eai_runtime_t *rt)
{
    EAI_LOG_INFO(LOG_MOD, "stub runtime initialized");
    return EAI_OK;
}

static eai_status_t stub_load_model(eai_runtime_t *rt,
                                     const eai_model_manifest_t *manifest,
                                     const char *model_path)
{
    EAI_LOG_INFO(LOG_MOD, "stub: loaded model '%s' from %s", manifest->name, model_path);
    rt->loaded = true;
    memcpy(&rt->manifest, manifest, sizeof(eai_model_manifest_t));
    return EAI_OK;
}

static eai_status_t stub_infer(eai_runtime_t *rt,
                                const eai_inference_input_t *in,
                                eai_inference_output_t *out)
{
    if (!rt->loaded) return EAI_ERR_RUNTIME;

    const char *response = "[stub] inference result for input";
    size_t rlen = strlen(response);
    if (rlen >= sizeof(out->text)) rlen = sizeof(out->text) - 1;
    memcpy(out->text, response, rlen);
    out->text[rlen] = '\0';
    out->text_len = rlen;
    out->confidence = 0.95f;
    out->tokens_used = 12;
    out->latency_ms = 1;

    return EAI_OK;
}

static eai_status_t stub_unload_model(eai_runtime_t *rt)
{
    rt->loaded = false;
    EAI_LOG_INFO(LOG_MOD, "stub: model unloaded");
    return EAI_OK;
}

static void stub_shutdown(eai_runtime_t *rt)
{
    rt->loaded = false;
    EAI_LOG_INFO(LOG_MOD, "stub runtime shutdown");
}

const eai_runtime_ops_t eai_runtime_stub_ops = {
    .name         = "stub",
    .init         = stub_init,
    .load_model   = stub_load_model,
    .infer        = stub_infer,
    .unload_model = stub_unload_model,
    .shutdown     = stub_shutdown,
};

/* ---- EAI-Min runtime wrapper ---- */

eai_status_t eai_min_runtime_create(eai_min_runtime_t *rt, eai_runtime_type_t type)
{
    if (!rt) return EAI_ERR_INVALID;
    memset(rt, 0, sizeof(*rt));

    const eai_runtime_ops_t *ops = NULL;

    switch (type) {
    case EAI_RUNTIME_LLAMA_CPP:
#ifdef EAI_LLAMA_CPP_ENABLED
        EAI_LOG_INFO(LOG_MOD, "llama.cpp backend selected (real)");
        ops = &eai_runtime_llama_ops;
#else
        EAI_LOG_INFO(LOG_MOD, "llama.cpp backend selected (stub)");
        ops = &eai_runtime_stub_ops;
#endif
        break;
    case EAI_RUNTIME_ONNX:
        EAI_LOG_INFO(LOG_MOD, "ONNX backend selected (using stub)");
        ops = &eai_runtime_stub_ops;
        break;
    case EAI_RUNTIME_TFLITE:
        EAI_LOG_INFO(LOG_MOD, "TFLite backend selected (using stub)");
        ops = &eai_runtime_stub_ops;
        break;
    default:
        EAI_LOG_INFO(LOG_MOD, "custom/stub backend selected");
        ops = &eai_runtime_stub_ops;
        break;
    }

    eai_status_t s = eai_runtime_init(&rt->base, ops);
    if (s != EAI_OK) return s;

    rt->max_tokens   = 256;
    rt->temperature  = 0.7f;
    rt->initialized  = true;

    return EAI_OK;
}

eai_status_t eai_min_runtime_load(eai_min_runtime_t *rt, const char *model_path,
                                   const eai_model_manifest_t *manifest)
{
    if (!rt || !rt->initialized) return EAI_ERR_INVALID;
    rt->model_path = model_path;
    return eai_runtime_load(&rt->base, manifest, model_path);
}

eai_status_t eai_min_runtime_infer(eai_min_runtime_t *rt,
                                    const char *prompt,
                                    char *output, size_t output_size)
{
    if (!rt || !rt->initialized || !rt->base.loaded) return EAI_ERR_RUNTIME;

    eai_inference_input_t in = {
        .text     = prompt,
        .text_len = strlen(prompt),
        .binary   = NULL,
        .binary_len = 0,
    };

    eai_inference_output_t out;
    memset(&out, 0, sizeof(out));

    eai_status_t s = eai_runtime_infer(&rt->base, &in, &out);
    if (s != EAI_OK) return s;

    size_t copy_len = out.text_len < output_size - 1 ? out.text_len : output_size - 1;
    memcpy(output, out.text, copy_len);
    output[copy_len] = '\0';

    return EAI_OK;
}

void eai_min_runtime_destroy(eai_min_runtime_t *rt)
{
    if (!rt) return;
    if (rt->base.loaded) eai_runtime_unload(&rt->base);
    eai_runtime_shutdown(&rt->base);
    rt->initialized = false;
}
