// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef ENI_POLICY_H
#define ENI_POLICY_H

#include "eni/types.h"

#define ENI_POLICY_MAX_RULES 64
#define ENI_POLICY_ACTION_MAX 64

typedef enum {
    ENI_ACTION_SAFE,
    ENI_ACTION_CONTROLLED,
    ENI_ACTION_RESTRICTED,
} eni_action_class_t;

typedef enum {
    ENI_POLICY_ALLOW,
    ENI_POLICY_DENY,
    ENI_POLICY_CONFIRM,
} eni_policy_verdict_t;

typedef struct {
    char                action[ENI_POLICY_ACTION_MAX];
    eni_policy_verdict_t verdict;
    eni_action_class_t  action_class;
} eni_policy_rule_t;

typedef struct {
    eni_policy_rule_t rules[ENI_POLICY_MAX_RULES];
    int               count;
    bool              default_deny;
} eni_policy_engine_t;

eni_status_t        eni_policy_init(eni_policy_engine_t *engine);
eni_status_t        eni_policy_add_rule(eni_policy_engine_t *engine,
                                        const char *action,
                                        eni_policy_verdict_t verdict,
                                        eni_action_class_t action_class);
eni_policy_verdict_t eni_policy_evaluate(const eni_policy_engine_t *engine,
                                         const char *action);
eni_status_t        eni_policy_set_default_deny(eni_policy_engine_t *engine, bool deny);
void                eni_policy_dump(const eni_policy_engine_t *engine);

#endif /* ENI_POLICY_H */
