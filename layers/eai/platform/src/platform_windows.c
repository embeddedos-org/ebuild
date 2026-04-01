// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eai/platform.h"
#include "eai/log.h"
#include <string.h>
#include <stdio.h>

#define LOG_MOD "plat-win"

#ifdef _WIN32

#include <windows.h>

static eai_status_t win_init(eai_platform_t *plat)
{
    EAI_LOG_INFO(LOG_MOD, "Windows platform adapter initialized");
    return EAI_OK;
}

static eai_status_t win_get_device_info(eai_platform_t *plat, char *buf, size_t buf_size)
{
    OSVERSIONINFOA vi;
    memset(&vi, 0, sizeof(vi));
    vi.dwOSVersionInfoSize = sizeof(vi);
    snprintf(buf, buf_size, "Windows %lu.%lu (Build %lu)",
             (unsigned long)vi.dwMajorVersion,
             (unsigned long)vi.dwMinorVersion,
             (unsigned long)vi.dwBuildNumber);
    return EAI_OK;
}

static eai_status_t win_read_gpio(eai_platform_t *plat, int pin, int *value)
{
    return EAI_ERR_UNSUPPORTED;
}

static eai_status_t win_write_gpio(eai_platform_t *plat, int pin, int value)
{
    return EAI_ERR_UNSUPPORTED;
}

static eai_status_t win_get_memory_info(eai_platform_t *plat,
                                         uint64_t *total, uint64_t *available)
{
    MEMORYSTATUSEX ms;
    ms.dwLength = sizeof(ms);
    if (!GlobalMemoryStatusEx(&ms)) return EAI_ERR_IO;
    if (total)     *total     = ms.ullTotalPhys;
    if (available) *available = ms.ullAvailPhys;
    return EAI_OK;
}

static eai_status_t win_get_cpu_temp(eai_platform_t *plat, float *temp_c)
{
    return EAI_ERR_UNSUPPORTED;
}

static void win_shutdown(eai_platform_t *plat)
{
    EAI_LOG_INFO(LOG_MOD, "Windows platform shut down");
}

const eai_platform_ops_t eai_platform_windows_ops = {
    .name            = "windows",
    .init            = win_init,
    .get_device_info = win_get_device_info,
    .read_gpio       = win_read_gpio,
    .write_gpio      = win_write_gpio,
    .get_memory_info = win_get_memory_info,
    .get_cpu_temp    = win_get_cpu_temp,
    .shutdown        = win_shutdown,
};

#else /* non-Windows stub */

const eai_platform_ops_t eai_platform_windows_ops = {
    .name = "windows-unavailable",
};

#endif
