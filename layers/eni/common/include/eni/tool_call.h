// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef ENI_TOOL_CALL_H
#define ENI_TOOL_CALL_H

#include "eni/types.h"

#define ENI_TOOL_NAME_MAX   64
#define ENI_TOOL_MAX_ARGS   16
#define ENI_TOOL_RESULT_MAX 4096

typedef struct {
    char     tool[ENI_TOOL_NAME_MAX];
    eni_kv_t args[ENI_TOOL_MAX_ARGS];
    int      arg_count;
} eni_tool_call_t;

typedef struct {
    char         data[ENI_TOOL_RESULT_MAX];
    size_t       len;
    eni_status_t status;
    uint32_t     latency_ms;
} eni_tool_result_t;

typedef eni_status_t (*eni_tool_exec_fn)(
    const eni_tool_call_t *call,
    eni_tool_result_t     *result
);

typedef struct {
    char            name[ENI_TOOL_NAME_MAX];
    const char     *description;
    eni_tool_exec_fn exec;
} eni_tool_entry_t;

#define ENI_TOOL_REGISTRY_MAX 64

typedef struct {
    eni_tool_entry_t tools[ENI_TOOL_REGISTRY_MAX];
    int              count;
} eni_tool_registry_t;

eni_status_t     eni_tool_registry_init(eni_tool_registry_t *reg);
eni_status_t     eni_tool_register(eni_tool_registry_t *reg, const eni_tool_entry_t *entry);
eni_tool_entry_t *eni_tool_find(eni_tool_registry_t *reg, const char *name);
eni_status_t     eni_tool_exec(eni_tool_registry_t *reg, const eni_tool_call_t *call,
                               eni_tool_result_t *result);
void             eni_tool_registry_list(const eni_tool_registry_t *reg);

#endif /* ENI_TOOL_CALL_H */
