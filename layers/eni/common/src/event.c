// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eni/event.h"
#include "eni/log.h"
#include <string.h>
#include <stdio.h>

static uint32_t s_event_id_counter = 0;

eni_status_t eni_event_init(eni_event_t *ev, eni_event_type_t type, const char *source)
{
    if (!ev || !source) return ENI_ERR_INVALID;

    memset(ev, 0, sizeof(*ev));
    ev->id      = ++s_event_id_counter;
    ev->version = 1;
    ev->type    = type;
    ev->timestamp = eni_timestamp_now();

    size_t slen = strlen(source);
    if (slen >= ENI_EVENT_SOURCE_MAX) slen = ENI_EVENT_SOURCE_MAX - 1;
    memcpy(ev->source, source, slen);
    ev->source[slen] = '\0';

    return ENI_OK;
}

eni_status_t eni_event_set_intent(eni_event_t *ev, const char *intent, float confidence)
{
    if (!ev || !intent) return ENI_ERR_INVALID;
    if (ev->type != ENI_EVENT_INTENT) return ENI_ERR_INVALID;

    size_t len = strlen(intent);
    if (len >= ENI_EVENT_INTENT_MAX) len = ENI_EVENT_INTENT_MAX - 1;
    memcpy(ev->payload.intent.name, intent, len);
    ev->payload.intent.name[len] = '\0';
    ev->payload.intent.confidence = confidence;

    return ENI_OK;
}

eni_status_t eni_event_add_feature(eni_event_t *ev, const char *name, float value)
{
    if (!ev || !name) return ENI_ERR_INVALID;
    if (ev->type != ENI_EVENT_FEATURES) return ENI_ERR_INVALID;

    eni_feature_set_t *fs = &ev->payload.features;
    if (fs->count >= ENI_EVENT_FEATURES_MAX) return ENI_ERR_OVERFLOW;

    eni_feature_t *f = &fs->features[fs->count];
    size_t len = strlen(name);
    if (len >= sizeof(f->name)) len = sizeof(f->name) - 1;
    memcpy(f->name, name, len);
    f->name[len] = '\0';
    f->value = value;
    fs->count++;

    return ENI_OK;
}

eni_status_t eni_event_set_raw(eni_event_t *ev, const uint8_t *data, size_t len)
{
    if (!ev || !data) return ENI_ERR_INVALID;
    if (ev->type != ENI_EVENT_RAW) return ENI_ERR_INVALID;
    if (len > ENI_EVENT_PAYLOAD_MAX) return ENI_ERR_OVERFLOW;

    memcpy(ev->payload.raw.data, data, len);
    ev->payload.raw.len = len;

    return ENI_OK;
}

void eni_event_print(const eni_event_t *ev)
{
    if (!ev) return;

    const char *type_str = "unknown";
    switch (ev->type) {
    case ENI_EVENT_INTENT:   type_str = "intent";   break;
    case ENI_EVENT_FEATURES: type_str = "features"; break;
    case ENI_EVENT_RAW:      type_str = "raw";      break;
    case ENI_EVENT_CONTROL:  type_str = "control";  break;
    }

    printf("[event] id=%u v=%u type=%s source=%s\n",
           ev->id, ev->version, type_str, ev->source);

    if (ev->type == ENI_EVENT_INTENT) {
        printf("  intent: %s (confidence=%.2f)\n",
               ev->payload.intent.name, ev->payload.intent.confidence);
    } else if (ev->type == ENI_EVENT_FEATURES) {
        printf("  features (%d):\n", ev->payload.features.count);
        for (int i = 0; i < ev->payload.features.count; i++) {
            printf("    %s = %.4f\n",
                   ev->payload.features.features[i].name,
                   ev->payload.features.features[i].value);
        }
    } else if (ev->type == ENI_EVENT_RAW) {
        printf("  raw: %zu bytes\n", ev->payload.raw.len);
    }
}
