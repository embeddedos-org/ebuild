// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef EAI_MIN_ROUTER_H
#define EAI_MIN_ROUTER_H

#include "eai/types.h"
#include "eai/runtime_contract.h"

typedef enum {
    EAI_ROUTE_LOCAL,
    EAI_ROUTE_CLOUD,
    EAI_ROUTE_AUTO,
} eai_route_target_t;

typedef struct {
    const char       *cloud_endpoint;
    const char       *api_key;
    uint32_t          timeout_ms;
    bool              cloud_available;
    eai_route_target_t default_target;
} eai_min_router_t;

eai_status_t eai_min_router_init(eai_min_router_t *router, eai_route_target_t default_target);
eai_status_t eai_min_router_set_cloud(eai_min_router_t *router,
                                       const char *endpoint, const char *api_key);
eai_route_target_t eai_min_router_decide(const eai_min_router_t *router,
                                          const eai_inference_input_t *input);
eai_status_t eai_min_router_infer_cloud(eai_min_router_t *router,
                                         const eai_inference_input_t *in,
                                         eai_inference_output_t *out);

#endif /* EAI_MIN_ROUTER_H */
