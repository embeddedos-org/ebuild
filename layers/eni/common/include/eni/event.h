// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef ENI_EVENT_H
#define ENI_EVENT_H

#include "eni/types.h"

#define ENI_EVENT_INTENT_MAX    64
#define ENI_EVENT_PAYLOAD_MAX   4096
#define ENI_EVENT_FEATURES_MAX  32
#define ENI_EVENT_SOURCE_MAX    64

typedef enum {
    ENI_EVENT_INTENT,
    ENI_EVENT_FEATURES,
    ENI_EVENT_RAW,
    ENI_EVENT_CONTROL,
} eni_event_type_t;

typedef struct {
    char  name[ENI_EVENT_INTENT_MAX];
    float confidence;
} eni_intent_t;

typedef struct {
    char  name[32];
    float value;
} eni_feature_t;

typedef struct {
    eni_feature_t features[ENI_EVENT_FEATURES_MAX];
    int           count;
} eni_feature_set_t;

typedef struct {
    uint8_t data[ENI_EVENT_PAYLOAD_MAX];
    size_t  len;
} eni_raw_payload_t;

typedef struct {
    uint32_t         id;
    uint32_t         version;
    eni_event_type_t type;
    eni_timestamp_t  timestamp;
    char             source[ENI_EVENT_SOURCE_MAX];

    union {
        eni_intent_t      intent;
        eni_feature_set_t features;
        eni_raw_payload_t raw;
    } payload;
} eni_event_t;

eni_status_t eni_event_init(eni_event_t *ev, eni_event_type_t type, const char *source);
eni_status_t eni_event_set_intent(eni_event_t *ev, const char *intent, float confidence);
eni_status_t eni_event_add_feature(eni_event_t *ev, const char *name, float value);
eni_status_t eni_event_set_raw(eni_event_t *ev, const uint8_t *data, size_t len);
void         eni_event_print(const eni_event_t *ev);

#endif /* ENI_EVENT_H */
