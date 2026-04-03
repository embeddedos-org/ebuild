// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "generic.h"
#include "eni/log.h"
#include <string.h>
#include <stdlib.h>

typedef struct {
    eni_transport_t transport;
    char            endpoint[256];
    uint32_t        timeout_ms;
} generic_ctx_t;

static eni_status_t generic_init(eni_provider_t *prov, const void *config)
{
    generic_ctx_t *ctx = (generic_ctx_t *)calloc(1, sizeof(generic_ctx_t));
    if (!ctx) return ENI_ERR_NOMEM;

    if (config) {
        const eni_generic_config_t *gcfg = (const eni_generic_config_t *)config;
        ctx->transport  = gcfg->transport;
        ctx->timeout_ms = gcfg->timeout_ms;
        if (gcfg->endpoint) {
            size_t len = strlen(gcfg->endpoint);
            if (len >= sizeof(ctx->endpoint)) len = sizeof(ctx->endpoint) - 1;
            memcpy(ctx->endpoint, gcfg->endpoint, len);
            ctx->endpoint[len] = '\0';
        }
    } else {
        ctx->transport  = ENI_TRANSPORT_TCP;
        ctx->timeout_ms = 1000;
    }

    prov->ctx = ctx;
    ENI_LOG_INFO("generic", "initialized (transport=%d endpoint=%s)",
                 ctx->transport, ctx->endpoint);
    return ENI_OK;
}

static eni_status_t generic_start(eni_provider_t *prov)
{
    generic_ctx_t *ctx = (generic_ctx_t *)prov->ctx;
    ENI_LOG_INFO("generic", "connecting to %s...", ctx->endpoint);
    /* TODO: actual socket/gRPC/MQTT connection */
    ENI_LOG_WARN("generic", "network transport not yet implemented — stub mode");
    return ENI_OK;
}

static eni_status_t generic_poll(eni_provider_t *prov, eni_event_t *ev)
{
    (void)prov;
    (void)ev;
    /* Stub — would read from network transport */
    return ENI_ERR_TIMEOUT;
}

static eni_status_t generic_stop(eni_provider_t *prov)
{
    ENI_LOG_INFO("generic", "disconnected");
    return ENI_OK;
}

static void generic_shutdown(eni_provider_t *prov)
{
    if (prov && prov->ctx) {
        free(prov->ctx);
        prov->ctx = NULL;
    }
    ENI_LOG_INFO("generic", "shutdown");
}

const eni_provider_ops_t eni_provider_generic_ops = {
    .name     = "generic",
    .init     = generic_init,
    .poll     = generic_poll,
    .start    = generic_start,
    .stop     = generic_stop,
    .shutdown = generic_shutdown,
};
