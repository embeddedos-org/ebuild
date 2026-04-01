// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef ENI_FW_OBSERVABILITY_H
#define ENI_FW_OBSERVABILITY_H

#include "eni/common.h"

typedef struct {
    uint64_t events_ingested;
    uint64_t events_routed;
    uint64_t events_executed;
    uint64_t events_denied;
    uint64_t events_dropped;
    uint64_t total_latency_ms;
} eni_fw_metrics_t;

typedef struct {
    eni_timestamp_t timestamp;
    char            action[ENI_POLICY_ACTION_MAX];
    char            source[ENI_EVENT_SOURCE_MAX];
    eni_status_t    result;
} eni_fw_audit_entry_t;

#define ENI_FW_AUDIT_LOG_MAX 512

typedef struct {
    bool                  metrics_enabled;
    bool                  audit_enabled;
    bool                  trace_enabled;
    eni_fw_metrics_t      metrics;
    eni_fw_audit_entry_t  audit_log[ENI_FW_AUDIT_LOG_MAX];
    int                   audit_head;
    int                   audit_count;
} eni_fw_observability_t;

eni_status_t eni_fw_observability_init(eni_fw_observability_t *obs,
                                        bool metrics, bool audit, bool trace);
void         eni_fw_observability_record_event(eni_fw_observability_t *obs);
void         eni_fw_observability_record_exec(eni_fw_observability_t *obs, uint32_t latency_ms);
void         eni_fw_observability_record_denied(eni_fw_observability_t *obs);
void         eni_fw_observability_record_drop(eni_fw_observability_t *obs);
void         eni_fw_observability_audit(eni_fw_observability_t *obs,
                                         const char *action, const char *source,
                                         eni_status_t result);
void         eni_fw_observability_dump_metrics(const eni_fw_observability_t *obs);
void         eni_fw_observability_dump_audit(const eni_fw_observability_t *obs, int last_n);

#endif /* ENI_FW_OBSERVABILITY_H */
