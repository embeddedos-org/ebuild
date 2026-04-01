// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eai_fw/connector.h"
#include "eai/log.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

#define LOG_MOD "conn-modbus"

typedef struct {
    char host[256];
    int  port;
    int  slave_id;
    bool connected;
} modbus_ctx_t;

static modbus_ctx_t g_modbus_ctx;

static eai_status_t modbus_connect(eai_fw_connector_t *conn,
                                    const eai_kv_t *params, int param_count)
{
    modbus_ctx_t *ctx = &g_modbus_ctx;
    memset(ctx, 0, sizeof(*ctx));
    strncpy(ctx->host, "localhost", sizeof(ctx->host) - 1);
    ctx->port = 502;
    ctx->slave_id = 1;

    for (int i = 0; i < param_count; i++) {
        if (strcmp(params[i].key, "host") == 0)
            strncpy(ctx->host, params[i].value, sizeof(ctx->host) - 1);
        if (strcmp(params[i].key, "port") == 0)
            ctx->port = atoi(params[i].value);
        if (strcmp(params[i].key, "slave_id") == 0)
            ctx->slave_id = atoi(params[i].value);
    }

    conn->ctx = ctx;
    ctx->connected = true;
    conn->state = EAI_CONN_CONNECTED;
    EAI_LOG_INFO(LOG_MOD, "connected to %s:%d slave=%d", ctx->host, ctx->port, ctx->slave_id);
    return EAI_OK;
}

static eai_status_t modbus_disconnect(eai_fw_connector_t *conn)
{
    modbus_ctx_t *ctx = (modbus_ctx_t *)conn->ctx;
    if (ctx) ctx->connected = false;
    conn->state = EAI_CONN_DISCONNECTED;
    EAI_LOG_INFO(LOG_MOD, "disconnected");
    return EAI_OK;
}

static eai_status_t modbus_read(eai_fw_connector_t *conn, const char *register_addr,
                                 void *buf, size_t buf_size, size_t *bytes_read)
{
    modbus_ctx_t *ctx = (modbus_ctx_t *)conn->ctx;
    if (!ctx || !ctx->connected) return EAI_ERR_CONNECT;

    /* stub: read Modbus holding register */
    uint16_t reg_val = 1024;
    int written = snprintf((char *)buf, buf_size, "%u", reg_val);
    if (bytes_read) *bytes_read = (size_t)written;

    EAI_LOG_DEBUG(LOG_MOD, "read register=%s value=%u", register_addr, reg_val);
    return EAI_OK;
}

static eai_status_t modbus_write(eai_fw_connector_t *conn, const char *register_addr,
                                  const void *data, size_t data_len)
{
    modbus_ctx_t *ctx = (modbus_ctx_t *)conn->ctx;
    if (!ctx || !ctx->connected) return EAI_ERR_CONNECT;

    EAI_LOG_INFO(LOG_MOD, "write register=%s data_len=%zu", register_addr, data_len);
    return EAI_OK;
}

const eai_connector_ops_t eai_connector_modbus_ops = {
    .name       = "modbus",
    .type       = EAI_CONN_MODBUS,
    .connect    = modbus_connect,
    .disconnect = modbus_disconnect,
    .read       = modbus_read,
    .write      = modbus_write,
    .subscribe  = NULL,
};
