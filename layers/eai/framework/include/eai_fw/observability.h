// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef EAI_FW_OBSERVABILITY_H
#define EAI_FW_OBSERVABILITY_H

#include "eai/types.h"

#define EAI_OBS_MAX_METRICS   128
#define EAI_OBS_METRIC_NAME   64
#define EAI_OBS_MAX_SPANS     256
#define EAI_OBS_SPAN_NAME     64

typedef enum {
    EAI_METRIC_COUNTER,
    EAI_METRIC_GAUGE,
    EAI_METRIC_HISTOGRAM,
} eai_metric_type_t;

typedef struct {
    char              name[EAI_OBS_METRIC_NAME];
    eai_metric_type_t type;
    double            value;
    uint64_t          timestamp;
    const char       *labels;
} eai_metric_t;

typedef struct {
    char     name[EAI_OBS_SPAN_NAME];
    uint64_t start_us;
    uint64_t end_us;
    bool     active;
    const char *parent;
} eai_trace_span_t;

typedef struct {
    eai_metric_t     metrics[EAI_OBS_MAX_METRICS];
    int              metric_count;
    eai_trace_span_t spans[EAI_OBS_MAX_SPANS];
    int              span_count;
    bool             enabled;
    const char      *export_endpoint;
} eai_fw_observability_t;

eai_status_t eai_fw_obs_init(eai_fw_observability_t *obs, bool enabled);
eai_status_t eai_fw_obs_counter_inc(eai_fw_observability_t *obs, const char *name, double val);
eai_status_t eai_fw_obs_gauge_set(eai_fw_observability_t *obs, const char *name, double val);
eai_status_t eai_fw_obs_span_start(eai_fw_observability_t *obs, const char *name, const char *parent);
eai_status_t eai_fw_obs_span_end(eai_fw_observability_t *obs, const char *name);
void         eai_fw_obs_dump_metrics(const eai_fw_observability_t *obs);
void         eai_fw_obs_dump_spans(const eai_fw_observability_t *obs);

#endif /* EAI_FW_OBSERVABILITY_H */
