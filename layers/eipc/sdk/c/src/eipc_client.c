// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/*
 * EIPC High-level Client API
 */

#include "eipc.h"

#include <string.h>
#include <stdio.h>
#include <time.h>

/* --------------- utility implementations --------------- */

void eipc_timestamp_now(char *buf, size_t buf_size) {
    if (!buf || buf_size == 0) return;
    snprintf(buf, buf_size, "%llu", (unsigned long long)time(NULL));
}

void eipc_generate_request_id(char *buf, size_t buf_size) {
    if (!buf || buf_size == 0) return;
    snprintf(buf, buf_size, "req-%08lx-%04x",
             (unsigned long)time(NULL),
             (unsigned)(rand() & 0xFFFF));
}

/* --------------- helpers --------------- */

static void fill_header(eipc_header_t *h,
                        const char *service_id,
                        uint64_t sequence) {
    memset(h, 0, sizeof(*h));
    strncpy(h->service_id, service_id, sizeof(h->service_id) - 1);
    eipc_generate_request_id(h->request_id, sizeof(h->request_id));
    h->sequence = sequence;
    eipc_timestamp_now(h->timestamp, sizeof(h->timestamp));
    h->priority = EIPC_PRIORITY_P1;
    h->payload_format = EIPC_PAYLOAD_JSON;
}

static eipc_status_t build_and_send(eipc_client_t *c,
                                    uint8_t msg_type,
                                    const eipc_header_t *hdr,
                                    const uint8_t *payload,
                                    size_t payload_len) {
    eipc_frame_t frame;
    eipc_status_t rc;
    char header_json[EIPC_MAX_HEADER];
    size_t signable_len;

    memset(&frame, 0, sizeof(frame));

    frame.version = EIPC_PROTOCOL_VER;
    frame.msg_type = msg_type;
    frame.flags = EIPC_FLAG_HMAC;

    rc = eipc_header_to_json(hdr, header_json, sizeof(header_json));
    if (rc != EIPC_OK) return rc;

    size_t hdr_json_len = strlen(header_json);
    memcpy(frame.header, header_json, hdr_json_len);
    frame.header_len = (uint32_t)hdr_json_len;

    if (payload && payload_len > 0) {
        if (payload_len > sizeof(frame.payload))
            return EIPC_ERR_FRAME_TOO_LARGE;
        memcpy(frame.payload, payload, payload_len);
        frame.payload_len = (uint32_t)payload_len;
    }

    {
        uint8_t signable[EIPC_MAX_FRAME];
        signable_len = eipc_frame_signable_bytes(&frame, signable, sizeof(signable));
        if (signable_len == 0)
            return EIPC_ERR_INTEGRITY;

        eipc_hmac_sign(c->hmac_key, c->hmac_key_len,
                       signable, signable_len,
                       frame.mac);
    }

    return eipc_transport_send_frame(c->sock, &frame);
}

/* --------------- public API --------------- */

eipc_status_t eipc_client_init(eipc_client_t *c, const char *service_id) {
    if (!c || !service_id) return EIPC_ERR_INVALID;

    memset(c, 0, sizeof(*c));
    c->sock = EIPC_INVALID_SOCKET;
    strncpy(c->service_id, service_id, sizeof(c->service_id) - 1);

    return EIPC_OK;
}

eipc_status_t eipc_client_connect(eipc_client_t *c,
                                  const char *address,
                                  const char *hmac_key) {
    eipc_status_t rc;
    size_t key_len;

    if (!c || !address || !hmac_key) return EIPC_ERR_INVALID;

    key_len = strlen(hmac_key);
    if (key_len > sizeof(c->hmac_key)) return EIPC_ERR_INVALID;
    memcpy(c->hmac_key, hmac_key, key_len);
    c->hmac_key_len = (uint32_t)key_len;

    rc = eipc_transport_connect(&c->sock, address);
    if (rc != EIPC_OK) return rc;

    c->connected = true;
    c->sequence = 0;

    return EIPC_OK;
}

eipc_status_t eipc_client_send_intent(eipc_client_t *c,
                                      const char *intent,
                                      float confidence) {
    eipc_header_t hdr;
    eipc_intent_event_t ev;
    char payload_json[EIPC_MAX_PAYLOAD];
    eipc_status_t rc;

    if (!c || !c->connected || !intent) return EIPC_ERR_INVALID;

    c->sequence++;

    fill_header(&hdr, c->service_id, c->sequence);

    memset(&ev, 0, sizeof(ev));
    strncpy(ev.intent, intent, sizeof(ev.intent) - 1);
    ev.confidence = confidence;

    rc = eipc_intent_to_json(&ev, payload_json, sizeof(payload_json));
    if (rc != EIPC_OK) return rc;

    return build_and_send(c, EIPC_MSG_INTENT, &hdr,
                          (const uint8_t *)payload_json, strlen(payload_json));
}

