// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eai_fw/connector.h"
#include "eai/log.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

#define LOG_MOD "conn-mqtt"

typedef struct {
    char broker[256];
    int  port;
    char client_id[64];
    bool connected;
} mqtt_ctx_t;

static mqtt_ctx_t g_mqtt_ctx;

static eai_status_t mqtt_connect(eai_fw_connector_t *conn,
                                  const eai_kv_t *params, int param_count)
{
    mqtt_ctx_t *ctx = &g_mqtt_ctx;
    memset(ctx, 0, sizeof(*ctx));
    strncpy(ctx->broker, "localhost", sizeof(ctx->broker) - 1);
    ctx->port = 1883;
    strncpy(ctx->client_id, "eai-client", sizeof(ctx->client_id) - 1);

    for (int i = 0; i < param_count; i++) {
        if (strcmp(params[i].key, "broker") == 0)
            strncpy(ctx->broker, params[i].value, sizeof(ctx->broker) - 1);
        if (strcmp(params[i].key, "port") == 0)
            ctx->port = atoi(params[i].value);
        if (strcmp(params[i].key, "client_id") == 0)
            strncpy(ctx->client_id, params[i].value, sizeof(ctx->client_id) - 1);
    }

    conn->ctx = ctx;
    ctx->connected = true;
    conn->state = EAI_CONN_CONNECTED;
    EAI_LOG_INFO(LOG_MOD, "connected to %s:%d as %s", ctx->broker, ctx->port, ctx->client_id);
    return EAI_OK;
}

static eai_status_t mqtt_disconnect(eai_fw_connector_t *conn)
{
    mqtt_ctx_t *ctx = (mqtt_ctx_t *)conn->ctx;
    if (ctx) ctx->connected = false;
    conn->state = EAI_CONN_DISCONNECTED;
    EAI_LOG_INFO(LOG_MOD, "disconnected");
    return EAI_OK;
}

static eai_status_t mqtt_write(eai_fw_connector_t *conn, const char *topic,
                                const void *data, size_t data_len)
{
    mqtt_ctx_t *ctx = (mqtt_ctx_t *)conn->ctx;
    if (!ctx || !ctx->connected) return EAI_ERR_CONNECT;

    EAI_LOG_INFO(LOG_MOD, "publish topic='%s' payload_len=%zu", topic, data_len);
    /* stub: real implementation would use an MQTT client library */
    return EAI_OK;
}

static eai_status_t mqtt_read(eai_fw_connector_t *conn, const char *topic,
                               void *buf, size_t buf_size, size_t *bytes_read)
{
    mqtt_ctx_t *ctx = (mqtt_ctx_t *)conn->ctx;
    if (!ctx || !ctx->connected) return EAI_ERR_CONNECT;

    const char *stub_data = "{\"status\":\"ok\"}";
    size_t slen = strlen(stub_data);
    size_t copy = slen < buf_size - 1 ? slen : buf_size - 1;
    memcpy(buf, stub_data, copy);
    ((char *)buf)[copy] = '\0';
    if (bytes_read) *bytes_read = copy;

    EAI_LOG_DEBUG(LOG_MOD, "read from topic='%s' bytes=%zu", topic, copy);
    return EAI_OK;
}

static eai_status_t mqtt_subscribe(eai_fw_connector_t *conn, const char *topic,
                                    void (*callback)(const char *, const void *, size_t))
{
    mqtt_ctx_t *ctx = (mqtt_ctx_t *)conn->ctx;
    if (!ctx || !ctx->connected) return EAI_ERR_CONNECT;

    EAI_LOG_INFO(LOG_MOD, "subscribed to topic='%s'", topic);
    return EAI_OK;
}

const eai_connector_ops_t eai_connector_mqtt_ops = {
    .name       = "mqtt",
    .type       = EAI_CONN_MQTT,
    .connect    = mqtt_connect,
    .disconnect = mqtt_disconnect,
    .read       = mqtt_read,
    .write      = mqtt_write,
    .subscribe  = mqtt_subscribe,
};
