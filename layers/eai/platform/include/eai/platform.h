// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef EAI_PLATFORM_H
#define EAI_PLATFORM_H

#include "eai/types.h"

typedef struct eai_platform_s eai_platform_t;

typedef struct {
    const char *name;
    eai_status_t (*init)(eai_platform_t *plat);
    eai_status_t (*get_device_info)(eai_platform_t *plat, char *buf, size_t buf_size);
    eai_status_t (*read_gpio)(eai_platform_t *plat, int pin, int *value);
    eai_status_t (*write_gpio)(eai_platform_t *plat, int pin, int value);
    eai_status_t (*get_memory_info)(eai_platform_t *plat, uint64_t *total, uint64_t *available);
    eai_status_t (*get_cpu_temp)(eai_platform_t *plat, float *temp_c);
    void         (*shutdown)(eai_platform_t *plat);
} eai_platform_ops_t;

struct eai_platform_s {
    const eai_platform_ops_t *ops;
    void                     *ctx;
    bool                      initialized;
};

eai_status_t eai_platform_init(eai_platform_t *plat, const eai_platform_ops_t *ops);
eai_status_t eai_platform_detect(eai_platform_t *plat);
void         eai_platform_shutdown(eai_platform_t *plat);

extern const eai_platform_ops_t eai_platform_linux_ops;
extern const eai_platform_ops_t eai_platform_windows_ops;
extern const eai_platform_ops_t eai_platform_container_ops;
extern const eai_platform_ops_t eai_platform_eos_ops;

#endif /* EAI_PLATFORM_H */
