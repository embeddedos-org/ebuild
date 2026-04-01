// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef ENI_FW_SERVICE_H
#define ENI_FW_SERVICE_H

#include "eni/common.h"
#include "eni_fw/provider_manager.h"
#include "eni_fw/stream_bus.h"
#include "eni_fw/router.h"
#include "eni_fw/orchestrator.h"
#include "eni_fw/connectors.h"
#include "eni_fw/observability.h"

typedef enum {
    ENI_FW_STATE_INIT,
    ENI_FW_STATE_RUNNING,
    ENI_FW_STATE_STOPPED,
    ENI_FW_STATE_ERROR,
} eni_fw_state_t;

typedef struct {
    eni_config_t                config;
    eni_fw_provider_manager_t   providers;
    eni_fw_stream_bus_t         stream_bus;
    eni_fw_router_t             router;
    eni_policy_engine_t         policy;
    eni_fw_orchestrator_t       orchestrator;
    eni_fw_connector_manager_t  connectors;
    eni_fw_observability_t      observability;
    eni_fw_state_t              state;
} eni_fw_service_t;

eni_status_t eni_fw_service_init(eni_fw_service_t *svc, const eni_config_t *cfg);
eni_status_t eni_fw_service_add_provider(eni_fw_service_t *svc,
                                          const eni_provider_ops_t *ops,
                                          const char *name);
eni_status_t eni_fw_service_start(eni_fw_service_t *svc);
eni_status_t eni_fw_service_tick(eni_fw_service_t *svc);
eni_status_t eni_fw_service_stop(eni_fw_service_t *svc);
void         eni_fw_service_shutdown(eni_fw_service_t *svc);
void         eni_fw_service_stats(const eni_fw_service_t *svc);

#endif /* ENI_FW_SERVICE_H */
