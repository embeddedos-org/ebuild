// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eai/tools_builtin.h"
#include "eai/log.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define LOG_MOD "tools"

/* ========== mqtt.publish ========== */

static eai_status_t tool_mqtt_publish_exec(const eai_kv_t *args, int arg_count,
                                            eai_tool_result_t *result)
{
    const char *topic = NULL;
    const char *payload = NULL;
    const char *qos_str = NULL;

    for (int i = 0; i < arg_count; i++) {
        if (strcmp(args[i].key, "topic") == 0)   topic = args[i].value;
        if (strcmp(args[i].key, "payload") == 0)  payload = args[i].value;
        if (strcmp(args[i].key, "qos") == 0)      qos_str = args[i].value;
    }

    if (!topic || !payload) {
        snprintf(result->data, sizeof(result->data), "error: topic and payload required");
        result->len = strlen(result->data);
        return EAI_ERR_INVALID;
    }

    int qos = qos_str ? atoi(qos_str) : 0;

    EAI_LOG_INFO(LOG_MOD, "mqtt.publish topic='%s' qos=%d payload='%s'", topic, qos, payload);

    /* stub: real implementation would use MQTT client */
    snprintf(result->data, sizeof(result->data),
             "{\"status\":\"published\",\"topic\":\"%s\",\"qos\":%d}", topic, qos);
    result->len = strlen(result->data);
    return EAI_OK;
}

eai_status_t eai_tool_mqtt_publish_register(eai_tool_registry_t *reg)
{
    eai_tool_t tool = {0};
    strncpy(tool.name, "mqtt.publish", EAI_TOOL_NAME_MAX - 1);
    tool.description = "Publish a message to an MQTT topic";
    tool.params[0] = (eai_tool_param_t){"topic",   EAI_PARAM_STRING, true};
    tool.params[1] = (eai_tool_param_t){"payload", EAI_PARAM_STRING, true};
    tool.params[2] = (eai_tool_param_t){"qos",     EAI_PARAM_INT,    false};
    tool.param_count = 3;
    tool.permissions[0] = "mqtt:write";
    tool.permission_count = 1;
    tool.exec = tool_mqtt_publish_exec;
    return eai_tool_register(reg, &tool);
}

/* ========== device.read_sensor ========== */

static eai_status_t tool_device_read_sensor_exec(const eai_kv_t *args, int arg_count,
                                                   eai_tool_result_t *result)
{
    const char *sensor_id = NULL;
    const char *sensor_type = NULL;

    for (int i = 0; i < arg_count; i++) {
        if (strcmp(args[i].key, "sensor_id") == 0)   sensor_id = args[i].value;
        if (strcmp(args[i].key, "type") == 0)         sensor_type = args[i].value;
    }

    if (!sensor_id) {
        snprintf(result->data, sizeof(result->data), "error: sensor_id required");
        result->len = strlen(result->data);
        return EAI_ERR_INVALID;
    }

    EAI_LOG_INFO(LOG_MOD, "device.read_sensor id='%s' type='%s'",
                 sensor_id, sensor_type ? sensor_type : "auto");

    /* stub: simulate sensor readings */
    double temp_value = 23.5 + (rand() % 100) / 10.0;
    snprintf(result->data, sizeof(result->data),
             "{\"sensor_id\":\"%s\",\"value\":%.2f,\"unit\":\"C\",\"timestamp\":%lu}",
             sensor_id, temp_value, (unsigned long)time(NULL));
    result->len = strlen(result->data);
    return EAI_OK;
}

eai_status_t eai_tool_device_read_sensor_register(eai_tool_registry_t *reg)
{
    eai_tool_t tool = {0};
    strncpy(tool.name, "device.read_sensor", EAI_TOOL_NAME_MAX - 1);
    tool.description = "Read a value from a hardware sensor";
    tool.params[0] = (eai_tool_param_t){"sensor_id", EAI_PARAM_STRING, true};
    tool.params[1] = (eai_tool_param_t){"type",      EAI_PARAM_STRING, false};
    tool.param_count = 2;
    tool.permissions[0] = "sensor:read";
    tool.permission_count = 1;
    tool.exec = tool_device_read_sensor_exec;
    return eai_tool_register(reg, &tool);
}

/* ========== http.get ========== */

static eai_status_t tool_http_get_exec(const eai_kv_t *args, int arg_count,
                                        eai_tool_result_t *result)
{
    const char *url = NULL;
    const char *timeout_str = NULL;

    for (int i = 0; i < arg_count; i++) {
        if (strcmp(args[i].key, "url") == 0)     url = args[i].value;
        if (strcmp(args[i].key, "timeout") == 0) timeout_str = args[i].value;
    }

    if (!url) {
        snprintf(result->data, sizeof(result->data), "error: url required");
        result->len = strlen(result->data);
        return EAI_ERR_INVALID;
    }

    int timeout = timeout_str ? atoi(timeout_str) : 5000;

    EAI_LOG_INFO(LOG_MOD, "http.get url='%s' timeout=%dms", url, timeout);

    /* stub: real implementation would use HTTP client (curl, etc.) */
    snprintf(result->data, sizeof(result->data),
             "{\"status\":200,\"url\":\"%s\",\"body\":\"[stub response]\"}", url);
    result->len = strlen(result->data);
    return EAI_OK;
}

eai_status_t eai_tool_http_get_register(eai_tool_registry_t *reg)
{
    eai_tool_t tool = {0};
    strncpy(tool.name, "http.get", EAI_TOOL_NAME_MAX - 1);
    tool.description = "Perform an HTTP GET request";
    tool.params[0] = (eai_tool_param_t){"url",     EAI_PARAM_STRING, true};
    tool.params[1] = (eai_tool_param_t){"timeout", EAI_PARAM_INT,    false};
    tool.param_count = 2;
    tool.permissions[0] = "network:http";
    tool.permission_count = 1;
    tool.exec = tool_http_get_exec;
    return eai_tool_register(reg, &tool);
}

/* ========== Register all built-in tools ========== */

eai_status_t eai_tools_register_builtins(eai_tool_registry_t *reg)
{
    if (!reg) return EAI_ERR_INVALID;

    eai_status_t s;
    s = eai_tool_mqtt_publish_register(reg);
    if (s != EAI_OK) return s;

    s = eai_tool_device_read_sensor_register(reg);
    if (s != EAI_OK) return s;

    s = eai_tool_http_get_register(reg);
    if (s != EAI_OK) return s;

    EAI_LOG_INFO(LOG_MOD, "registered %d built-in tools", reg->count);
    return EAI_OK;
}
