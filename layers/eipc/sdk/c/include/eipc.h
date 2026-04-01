// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef EIPC_H
#define EIPC_H

#include "eipc_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ══════════════════════════════════════════════════════════════
 *  Frame encode / decode (wire-compatible with Go protocol)
 * ══════════════════════════════════════════════════════════════ */

eipc_status_t eipc_frame_encode(const eipc_frame_t *frame, uint8_t *buf, size_t buf_size, size_t *out_len);
eipc_status_t eipc_frame_decode(const uint8_t *buf, size_t buf_len, eipc_frame_t *frame);
size_t        eipc_frame_signable_bytes(const eipc_frame_t *frame, uint8_t *buf, size_t buf_size);

/* ══════════════════════════════════════════════════════════════
 *  HMAC-SHA256
 * ══════════════════════════════════════════════════════════════ */

void eipc_hmac_sign(const uint8_t *key, size_t key_len,
                    const uint8_t *data, size_t data_len,
                    uint8_t mac[EIPC_MAC_SIZE]);
bool eipc_hmac_verify(const uint8_t *key, size_t key_len,
                      const uint8_t *data, size_t data_len,
                      const uint8_t mac[EIPC_MAC_SIZE]);

/* ══════════════════════════════════════════════════════════════
 *  JSON helpers (minimal, no external deps)
 * ══════════════════════════════════════════════════════════════ */

eipc_status_t eipc_header_to_json(const eipc_header_t *hdr, char *buf, size_t buf_size);
eipc_status_t eipc_header_from_json(const char *json, size_t json_len, eipc_header_t *hdr);

eipc_status_t eipc_intent_to_json(const eipc_intent_event_t *ev, char *buf, size_t buf_size);
eipc_status_t eipc_intent_from_json(const char *json, size_t json_len, eipc_intent_event_t *ev);

eipc_status_t eipc_ack_to_json(const eipc_ack_event_t *ev, char *buf, size_t buf_size);
eipc_status_t eipc_ack_from_json(const char *json, size_t json_len, eipc_ack_event_t *ev);

eipc_status_t eipc_tool_request_to_json(const eipc_tool_request_t *ev, char *buf, size_t buf_size);
eipc_status_t eipc_heartbeat_to_json(const eipc_heartbeat_event_t *ev, char *buf, size_t buf_size);

/* ══════════════════════════════════════════════════════════════
 *  Transport (TCP + Unix socket, length-prefixed framing)
 * ══════════════════════════════════════════════════════════════ */

eipc_status_t eipc_transport_connect(eipc_socket_t *sock, const char *address);
eipc_status_t eipc_transport_listen(eipc_socket_t *sock, const char *address);
eipc_status_t eipc_transport_accept(eipc_socket_t listen_sock, eipc_socket_t *client_sock,
                                     char *remote_addr, size_t remote_addr_size);
eipc_status_t eipc_transport_send_frame(eipc_socket_t sock, const eipc_frame_t *frame);
eipc_status_t eipc_transport_recv_frame(eipc_socket_t sock, eipc_frame_t *frame);
void          eipc_transport_close(eipc_socket_t sock);

/* ══════════════════════════════════════════════════════════════
 *  High-level Client API
 * ══════════════════════════════════════════════════════════════ */

eipc_status_t eipc_client_init(eipc_client_t *c, const char *service_id);
eipc_status_t eipc_client_connect(eipc_client_t *c, const char *address,
                                   const char *hmac_key);
eipc_status_t eipc_client_send_intent(eipc_client_t *c, const char *intent,
                                       float confidence);
eipc_status_t eipc_client_send_tool_request(eipc_client_t *c, const char *tool,
                                             const eipc_kv_t *args, int arg_count);
eipc_status_t eipc_client_send_heartbeat(eipc_client_t *c);
eipc_status_t eipc_client_receive(eipc_client_t *c, eipc_message_t *msg);
void          eipc_client_close(eipc_client_t *c);

/* ══════════════════════════════════════════════════════════════
 *  High-level Server API
 * ══════════════════════════════════════════════════════════════ */

eipc_status_t eipc_server_init(eipc_server_t *s);
eipc_status_t eipc_server_listen(eipc_server_t *s, const char *address,
                                  const char *hmac_key);
eipc_status_t eipc_server_accept(eipc_server_t *s, eipc_conn_t *conn);
eipc_status_t eipc_server_receive(eipc_conn_t *conn, eipc_message_t *msg);
eipc_status_t eipc_server_send_ack(eipc_conn_t *conn, const char *request_id,
                                    const char *status);
eipc_status_t eipc_server_send_message(eipc_conn_t *conn, const eipc_message_t *msg);
void          eipc_conn_close(eipc_conn_t *conn);
void          eipc_server_close(eipc_server_t *s);

/* ══════════════════════════════════════════════════════════════
 *  Utility
 * ══════════════════════════════════════════════════════════════ */

void eipc_timestamp_now(char *buf, size_t buf_size);
void eipc_generate_request_id(char *buf, size_t buf_size);

#ifdef __cplusplus
}
#endif

#endif /* EIPC_H */
