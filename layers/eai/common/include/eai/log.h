// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef EAI_LOG_H
#define EAI_LOG_H

#include "eai/types.h"
#include <stdio.h>

void eai_log_set_level(eai_log_level_t level);
void eai_log_set_output(FILE *fp);
void eai_log_write(eai_log_level_t level, const char *module, const char *fmt, ...);

#define EAI_LOG_TRACE(mod, ...) eai_log_write(EAI_LOG_TRACE, mod, __VA_ARGS__)
#define EAI_LOG_DEBUG(mod, ...) eai_log_write(EAI_LOG_DEBUG, mod, __VA_ARGS__)
#define EAI_LOG_INFO(mod, ...)  eai_log_write(EAI_LOG_INFO,  mod, __VA_ARGS__)
#define EAI_LOG_WARN(mod, ...)  eai_log_write(EAI_LOG_WARN,  mod, __VA_ARGS__)
#define EAI_LOG_ERROR(mod, ...) eai_log_write(EAI_LOG_ERROR, mod, __VA_ARGS__)
#define EAI_LOG_FATAL(mod, ...) eai_log_write(EAI_LOG_FATAL, mod, __VA_ARGS__)

#endif /* EAI_LOG_H */
