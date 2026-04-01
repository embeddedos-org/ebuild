// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eai_fw/connector.h"
#include "eai/log.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

#define LOG_MOD "conn-can"

typedef struct {
    char interface_name[32];  /* e.g., "can0", "vcan0" */
    int  bitrate;
    bool connected;
} can_ctx_t;

static can_ctx_t g_can_ctx;

static eai_status_t can_connect(eai_fw_connector_t *conn,
                                 const eai_kv_t *params, int param_count)
{
    can_ctx_t *ctx = &g_can_ctx;
    memset(ctx, 0, sizeof(*ctx));
    strncpy(ctx->interface_name, "can0", sizeof(ctx->interface_name) - 1);
    ctx->bitrate = 500000;

    for (int i = 0; i < param_count; i++) {
        if (strcmp(params[i].key, "interface") == 0)
            strncpy(ctx->interface_name, params[i].value, sizeof(ctx->interface_name) - 1);
        if (strcmp(params[i].key, "bitrate") == 0)
            ctx->bitrate = atoi(params[i].value);
    }

    conn->ctx = ctx;
    ctx->connected = true;
    conn->state = EAI_CONN_CONNECTED;
    EAI_LOG_INFO(LOG_MOD, "connected to %s at %d bps", ctx->interface_name, ctx->bitrate);
    return EAI_OK;
}

static eai_status_t can_disconnect(eai_fw_connector_t *conn)
{
    can_ctx_t *ctx = (can_ctx_t *)conn->ctx;
    if (ctx) ctx->connected = false;
    conn->state = EAI_CONN_DISCONNECTED;
    EAI_LOG_INFO(LOG_MOD, "disconnected");
    return EAI_OK;
}

static eai_status_t can_read(eai_fw_connector_t *conn, const char *can_id,
                              void *buf, size_t buf_size, size_t *bytes_read)
{
    can_ctx_t *ctx = (can_ctx_t *)conn->ctx;
    if (!ctx || !ctx->connected) return EAI_ERR_CONNECT;

    /* stub: read CAN frame */
    uint8_t frame[] = {0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08};
    size_t copy = sizeof(frame) < buf_size ? sizeof(frame) : buf_size;
    memcpy(buf, frame, copy);
    if (bytes_read) *bytes_read = copy;

    EAI_LOG_DEBUG(LOG_MOD, "read CAN id=%s bytes=%zu", can_id, copy);
    return EAI_OK;
}

static eai_status_t can_write(eai_fw_connector_t *conn, const char *can_id,
                               const void *data, size_t data_len)
{
    can_ctx_t *ctx = (can_ctx_t *)conn->ctx;
    if (!ctx || !ctx->connected) return EAI_ERR_CONNECT;

    if (data_len > 8) {
        EAI_LOG_ERROR(LOG_MOD, "CAN frame max 8 bytes, got %zu", data_len);
        return EAI_ERR_INVALID;
    }

    EAI_LOG_INFO(LOG_MOD, "write CAN id=%s data_len=%zu", can_id, data_len);
    return EAI_OK;
}

const eai_connector_ops_t eai_connector_can_ops = {
    .name       = "can",
    .type       = EAI_CONN_CAN,
    .connect    = can_connect,
    .disconnect = can_disconnect,
    .read       = can_read,
    .write      = can_write,
    .subscribe  = NULL,
};

/* ---- Connector manager implementation ---- */

eai_status_t eai_fw_conn_mgr_init(eai_fw_connector_mgr_t *mgr)
{
    if (!mgr) return EAI_ERR_INVALID;
    memset(mgr, 0, sizeof(*mgr));
    return EAI_OK;
}

eai_status_t eai_fw_conn_add(eai_fw_connector_mgr_t *mgr, const char *name,
                              const eai_connector_ops_t *ops)
{
    if (!mgr || !name || !ops) return EAI_ERR_INVALID;
    if (mgr->count >= EAI_CONNECTOR_MAX) return EAI_ERR_NOMEM;

    eai_fw_connector_t *conn = &mgr->connectors[mgr->count];
    strncpy(conn->name, name, EAI_CONNECTOR_NAME_MAX - 1);
    conn->ops = ops;
    conn->state = EAI_CONN_DISCONNECTED;
    conn->ctx = NULL;
    mgr->count++;

    EAI_LOG_INFO("conn-mgr", "added connector: %s (%s)", name, ops->name);
    return EAI_OK;
}

eai_fw_connector_t *eai_fw_conn_find(eai_fw_connector_mgr_t *mgr, const char *name)
{
    if (!mgr || !name) return NULL;
    for (int i = 0; i < mgr->count; i++) {
        if (strcmp(mgr->connectors[i].name, name) == 0)
            return &mgr->connectors[i];
    }
    return NULL;
}

eai_status_t eai_fw_conn_connect_all(eai_fw_connector_mgr_t *mgr,
                                      const eai_kv_t *params, int param_count)
{
    if (!mgr) return EAI_ERR_INVALID;
    for (int i = 0; i < mgr->count; i++) {
        if (mgr->connectors[i].ops->connect) {
            eai_status_t s = mgr->connectors[i].ops->connect(
                &mgr->connectors[i], params, param_count);
            if (s != EAI_OK) {
                EAI_LOG_ERROR("conn-mgr", "failed to connect: %s", mgr->connectors[i].name);
            }
        }
    }
    return EAI_OK;
}

void eai_fw_conn_disconnect_all(eai_fw_connector_mgr_t *mgr)
{
    if (!mgr) return;
    for (int i = 0; i < mgr->count; i++) {
        if (mgr->connectors[i].ops->disconnect) {
            mgr->connectors[i].ops->disconnect(&mgr->connectors[i]);
        }
    }
}
