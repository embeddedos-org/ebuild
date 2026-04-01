// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eai/tool.h"
#include "eai/log.h"
#include <string.h>
#include <stdio.h>

#define LOG_MOD "tool-reg"

eai_status_t eai_tool_registry_init(eai_tool_registry_t *reg)
{
    if (!reg) return EAI_ERR_INVALID;
    memset(reg, 0, sizeof(*reg));
    return EAI_OK;
}

eai_status_t eai_tool_register(eai_tool_registry_t *reg, const eai_tool_t *tool)
{
    if (!reg || !tool) return EAI_ERR_INVALID;
    if (reg->count >= EAI_TOOL_REGISTRY_MAX) {
        EAI_LOG_ERROR(LOG_MOD, "registry full, cannot register: %s", tool->name);
        return EAI_ERR_NOMEM;
    }

    /* check for duplicates */
    for (int i = 0; i < reg->count; i++) {
        if (strcmp(reg->tools[i].name, tool->name) == 0) {
            EAI_LOG_WARN(LOG_MOD, "tool already registered: %s", tool->name);
            return EAI_ERR_INVALID;
        }
    }

    memcpy(&reg->tools[reg->count], tool, sizeof(eai_tool_t));
    reg->count++;
    EAI_LOG_DEBUG(LOG_MOD, "registered tool: %s", tool->name);
    return EAI_OK;
}

eai_tool_t *eai_tool_find(eai_tool_registry_t *reg, const char *name)
{
    if (!reg || !name) return NULL;
    for (int i = 0; i < reg->count; i++) {
        if (strcmp(reg->tools[i].name, name) == 0) {
            return &reg->tools[i];
        }
    }
    return NULL;
}

eai_status_t eai_tool_exec(eai_tool_t *tool, const eai_kv_t *args, int arg_count,
                           eai_tool_result_t *result)
{
    if (!tool || !result) return EAI_ERR_INVALID;
    if (!tool->exec) {
        EAI_LOG_ERROR(LOG_MOD, "tool %s has no exec function", tool->name);
        return EAI_ERR_UNSUPPORTED;
    }

    memset(result, 0, sizeof(*result));
    EAI_LOG_DEBUG(LOG_MOD, "executing tool: %s", tool->name);
    eai_status_t s = tool->exec(args, arg_count, result);
    result->status = s;
    return s;
}

void eai_tool_registry_list(const eai_tool_registry_t *reg)
{
    if (!reg) return;
    printf("Registered tools (%d):\n", reg->count);
    for (int i = 0; i < reg->count; i++) {
        printf("  [%d] %s", i, reg->tools[i].name);
        if (reg->tools[i].description)
            printf(" — %s", reg->tools[i].description);
        printf("\n");
    }
}
