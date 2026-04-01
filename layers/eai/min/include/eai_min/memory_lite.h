// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef EAI_MIN_MEMORY_LITE_H
#define EAI_MIN_MEMORY_LITE_H

#include "eai/types.h"

#define EAI_MEM_MAX_ENTRIES 128
#define EAI_MEM_KEY_MAX     64
#define EAI_MEM_VALUE_MAX   512

typedef struct {
    char     key[EAI_MEM_KEY_MAX];
    char     value[EAI_MEM_VALUE_MAX];
    uint64_t timestamp;
    bool     persistent;
} eai_mem_entry_t;

typedef struct {
    eai_mem_entry_t entries[EAI_MEM_MAX_ENTRIES];
    int             count;
    const char     *storage_path;  /* for persistent entries */
} eai_mem_lite_t;

eai_status_t eai_mem_lite_init(eai_mem_lite_t *mem, const char *storage_path);
eai_status_t eai_mem_lite_set(eai_mem_lite_t *mem, const char *key, const char *value, bool persistent);
const char  *eai_mem_lite_get(const eai_mem_lite_t *mem, const char *key);
eai_status_t eai_mem_lite_delete(eai_mem_lite_t *mem, const char *key);
eai_status_t eai_mem_lite_save(const eai_mem_lite_t *mem);
eai_status_t eai_mem_lite_load(eai_mem_lite_t *mem);
void         eai_mem_lite_clear(eai_mem_lite_t *mem);
int          eai_mem_lite_count(const eai_mem_lite_t *mem);

#endif /* EAI_MIN_MEMORY_LITE_H */
