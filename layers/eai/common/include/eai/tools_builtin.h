// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef EAI_TOOLS_BUILTIN_H
#define EAI_TOOLS_BUILTIN_H

#include "eai/tool.h"

eai_status_t eai_tools_register_builtins(eai_tool_registry_t *reg);

/* Individual tool registration */
eai_status_t eai_tool_mqtt_publish_register(eai_tool_registry_t *reg);
eai_status_t eai_tool_device_read_sensor_register(eai_tool_registry_t *reg);
eai_status_t eai_tool_http_get_register(eai_tool_registry_t *reg);

#endif /* EAI_TOOLS_BUILTIN_H */
