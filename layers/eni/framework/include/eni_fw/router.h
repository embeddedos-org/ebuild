// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef ENI_FW_ROUTER_H
#define ENI_FW_ROUTER_H

#include "eni/common.h"

typedef enum {
    ENI_ROUTE_CRITICAL,
    ENI_ROUTE_NORMAL,
    ENI_ROUTE_LOW,
} eni_route_priority_t;

typedef struct {
    eni_event_type_t     type_filter;
    eni_route_priority_t priority;
    uint32_t             max_latency_ms;
    bool                 local_only;
} eni_route_rule_t;

#define ENI_FW_MAX_ROUTES 32

typedef struct {
    eni_route_rule_t rules[ENI_FW_MAX_ROUTES];
    int              count;
} eni_fw_router_t;

eni_status_t         eni_fw_router_init(eni_fw_router_t *router);
eni_status_t         eni_fw_router_add_rule(eni_fw_router_t *router,
                                             eni_event_type_t type,
                                             eni_route_priority_t priority,
                                             uint32_t max_latency_ms,
                                             bool local_only);
eni_route_priority_t eni_fw_router_classify(const eni_fw_router_t *router,
                                             const eni_event_t *ev);

#endif /* ENI_FW_ROUTER_H */
