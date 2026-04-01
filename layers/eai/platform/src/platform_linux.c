// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eai/platform.h"
#include "eai/log.h"
#include <string.h>
#include <stdio.h>

#define LOG_MOD "plat-linux"

#ifndef _WIN32

#ifdef __linux__
#include <sys/sysinfo.h>
#endif
#include <unistd.h>

static eai_status_t linux_init(eai_platform_t *plat)
{
    EAI_LOG_INFO(LOG_MOD, "Linux platform adapter initialized");
    return EAI_OK;
}

static eai_status_t linux_get_device_info(eai_platform_t *plat, char *buf, size_t buf_size)
{
    FILE *fp = fopen("/etc/os-release", "r");
    if (!fp) {
        snprintf(buf, buf_size, "Linux (unknown)");
        return EAI_OK;
    }
    char line[256];
    while (fgets(line, sizeof(line), fp)) {
        if (strncmp(line, "PRETTY_NAME=", 12) == 0) {
            char *start = strchr(line, '"');
            if (start) {
                start++;
                char *end = strchr(start, '"');
                if (end) *end = '\0';
                snprintf(buf, buf_size, "%s", start);
                fclose(fp);
                return EAI_OK;
            }
        }
    }
    fclose(fp);
    snprintf(buf, buf_size, "Linux");
    return EAI_OK;
}

static eai_status_t linux_read_gpio(eai_platform_t *plat, int pin, int *value)
{
    char path[128];
    snprintf(path, sizeof(path), "/sys/class/gpio/gpio%d/value", pin);
    FILE *fp = fopen(path, "r");
    if (!fp) return EAI_ERR_IO;
    if (fscanf(fp, "%d", value) != 1) {
        fclose(fp);
        return EAI_ERR_IO;
    }
    fclose(fp);
    return EAI_OK;
}

static eai_status_t linux_write_gpio(eai_platform_t *plat, int pin, int value)
{
    char path[128];
    snprintf(path, sizeof(path), "/sys/class/gpio/gpio%d/value", pin);
    FILE *fp = fopen(path, "w");
    if (!fp) return EAI_ERR_IO;
    fprintf(fp, "%d", value);
    fclose(fp);
    return EAI_OK;
}

static eai_status_t linux_get_memory_info(eai_platform_t *plat,
                                           uint64_t *total, uint64_t *available)
{
#ifdef __linux__
    struct sysinfo si;
    if (sysinfo(&si) != 0) return EAI_ERR_IO;
    if (total)     *total     = (uint64_t)si.totalram * si.mem_unit;
    if (available) *available = (uint64_t)si.freeram  * si.mem_unit;
    return EAI_OK;
#else
    if (total)     *total     = 0;
    if (available) *available = 0;
    return EAI_ERR_UNSUPPORTED;
#endif
}

static eai_status_t linux_get_cpu_temp(eai_platform_t *plat, float *temp_c)
{
    FILE *fp = fopen("/sys/class/thermal/thermal_zone0/temp", "r");
    if (!fp) return EAI_ERR_IO;
    int millideg;
    if (fscanf(fp, "%d", &millideg) != 1) {
        fclose(fp);
        return EAI_ERR_IO;
    }
    fclose(fp);
    *temp_c = millideg / 1000.0f;
    return EAI_OK;
}

static void linux_shutdown(eai_platform_t *plat)
{
    EAI_LOG_INFO(LOG_MOD, "Linux platform shut down");
}

const eai_platform_ops_t eai_platform_linux_ops = {
    .name            = "linux",
    .init            = linux_init,
    .get_device_info = linux_get_device_info,
    .read_gpio       = linux_read_gpio,
    .write_gpio      = linux_write_gpio,
    .get_memory_info = linux_get_memory_info,
    .get_cpu_temp    = linux_get_cpu_temp,
    .shutdown        = linux_shutdown,
};

#else /* _WIN32 stub so the symbol exists on Windows builds */

const eai_platform_ops_t eai_platform_linux_ops = {
    .name = "linux-unavailable",
};

#endif
