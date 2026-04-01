// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eai_fw/connector.h"
#include "eai/log.h"
#include <string.h>
#include <stdio.h>

#define LOG_MOD "conn-opcua"

typedef struct {
    char endpoint[256];
    bool connected;
} opcua_ctx_t;

static opcua_ctx_t g_opcua_ctx;

static eai_status_t opcua_connect(eai_fw_connector_t *conn,
                                   const eai_kv_t *params, int param_count)
{
    opcua_ctx_t *ctx = &g_opcua_ctx;
    memset(ctx, 0, sizeof(*ctx));
    strncpy(ctx->endpoint, "opc.tcp://localhost:4840", sizeof(ctx->endpoint) - 1);

    for (int i = 0; i < param_count; i++) {
        if (strcmp(params[i].key, "endpoint") == 0)
            strncpy(ctx->endpoint, params[i].value, sizeof(ctx->endpoint) - 1);
    }

    conn->ctx = ctx;
    ctx->connected = true;
    conn->state = EAI_CONN_CONNECTED;
    EAI_LOG_INFO(LOG_MOD, "connected to %s", ctx->endpoint);
    return EAI_OK;
}

static eai_status_t opcua_disconnect(eai_fw_connector_t *conn)
{
    opcua_ctx_t *ctx = (opcua_ctx_t *)conn->ctx;
    if (ctx) ctx->connected = false;
    conn->state = EAI_CONN_DISCONNECTED;
    EAI_LOG_INFO(LOG_MOD, "disconnected");
    return EAI_OK;
}

static eai_status_t opcua_read(eai_fw_connector_t *conn, const char *node_id,
                                void *buf, size_t buf_size, size_t *bytes_read)
{
    opcua_ctx_t *ctx = (opcua_ctx_t *)conn->ctx;
    if (!ctx || !ctx->connected) return EAI_ERR_CONNECT;

    /* stub: read OPC-UA node value */
    const char *stub = "42.5";
    size_t slen = strlen(stub);
    size_t copy = slen < buf_size - 1 ? slen : buf_size - 1;
    memcpy(buf, stub, copy);
    ((char *)buf)[copy] = '\0';
    if (bytes_read) *bytes_read = copy;

    EAI_LOG_DEBUG(LOG_MOD, "read node='%s' value=%s", node_id, stub);
    return EAI_OK;
}

static eai_status_t opcua_write(eai_fw_connector_t *conn, const char *node_id,
                                 const void *data, size_t data_len)
{
    opcua_ctx_t *ctx = (opcua_ctx_t *)conn->ctx;
    if (!ctx || !ctx->connected) return EAI_ERR_CONNECT;

    EAI_LOG_INFO(LOG_MOD, "write node='%s' data_len=%zu", node_id, data_len);
    return EAI_OK;
}

const eai_connector_ops_t eai_connector_opcua_ops = {
    .name       = "opcua",
    .type       = EAI_CONN_OPCUA,
    .connect    = opcua_connect,
    .disconnect = opcua_disconnect,
    .read       = opcua_read,
    .write      = opcua_write,
    .subscribe  = NULL,
};
