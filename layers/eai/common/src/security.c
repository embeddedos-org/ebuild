// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eai/security.h"
#include "eai/log.h"
#include <string.h>

#define LOG_MOD "security"

eai_status_t eai_security_ctx_init(eai_security_ctx_t *ctx, const char *identity)
{
    if (!ctx || !identity) return EAI_ERR_INVALID;
    memset(ctx, 0, sizeof(*ctx));
    ctx->identity = identity;
    ctx->granted.count = 0;
    return EAI_OK;
}

eai_status_t eai_security_grant(eai_security_ctx_t *ctx, const char *permission)
{
    if (!ctx || !permission) return EAI_ERR_INVALID;
    if (ctx->granted.count >= EAI_PERM_MAX) {
        EAI_LOG_ERROR(LOG_MOD, "permission set full for %s", ctx->identity);
        return EAI_ERR_NOMEM;
    }

    /* check duplicate */
    for (int i = 0; i < ctx->granted.count; i++) {
        if (strcmp(ctx->granted.permissions[i], permission) == 0)
            return EAI_OK;
    }

    ctx->granted.permissions[ctx->granted.count++] = permission;
    EAI_LOG_DEBUG(LOG_MOD, "granted '%s' to %s", permission, ctx->identity);
    return EAI_OK;
}

bool eai_security_check(const eai_security_ctx_t *ctx, const char *permission)
{
    if (!ctx || !permission) return false;
    for (int i = 0; i < ctx->granted.count; i++) {
        if (strcmp(ctx->granted.permissions[i], permission) == 0)
            return true;
        /* wildcard: "sensor:*" matches "sensor:read" */
        size_t plen = strlen(ctx->granted.permissions[i]);
        if (plen > 1 && ctx->granted.permissions[i][plen - 1] == '*') {
            if (strncmp(ctx->granted.permissions[i], permission, plen - 1) == 0)
                return true;
        }
    }
    return false;
}

bool eai_security_check_tool(const eai_security_ctx_t *ctx,
                             const char **required_perms, int count)
{
    if (!ctx || !required_perms) return false;
    for (int i = 0; i < count; i++) {
        if (!eai_security_check(ctx, required_perms[i])) {
            EAI_LOG_WARN(LOG_MOD, "denied '%s' for %s", required_perms[i], ctx->identity);
            return false;
        }
    }
    return true;
}
