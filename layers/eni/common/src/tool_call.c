// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eni/tool_call.h"
#include "eni/log.h"
#include <string.h>
#include <stdio.h>

eni_status_t eni_tool_registry_init(eni_tool_registry_t *reg)
{
    if (!reg) return ENI_ERR_INVALID;
    memset(reg, 0, sizeof(*reg));
    return ENI_OK;
}

eni_status_t eni_tool_register(eni_tool_registry_t *reg, const eni_tool_entry_t *entry)
{
    if (!reg || !entry || !entry->exec) return ENI_ERR_INVALID;
    if (reg->count >= ENI_TOOL_REGISTRY_MAX) return ENI_ERR_OVERFLOW;

    eni_tool_entry_t *dst = &reg->tools[reg->count];
    size_t len = strlen(entry->name);
    if (len >= ENI_TOOL_NAME_MAX) len = ENI_TOOL_NAME_MAX - 1;
    memcpy(dst->name, entry->name, len);
    dst->name[len] = '\0';
    dst->description = entry->description;
    dst->exec        = entry->exec;
    reg->count++;

    ENI_LOG_DEBUG("tool_reg", "registered tool: %s", dst->name);
    return ENI_OK;
}

eni_tool_entry_t *eni_tool_find(eni_tool_registry_t *reg, const char *name)
{
    if (!reg || !name) return NULL;
    for (int i = 0; i < reg->count; i++) {
        if (strcmp(reg->tools[i].name, name) == 0) {
            return &reg->tools[i];
        }
    }
    return NULL;
}

eni_status_t eni_tool_exec(eni_tool_registry_t *reg, const eni_tool_call_t *call,
                            eni_tool_result_t *result)
{
    if (!reg || !call || !result) return ENI_ERR_INVALID;

    eni_tool_entry_t *entry = eni_tool_find(reg, call->tool);
    if (!entry) {
        ENI_LOG_WARN("tool_reg", "tool not found: %s", call->tool);
        return ENI_ERR_NOT_FOUND;
    }

    memset(result, 0, sizeof(*result));
    eni_timestamp_t start = eni_timestamp_now();

    eni_status_t st = entry->exec(call, result);
    result->status = st;

    eni_timestamp_t end = eni_timestamp_now();
    uint64_t elapsed_ms = (end.sec - start.sec) * 1000 +
                          (end.nsec > start.nsec
                               ? (end.nsec - start.nsec) / 1000000
                               : 0);
    result->latency_ms = (uint32_t)elapsed_ms;

    ENI_LOG_DEBUG("tool_reg", "exec %s → %s (%u ms)",
                  call->tool, eni_status_str(st), result->latency_ms);
    return st;
}

void eni_tool_registry_list(const eni_tool_registry_t *reg)
{
    if (!reg) return;
    printf("[tool_registry] %d tools:\n", reg->count);
    for (int i = 0; i < reg->count; i++) {
        printf("  [%d] %s — %s\n", i, reg->tools[i].name,
               reg->tools[i].description ? reg->tools[i].description : "(no description)");
    }
}
