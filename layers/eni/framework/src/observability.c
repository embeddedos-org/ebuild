// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eni_fw/observability.h"
#include "eni/log.h"
#include <string.h>
#include <stdio.h>

eni_status_t eni_fw_observability_init(eni_fw_observability_t *obs,
                                        bool metrics, bool audit, bool trace)
{
    if (!obs) return ENI_ERR_INVALID;
    memset(obs, 0, sizeof(*obs));
    obs->metrics_enabled = metrics;
    obs->audit_enabled   = audit;
    obs->trace_enabled   = trace;
    return ENI_OK;
}

void eni_fw_observability_record_event(eni_fw_observability_t *obs)
{
    if (!obs || !obs->metrics_enabled) return;
    obs->metrics.events_ingested++;
}

void eni_fw_observability_record_exec(eni_fw_observability_t *obs, uint32_t latency_ms)
{
    if (!obs || !obs->metrics_enabled) return;
    obs->metrics.events_executed++;
    obs->metrics.total_latency_ms += latency_ms;
}

void eni_fw_observability_record_denied(eni_fw_observability_t *obs)
{
    if (!obs || !obs->metrics_enabled) return;
    obs->metrics.events_denied++;
}

void eni_fw_observability_record_drop(eni_fw_observability_t *obs)
{
    if (!obs || !obs->metrics_enabled) return;
    obs->metrics.events_dropped++;
}

void eni_fw_observability_audit(eni_fw_observability_t *obs,
                                 const char *action, const char *source,
                                 eni_status_t result)
{
    if (!obs || !obs->audit_enabled) return;

    int idx = (obs->audit_head + obs->audit_count) % ENI_FW_AUDIT_LOG_MAX;
    if (obs->audit_count >= ENI_FW_AUDIT_LOG_MAX) {
        obs->audit_head = (obs->audit_head + 1) % ENI_FW_AUDIT_LOG_MAX;
    } else {
        obs->audit_count++;
    }

    eni_fw_audit_entry_t *entry = &obs->audit_log[idx];
    entry->timestamp = eni_timestamp_now();
    entry->result    = result;

    if (action) {
        size_t len = strlen(action);
        if (len >= ENI_POLICY_ACTION_MAX) len = ENI_POLICY_ACTION_MAX - 1;
        memcpy(entry->action, action, len);
        entry->action[len] = '\0';
    } else {
        entry->action[0] = '\0';
    }

    if (source) {
        size_t len = strlen(source);
        if (len >= ENI_EVENT_SOURCE_MAX) len = ENI_EVENT_SOURCE_MAX - 1;
        memcpy(entry->source, source, len);
        entry->source[len] = '\0';
    } else {
        entry->source[0] = '\0';
    }
}

void eni_fw_observability_dump_metrics(const eni_fw_observability_t *obs)
{
    if (!obs) return;

    const eni_fw_metrics_t *m = &obs->metrics;
    printf("[metrics] ingested=%llu routed=%llu executed=%llu denied=%llu dropped=%llu avg_latency=%llu ms\n",
           (unsigned long long)m->events_ingested,
           (unsigned long long)m->events_routed,
           (unsigned long long)m->events_executed,
           (unsigned long long)m->events_denied,
           (unsigned long long)m->events_dropped,
           m->events_executed > 0
               ? (unsigned long long)(m->total_latency_ms / m->events_executed)
               : 0ULL);
}

void eni_fw_observability_dump_audit(const eni_fw_observability_t *obs, int last_n)
{
    if (!obs || obs->audit_count == 0) return;

    int start = 0;
    int count = obs->audit_count;
    if (last_n > 0 && last_n < count) {
        start = count - last_n;
        count = last_n;
    }

    printf("[audit] last %d entries:\n", count);
    for (int i = 0; i < count; i++) {
        int idx = (obs->audit_head + start + i) % ENI_FW_AUDIT_LOG_MAX;
        const eni_fw_audit_entry_t *e = &obs->audit_log[idx];
        printf("  [%llu.%u] %s from %s → %s\n",
               (unsigned long long)e->timestamp.sec,
               e->timestamp.nsec,
               e->action, e->source,
               eni_status_str(e->result));
    }
}
