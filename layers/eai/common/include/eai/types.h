// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef EAI_TYPES_H
#define EAI_TYPES_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

typedef enum {
    EAI_OK = 0,
    EAI_ERR_NOMEM,
    EAI_ERR_INVALID,
    EAI_ERR_NOT_FOUND,
    EAI_ERR_IO,
    EAI_ERR_TIMEOUT,
    EAI_ERR_PERMISSION,
    EAI_ERR_RUNTIME,
    EAI_ERR_CONNECT,
    EAI_ERR_PROTOCOL,
    EAI_ERR_CONFIG,
    EAI_ERR_UNSUPPORTED,
} eai_status_t;

typedef enum {
    EAI_VARIANT_MIN,
    EAI_VARIANT_FRAMEWORK,
} eai_variant_t;

typedef enum {
    EAI_MODE_LOCAL,
    EAI_MODE_CLOUD,
    EAI_MODE_HYBRID,
} eai_mode_t;

typedef enum {
    EAI_LOG_TRACE,
    EAI_LOG_DEBUG,
    EAI_LOG_INFO,
    EAI_LOG_WARN,
    EAI_LOG_ERROR,
    EAI_LOG_FATAL,
} eai_log_level_t;

typedef struct {
    const char *key;
    const char *value;
} eai_kv_t;

typedef struct {
    uint8_t *data;
    size_t   len;
    size_t   cap;
} eai_buffer_t;

const char *eai_status_str(eai_status_t status);

#endif /* EAI_TYPES_H */
