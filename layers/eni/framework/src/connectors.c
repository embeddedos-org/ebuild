// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eni_fw/connectors.h"
#include "eni/log.h"
#include <string.h>

eni_status_t eni_fw_connector_manager_init(eni_fw_connector_manager_t *mgr)
{
    if (!mgr) return ENI_ERR_INVALID;
    memset(mgr, 0, sizeof(*mgr));
    return ENI_OK;
}

eni_status_t eni_fw_connector_manager_add(eni_fw_connector_manager_t *mgr,
                                            const eni_fw_connector_ops_t *ops,
                                            const char *name, const void *config)
{
    if (!mgr || !ops || !name) return ENI_ERR_INVALID;
    if (mgr->count >= ENI_FW_MAX_CONNECTORS) return ENI_ERR_OVERFLOW;

    eni_fw_connector_t *conn = &mgr->connectors[mgr->count];
    size_t len = strlen(name);
    if (len >= ENI_FW_CONNECTOR_NAME_MAX) len = ENI_FW_CONNECTOR_NAME_MAX - 1;
    memcpy(conn->name, name, len);
    conn->name[len] = '\0';
    conn->ops    = ops;
    conn->ctx    = NULL;
    conn->active = false;

    if (ops->init) {
        eni_status_t st = ops->init(conn, config);
        if (st != ENI_OK) return st;
    }

    conn->active = true;
    mgr->count++;
    ENI_LOG_INFO("fw.connectors", "added connector: %s", name);
    return ENI_OK;
}

eni_status_t eni_fw_connector_broadcast(eni_fw_connector_manager_t *mgr,
                                          const eni_event_t *ev)
{
    if (!mgr || !ev) return ENI_ERR_INVALID;

    for (int i = 0; i < mgr->count; i++) {
        eni_fw_connector_t *conn = &mgr->connectors[i];
        if (!conn->active || !conn->ops || !conn->ops->send) continue;

        eni_status_t st = conn->ops->send(conn, ev);
        if (st != ENI_OK) {
            ENI_LOG_WARN("fw.connectors", "send failed on connector: %s", conn->name);
        }
    }

    return ENI_OK;
}

void eni_fw_connector_manager_shutdown(eni_fw_connector_manager_t *mgr)
{
    if (!mgr) return;

    for (int i = 0; i < mgr->count; i++) {
        eni_fw_connector_t *conn = &mgr->connectors[i];
        if (conn->ops && conn->ops->shutdown) {
            conn->ops->shutdown(conn);
        }
        conn->active = false;
    }
    mgr->count = 0;
    ENI_LOG_INFO("fw.connectors", "all connectors shutdown");
}
