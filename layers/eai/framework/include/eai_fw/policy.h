// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef EAI_FW_POLICY_H
#define EAI_FW_POLICY_H

#include "eai/types.h"

#define EAI_POLICY_MAX_RULES 32

typedef enum {
    EAI_POLICY_ALLOW,
    EAI_POLICY_DENY,
    EAI_POLICY_AUDIT,
} eai_policy_action_t;

typedef struct {
    const char        *subject;   /* "agent", "tool", "connector", "*" */
    const char        *resource;  /* tool name, connector name, or "*" */
    const char        *operation; /* "exec", "read", "write", "connect", "*" */
    eai_policy_action_t action;
} eai_policy_rule_t;

typedef struct {
    eai_policy_rule_t rules[EAI_POLICY_MAX_RULES];
    int               rule_count;
    bool              cloud_fallback;
    bool              allow_external_tools;
    uint32_t          max_inference_ms;
    uint32_t          max_memory_mb;
} eai_fw_policy_t;

eai_status_t      eai_fw_policy_init(eai_fw_policy_t *policy);
eai_status_t      eai_fw_policy_add_rule(eai_fw_policy_t *policy, const eai_policy_rule_t *rule);
eai_policy_action_t eai_fw_policy_check(const eai_fw_policy_t *policy,
                                         const char *subject,
                                         const char *resource,
                                         const char *operation);
void              eai_fw_policy_dump(const eai_fw_policy_t *policy);

#endif /* EAI_FW_POLICY_H */
