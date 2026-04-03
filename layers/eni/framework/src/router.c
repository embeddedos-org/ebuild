// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eni_fw/router.h"
#include "eni/log.h"
#include <string.h>

eni_status_t eni_fw_router_init(eni_fw_router_t *router)
{
    if (!router) return ENI_ERR_INVALID;
    memset(router, 0, sizeof(*router));
    return ENI_OK;
}

eni_status_t eni_fw_router_add_rule(eni_fw_router_t *router,
                                     eni_event_type_t type,
                                     eni_route_priority_t priority,
                                     uint32_t max_latency_ms,
                                     bool local_only)
{
    if (!router) return ENI_ERR_INVALID;
    if (router->count >= ENI_FW_MAX_ROUTES) return ENI_ERR_OVERFLOW;

    eni_route_rule_t *rule = &router->rules[router->count];
    rule->type_filter    = type;
    rule->priority       = priority;
    rule->max_latency_ms = max_latency_ms;
    rule->local_only     = local_only;
    router->count++;

    return ENI_OK;
}

eni_route_priority_t eni_fw_router_classify(const eni_fw_router_t *router,
                                             const eni_event_t *ev)
{
    if (!router || !ev) return ENI_ROUTE_NORMAL;

    for (int i = 0; i < router->count; i++) {
        if (router->rules[i].type_filter == ev->type) {
            return router->rules[i].priority;
        }
    }

    return ENI_ROUTE_NORMAL;
}
