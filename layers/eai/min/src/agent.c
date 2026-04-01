// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eai_min/agent.h"
#include "eai/log.h"
#include <string.h>
#include <stdio.h>

#ifdef _MSC_VER
#define strtok_r strtok_s
#endif

#define LOG_MOD "min-agent"

eai_status_t eai_min_agent_init(eai_min_agent_t *agent,
                                 eai_min_runtime_t *runtime,
                                 eai_tool_registry_t *tools,
                                 eai_mem_lite_t *memory)
{
    if (!agent || !runtime) return EAI_ERR_INVALID;
    memset(agent, 0, sizeof(*agent));
    agent->runtime  = runtime;
    agent->tools    = tools;
    agent->memory   = memory;
    agent->state    = EAI_AGENT_IDLE;
    agent->iteration = 0;
    return EAI_OK;
}

static eai_status_t agent_think(eai_min_agent_t *agent, const char *goal)
{
    char prompt[EAI_AGENT_PROMPT_MAX];
    snprintf(prompt, sizeof(prompt),
             "You are an embedded AI agent. Goal: %s\n"
             "Available tools: ", goal);

    /* append tool names */
    if (agent->tools) {
        for (int i = 0; i < agent->tools->count; i++) {
            size_t plen = strlen(prompt);
            snprintf(prompt + plen, sizeof(prompt) - plen,
                     "%s%s", i > 0 ? ", " : "", agent->tools->tools[i].name);
        }
    }

    /* check memory for context */
    if (agent->memory) {
        const char *ctx = eai_mem_lite_get(agent->memory, "last_context");
        if (ctx) {
            size_t plen = strlen(prompt);
            snprintf(prompt + plen, sizeof(prompt) - plen,
                     "\nPrevious context: %s", ctx);
        }
    }

    char output[4096];
    eai_status_t s = eai_min_runtime_infer(agent->runtime, prompt, output, sizeof(output));
    if (s != EAI_OK) {
        agent->state = EAI_AGENT_ERROR;
        return s;
    }

    strncpy(agent->last_output, output, sizeof(agent->last_output) - 1);
    agent->last_output[sizeof(agent->last_output) - 1] = '\0';

    /* check if output contains tool call pattern "CALL:<tool_name>(<args>)" */
    if (strncmp(output, "CALL:", 5) == 0) {
        agent->state = EAI_AGENT_TOOL_CALL;
    } else {
        agent->state = EAI_AGENT_DONE;
    }

    return EAI_OK;
}

static eai_status_t agent_handle_tool_call(eai_min_agent_t *agent)
{
    if (!agent->tools) {
        agent->state = EAI_AGENT_ERROR;
        return EAI_ERR_NOT_FOUND;
    }

    /* parse "CALL:<tool_name>(<key>=<val>)" */
    char tool_name[EAI_TOOL_NAME_MAX];
    char args_str[1024];

    const char *p = agent->last_output + 5;  /* skip "CALL:" */
    const char *paren = strchr(p, '(');
    if (!paren) {
        agent->state = EAI_AGENT_ERROR;
        return EAI_ERR_INVALID;
    }

    size_t name_len = (size_t)(paren - p);
    if (name_len >= sizeof(tool_name)) name_len = sizeof(tool_name) - 1;
    memcpy(tool_name, p, name_len);
    tool_name[name_len] = '\0';

    eai_tool_t *tool = eai_tool_find(agent->tools, tool_name);
    if (!tool) {
        EAI_LOG_ERROR(LOG_MOD, "tool not found: %s", tool_name);
        agent->state = EAI_AGENT_ERROR;
        return EAI_ERR_NOT_FOUND;
    }

    /* parse arguments from "CALL:tool_name(key=val, key2=val2)" */
    static char key_bufs[EAI_TOOL_MAX_PARAMS][128];
    static char val_bufs[EAI_TOOL_MAX_PARAMS][256];
    eai_kv_t args[EAI_TOOL_MAX_PARAMS];
    int arg_count = 0;

    const char *args_start = paren + 1;
    const char *args_end = strchr(args_start, ')');
    if (args_end && args_end > args_start) {
        size_t args_len = (size_t)(args_end - args_start);
        if (args_len >= sizeof(args_str)) args_len = sizeof(args_str) - 1;
        memcpy(args_str, args_start, args_len);
        args_str[args_len] = '\0';

        char *saveptr = NULL;
        char *token = strtok_r(args_str, ",", &saveptr);
        while (token && arg_count < EAI_TOOL_MAX_PARAMS) {
            while (*token == ' ') token++;
            char *eq = strchr(token, '=');
            if (eq) {
                size_t klen = (size_t)(eq - token);
                while (klen > 0 && token[klen - 1] == ' ') klen--;
                if (klen >= sizeof(key_bufs[0])) klen = sizeof(key_bufs[0]) - 1;
                memcpy(key_bufs[arg_count], token, klen);
                key_bufs[arg_count][klen] = '\0';

                const char *vstart = eq + 1;
                while (*vstart == ' ') vstart++;
                size_t vlen = strlen(vstart);
                while (vlen > 0 && vstart[vlen - 1] == ' ') vlen--;
                if (vlen >= sizeof(val_bufs[0])) vlen = sizeof(val_bufs[0]) - 1;
                memcpy(val_bufs[arg_count], vstart, vlen);
                val_bufs[arg_count][vlen] = '\0';

                args[arg_count].key   = key_bufs[arg_count];
                args[arg_count].value = val_bufs[arg_count];
                arg_count++;
            }
            token = strtok_r(NULL, ",", &saveptr);
        }
    }

    eai_tool_result_t result;
    eai_status_t s = eai_tool_exec(tool, args, arg_count, &result);

    if (s == EAI_OK && result.len > 0) {
        snprintf(agent->last_output, sizeof(agent->last_output),
                 "Tool %s returned: %.*s", tool_name, (int)result.len, result.data);
    }

    agent->state = EAI_AGENT_THINKING;
    return s;
}

