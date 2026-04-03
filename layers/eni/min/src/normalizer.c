// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eni_min/normalizer.h"
#include "eni/log.h"
#include <string.h>

eni_status_t eni_min_normalizer_init(eni_min_normalizer_t *norm, eni_mode_t mode)
{
    if (!norm) return ENI_ERR_INVALID;
    norm->mode = mode;
    return ENI_OK;
}

eni_status_t eni_min_normalizer_process(eni_min_normalizer_t *norm,
                                         const eni_event_t *raw,
                                         eni_event_t *normalized)
{
    if (!norm || !raw || !normalized) return ENI_ERR_INVALID;

    memcpy(normalized, raw, sizeof(*normalized));

    /* Clamp confidence to [0.0, 1.0] */
    if (normalized->type == ENI_EVENT_INTENT) {
        if (normalized->payload.intent.confidence < 0.0f)
            normalized->payload.intent.confidence = 0.0f;
        if (normalized->payload.intent.confidence > 1.0f)
            normalized->payload.intent.confidence = 1.0f;
    }

    /* Clamp feature values to [0.0, 1.0] */
    if (normalized->type == ENI_EVENT_FEATURES) {
        for (int i = 0; i < normalized->payload.features.count; i++) {
            float *v = &normalized->payload.features.features[i].value;
            if (*v < 0.0f) *v = 0.0f;
            if (*v > 1.0f) *v = 1.0f;
        }
    }

    /* Refresh timestamp */
    normalized->timestamp = eni_timestamp_now();

    return ENI_OK;
}
