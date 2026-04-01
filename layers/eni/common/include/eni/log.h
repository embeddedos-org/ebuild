// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef ENI_LOG_H
#define ENI_LOG_H

#include "eni/types.h"
#include <stdio.h>

void eni_log_set_level(eni_log_level_t level);
void eni_log_set_output(FILE *fp);
void eni_log_write(eni_log_level_t level, const char *module, const char *fmt, ...);

#define ENI_LOG_TRACE(mod, ...) eni_log_write(ENI_LOG_TRACE, mod, __VA_ARGS__)
#define ENI_LOG_DEBUG(mod, ...) eni_log_write(ENI_LOG_DEBUG, mod, __VA_ARGS__)
#define ENI_LOG_INFO(mod, ...)  eni_log_write(ENI_LOG_INFO,  mod, __VA_ARGS__)
#define ENI_LOG_WARN(mod, ...)  eni_log_write(ENI_LOG_WARN,  mod, __VA_ARGS__)
#define ENI_LOG_ERROR(mod, ...) eni_log_write(ENI_LOG_ERROR, mod, __VA_ARGS__)
#define ENI_LOG_FATAL(mod, ...) eni_log_write(ENI_LOG_FATAL, mod, __VA_ARGS__)

#endif /* ENI_LOG_H */
