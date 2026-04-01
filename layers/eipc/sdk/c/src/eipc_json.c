// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/*
 * EIPC Minimal JSON Serializer/Deserializer
 * No external dependencies. Uses snprintf for serialization and
 * simple string scanning for deserialization.
 */

#include "eipc.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ---------- JSON Parse Helpers ---------- */

static int json_find_string(const char *json, const char *key,
                            char *out, size_t out_size) {
    char pattern[128];
    const char *start, *end;
    size_t len;

    snprintf(pattern, sizeof(pattern), "\"%s\"", key);
    start = strstr(json, pattern);
    if (!start) {
        out[0] = '\0';
        return -1;
    }

    start += strlen(pattern);
    while (*start == ' ' || *start == ':' || *start == '\t' || *start == '\n')
        start++;

    if (*start != '"') {
        out[0] = '\0';
        return -1;
    }
    start++;

    end = start;
    while (*end && *end != '"') {
        if (*end == '\\' && *(end + 1))
            end += 2;
        else
            end++;
    }

    len = (size_t)(end - start);
    if (len >= out_size)
        len = out_size - 1;
    memcpy(out, start, len);
    out[len] = '\0';
    return 0;
}

static int json_find_uint64(const char *json, const char *key, uint64_t *out) {
    char pattern[128];
    const char *start;

    snprintf(pattern, sizeof(pattern), "\"%s\"", key);
    start = strstr(json, pattern);
    if (!start) {
        *out = 0;
        return -1;
    }

    start += strlen(pattern);
    while (*start == ' ' || *start == ':' || *start == '\t' || *start == '\n')
        start++;

    if (*start == '"')
        start++;
    *out = (uint64_t)strtoull(start, NULL, 10);
    return 0;
}

static int json_find_int(const char *json, const char *key, int *out) {
    uint64_t val;
    if (json_find_uint64(json, key, &val) < 0) {
        *out = 0;
        return -1;
    }
    *out = (int)val;
    return 0;
}

static int json_find_float(const char *json, const char *key, float *out) {
    char pattern[128];
    const char *start;

    snprintf(pattern, sizeof(pattern), "\"%s\"", key);
    start = strstr(json, pattern);
    if (!start) {
        *out = 0.0f;
        return -1;
    }

    start += strlen(pattern);
    while (*start == ' ' || *start == ':' || *start == '\t' || *start == '\n')
        start++;

    if (*start == '"')
        start++;
    *out = (float)strtod(start, NULL);
    return 0;
}

/* ---------- JSON Escape Helper ---------- */

static size_t json_escape(const char *src, char *dst, size_t dst_size) {
    size_t si = 0, di = 0;
    if (!src || !dst || dst_size == 0) return 0;

    while (src[si] && di < dst_size - 1) {
        switch (src[si]) {
            case '"':
            case '\\':
                if (di + 2 >= dst_size) goto done;
                dst[di++] = '\\';
                dst[di++] = src[si];
                break;
            case '\n':
                if (di + 2 >= dst_size) goto done;
                dst[di++] = '\\';
                dst[di++] = 'n';
                break;
            case '\r':
                if (di + 2 >= dst_size) goto done;
                dst[di++] = '\\';
                dst[di++] = 'r';
                break;
            case '\t':
                if (di + 2 >= dst_size) goto done;
                dst[di++] = '\\';
                dst[di++] = 't';
                break;
            default:
                dst[di++] = src[si];
                break;
        }
        si++;
    }
done:
    dst[di] = '\0';
    return di;
}

/* ---------- Header JSON ---------- */

eipc_status_t eipc_header_to_json(const eipc_header_t *hdr,
                                  char *buf, size_t buf_size,
                                  size_t *out_len) {
    int n;

    if (!hdr || !buf || !out_len)
        return EIPC_ERR_INVALID;

    n = snprintf(buf, buf_size,
        "{\"service_id\":\"%s\","
        "\"session_id\":\"%s\","
        "\"request_id\":\"%s\","
        "\"sequence\":%llu,"
        "\"timestamp\":\"%llu\","
        "\"priority\":%d,"
        "\"capability\":\"%s\","
        "\"payload_format\":%d}",
        hdr->service_id,
        hdr->session_id,
        hdr->request_id,
        (unsigned long long)hdr->sequence,
        (unsigned long long)hdr->timestamp,
        hdr->priority,
        hdr->capability,
        hdr->payload_format);

    if (n < 0 || (size_t)n >= buf_size)
        return EIPC_ERR_BUFFER;

    *out_len = (size_t)n;
    return EIPC_OK;
}

eipc_status_t eipc_header_from_json(const char *json, size_t json_len,
                                    eipc_header_t *hdr) {
    uint64_t val;
    int ival;
    (void)json_len;

    if (!json || !hdr)
        return EIPC_ERR_INVALID;

    memset(hdr, 0, sizeof(*hdr));

    json_find_string(json, "service_id", hdr->service_id, sizeof(hdr->service_id));
    json_find_string(json, "session_id", hdr->session_id, sizeof(hdr->session_id));
    json_find_string(json, "request_id", hdr->request_id, sizeof(hdr->request_id));

    if (json_find_uint64(json, "sequence", &val) == 0)
        hdr->sequence = val;
    if (json_find_uint64(json, "timestamp", &val) == 0)
        hdr->timestamp = val;
    if (json_find_int(json, "priority", &ival) == 0)
        hdr->priority = ival;

    json_find_string(json, "capability", hdr->capability, sizeof(hdr->capability));

    if (json_find_int(json, "payload_format", &ival) == 0)
        hdr->payload_format = ival;

    return EIPC_OK;
}

