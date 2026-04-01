// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef EAI_SECURITY_H
#define EAI_SECURITY_H

#include "eai/types.h"

#define EAI_PERM_MAX 32

typedef struct {
    const char *permissions[EAI_PERM_MAX];
    int         count;
} eai_permission_set_t;

typedef struct {
    const char         *identity;
    eai_permission_set_t granted;
} eai_security_ctx_t;

eai_status_t eai_security_ctx_init(eai_security_ctx_t *ctx, const char *identity);
eai_status_t eai_security_grant(eai_security_ctx_t *ctx, const char *permission);
bool         eai_security_check(const eai_security_ctx_t *ctx, const char *permission);
bool         eai_security_check_tool(const eai_security_ctx_t *ctx,
                                     const char **required_perms, int count);

#endif /* EAI_SECURITY_H */
