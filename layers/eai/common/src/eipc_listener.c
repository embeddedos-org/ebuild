// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eai/eipc_listener.h"
#include "eai/log.h"
#include <string.h>
#include <stdio.h>

#ifdef EAI_EIPC_ENABLED

#define LOG_MOD "eipc-listener"

eai_status_t eai_eipc_listener_init(eai_eipc_listener_t *listener)
{
    if (!listener) return EAI_ERR_INVALID;

    memset(listener, 0, sizeof(*listener));
    eipc_status_t rc = eipc_server_init(&listener->server);
    if (rc != EIPC_OK) {
        EAI_LOG_ERROR(LOG_MOD, "eipc_server_init failed: %d", rc);
        return EAI_ERR_RUNTIME;
    }

    listener->listening = false;
    listener->has_client = false;
    listener->received_count = 0;
    listener->ack_count = 0;

    EAI_LOG_DEBUG(LOG_MOD, "listener initialized");
    return EAI_OK;
}

eai_status_t eai_eipc_listener_start(eai_eipc_listener_t *listener,
                                      const char *address, const char *hmac_key)
{
    if (!listener || !address || !hmac_key) return EAI_ERR_INVALID;

    eipc_status_t rc = eipc_server_listen(&listener->server, address, hmac_key);
    if (rc != EIPC_OK) {
        EAI_LOG_ERROR(LOG_MOD, "eipc_server_listen failed on %s: %d", address, rc);
        return EAI_ERR_CONNECT;
    }

    listener->listening = true;
    EAI_LOG_INFO(LOG_MOD, "listening on %s", address);
    return EAI_OK;
}

eai_status_t eai_eipc_listener_accept(eai_eipc_listener_t *listener)
{
    if (!listener || !listener->listening) return EAI_ERR_INVALID;

    eipc_status_t rc = eipc_server_accept(&listener->server, &listener->active_conn);
    if (rc != EIPC_OK) {
        EAI_LOG_ERROR(LOG_MOD, "eipc_server_accept failed: %d", rc);
        return EAI_ERR_CONNECT;
    }

    listener->has_client = true;
    EAI_LOG_INFO(LOG_MOD, "accepted client connection");
    return EAI_OK;
}

eai_status_t eai_eipc_listener_receive_intent(eai_eipc_listener_t *listener,
                                               char *intent, size_t intent_size,
                                               float *confidence)
{
    if (!listener || !listener->has_client || !intent || !confidence)
        return EAI_ERR_INVALID;

    eipc_message_t msg;
    memset(&msg, 0, sizeof(msg));

    eipc_status_t rc = eipc_server_receive(&listener->active_conn, &msg);
    if (rc != EIPC_OK) {
        EAI_LOG_ERROR(LOG_MOD, "eipc_server_receive failed: %d", rc);
        return EAI_ERR_IO;
    }

    if (msg.msg_type != EIPC_MSG_INTENT) {
        EAI_LOG_WARN(LOG_MOD, "unexpected msg_type 0x%02x, expected intent", msg.msg_type);
        return EAI_ERR_PROTOCOL;
    }

    eipc_intent_event_t ev;
    memset(&ev, 0, sizeof(ev));
    rc = eipc_intent_from_json((const char *)msg.payload, msg.payload_len, &ev);
    if (rc != EIPC_OK) {
        EAI_LOG_ERROR(LOG_MOD, "failed to parse intent JSON: %d", rc);
        return EAI_ERR_PROTOCOL;
    }

    strncpy(intent, ev.intent, intent_size - 1);
    intent[intent_size - 1] = '\0';
    *confidence = ev.confidence;

    listener->received_count++;
    EAI_LOG_DEBUG(LOG_MOD, "received intent: %s (%.2f)", intent, *confidence);
    return EAI_OK;
}

eai_status_t eai_eipc_listener_send_ack(eai_eipc_listener_t *listener,
                                         const char *request_id, const char *status)
{
    if (!listener || !listener->has_client || !status) return EAI_ERR_INVALID;

    char rid[64];
    if (!request_id || request_id[0] == '\0') {
        eipc_generate_request_id(rid, sizeof(rid));
        request_id = rid;
    }

    eipc_status_t rc = eipc_server_send_ack(&listener->active_conn, request_id, status);
    if (rc != EIPC_OK) {
        EAI_LOG_ERROR(LOG_MOD, "eipc_server_send_ack failed: %d", rc);
        return EAI_ERR_IO;
    }

    listener->ack_count++;
    EAI_LOG_DEBUG(LOG_MOD, "sent ack [%s] status=%s", request_id, status);
    return EAI_OK;
}

void eai_eipc_listener_close(eai_eipc_listener_t *listener)
{
    if (!listener) return;

    if (listener->has_client) {
        eipc_conn_close(&listener->active_conn);
        listener->has_client = false;
    }

    if (listener->listening) {
        eipc_server_close(&listener->server);
        listener->listening = false;
    }

    EAI_LOG_INFO(LOG_MOD, "listener closed (received=%llu, acked=%llu)",
                 (unsigned long long)listener->received_count,
                 (unsigned long long)listener->ack_count);
}

void eai_eipc_listener_stats(const eai_eipc_listener_t *listener)
{
    if (!listener) return;

    printf("EIPC Listener Stats:\n");
    printf("  listening:  %s\n", listener->listening ? "yes" : "no");
    printf("  has_client: %s\n", listener->has_client ? "yes" : "no");
    printf("  received:   %llu\n", (unsigned long long)listener->received_count);
    printf("  acked:      %llu\n", (unsigned long long)listener->ack_count);
}

#endif /* EAI_EIPC_ENABLED */
