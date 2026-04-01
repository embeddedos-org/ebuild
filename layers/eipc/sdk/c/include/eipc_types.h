// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef EIPC_TYPES_H
#define EIPC_TYPES_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ══════════════════════════════════════════════════════════════
 *  Protocol constants (must match Go protocol package)
 * ══════════════════════════════════════════════════════════════ */

#define EIPC_MAGIC          0x45495043U  /* "EIPC" */
#define EIPC_PROTOCOL_VER   1
#define EIPC_MAC_SIZE       32           /* HMAC-SHA256 */
#define EIPC_MAX_FRAME      (1U << 20)   /* 1 MB */
#define EIPC_MAX_ARGS       16
#define EIPC_MAX_PAYLOAD    4096
#define EIPC_MAX_HEADER     1024
#define EIPC_SERVICE_ID_MAX 64
#define EIPC_SESSION_ID_MAX 64
#define EIPC_REQUEST_ID_MAX 64
#define EIPC_CAPABILITY_MAX 64
#define EIPC_TIMESTAMP_MAX  40
#define EIPC_INTENT_MAX     64
#define EIPC_TOOL_NAME_MAX  64
#define EIPC_KV_KEY_MAX     64
#define EIPC_KV_VALUE_MAX   256
#define EIPC_ROUTE_MAX      64

/* ══════════════════════════════════════════════════════════════
 *  Frame flags (must match Go protocol.FlagHMAC etc.)
 * ══════════════════════════════════════════════════════════════ */

#define EIPC_FLAG_HMAC      (1U << 0)
#define EIPC_FLAG_COMPRESS  (1U << 1)

/* ══════════════════════════════════════════════════════════════
 *  Message types (wire byte values match Go core.MsgTypeToByte)
 * ══════════════════════════════════════════════════════════════ */

#define EIPC_MSG_INTENT       ((uint8_t)'i')
#define EIPC_MSG_FEATURES     ((uint8_t)'f')
#define EIPC_MSG_TOOL_REQUEST ((uint8_t)'t')
#define EIPC_MSG_ACK          ((uint8_t)'a')
#define EIPC_MSG_POLICY       ((uint8_t)'p')
#define EIPC_MSG_HEARTBEAT    ((uint8_t)'h')
#define EIPC_MSG_AUDIT        ((uint8_t)'u')

/* ══════════════════════════════════════════════════════════════
 *  Payload format
 * ══════════════════════════════════════════════════════════════ */

#define EIPC_PAYLOAD_JSON     0
#define EIPC_PAYLOAD_MSGPACK  1

/* ══════════════════════════════════════════════════════════════
 *  Priority lanes (match Go core.PriorityP0..P3)
 * ══════════════════════════════════════════════════════════════ */

#define EIPC_PRIORITY_P0  0  /* Control-critical */
#define EIPC_PRIORITY_P1  1  /* Interactive */
#define EIPC_PRIORITY_P2  2  /* Telemetry */
#define EIPC_PRIORITY_P3  3  /* Debug / audit bulk */

/* ══════════════════════════════════════════════════════════════
 *  Status codes
 * ══════════════════════════════════════════════════════════════ */

typedef enum {
    EIPC_OK = 0,
    EIPC_ERR_NOMEM,
    EIPC_ERR_INVALID,
    EIPC_ERR_IO,
    EIPC_ERR_TIMEOUT,
    EIPC_ERR_AUTH,
    EIPC_ERR_CAPABILITY,
    EIPC_ERR_INTEGRITY,
    EIPC_ERR_REPLAY,
    EIPC_ERR_BACKPRESSURE,
    EIPC_ERR_CONNECT,
    EIPC_ERR_PROTOCOL,
    EIPC_ERR_FRAME_TOO_LARGE,
    EIPC_ERR_BAD_MAGIC,
    EIPC_ERR_BAD_VERSION,
    EIPC_ERR_NOT_FOUND,
} eipc_status_t;

/* ══════════════════════════════════════════════════════════════
 *  Key-value pair (used for tool arguments)
 * ══════════════════════════════════════════════════════════════ */

typedef struct {
    char key[EIPC_KV_KEY_MAX];
    char value[EIPC_KV_VALUE_MAX];
} eipc_kv_t;

/* ══════════════════════════════════════════════════════════════
 *  Wire frame (matches Go protocol.Frame)
 *
 *  Wire: [magic:4][ver:2][msg_type:1][flags:1]
 *        [header_len:4][payload_len:4]
 *        [header][payload][mac:32?]
 * ══════════════════════════════════════════════════════════════ */

#define EIPC_FRAME_FIXED_SIZE  16  /* 4+2+1+1+4+4 */