eai_status_t eai_min_agent_run(eai_min_agent_t *agent, const eai_agent_task_t *task)
{
    if (!agent || !task || !task->goal) return EAI_ERR_INVALID;

    int max_iter = task->max_iterations > 0 ? task->max_iterations : EAI_AGENT_MAX_ITERATIONS;
    agent->state = EAI_AGENT_THINKING;
    agent->iteration = 0;

    EAI_LOG_INFO(LOG_MOD, "agent starting: goal='%s'", task->goal);

    while (agent->iteration < max_iter) {
        agent->iteration++;

        if (agent->state == EAI_AGENT_THINKING) {
            eai_status_t s = agent_think(agent, task->goal);
            if (s != EAI_OK) return s;
        }

        if (agent->state == EAI_AGENT_TOOL_CALL) {
            eai_status_t s = agent_handle_tool_call(agent);
            if (s != EAI_OK) {
                EAI_LOG_WARN(LOG_MOD, "tool call failed, continuing");
            }
            continue;
        }

        if (agent->state == EAI_AGENT_DONE) {
            EAI_LOG_INFO(LOG_MOD, "agent completed in %d iterations", agent->iteration);

            /* store result in memory */
            if (agent->memory) {
                eai_mem_lite_set(agent->memory, "last_context",
                                 agent->last_output, false);
            }
            return EAI_OK;
        }

        if (agent->state == EAI_AGENT_ERROR) {
            EAI_LOG_ERROR(LOG_MOD, "agent error at iteration %d", agent->iteration);
            return EAI_ERR_RUNTIME;
        }
    }

    EAI_LOG_WARN(LOG_MOD, "agent reached max iterations (%d)", max_iter);
    agent->state = EAI_AGENT_DONE;
    return EAI_OK;
}

eai_status_t eai_min_agent_step(eai_min_agent_t *agent)
{
    if (!agent) return EAI_ERR_INVALID;
    if (agent->state == EAI_AGENT_DONE || agent->state == EAI_AGENT_ERROR)
        return EAI_OK;

    agent->iteration++;
    return agent_think(agent, "continue previous task");
}

const char *eai_min_agent_output(const eai_min_agent_t *agent)
{
    if (!agent) return NULL;
    return agent->last_output;
}

void eai_min_agent_reset(eai_min_agent_t *agent)
{
    if (!agent) return;
    agent->state = EAI_AGENT_IDLE;
    agent->iteration = 0;
    memset(agent->last_output, 0, sizeof(agent->last_output));
}
