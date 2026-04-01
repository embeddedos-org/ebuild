// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "simulator.h"
#include "eni/log.h"
#include <string.h>
#include <stdlib.h>

typedef struct {
    uint32_t event_interval_ms;
    uint32_t tick_count;
    uint32_t cycle;
} sim_ctx_t;

static const char *s_sim_intents[] = {
    "move_left",
    "move_right",
    "select",
    "scroll_up",
    "scroll_down",
    "activate",
    "deactivate",
};
static const int s_sim_intent_count = sizeof(s_sim_intents) / sizeof(s_sim_intents[0]);

static eni_status_t sim_init(eni_provider_t *prov, const void *config)
{
    sim_ctx_t *ctx = (sim_ctx_t *)calloc(1, sizeof(sim_ctx_t));
    if (!ctx) return ENI_ERR_NOMEM;

    if (config) {
        const eni_simulator_config_t *scfg = (const eni_simulator_config_t *)config;
        ctx->event_interval_ms = scfg->event_interval_ms;
    } else {
        ctx->event_interval_ms = 500;
    }

    ctx->tick_count = 0;
    ctx->cycle = 0;
    prov->ctx = ctx;

    ENI_LOG_INFO("simulator", "initialized (interval=%u ms)", ctx->event_interval_ms);
    return ENI_OK;
}

static eni_status_t sim_start(eni_provider_t *prov)
{
    ENI_LOG_INFO("simulator", "started");
    return ENI_OK;
}

static eni_status_t sim_poll(eni_provider_t *prov, eni_event_t *ev)
{
    if (!prov || !ev) return ENI_ERR_INVALID;

    sim_ctx_t *ctx = (sim_ctx_t *)prov->ctx;
    if (!ctx) return ENI_ERR_RUNTIME;

    ctx->tick_count++;

    /* Generate an event every N ticks to simulate intermittent signals */
    if (ctx->tick_count % 3 != 0) {
        return ENI_ERR_TIMEOUT;
    }

    eni_status_t st = eni_event_init(ev, ENI_EVENT_INTENT, "simulator");
    if (st != ENI_OK) return st;

    int idx = ctx->cycle % s_sim_intent_count;
    float confidence = 0.75f + (float)(ctx->cycle % 25) / 100.0f;
    if (confidence > 1.0f) confidence = 1.0f;

    st = eni_event_set_intent(ev, s_sim_intents[idx], confidence);
    ctx->cycle++;

    return st;
}

static eni_status_t sim_stop(eni_provider_t *prov)
{
    ENI_LOG_INFO("simulator", "stopped");
    return ENI_OK;
}

static void sim_shutdown(eni_provider_t *prov)
{
    if (prov && prov->ctx) {
        free(prov->ctx);
        prov->ctx = NULL;
    }
    ENI_LOG_INFO("simulator", "shutdown");
}

const eni_provider_ops_t eni_provider_simulator_ops = {
    .name     = "simulator",
    .init     = sim_init,
    .poll     = sim_poll,
    .start    = sim_start,
    .stop     = sim_stop,
    .shutdown = sim_shutdown,
};
