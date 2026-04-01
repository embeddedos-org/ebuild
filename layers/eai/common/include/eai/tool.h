// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef EAI_TOOL_H
#define EAI_TOOL_H

#include "eai/types.h"

#define EAI_TOOL_MAX_PARAMS      16
#define EAI_TOOL_MAX_PERMISSIONS 8
#define EAI_TOOL_NAME_MAX        64
#define EAI_TOOL_REGISTRY_MAX    64

typedef enum {
    EAI_PARAM_STRING,
    EAI_PARAM_INT,
    EAI_PARAM_FLOAT,
    EAI_PARAM_BOOL,
    EAI_PARAM_BYTES,
} eai_param_type_t;

typedef struct {
    const char      *name;
    eai_param_type_t type;
    bool             required;
} eai_tool_param_t;

typedef struct {
    char             data[4096];
    size_t           len;
    eai_status_t     status;
} eai_tool_result_t;

typedef eai_status_t (*eai_tool_exec_fn)(
    const eai_kv_t    *args,
    int                arg_count,
    eai_tool_result_t *result
);

typedef struct {
    char              name[EAI_TOOL_NAME_MAX];
    const char       *description;
    eai_tool_param_t  params[EAI_TOOL_MAX_PARAMS];
    int               param_count;
    const char       *permissions[EAI_TOOL_MAX_PERMISSIONS];
    int               permission_count;
    eai_tool_exec_fn  exec;
} eai_tool_t;

typedef struct {
    eai_tool_t tools[EAI_TOOL_REGISTRY_MAX];
    int        count;
} eai_tool_registry_t;

eai_status_t eai_tool_registry_init(eai_tool_registry_t *reg);
eai_status_t eai_tool_register(eai_tool_registry_t *reg, const eai_tool_t *tool);
eai_tool_t  *eai_tool_find(eai_tool_registry_t *reg, const char *name);
eai_status_t eai_tool_exec(eai_tool_t *tool, const eai_kv_t *args, int arg_count, eai_tool_result_t *result);
void         eai_tool_registry_list(const eai_tool_registry_t *reg);

#endif /* EAI_TOOL_H */
