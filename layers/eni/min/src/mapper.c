// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eni_min/mapper.h"
#include "eni/log.h"
#include <string.h>
#include <stdio.h>

eni_status_t eni_min_mapper_init(eni_min_mapper_t *mapper)
{
    if (!mapper) return ENI_ERR_INVALID;
    memset(mapper, 0, sizeof(*mapper));
    return ENI_OK;
}

eni_status_t eni_min_mapper_add(eni_min_mapper_t *mapper,
                                 const char *intent, const char *tool)
{
    if (!mapper || !intent || !tool) return ENI_ERR_INVALID;
    if (mapper->count >= ENI_MAPPER_MAX_ENTRIES) return ENI_ERR_OVERFLOW;

    eni_mapper_entry_t *e = &mapper->entries[mapper->count];

    size_t ilen = strlen(intent);
    if (ilen >= ENI_EVENT_INTENT_MAX) ilen = ENI_EVENT_INTENT_MAX - 1;
    memcpy(e->intent, intent, ilen);
    e->intent[ilen] = '\0';

    size_t tlen = strlen(tool);
    if (tlen >= ENI_TOOL_NAME_MAX) tlen = ENI_TOOL_NAME_MAX - 1;
    memcpy(e->tool, tool, tlen);
    e->tool[tlen] = '\0';

    mapper->count++;
    ENI_LOG_DEBUG("min.mapper", "mapped %s → %s", intent, tool);
    return ENI_OK;
}

eni_status_t eni_min_mapper_resolve(const eni_min_mapper_t *mapper,
                                     const eni_event_t *ev,
                                     eni_tool_call_t *call)
{
    if (!mapper || !ev || !call) return ENI_ERR_INVALID;
    if (ev->type != ENI_EVENT_INTENT) return ENI_ERR_INVALID;

    memset(call, 0, sizeof(*call));

    for (int i = 0; i < mapper->count; i++) {
        if (strcmp(mapper->entries[i].intent, ev->payload.intent.name) == 0) {
            size_t len = strlen(mapper->entries[i].tool);
            if (len >= ENI_TOOL_NAME_MAX) len = ENI_TOOL_NAME_MAX - 1;
            memcpy(call->tool, mapper->entries[i].tool, len);
            call->tool[len] = '\0';
            call->arg_count = 0;
            return ENI_OK;
        }
    }

    ENI_LOG_WARN("min.mapper", "no mapping for intent: %s", ev->payload.intent.name);
    return ENI_ERR_NOT_FOUND;
}

void eni_min_mapper_dump(const eni_min_mapper_t *mapper)
{
    if (!mapper) return;
    printf("[mapper] %d entries:\n", mapper->count);
    for (int i = 0; i < mapper->count; i++) {
        printf("  %s → %s\n", mapper->entries[i].intent, mapper->entries[i].tool);
    }
}
