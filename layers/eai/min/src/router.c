// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eai_min/router.h"
#include "eai/log.h"
#include <string.h>

#define LOG_MOD "min-router"

eai_status_t eai_min_router_init(eai_min_router_t *router, eai_route_target_t default_target)
{
    if (!router) return EAI_ERR_INVALID;
    memset(router, 0, sizeof(*router));
    router->default_target  = default_target;
    router->timeout_ms      = 5000;
    router->cloud_available = false;
    return EAI_OK;
}

eai_status_t eai_min_router_set_cloud(eai_min_router_t *router,
                                       const char *endpoint, const char *api_key)
{
    if (!router || !endpoint) return EAI_ERR_INVALID;
    router->cloud_endpoint  = endpoint;
    router->api_key         = api_key;
    router->cloud_available = true;
    EAI_LOG_INFO(LOG_MOD, "cloud endpoint set: %s", endpoint);
    return EAI_OK;
}

eai_route_target_t eai_min_router_decide(const eai_min_router_t *router,
                                          const eai_inference_input_t *input)
{
    if (!router) return EAI_ROUTE_LOCAL;

    if (router->default_target == EAI_ROUTE_LOCAL)
        return EAI_ROUTE_LOCAL;

    if (router->default_target == EAI_ROUTE_CLOUD) {
        if (router->cloud_available) return EAI_ROUTE_CLOUD;
        EAI_LOG_WARN(LOG_MOD, "cloud requested but unavailable, falling back to local");
        return EAI_ROUTE_LOCAL;
    }

    /* AUTO mode: decide based on input complexity */
    if (input && input->text_len > 2048 && router->cloud_available) {
        EAI_LOG_DEBUG(LOG_MOD, "auto-routing to cloud (large input: %zu bytes)", input->text_len);
        return EAI_ROUTE_CLOUD;
    }

    return EAI_ROUTE_LOCAL;
}

eai_status_t eai_min_router_infer_cloud(eai_min_router_t *router,
                                         const eai_inference_input_t *in,
                                         eai_inference_output_t *out)
{
    if (!router || !router->cloud_available) return EAI_ERR_CONNECT;

    EAI_LOG_INFO(LOG_MOD, "cloud inference: endpoint=%s, input_len=%zu",
                 router->cloud_endpoint, in->text_len);

    /* placeholder: real implementation would use HTTP client */
    const char *stub = "[cloud] inference not yet implemented";
    strncpy(out->text, stub, sizeof(out->text) - 1);
    out->text_len   = strlen(stub);
    out->confidence = 0.0f;
    out->tokens_used = 0;
    out->latency_ms  = 0;

    return EAI_ERR_UNSUPPORTED;
}
