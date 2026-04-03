// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef ENI_MIN_MAPPER_H
#define ENI_MIN_MAPPER_H

#include "eni/common.h"

#define ENI_MAPPER_MAX_ENTRIES 64

typedef struct {
    char intent[ENI_EVENT_INTENT_MAX];
    char tool[ENI_TOOL_NAME_MAX];
} eni_mapper_entry_t;

typedef struct {
    eni_mapper_entry_t entries[ENI_MAPPER_MAX_ENTRIES];
    int                count;
} eni_min_mapper_t;

eni_status_t eni_min_mapper_init(eni_min_mapper_t *mapper);
eni_status_t eni_min_mapper_add(eni_min_mapper_t *mapper,
                                 const char *intent, const char *tool);
eni_status_t eni_min_mapper_resolve(const eni_min_mapper_t *mapper,
                                     const eni_event_t *ev,
                                     eni_tool_call_t *call);
void         eni_min_mapper_dump(const eni_min_mapper_t *mapper);

#endif /* ENI_MIN_MAPPER_H */
