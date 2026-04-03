// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eni_fw/service.h"
#include "eni/log.h"
#include <string.h>
#include <stdio.h>

eni_status_t eni_fw_service_init(eni_fw_service_t *svc, const eni_config_t *cfg)
{
    if (!svc || !cfg) return ENI_ERR_INVALID;

    memset(svc, 0, sizeof(*svc));
    memcpy(&svc->config, cfg, sizeof(*cfg));
    svc->state = ENI_FW_STATE_INIT;

    eni_status_t st;

    st = eni_fw_provider_manager_init(&svc->providers);
    if (st != ENI_OK) return st;

    st = eni_fw_stream_bus_init(&svc->stream_bus);
    if (st != ENI_OK) return st;

    st = eni_fw_router_init(&svc->router);
    if (st != ENI_OK) return st;

    st = eni_policy_init(&svc->policy);
    if (st != ENI_OK) return st;

    /* Load policy from config */
    for (int i = 0; i < cfg->policy.allow_count; i++) {
        eni_policy_add_rule(&svc->policy, cfg->policy.allow[i],
                            ENI_POLICY_ALLOW, ENI_ACTION_SAFE);
    }
    for (int i = 0; i < cfg->policy.deny_count; i++) {
        eni_policy_add_rule(&svc->policy, cfg->policy.deny[i],
                            ENI_POLICY_DENY, ENI_ACTION_RESTRICTED);
    }

    st = eni_fw_orchestrator_init(&svc->orchestrator, &svc->policy, &svc->router);
    if (st != ENI_OK) return st;

    st = eni_fw_connector_manager_init(&svc->connectors);
    if (st != ENI_OK) return st;

    st = eni_fw_observability_init(&svc->observability,
                                    cfg->observability.metrics,
                                    cfg->observability.audit,
                                    cfg->observability.trace);
    if (st != ENI_OK) return st;

    /* Default routing: control events are critical */
    eni_fw_router_add_rule(&svc->router, ENI_EVENT_CONTROL,
                           ENI_ROUTE_CRITICAL, cfg->routing.max_latency_ms, true);
    eni_fw_router_add_rule(&svc->router, ENI_EVENT_INTENT,
                           ENI_ROUTE_NORMAL, 50, false);
    eni_fw_router_add_rule(&svc->router, ENI_EVENT_FEATURES,
                           ENI_ROUTE_LOW, 100, false);

    ENI_LOG_INFO("fw.service", "initialized");
    return ENI_OK;
}

eni_status_t eni_fw_service_add_provider(eni_fw_service_t *svc,
                                          const eni_provider_ops_t *ops,
                                          const char *name)
{
    if (!svc || !ops || !name) return ENI_ERR_INVALID;
    return eni_fw_provider_manager_add(&svc->providers, ops, name, NULL);
}

eni_status_t eni_fw_service_start(eni_fw_service_t *svc)
{
    if (!svc) return ENI_ERR_INVALID;

    eni_status_t st = eni_fw_provider_manager_start_all(&svc->providers);
    if (st != ENI_OK) {
        svc->state = ENI_FW_STATE_ERROR;
        return st;
    }

    svc->state = ENI_FW_STATE_RUNNING;
    ENI_LOG_INFO("fw.service", "started");
    return ENI_OK;
}

eni_status_t eni_fw_service_tick(eni_fw_service_t *svc)
{
    if (!svc) return ENI_ERR_INVALID;
    if (svc->state != ENI_FW_STATE_RUNNING) return ENI_ERR_RUNTIME;

    /* Ingest from providers into stream bus */
    eni_event_t ev;
    int prov_idx = -1;
    eni_status_t st = eni_fw_provider_manager_poll_any(&svc->providers, &ev, &prov_idx);
    if (st == ENI_OK) {
        eni_fw_observability_record_event(&svc->observability);
        st = eni_fw_stream_bus_push(&svc->stream_bus, &ev);
        if (st != ENI_OK) {
            eni_fw_observability_record_drop(&svc->observability);
        }
    }

    /* Process one event from the bus */
    if (!eni_fw_stream_bus_empty(&svc->stream_bus)) {
        eni_event_t bus_ev;
        st = eni_fw_stream_bus_pop(&svc->stream_bus, &bus_ev);
        if (st == ENI_OK) {
            /* Route and classify */
            eni_route_priority_t pri = eni_fw_router_classify(&svc->router, &bus_ev);

            /* Dispatch intent events through orchestrator */
            if (bus_ev.type == ENI_EVENT_INTENT &&
                (pri == ENI_ROUTE_CRITICAL || pri == ENI_ROUTE_NORMAL)) {
                eni_tool_call_t call;
                memset(&call, 0, sizeof(call));
                strncpy(call.tool, bus_ev.payload.intent.name,
                        ENI_TOOL_NAME_MAX - 1);

                eni_tool_result_t result;
                memset(&result, 0, sizeof(result));

                eni_status_t dispatch_st = eni_fw_orchestrator_dispatch(
                    &svc->orchestrator, &bus_ev, &call, &result);
                if (dispatch_st != ENI_OK) {
                    ENI_LOG_WARN("fw.service", "orchestrator dispatch failed for '%s'",
                                 bus_ev.payload.intent.name);
                }
            }

            /* Broadcast to connectors */
            eni_fw_connector_broadcast(&svc->connectors, &bus_ev);

            /* Audit */
            if (bus_ev.type == ENI_EVENT_INTENT) {
                eni_fw_observability_audit(&svc->observability,
                                           bus_ev.payload.intent.name,
                                           bus_ev.source, ENI_OK);
            }
        }
    }

    return ENI_OK;
}

eni_status_t eni_fw_service_stop(eni_fw_service_t *svc)
{
    if (!svc) return ENI_ERR_INVALID;

    eni_fw_provider_manager_stop_all(&svc->providers);
    svc->state = ENI_FW_STATE_STOPPED;
    ENI_LOG_INFO("fw.service", "stopped");
    return ENI_OK;
}

void eni_fw_service_shutdown(eni_fw_service_t *svc)
{
    if (!svc) return;

    if (svc->state == ENI_FW_STATE_RUNNING) {
        eni_fw_service_stop(svc);
    }
    eni_fw_provider_manager_shutdown(&svc->providers);
    eni_fw_connector_manager_shutdown(&svc->connectors);
    ENI_LOG_INFO("fw.service", "shutdown complete");
}

void eni_fw_service_stats(const eni_fw_service_t *svc)
{
    if (!svc) return;

    const char *state_str;
    switch (svc->state) {
    case ENI_FW_STATE_INIT:    state_str = "init";    break;
    case ENI_FW_STATE_RUNNING: state_str = "running"; break;
    case ENI_FW_STATE_STOPPED: state_str = "stopped"; break;
    case ENI_FW_STATE_ERROR:   state_str = "error";   break;
    default:                   state_str = "unknown";  break;
    }

    printf("[eni-framework] state=%s\n", state_str);
    eni_fw_stream_bus_stats(&svc->stream_bus);
    eni_fw_orchestrator_stats(&svc->orchestrator);
    eni_fw_observability_dump_metrics(&svc->observability);
}
