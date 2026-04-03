// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eni_fw/provider_manager.h"
#include "eni/log.h"
#include <string.h>

eni_status_t eni_fw_provider_manager_init(eni_fw_provider_manager_t *mgr)
{
    if (!mgr) return ENI_ERR_INVALID;
    memset(mgr, 0, sizeof(*mgr));
    return ENI_OK;
}

eni_status_t eni_fw_provider_manager_add(eni_fw_provider_manager_t *mgr,
                                          const eni_provider_ops_t *ops,
                                          const char *name,
                                          const void *config)
{
    if (!mgr || !ops || !name) return ENI_ERR_INVALID;
    if (mgr->count >= ENI_FW_MAX_PROVIDERS) return ENI_ERR_OVERFLOW;

    eni_status_t st = eni_provider_init(&mgr->providers[mgr->count], ops, name, config);
    if (st == ENI_OK) {
        mgr->count++;
        ENI_LOG_INFO("fw.providers", "added provider: %s (total=%d)", name, mgr->count);
    }
    return st;
}

eni_status_t eni_fw_provider_manager_start_all(eni_fw_provider_manager_t *mgr)
{
    if (!mgr) return ENI_ERR_INVALID;

    mgr->active_count = 0;
    for (int i = 0; i < mgr->count; i++) {
        eni_status_t st = eni_provider_start(&mgr->providers[i]);
        if (st == ENI_OK) {
            mgr->active_count++;
        } else {
            ENI_LOG_WARN("fw.providers", "failed to start provider: %s",
                         mgr->providers[i].name);
        }
    }

    ENI_LOG_INFO("fw.providers", "started %d/%d providers",
                 mgr->active_count, mgr->count);
    return mgr->active_count > 0 ? ENI_OK : ENI_ERR_PROVIDER;
}

eni_status_t eni_fw_provider_manager_stop_all(eni_fw_provider_manager_t *mgr)
{
    if (!mgr) return ENI_ERR_INVALID;

    for (int i = 0; i < mgr->count; i++) {
        eni_provider_stop(&mgr->providers[i]);
    }
    mgr->active_count = 0;
    ENI_LOG_INFO("fw.providers", "all providers stopped");
    return ENI_OK;
}

eni_status_t eni_fw_provider_manager_poll_any(eni_fw_provider_manager_t *mgr,
                                               eni_event_t *ev, int *provider_index)
{
    if (!mgr || !ev) return ENI_ERR_INVALID;

    for (int i = 0; i < mgr->count; i++) {
        if (!mgr->providers[i].running) continue;

        eni_status_t st = eni_provider_poll(&mgr->providers[i], ev);
        if (st == ENI_OK) {
            if (provider_index) *provider_index = i;
            return ENI_OK;
        }
    }

    return ENI_ERR_TIMEOUT;
}

void eni_fw_provider_manager_shutdown(eni_fw_provider_manager_t *mgr)
{
    if (!mgr) return;

    for (int i = 0; i < mgr->count; i++) {
        eni_provider_shutdown(&mgr->providers[i]);
    }
    mgr->count = 0;
    mgr->active_count = 0;
}
