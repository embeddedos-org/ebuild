// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef EAI_FW_CONNECTOR_H
#define EAI_FW_CONNECTOR_H

#include "eai/types.h"

#define EAI_CONNECTOR_MAX       16
#define EAI_CONNECTOR_NAME_MAX  32
#define EAI_CONNECTOR_BUF_MAX   4096

typedef enum {
    EAI_CONN_MQTT,
    EAI_CONN_OPCUA,
    EAI_CONN_MODBUS,
    EAI_CONN_CAN,
    EAI_CONN_CUSTOM,
} eai_connector_type_t;

typedef enum {
    EAI_CONN_DISCONNECTED,
    EAI_CONN_CONNECTING,
    EAI_CONN_CONNECTED,
    EAI_CONN_ERROR,
} eai_connector_state_t;

typedef struct eai_fw_connector_s eai_fw_connector_t;

typedef struct {
    const char        *name;
    eai_connector_type_t type;
    eai_status_t (*connect)(eai_fw_connector_t *conn, const eai_kv_t *params, int param_count);
    eai_status_t (*disconnect)(eai_fw_connector_t *conn);
    eai_status_t (*read)(eai_fw_connector_t *conn, const char *address,
                          void *buf, size_t buf_size, size_t *bytes_read);
    eai_status_t (*write)(eai_fw_connector_t *conn, const char *address,
                           const void *data, size_t data_len);
    eai_status_t (*subscribe)(eai_fw_connector_t *conn, const char *topic,
                               void (*callback)(const char *topic, const void *data, size_t len));
} eai_connector_ops_t;

struct eai_fw_connector_s {
    char                    name[EAI_CONNECTOR_NAME_MAX];
    const eai_connector_ops_t *ops;
    eai_connector_state_t   state;
    void                   *ctx;
};

typedef struct {
    eai_fw_connector_t connectors[EAI_CONNECTOR_MAX];
    int                count;
} eai_fw_connector_mgr_t;

eai_status_t eai_fw_conn_mgr_init(eai_fw_connector_mgr_t *mgr);
eai_status_t eai_fw_conn_add(eai_fw_connector_mgr_t *mgr, const char *name,
                              const eai_connector_ops_t *ops);
eai_fw_connector_t *eai_fw_conn_find(eai_fw_connector_mgr_t *mgr, const char *name);
eai_status_t eai_fw_conn_connect_all(eai_fw_connector_mgr_t *mgr,
                                      const eai_kv_t *params, int param_count);
void         eai_fw_conn_disconnect_all(eai_fw_connector_mgr_t *mgr);

/* Built-in connector ops */
extern const eai_connector_ops_t eai_connector_mqtt_ops;
extern const eai_connector_ops_t eai_connector_opcua_ops;
extern const eai_connector_ops_t eai_connector_modbus_ops;
extern const eai_connector_ops_t eai_connector_can_ops;

#endif /* EAI_FW_CONNECTOR_H */