typedef struct {
    uint16_t version;
    uint8_t  msg_type;
    uint8_t  flags;
    uint8_t  header[EIPC_MAX_HEADER];
    uint32_t header_len;
    uint8_t  payload[EIPC_MAX_PAYLOAD];
    uint32_t payload_len;
    uint8_t  mac[EIPC_MAC_SIZE];
} eipc_frame_t;

/* ══════════════════════════════════════════════════════════════
 *  Header (matches Go protocol.Header, serialized as JSON)
 * ══════════════════════════════════════════════════════════════ */

typedef struct {
    char     service_id[EIPC_SERVICE_ID_MAX];
    char     session_id[EIPC_SESSION_ID_MAX];
    char     request_id[EIPC_REQUEST_ID_MAX];
    uint64_t sequence;
    char     timestamp[EIPC_TIMESTAMP_MAX];
    uint8_t  priority;
    char     capability[EIPC_CAPABILITY_MAX];
    char     route[EIPC_ROUTE_MAX];
    uint8_t  payload_format;
} eipc_header_t;

/* ══════════════════════════════════════════════════════════════
 *  High-level message (decoded frame)
 * ══════════════════════════════════════════════════════════════ */

typedef struct {
    uint16_t version;
    uint8_t  msg_type;
    char     source[EIPC_SERVICE_ID_MAX];
    char     session_id[EIPC_SESSION_ID_MAX];
    char     request_id[EIPC_REQUEST_ID_MAX];
    uint8_t  priority;
    char     capability[EIPC_CAPABILITY_MAX];
    uint8_t  payload[EIPC_MAX_PAYLOAD];
    uint32_t payload_len;
} eipc_message_t;

/* ══════════════════════════════════════════════════════════════
 *  Event types (match Go core event structs)
 * ══════════════════════════════════════════════════════════════ */

typedef struct {
    char  intent[EIPC_INTENT_MAX];
    float confidence;
    char  session_id[EIPC_SESSION_ID_MAX];
} eipc_intent_event_t;

typedef struct {
    char request_id[EIPC_REQUEST_ID_MAX];
    char status[32];
    char error[256];
} eipc_ack_event_t;

typedef struct {
    char     tool[EIPC_TOOL_NAME_MAX];
    eipc_kv_t args[EIPC_MAX_ARGS];
    int      arg_count;
    char     permission[EIPC_CAPABILITY_MAX];
    char     audit_id[EIPC_REQUEST_ID_MAX];
} eipc_tool_request_t;

typedef struct {
    char request_id[EIPC_REQUEST_ID_MAX];
    bool allowed;
    char reason[256];
} eipc_policy_result_t;

typedef struct {
    char service[EIPC_SERVICE_ID_MAX];
    char status[32];
} eipc_heartbeat_event_t;

typedef struct {
    char request_id[EIPC_REQUEST_ID_MAX];
    char actor[EIPC_SERVICE_ID_MAX];
    char action[EIPC_TOOL_NAME_MAX];
    char target[EIPC_SERVICE_ID_MAX];
    char decision[32];
    char result[32];
} eipc_audit_event_t;

/* ══════════════════════════════════════════════════════════════
 *  Socket abstraction
 * ══════════════════════════════════════════════════════════════ */

#ifdef _WIN32
#include <winsock2.h>
typedef SOCKET eipc_socket_t;
#define EIPC_INVALID_SOCKET INVALID_SOCKET
#else
typedef int eipc_socket_t;
#define EIPC_INVALID_SOCKET (-1)
#endif

/* ══════════════════════════════════════════════════════════════
 *  Client handle
 * ══════════════════════════════════════════════════════════════ */

typedef struct {
    eipc_socket_t sock;
    char          service_id[EIPC_SERVICE_ID_MAX];
    uint8_t       hmac_key[EIPC_MAC_SIZE];
    uint32_t      hmac_key_len;
    uint64_t      sequence;
    bool          connected;
} eipc_client_t;

/* ══════════════════════════════════════════════════════════════
 *  Server handle + connection
 * ══════════════════════════════════════════════════════════════ */

typedef struct {
    eipc_socket_t sock;
    uint8_t       hmac_key[EIPC_MAC_SIZE];
    uint32_t      hmac_key_len;
    uint64_t      sequence;
    char          remote_addr[128];
} eipc_conn_t;

typedef struct {
    eipc_socket_t listen_sock;
    uint8_t       hmac_key[EIPC_MAC_SIZE];
    uint32_t      hmac_key_len;
} eipc_server_t;

#ifdef __cplusplus
}
#endif

#endif /* EIPC_TYPES_H */
