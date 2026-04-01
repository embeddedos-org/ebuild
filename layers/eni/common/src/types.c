// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eni/types.h"

#ifdef _WIN32
#include <windows.h>
#else
#include <time.h>
#endif

const char *eni_status_str(eni_status_t status)
{
    switch (status) {
    case ENI_OK:               return "OK";
    case ENI_ERR_NOMEM:        return "ERR_NOMEM";
    case ENI_ERR_INVALID:      return "ERR_INVALID";
    case ENI_ERR_NOT_FOUND:    return "ERR_NOT_FOUND";
    case ENI_ERR_IO:           return "ERR_IO";
    case ENI_ERR_TIMEOUT:      return "ERR_TIMEOUT";
    case ENI_ERR_PERMISSION:   return "ERR_PERMISSION";
    case ENI_ERR_RUNTIME:      return "ERR_RUNTIME";
    case ENI_ERR_CONNECT:      return "ERR_CONNECT";
    case ENI_ERR_PROTOCOL:     return "ERR_PROTOCOL";
    case ENI_ERR_CONFIG:       return "ERR_CONFIG";
    case ENI_ERR_UNSUPPORTED:  return "ERR_UNSUPPORTED";
    case ENI_ERR_POLICY_DENIED:return "ERR_POLICY_DENIED";
    case ENI_ERR_PROVIDER:     return "ERR_PROVIDER";
    case ENI_ERR_OVERFLOW:     return "ERR_OVERFLOW";
    default:                   return "UNKNOWN";
    }
}

eni_timestamp_t eni_timestamp_now(void)
{
    eni_timestamp_t ts = {0, 0};
#ifdef _WIN32
    FILETIME ft;
    GetSystemTimeAsFileTime(&ft);
    uint64_t ticks = ((uint64_t)ft.dwHighDateTime << 32) | ft.dwLowDateTime;
    ticks -= 116444736000000000ULL; /* Windows epoch → Unix epoch */
    ts.sec  = ticks / 10000000ULL;
    ts.nsec = (uint32_t)((ticks % 10000000ULL) * 100);
#else
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    ts.sec  = (uint64_t)now.tv_sec;
    ts.nsec = (uint32_t)now.tv_nsec;
#endif
    return ts;
}
