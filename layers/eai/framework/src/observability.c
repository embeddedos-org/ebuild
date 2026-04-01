// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eai_fw/observability.h"
#include "eai/log.h"
#include <string.h>
#include <stdio.h>
#include <time.h>

#define LOG_MOD "fw-obs"

#ifdef _WIN32
#include <windows.h>
static uint64_t get_time_us(void)
{
    LARGE_INTEGER freq, counter;
    QueryPerformanceFrequency(&freq);
    QueryPerformanceCounter(&counter);
    return (uint64_t)(counter.QuadPart * 1000000 / freq.QuadPart);
}
#else
#include <sys/time.h>
static uint64_t get_time_us(void)
{
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (uint64_t)tv.tv_sec * 1000000 + (uint64_t)tv.tv_usec;
}
#endif

eai_status_t eai_fw_obs_init(eai_fw_observability_t *obs, bool enabled)
{
    if (!obs) return EAI_ERR_INVALID;
    memset(obs, 0, sizeof(*obs));
    obs->enabled = enabled;
    return EAI_OK;
}

static eai_metric_t *find_or_create_metric(eai_fw_observability_t *obs,
                                            const char *name,
                                            eai_metric_type_t type)
{
    for (int i = 0; i < obs->metric_count; i++) {
        if (strcmp(obs->metrics[i].name, name) == 0) return &obs->metrics[i];
    }
    if (obs->metric_count >= EAI_OBS_MAX_METRICS) return NULL;

    eai_metric_t *m = &obs->metrics[obs->metric_count++];
    strncpy(m->name, name, EAI_OBS_METRIC_NAME - 1);
    m->type = type;
    m->value = 0;
    m->timestamp = (uint64_t)time(NULL);
    return m;
}

eai_status_t eai_fw_obs_counter_inc(eai_fw_observability_t *obs, const char *name, double val)
{
    if (!obs || !obs->enabled || !name) return EAI_ERR_INVALID;
    eai_metric_t *m = find_or_create_metric(obs, name, EAI_METRIC_COUNTER);
    if (!m) return EAI_ERR_NOMEM;
    m->value += val;
    m->timestamp = (uint64_t)time(NULL);
    return EAI_OK;
}

eai_status_t eai_fw_obs_gauge_set(eai_fw_observability_t *obs, const char *name, double val)
{
    if (!obs || !obs->enabled || !name) return EAI_ERR_INVALID;
    eai_metric_t *m = find_or_create_metric(obs, name, EAI_METRIC_GAUGE);
    if (!m) return EAI_ERR_NOMEM;
    m->value = val;
    m->timestamp = (uint64_t)time(NULL);
    return EAI_OK;
}

eai_status_t eai_fw_obs_span_start(eai_fw_observability_t *obs, const char *name,
                                    const char *parent)
{
    if (!obs || !obs->enabled || !name) return EAI_ERR_INVALID;
    if (obs->span_count >= EAI_OBS_MAX_SPANS) return EAI_ERR_NOMEM;

    eai_trace_span_t *span = &obs->spans[obs->span_count++];
    strncpy(span->name, name, EAI_OBS_SPAN_NAME - 1);
    span->start_us = get_time_us();
    span->end_us = 0;
    span->active = true;
    span->parent = parent;
    return EAI_OK;
}

eai_status_t eai_fw_obs_span_end(eai_fw_observability_t *obs, const char *name)
{
    if (!obs || !obs->enabled || !name) return EAI_ERR_INVALID;

    for (int i = obs->span_count - 1; i >= 0; i--) {
        if (obs->spans[i].active && strcmp(obs->spans[i].name, name) == 0) {
            obs->spans[i].end_us = get_time_us();
            obs->spans[i].active = false;
            EAI_LOG_DEBUG(LOG_MOD, "span '%s' duration=%llu us",
                          name, (unsigned long long)(obs->spans[i].end_us - obs->spans[i].start_us));
            return EAI_OK;
        }
    }
    return EAI_ERR_NOT_FOUND;
}

void eai_fw_obs_dump_metrics(const eai_fw_observability_t *obs)
{
    if (!obs) return;
    static const char *type_names[] = {"counter", "gauge", "histogram"};
    printf("Metrics (%d):\n", obs->metric_count);
    for (int i = 0; i < obs->metric_count; i++) {
        printf("  [%s] %s = %.4f\n",
               type_names[obs->metrics[i].type],
               obs->metrics[i].name,
               obs->metrics[i].value);
    }
}

void eai_fw_obs_dump_spans(const eai_fw_observability_t *obs)
{
    if (!obs) return;
    printf("Trace spans (%d):\n", obs->span_count);
    for (int i = 0; i < obs->span_count; i++) {
        uint64_t dur = obs->spans[i].end_us > obs->spans[i].start_us
                     ? obs->spans[i].end_us - obs->spans[i].start_us : 0;
        printf("  %s: %llu us %s%s%s\n",
               obs->spans[i].name,
               (unsigned long long)dur,
               obs->spans[i].active ? "(active)" : "(done)",
               obs->spans[i].parent ? " parent=" : "",
               obs->spans[i].parent ? obs->spans[i].parent : "");
    }
}
