// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eni/policy.h"
#include "eni/log.h"
#include <string.h>
#include <stdio.h>

eni_status_t eni_policy_init(eni_policy_engine_t *engine)
{
    if (!engine) return ENI_ERR_INVALID;
    memset(engine, 0, sizeof(*engine));
    engine->default_deny = false;
    return ENI_OK;
}

eni_status_t eni_policy_add_rule(eni_policy_engine_t *engine,
                                  const char *action,
                                  eni_policy_verdict_t verdict,
                                  eni_action_class_t action_class)
{
    if (!engine || !action) return ENI_ERR_INVALID;
    if (engine->count >= ENI_POLICY_MAX_RULES) return ENI_ERR_OVERFLOW;

    eni_policy_rule_t *rule = &engine->rules[engine->count];
    size_t len = strlen(action);
    if (len >= ENI_POLICY_ACTION_MAX) len = ENI_POLICY_ACTION_MAX - 1;
    memcpy(rule->action, action, len);
    rule->action[len] = '\0';
    rule->verdict      = verdict;
    rule->action_class = action_class;
    engine->count++;

    ENI_LOG_DEBUG("policy", "added rule: %s → %s",
                  action,
                  verdict == ENI_POLICY_ALLOW ? "allow" :
                  verdict == ENI_POLICY_DENY  ? "deny"  : "confirm");

    return ENI_OK;
}

eni_policy_verdict_t eni_policy_evaluate(const eni_policy_engine_t *engine,
                                          const char *action)
{
    if (!engine || !action) return ENI_POLICY_DENY;

    for (int i = 0; i < engine->count; i++) {
        if (strcmp(engine->rules[i].action, action) == 0) {
            return engine->rules[i].verdict;
        }
    }

    return engine->default_deny ? ENI_POLICY_DENY : ENI_POLICY_ALLOW;
}

eni_status_t eni_policy_set_default_deny(eni_policy_engine_t *engine, bool deny)
{
    if (!engine) return ENI_ERR_INVALID;
    engine->default_deny = deny;
    return ENI_OK;
}

void eni_policy_dump(const eni_policy_engine_t *engine)
{
    if (!engine) return;

    printf("[policy] %d rules (default=%s)\n",
           engine->count, engine->default_deny ? "deny" : "allow");

    for (int i = 0; i < engine->count; i++) {
        const eni_policy_rule_t *r = &engine->rules[i];
        const char *verdict_str =
            r->verdict == ENI_POLICY_ALLOW   ? "allow" :
            r->verdict == ENI_POLICY_DENY    ? "deny"  : "confirm";
        const char *class_str =
            r->action_class == ENI_ACTION_SAFE       ? "safe" :
            r->action_class == ENI_ACTION_CONTROLLED ? "controlled" : "restricted";
        printf("  [%d] %s → %s (%s)\n", i, r->action, verdict_str, class_str);
    }
}
