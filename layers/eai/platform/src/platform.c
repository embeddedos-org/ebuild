// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eai/platform.h"
#include "eai/log.h"
#include <string.h>

#define LOG_MOD "platform"

eai_status_t eai_platform_init(eai_platform_t *plat, const eai_platform_ops_t *ops)
{
    if (!plat || !ops) return EAI_ERR_INVALID;
    memset(plat, 0, sizeof(*plat));
    plat->ops = ops;
    plat->initialized = false;

    eai_status_t s = ops->init(plat);
    if (s == EAI_OK) {
        plat->initialized = true;
        EAI_LOG_INFO(LOG_MOD, "initialized platform: %s", ops->name);
    }
    return s;
}

eai_status_t eai_platform_detect(eai_platform_t *plat)
{
    if (!plat) return EAI_ERR_INVALID;

#ifdef _WIN32
    return eai_platform_init(plat, &eai_platform_windows_ops);
#else
    return eai_platform_init(plat, &eai_platform_linux_ops);
#endif
}

void eai_platform_shutdown(eai_platform_t *plat)
{
    if (!plat || !plat->initialized) return;
    if (plat->ops->shutdown) plat->ops->shutdown(plat);
    plat->initialized = false;
    EAI_LOG_INFO(LOG_MOD, "platform shut down");
}
