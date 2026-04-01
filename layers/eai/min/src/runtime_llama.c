// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifdef EAI_LLAMA_CPP_ENABLED

#include "eai_min/runtime_llama.h"
#include "eai/log.h"
#include "llama.h"
#include <string.h>
#include <stdlib.h>
#include <time.h>

#define LOG_MOD "rt-llama"

typedef struct {
    struct llama_model *model;
    struct llama_context *ctx;
    int n_ctx;
    int n_threads;
} llama_rt_ctx_t;

static eai_status_t llama_init(eai_runtime_t *rt) {
    llama_backend_init();
    llama_rt_ctx_t *lctx = calloc(1, sizeof(llama_rt_ctx_t));
    if (!lctx) return EAI_ERR_NOMEM;
    lctx->n_ctx = 2048;
    lctx->n_threads = 4;
    rt->ctx = lctx;
    EAI_LOG_INFO(LOG_MOD, "llama.cpp backend initialized");
    return EAI_OK;
}

static eai_status_t llama_load_model(eai_runtime_t *rt,
                                     const eai_model_manifest_t *manifest,
                                     const char *model_path) {
    llama_rt_ctx_t *lctx = (llama_rt_ctx_t *)rt->ctx;
    if (!lctx) return EAI_ERR_INVALID;

    struct llama_model_params model_params = llama_model_default_params();
    lctx->model = llama_load_model_from_file(model_path, model_params);
    if (!lctx->model) {
        EAI_LOG_ERROR(LOG_MOD, "failed to load model: %s", model_path);
        return EAI_ERR_IO;
    }

    struct llama_context_params ctx_params = llama_context_default_params();
    ctx_params.n_ctx = lctx->n_ctx;
    ctx_params.n_threads = lctx->n_threads;
    lctx->ctx = llama_new_context_with_model(lctx->model, ctx_params);
    if (!lctx->ctx) {
        llama_free_model(lctx->model);
        lctx->model = NULL;
        return EAI_ERR_RUNTIME;
    }

    rt->loaded = true;
    EAI_LOG_INFO(LOG_MOD, "model loaded: %s (ctx=%d)", model_path, lctx->n_ctx);
    return EAI_OK;
}

static eai_status_t llama_infer(eai_runtime_t *rt,
                                const eai_inference_input_t *in,
                                eai_inference_output_t *out) {
    llama_rt_ctx_t *lctx = (llama_rt_ctx_t *)rt->ctx;
    if (!lctx || !lctx->ctx || !lctx->model) return EAI_ERR_RUNTIME;
    if (!in || !in->text || !out) return EAI_ERR_INVALID;

    memset(out, 0, sizeof(*out));
    clock_t start = clock();

    /* Tokenize input */
    int n_tokens = llama_tokenize(lctx->model, in->text, (int)in->text_len,
                                  NULL, 0, true, false);
    if (n_tokens < 0) n_tokens = -n_tokens;
    llama_token *tokens = malloc(sizeof(llama_token) * (n_tokens + 1));
    if (!tokens) return EAI_ERR_NOMEM;
    n_tokens = llama_tokenize(lctx->model, in->text, (int)in->text_len,
                              tokens, n_tokens + 1, true, false);

    /* Create batch and evaluate */
    struct llama_batch batch = llama_batch_init(n_tokens, 0, 1);
    for (int i = 0; i < n_tokens; i++) {
        llama_batch_add(&batch, tokens[i], i,
                        (llama_seq_id[]){0}, 1, false);
    }
    if (batch.n_tokens > 0) batch.logits[batch.n_tokens - 1] = true;
    llama_decode(lctx->ctx, batch);

    /* Generate tokens */
    int max_gen = 256;
    size_t out_pos = 0;
    for (int i = 0; i < max_gen; i++) {
        float *logits = llama_get_logits(lctx->ctx);
        int n_vocab = llama_n_vocab(lctx->model);

        /* Greedy sampling */
        llama_token best = 0;
        float best_logit = logits[0];
        for (int v = 1; v < n_vocab; v++) {
            if (logits[v] > best_logit) {
                best_logit = logits[v];
                best = v;
            }
        }

        if (llama_token_is_eog(lctx->model, best)) break;

        char piece[64];
        int piece_len = llama_token_to_piece(lctx->model, best,
                                             piece, sizeof(piece), 0, false);
        if (piece_len > 0 && out_pos + piece_len < sizeof(out->text) - 1) {
            memcpy(out->text + out_pos, piece, piece_len);
            out_pos += piece_len;
        }
        out->tokens_used++;

        struct llama_batch next = llama_batch_init(1, 0, 1);
        llama_batch_add(&next, best, n_tokens + i,
                        (llama_seq_id[]){0}, 1, true);
        llama_decode(lctx->ctx, next);
        llama_batch_free(next);
    }

    out->text[out_pos] = '\0';
    out->text_len = out_pos;
    out->confidence = 0.9f;
    out->latency_ms = (uint32_t)((clock() - start) * 1000 / CLOCKS_PER_SEC);

    llama_batch_free(batch);
    free(tokens);
    llama_kv_cache_clear(lctx->ctx);

    EAI_LOG_INFO(LOG_MOD, "inference complete: %zu tokens in %u ms",
                 out->tokens_used, out->latency_ms);
    return EAI_OK;
}

static eai_status_t llama_unload(eai_runtime_t *rt) {
    llama_rt_ctx_t *lctx = (llama_rt_ctx_t *)rt->ctx;
    if (lctx) {
        if (lctx->ctx) { llama_free(lctx->ctx); lctx->ctx = NULL; }
        if (lctx->model) { llama_free_model(lctx->model); lctx->model = NULL; }
    }
    rt->loaded = false;
    return EAI_OK;
}

static void llama_shutdown(eai_runtime_t *rt) {
    llama_unload(rt);
    llama_rt_ctx_t *lctx = (llama_rt_ctx_t *)rt->ctx;
    free(lctx);
    rt->ctx = NULL;
    llama_backend_free();
}

const eai_runtime_ops_t eai_runtime_llama_ops = {
    .name         = "llama.cpp",
    .init         = llama_init,
    .load_model   = llama_load_model,
    .infer        = llama_infer,
    .unload_model = llama_unload,
    .shutdown     = llama_shutdown,
};

#endif /* EAI_LLAMA_CPP_ENABLED */
