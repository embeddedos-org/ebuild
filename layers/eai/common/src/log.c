// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eai/log.h"
#include "eai/types.h"
#include <stdio.h>
#include <stdarg.h>
#include <time.h>

static eai_log_level_t g_log_level = EAI_LOG_INFO;
static FILE           *g_log_fp    = NULL;

static const char *level_names[] = {
    "TRACE", "DEBUG", "INFO", "WARN", "ERROR", "FATAL"
};

static const char *level_colors[] = {
    "\033[90m",   /* TRACE: gray */
    "\033[36m",   /* DEBUG: cyan */
    "\033[32m",   /* INFO:  green */
    "\033[33m",   /* WARN:  yellow */
    "\033[31m",   /* ERROR: red */
    "\033[35m",   /* FATAL: magenta */
};

void eai_log_set_level(eai_log_level_t level)
{
    g_log_level = level;
}

void eai_log_set_output(FILE *fp)
{
    g_log_fp = fp;
}

void eai_log_write(eai_log_level_t level, const char *module, const char *fmt, ...)
{
    if (level < g_log_level) return;

    FILE *out = g_log_fp ? g_log_fp : stderr;

    time_t now = time(NULL);
    struct tm *t = localtime(&now);
    char timebuf[32];
    strftime(timebuf, sizeof(timebuf), "%H:%M:%S", t);

    fprintf(out, "%s%s [%s] %s: ",
            level_colors[level], timebuf, level_names[level], module);

    va_list args;
    va_start(args, fmt);
    vfprintf(out, fmt, args);
    va_end(args);

    fprintf(out, "\033[0m\n");
    fflush(out);
}
