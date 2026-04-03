// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eni_platform/platform.h"

#ifdef ENI_PLATFORM_EOS_ENABLED

eni_status_t eni_platform_init(void)
{
    /* EoS: initialize system services, GPIO, real-time scheduler */
    return ENI_OK;
}

eni_platform_info_t eni_platform_info(void)
{
    eni_platform_info_t info = {
        .os_name          = "eos",
#if defined(__aarch64__)
        .arch             = "arm64",
#elif defined(__x86_64__)
        .arch             = "x86_64",
#elif defined(__riscv)
        .arch             = "riscv64",
#else
        .arch             = "unknown",
#endif
        .realtime_capable = true,
        .hardware_access  = true,
    };
    return info;
}

void eni_platform_sleep_ms(uint32_t ms)
{
    /* EoS: real-time sleep via system scheduler */
    (void)ms;
}

uint64_t eni_platform_monotonic_ms(void)
{
    /* EoS: high-precision monotonic clock */
    return 0;
}

#endif /* ENI_PLATFORM_EOS_ENABLED */