/* ---------- Intent JSON ---------- */

eipc_status_t eipc_intent_to_json(const eipc_intent_t *intent,
                                  char *buf, size_t buf_size,
                                  size_t *out_len) {
    int n;
    char escaped_intent[256];
    char escaped_session[128];

    if (!intent || !buf || !out_len)
        return EIPC_ERR_INVALID;

    json_escape(intent->intent, escaped_intent, sizeof(escaped_intent));
    json_escape(intent->session_id, escaped_session, sizeof(escaped_session));

    n = snprintf(buf, buf_size,
        "{\"intent\":\"%s\","
        "\"confidence\":%.2f,"
        "\"session_id\":\"%s\"}",
        escaped_intent,
        intent->confidence,
        escaped_session);

    if (n < 0 || (size_t)n >= buf_size)
        return EIPC_ERR_BUFFER;

    *out_len = (size_t)n;
    return EIPC_OK;
}

eipc_status_t eipc_intent_from_json(const char *json, size_t json_len,
                                    eipc_intent_t *intent) {
    (void)json_len;

    if (!json || !intent)
        return EIPC_ERR_INVALID;

    memset(intent, 0, sizeof(*intent));

    json_find_string(json, "intent", intent->intent, sizeof(intent->intent));
    json_find_float(json, "confidence", &intent->confidence);
    json_find_string(json, "session_id", intent->session_id, sizeof(intent->session_id));

    return EIPC_OK;
}

/* ---------- Ack JSON ---------- */

eipc_status_t eipc_ack_to_json(const eipc_ack_t *ack,
                               char *buf, size_t buf_size,
                               size_t *out_len) {
    int n;
    char escaped_error[512];

    if (!ack || !buf || !out_len)
        return EIPC_ERR_INVALID;

    json_escape(ack->error, escaped_error, sizeof(escaped_error));

    n = snprintf(buf, buf_size,
        "{\"request_id\":\"%s\","
        "\"status\":\"%s\","
        "\"error\":\"%s\"}",
        ack->request_id,
        ack->status,
        escaped_error);

    if (n < 0 || (size_t)n >= buf_size)
        return EIPC_ERR_BUFFER;

    *out_len = (size_t)n;
    return EIPC_OK;
}

eipc_status_t eipc_ack_from_json(const char *json, size_t json_len,
                                 eipc_ack_t *ack) {
    (void)json_len;

    if (!json || !ack)
        return EIPC_ERR_INVALID;

    memset(ack, 0, sizeof(*ack));

    json_find_string(json, "request_id", ack->request_id, sizeof(ack->request_id));
    json_find_string(json, "status", ack->status, sizeof(ack->status));
    json_find_string(json, "error", ack->error, sizeof(ack->error));

    return EIPC_OK;
}

/* ---------- Tool Request JSON ---------- */

eipc_status_t eipc_tool_request_to_json(const eipc_tool_request_t *req,
                                        char *buf, size_t buf_size,
                                        size_t *out_len) {
    int n;
    char args_json[2048];
    size_t ai = 0;
    int i;

    if (!req || !buf || !out_len)
        return EIPC_ERR_INVALID;

    args_json[ai++] = '{';
    for (i = 0; i < req->args_count && i < EIPC_MAX_TOOL_ARGS; i++) {
        char ek[128], ev[256];
        int written;

        if (i > 0)
            args_json[ai++] = ',';

        json_escape(req->args[i].key, ek, sizeof(ek));
        json_escape(req->args[i].value, ev, sizeof(ev));

        written = snprintf(args_json + ai, sizeof(args_json) - ai,
                          "\"%s\":\"%s\"", ek, ev);
        if (written < 0 || (size_t)written >= sizeof(args_json) - ai)
            return EIPC_ERR_BUFFER;
        ai += (size_t)written;
    }
    args_json[ai++] = '}';
    args_json[ai] = '\0';

    n = snprintf(buf, buf_size,
        "{\"tool\":\"%s\","
        "\"args\":%s,"
        "\"permission\":\"%s\"}",
        req->tool,
        args_json,
        req->permission);

    if (n < 0 || (size_t)n >= buf_size)
        return EIPC_ERR_BUFFER;

    *out_len = (size_t)n;
    return EIPC_OK;
}

/* ---------- Heartbeat JSON ---------- */

eipc_status_t eipc_heartbeat_to_json(const eipc_heartbeat_t *hb,
                                     char *buf, size_t buf_size,
                                     size_t *out_len) {
    int n;

    if (!hb || !buf || !out_len)
        return EIPC_ERR_INVALID;

    n = snprintf(buf, buf_size,
        "{\"service\":\"%s\","
        "\"status\":\"%s\"}",
        hb->service,
        hb->status);

    if (n < 0 || (size_t)n >= buf_size)
        return EIPC_ERR_BUFFER;

    *out_len = (size_t)n;
    return EIPC_OK;
}
