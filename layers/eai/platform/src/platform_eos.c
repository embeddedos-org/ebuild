// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eai/platform.h"
#include <stdio.h>
#include <time.h>

#if defined(EAI_PLATFORM_EOS_ENABLED)

static int eos_init(void) { return 0; }
static void eos_deinit(void) {}
static uint64_t eos_monotonic_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}
static void eos_sleep_ms(uint32_t ms) {
    struct timespec ts = { .tv_sec = ms / 1000, .tv_nsec = (ms % 1000) * 1000000 };
    nanosleep(&ts, NULL);
}
static void eos_log(const char *mod, const char *msg) {
    printf("[EoS/%s] %s\n", mod, msg);
}

const eai_platform_ops_t eai_platform_eos_ops = {
    .init         = eos_init,
    .deinit       = eos_deinit,
    .monotonic_ms = eos_monotonic_ms,
    .sleep_ms     = eos_sleep_ms,
    .log          = eos_log,
};

#endif
