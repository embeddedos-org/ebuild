// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef ENI_FW_CONNECTORS_H
#define ENI_FW_CONNECTORS_H

#include "eni/common.h"

#define ENI_FW_CONNECTOR_NAME_MAX 64
#define ENI_FW_MAX_CONNECTORS     16

typedef struct eni_fw_connector_s eni_fw_connector_t;

typedef struct {
    const char  *name;
    eni_status_t (*init)(eni_fw_connector_t *conn, const void *config);
    eni_status_t (*send)(eni_fw_connector_t *conn, const eni_event_t *ev);
    eni_status_t (*recv)(eni_fw_connector_t *conn, eni_event_t *ev);
    void         (*shutdown)(eni_fw_connector_t *conn);
} eni_fw_connector_ops_t;

struct eni_fw_connector_s {
    char                          name[ENI_FW_CONNECTOR_NAME_MAX];
    const eni_fw_connector_ops_t *ops;
    void                         *ctx;
    bool                          active;
};

typedef struct {
    eni_fw_connector_t connectors[ENI_FW_MAX_CONNECTORS];
    int                count;
} eni_fw_connector_manager_t;

eni_status_t eni_fw_connector_manager_init(eni_fw_connector_manager_t *mgr);
eni_status_t eni_fw_connector_manager_add(eni_fw_connector_manager_t *mgr,
                                            const eni_fw_connector_ops_t *ops,
                                            const char *name, const void *config);
eni_status_t eni_fw_connector_broadcast(eni_fw_connector_manager_t *mgr,
                                          const eni_event_t *ev);
void         eni_fw_connector_manager_shutdown(eni_fw_connector_manager_t *mgr);

#endif /* ENI_FW_CONNECTORS_H */
