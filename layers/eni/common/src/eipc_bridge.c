// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eni/eipc_bridge.h"
#include "eni/log.h"
#include <string.h>
#include <stdio.h>

#ifdef ENI_EIPC_ENABLED

eni_status_t eni_eipc_bridge_init(eni_eipc_bridge_t *bridge, eni_eipc_mode_t mode)
{
    if (!bridge) return ENI_ERR_INVALID;

    memset(bridge, 0, sizeof(*bridge));
    bridge->mode = mode;
    bridge->connected = false;
    return ENI_OK;
}

eni_status_t eni_eipc_bridge_connect(eni_eipc_bridge_t *bridge,
                                      const char *address, const char *hmac_key,
                                      const char *service_id)
{
    if (!bridge || !address || !hmac_key || !service_id) return ENI_ERR_INVALID;

    eipc_status_t st = eipc_client_init(&bridge->client, service_id);
    if (st != EIPC_OK) {
        ENI_LOG_ERROR("eipc_bridge", "client init failed: %d", st);
        bridge->error_count++;
        return ENI_ERR_RUNTIME;
    }

    st = eipc_client_connect(&bridge->client, address, hmac_key);
    if (st != EIPC_OK) {
        ENI_LOG_ERROR("eipc_bridge", "connect to %s failed: %d", address, st);
        bridge->error_count++;
        return ENI_ERR_CONNECT;
    }

    bridge->connected = true;
    ENI_LOG_INFO("eipc_bridge", "connected to %s (service=%s mode=%s)",
                 address, service_id,
                 bridge->mode == ENI_EIPC_MODE_DUAL ? "dual" : "forward-only");
    return ENI_OK;
}

eni_status_t eni_eipc_bridge_send_intent(eni_eipc_bridge_t *bridge,
                                          const char *intent, float confidence)
{
    if (!bridge || !intent) return ENI_ERR_INVALID;
    if (!bridge->connected) return ENI_ERR_CONNECT;

    eipc_status_t st = eipc_client_send_intent(&bridge->client, intent, confidence);
    if (st != EIPC_OK) {
        ENI_LOG_ERROR("eipc_bridge", "send_intent '%s' failed: %d", intent, st);
        bridge->error_count++;
        return ENI_ERR_RUNTIME;
    }

    bridge->sent_count++;
    return ENI_OK;
}

eni_status_t eni_eipc_bridge_send_tool_request(eni_eipc_bridge_t *bridge,
                                                const char *tool,
                                                const eni_kv_t *args, int arg_count)
{
    if (!bridge || !tool) return ENI_ERR_INVALID;
    if (!bridge->connected) return ENI_ERR_CONNECT;

    eipc_kv_t eipc_args[EIPC_MAX_ARGS];
    int count = arg_count < EIPC_MAX_ARGS ? arg_count : EIPC_MAX_ARGS;

    for (int i = 0; i < count; i++) {
        memset(&eipc_args[i], 0, sizeof(eipc_args[i]));
        strncpy(eipc_args[i].key, args[i].key, sizeof(eipc_args[i].key) - 1);
        strncpy(eipc_args[i].value, args[i].value, sizeof(eipc_args[i].value) - 1);
    }

    eipc_status_t st = eipc_client_send_tool_request(&bridge->client, tool,
                                                      eipc_args, count);
    if (st != EIPC_OK) {
        ENI_LOG_ERROR("eipc_bridge", "send_tool_request '%s' failed: %d", tool, st);
        bridge->error_count++;
        return ENI_ERR_RUNTIME;
    }

    bridge->sent_count++;
    return ENI_OK;
}

eni_status_t eni_eipc_bridge_poll_ack(eni_eipc_bridge_t *bridge)
{
    if (!bridge) return ENI_ERR_INVALID;
    if (!bridge->connected) return ENI_ERR_CONNECT;

    eipc_message_t msg;
    eipc_status_t st = eipc_client_receive(&bridge->client, &msg);
    if (st == EIPC_OK) {
        bridge->ack_count++;
    }

    return ENI_OK;
}

void eni_eipc_bridge_close(eni_eipc_bridge_t *bridge)
{
    if (!bridge) return;

    if (bridge->connected) {
        eipc_client_close(&bridge->client);
        bridge->connected = false;
        ENI_LOG_INFO("eipc_bridge", "connection closed");
    }
}

void eni_eipc_bridge_stats(const eni_eipc_bridge_t *bridge)
{
    if (!bridge) return;

    printf("[eni-eipc] connected=%s sent=%llu ack=%llu errors=%llu\n",
           bridge->connected ? "yes" : "no",
           (unsigned long long)bridge->sent_count,
           (unsigned long long)bridge->ack_count,
           (unsigned long long)bridge->error_count);
}

#endif /* ENI_EIPC_ENABLED */
