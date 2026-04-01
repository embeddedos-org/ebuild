// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef EAI_MIN_AGENT_H
#define EAI_MIN_AGENT_H

#include "eai/types.h"
#include "eai/tool.h"
#include "eai_min/runtime.h"
#include "eai_min/memory_lite.h"

#define EAI_AGENT_MAX_ITERATIONS 10
#define EAI_AGENT_PROMPT_MAX     4096

typedef enum {
    EAI_AGENT_IDLE,
    EAI_AGENT_THINKING,
    EAI_AGENT_TOOL_CALL,
    EAI_AGENT_DONE,
    EAI_AGENT_ERROR,
} eai_agent_state_t;

typedef struct {
    const char *goal;
    bool        offline_only;
    int         max_iterations;
} eai_agent_task_t;

typedef struct {
    eai_min_runtime_t   *runtime;
    eai_tool_registry_t *tools;
    eai_mem_lite_t      *memory;
    eai_agent_state_t    state;
    int                  iteration;
    char                 last_output[4096];
} eai_min_agent_t;

eai_status_t eai_min_agent_init(eai_min_agent_t *agent,
                                 eai_min_runtime_t *runtime,
                                 eai_tool_registry_t *tools,
                                 eai_mem_lite_t *memory);

eai_status_t eai_min_agent_run(eai_min_agent_t *agent, const eai_agent_task_t *task);
eai_status_t eai_min_agent_step(eai_min_agent_t *agent);
const char  *eai_min_agent_output(const eai_min_agent_t *agent);
void         eai_min_agent_reset(eai_min_agent_t *agent);

#endif /* EAI_MIN_AGENT_H */
