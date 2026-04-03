// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eni_min/service.h"
#include "eni/log.h"
#ifdef ENI_EIPC_ENABLED
#include "eni/eipc_bridge.h"
#endif
#include <string.h>
#include <stdio.h>

eni_status_t eni_min_service_init(eni_min_service_t *svc, const eni_config_t *cfg,
                                   const eni_provider_ops_t *provider_ops)
{
    if (!svc || !cfg || !provider_ops) return ENI_ERR_INVALID;

    memset(svc, 0, sizeof(*svc));
    memcpy(&svc->config, cfg, sizeof(*cfg));
    svc->state = ENI_MIN_STATE_INIT;

    eni_status_t st;

    const char *prov_name = cfg->provider_count > 0 && cfg->providers[0].name
                          ? cfg->providers[0].name : "default";
    eni_transport_t transport = cfg->provider_count > 0
                              ? cfg->providers[0].transport : ENI_TRANSPORT_UNIX_SOCKET;

    st = eni_min_input_init(&svc->input, provider_ops, prov_name, transport);
    if (st != ENI_OK) return st;

    st = eni_min_normalizer_init(&svc->normalizer, cfg->mode);
    if (st != ENI_OK) return st;

    st = eni_min_filter_init(&svc->filter, cfg->filter.min_confidence,
                              cfg->filter.debounce_ms);
    if (st != ENI_OK) return st;

    st = eni_min_mapper_init(&svc->mapper);
    if (st != ENI_OK) return st;

    st = eni_policy_init(&svc->policy);
    if (st != ENI_OK) return st;

    /* Load policy rules from config */
    for (int i = 0; i < cfg->policy.allow_count; i++) {
        eni_policy_add_rule(&svc->policy, cfg->policy.allow[i],
                            ENI_POLICY_ALLOW, ENI_ACTION_SAFE);
    }
    for (int i = 0; i < cfg->policy.deny_count; i++) {
        eni_policy_add_rule(&svc->policy, cfg->policy.deny[i],
                            ENI_POLICY_DENY, ENI_ACTION_RESTRICTED);
    }

    st = eni_min_tool_bridge_init(&svc->tool_bridge, &svc->policy);
    if (st != ENI_OK) return st;

    ENI_LOG_INFO("min.service", "initialized (provider=%s)", prov_name);
    return ENI_OK;
}

eni_status_t eni_min_service_start(eni_min_service_t *svc)
{
    if (!svc) return ENI_ERR_INVALID;

    eni_status_t st = eni_min_input_connect(&svc->input);
    if (st != ENI_OK) {
        svc->state = ENI_MIN_STATE_ERROR;
        return st;
    }

    svc->state = ENI_MIN_STATE_RUNNING;
    ENI_LOG_INFO("min.service", "started");
    return ENI_OK;
}

eni_status_t eni_min_service_tick(eni_min_service_t *svc)
{
    if (!svc) return ENI_ERR_INVALID;
    if (svc->state != ENI_MIN_STATE_RUNNING) return ENI_ERR_RUNTIME;

    eni_event_t raw_ev;
    eni_status_t st = eni_min_input_poll(&svc->input, &raw_ev);
    if (st == ENI_ERR_TIMEOUT) return ENI_OK; /* no event available */
    if (st != ENI_OK) return st;

    svc->events_processed++;

    /* Normalize */
    eni_event_t norm_ev;
    st = eni_min_normalizer_process(&svc->normalizer, &raw_ev, &norm_ev);
    if (st != ENI_OK) return st;

    /* Filter */
    if (!eni_min_filter_accept(&svc->filter, &norm_ev)) {
        svc->events_filtered++;
        return ENI_OK;
    }

    /* Map intent to tool call */
    eni_tool_call_t call;
    st = eni_min_mapper_resolve(&svc->mapper, &norm_ev, &call);
    if (st != ENI_OK) return st;

#ifdef ENI_EIPC_ENABLED
    if (svc->eipc_bridge) {
        eni_eipc_bridge_t *bridge = (eni_eipc_bridge_t *)svc->eipc_bridge;
        eni_eipc_bridge_send_intent(bridge,
            norm_ev.payload.intent.name,
            norm_ev.payload.intent.confidence);
        if (bridge->mode == ENI_EIPC_MODE_FORWARD) {
            svc->events_executed++;
            return ENI_OK;
        }
    }
#endif

    /* Execute */
    eni_tool_result_t result;
    st = eni_min_tool_bridge_exec(&svc->tool_bridge, &call, &result);
    if (st == ENI_OK) {
        svc->events_executed++;
    }

    return st;
}

eni_status_t eni_min_service_stop(eni_min_service_t *svc)
{
    if (!svc) return ENI_ERR_INVALID;

    eni_min_input_disconnect(&svc->input);
    svc->state = ENI_MIN_STATE_STOPPED;
    ENI_LOG_INFO("min.service", "stopped");
    return ENI_OK;
}

void eni_min_service_shutdown(eni_min_service_t *svc)
{
    if (!svc) return;

    if (svc->state == ENI_MIN_STATE_RUNNING) {
        eni_min_service_stop(svc);
    }
    eni_min_input_shutdown(&svc->input);
    ENI_LOG_INFO("min.service", "shutdown complete");
}

void eni_min_service_stats(const eni_min_service_t *svc)
{
    if (!svc) return;

    const char *state_str;
    switch (svc->state) {
    case ENI_MIN_STATE_INIT:    state_str = "init";    break;
    case ENI_MIN_STATE_RUNNING: state_str = "running"; break;
    case ENI_MIN_STATE_STOPPED: state_str = "stopped"; break;
    case ENI_MIN_STATE_ERROR:   state_str = "error";   break;
    default:                    state_str = "unknown";  break;
    }

    printf("[eni-min] state=%s processed=%llu filtered=%llu executed=%llu\n",
           state_str,
           (unsigned long long)svc->events_processed,
           (unsigned long long)svc->events_filtered,
           (unsigned long long)svc->events_executed);
}