eipc_status_t eipc_client_send_tool_request(eipc_client_t *c,
                                            const char *tool,
                                            const eipc_kv_t *args,
                                            int arg_count) {
    eipc_header_t hdr;
    eipc_tool_request_t req;
    char payload_json[EIPC_MAX_PAYLOAD];
    eipc_status_t rc;

    if (!c || !c->connected || !tool) return EIPC_ERR_INVALID;

    c->sequence++;

    fill_header(&hdr, c->service_id, c->sequence);

    memset(&req, 0, sizeof(req));
    strncpy(req.tool, tool, sizeof(req.tool) - 1);
    if (args && arg_count > 0) {
        int n = arg_count;
        if (n > EIPC_MAX_ARGS) n = EIPC_MAX_ARGS;
        memcpy(req.args, args, sizeof(eipc_kv_t) * (size_t)n);
        req.arg_count = n;
    }

    rc = eipc_tool_request_to_json(&req, payload_json, sizeof(payload_json));
    if (rc != EIPC_OK) return rc;

    return build_and_send(c, EIPC_MSG_TOOL_REQUEST, &hdr,
                          (const uint8_t *)payload_json, strlen(payload_json));
}

eipc_status_t eipc_client_send_heartbeat(eipc_client_t *c) {
    eipc_header_t hdr;
    eipc_heartbeat_event_t hb;
    char payload_json[EIPC_MAX_PAYLOAD];
    eipc_status_t rc;

    if (!c || !c->connected) return EIPC_ERR_INVALID;

    c->sequence++;

    fill_header(&hdr, c->service_id, c->sequence);

    memset(&hb, 0, sizeof(hb));
    strncpy(hb.service, c->service_id, sizeof(hb.service) - 1);
    strncpy(hb.status, "alive", sizeof(hb.status) - 1);

    rc = eipc_heartbeat_to_json(&hb, payload_json, sizeof(payload_json));
    if (rc != EIPC_OK) return rc;

    return build_and_send(c, EIPC_MSG_HEARTBEAT, &hdr,
                          (const uint8_t *)payload_json, strlen(payload_json));
}

eipc_status_t eipc_client_receive(eipc_client_t *c, eipc_message_t *msg) {
    eipc_frame_t frame;
    eipc_header_t hdr;
    eipc_status_t rc;

    if (!c || !c->connected || !msg) return EIPC_ERR_INVALID;

    memset(&frame, 0, sizeof(frame));

    rc = eipc_transport_recv_frame(c->sock, &frame);
    if (rc != EIPC_OK) return rc;

    if (frame.flags & EIPC_FLAG_HMAC) {
        uint8_t signable[EIPC_MAX_FRAME];
        size_t signable_len = eipc_frame_signable_bytes(&frame, signable, sizeof(signable));
        if (signable_len == 0)
            return EIPC_ERR_INTEGRITY;

        if (!eipc_hmac_verify(c->hmac_key, c->hmac_key_len,
                              signable, signable_len, frame.mac))
            return EIPC_ERR_AUTH;
    }

    memset(msg, 0, sizeof(*msg));
    msg->msg_type = frame.msg_type;
    msg->version = frame.version;

    rc = eipc_header_from_json((const char *)frame.header, frame.header_len, &hdr);
    if (rc != EIPC_OK) return rc;

    strncpy(msg->source, hdr.service_id, sizeof(msg->source) - 1);
    strncpy(msg->session_id, hdr.session_id, sizeof(msg->session_id) - 1);
    strncpy(msg->request_id, hdr.request_id, sizeof(msg->request_id) - 1);
    msg->priority = hdr.priority;
    strncpy(msg->capability, hdr.capability, sizeof(msg->capability) - 1);

    if (frame.payload_len > 0) {
        if (frame.payload_len > sizeof(msg->payload))
            return EIPC_ERR_FRAME_TOO_LARGE;
        memcpy(msg->payload, frame.payload, frame.payload_len);
        msg->payload_len = frame.payload_len;
    }

    return EIPC_OK;
}

void eipc_client_close(eipc_client_t *c) {
    if (!c) return;

    if (c->sock != EIPC_INVALID_SOCKET) {
        eipc_transport_close(c->sock);
        c->sock = EIPC_INVALID_SOCKET;
    }
    c->connected = false;
    c->sequence = 0;
}
