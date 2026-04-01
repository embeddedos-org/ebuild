// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eni/provider_contract.h"
#include "eni/log.h"
#include <string.h>

eni_status_t eni_provider_init(eni_provider_t *prov, const eni_provider_ops_t *ops,
                                const char *name, const void *config)
{
    if (!prov || !ops || !name) return ENI_ERR_INVALID;

    memset(prov, 0, sizeof(*prov));
    size_t len = strlen(name);
    if (len >= ENI_PROVIDER_NAME_MAX) len = ENI_PROVIDER_NAME_MAX - 1;
    memcpy(prov->name, name, len);
    prov->name[len] = '\0';
    prov->ops     = ops;
    prov->running = false;

    if (ops->init) {
        return ops->init(prov, config);
    }
    return ENI_OK;
}

eni_status_t eni_provider_start(eni_provider_t *prov)
{
    if (!prov || !prov->ops) return ENI_ERR_INVALID;
    if (prov->running) return ENI_OK;

    eni_status_t st = ENI_OK;
    if (prov->ops->start) {
        st = prov->ops->start(prov);
    }
    if (st == ENI_OK) {
        prov->running = true;
        ENI_LOG_INFO("provider", "started: %s", prov->name);
    }
    return st;
}

eni_status_t eni_provider_poll(eni_provider_t *prov, eni_event_t *ev)
{
    if (!prov || !ev) return ENI_ERR_INVALID;
    if (!prov->running) return ENI_ERR_RUNTIME;
    if (!prov->ops || !prov->ops->poll) return ENI_ERR_UNSUPPORTED;

    return prov->ops->poll(prov, ev);
}

eni_status_t eni_provider_stop(eni_provider_t *prov)
{
    if (!prov || !prov->ops) return ENI_ERR_INVALID;
    if (!prov->running) return ENI_OK;

    eni_status_t st = ENI_OK;
    if (prov->ops->stop) {
        st = prov->ops->stop(prov);
    }
    prov->running = false;
    ENI_LOG_INFO("provider", "stopped: %s", prov->name);
    return st;
}

void eni_provider_shutdown(eni_provider_t *prov)
{
    if (!prov || !prov->ops) return;

    if (prov->running) {
        eni_provider_stop(prov);
    }
    if (prov->ops->shutdown) {
        prov->ops->shutdown(prov);
    }
    ENI_LOG_INFO("provider", "shutdown: %s", prov->name);
}
