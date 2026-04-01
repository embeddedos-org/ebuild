// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef ENI_MIN_FILTER_H
#define ENI_MIN_FILTER_H

#include "eni/common.h"

typedef struct {
    float       min_confidence;
    uint32_t    debounce_ms;
    eni_timestamp_t last_event_time;
    char        last_intent[ENI_EVENT_INTENT_MAX];
} eni_min_filter_t;

eni_status_t eni_min_filter_init(eni_min_filter_t *filter,
                                  float min_confidence, uint32_t debounce_ms);
bool         eni_min_filter_accept(eni_min_filter_t *filter, const eni_event_t *ev);

#endif /* ENI_MIN_FILTER_H */
