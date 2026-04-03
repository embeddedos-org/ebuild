// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eni/log.h"
#include <stdarg.h>
#include <time.h>

static eni_log_level_t s_log_level = ENI_LOG_INFO;
static FILE           *s_log_out   = NULL;

void eni_log_set_level(eni_log_level_t level)
{
    s_log_level = level;
}

void eni_log_set_output(FILE *fp)
{
    s_log_out = fp;
}

void eni_log_write(eni_log_level_t level, const char *module, const char *fmt, ...)
{
    if (level < s_log_level) return;

    FILE *out = s_log_out ? s_log_out : stderr;

    const char *level_str;
    switch (level) {
    case ENI_LOG_TRACE: level_str = "TRACE"; break;
    case ENI_LOG_DEBUG: level_str = "DEBUG"; break;
    case ENI_LOG_INFO:  level_str = "INFO";  break;
    case ENI_LOG_WARN:  level_str = "WARN";  break;
    case ENI_LOG_ERROR: level_str = "ERROR"; break;
    case ENI_LOG_FATAL: level_str = "FATAL"; break;
    default:            level_str = "???";   break;
    }

    time_t now = time(NULL);
    struct tm *t = localtime(&now);
    fprintf(out, "%04d-%02d-%02d %02d:%02d:%02d [%s] [%s] ",
            t->tm_year + 1900, t->tm_mon + 1, t->tm_mday,
            t->tm_hour, t->tm_min, t->tm_sec,
            level_str, module ? module : "eni");

    va_list args;
    va_start(args, fmt);
    vfprintf(out, fmt, args);
    va_end(args);

    fprintf(out, "\n");
    fflush(out);
}
