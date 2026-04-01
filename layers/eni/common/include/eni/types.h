// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef ENI_TYPES_H
#define ENI_TYPES_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

typedef enum {
    ENI_OK = 0,
    ENI_ERR_NOMEM,
    ENI_ERR_INVALID,
    ENI_ERR_NOT_FOUND,
    ENI_ERR_IO,
    ENI_ERR_TIMEOUT,
    ENI_ERR_PERMISSION,
    ENI_ERR_RUNTIME,
    ENI_ERR_CONNECT,
    ENI_ERR_PROTOCOL,
    ENI_ERR_CONFIG,
    ENI_ERR_UNSUPPORTED,
    ENI_ERR_POLICY_DENIED,
    ENI_ERR_PROVIDER,
    ENI_ERR_OVERFLOW,
} eni_status_t;

typedef enum {
    ENI_VARIANT_MIN,
    ENI_VARIANT_FRAMEWORK,
} eni_variant_t;

typedef enum {
    ENI_MODE_INTENT,
    ENI_MODE_FEATURES,
    ENI_MODE_RAW,
    ENI_MODE_FEATURES_INTENT,
} eni_mode_t;

typedef enum {
    ENI_LOG_TRACE,
    ENI_LOG_DEBUG,
    ENI_LOG_INFO,
    ENI_LOG_WARN,
    ENI_LOG_ERROR,
    ENI_LOG_FATAL,
} eni_log_level_t;

typedef enum {
    ENI_TRANSPORT_UNIX_SOCKET,
    ENI_TRANSPORT_TCP,
    ENI_TRANSPORT_GRPC,
    ENI_TRANSPORT_MQTT,
    ENI_TRANSPORT_SHARED_MEM,
} eni_transport_t;

typedef struct {
    const char *key;
    const char *value;
} eni_kv_t;

typedef struct {
    uint8_t *data;
    size_t   len;
    size_t   cap;
} eni_buffer_t;

typedef struct {
    uint64_t sec;
    uint32_t nsec;
} eni_timestamp_t;

const char     *eni_status_str(eni_status_t status);
eni_timestamp_t eni_timestamp_now(void);

#endif /* ENI_TYPES_H */
