// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef EAI_FW_MEMORY_H
#define EAI_FW_MEMORY_H

#include "eai/types.h"

#define EAI_FW_MEM_MAX_ENTRIES  1024
#define EAI_FW_MEM_KEY_MAX      128
#define EAI_FW_MEM_VALUE_MAX    2048
#define EAI_FW_MEM_NS_MAX       32

typedef struct {
    char     namespace_name[EAI_FW_MEM_NS_MAX];
    char     key[EAI_FW_MEM_KEY_MAX];
    char     value[EAI_FW_MEM_VALUE_MAX];
    uint64_t timestamp;
    uint32_t ttl_sec;     /* 0 = no expiry */
    bool     persistent;
} eai_fw_mem_entry_t;

typedef struct {
    eai_fw_mem_entry_t entries[EAI_FW_MEM_MAX_ENTRIES];
    int                count;
    const char        *storage_dir;
} eai_fw_memory_t;

eai_status_t eai_fw_mem_init(eai_fw_memory_t *mem, const char *storage_dir);
eai_status_t eai_fw_mem_set(eai_fw_memory_t *mem, const char *ns, const char *key,
                             const char *value, uint32_t ttl_sec);
const char  *eai_fw_mem_get(const eai_fw_memory_t *mem, const char *ns, const char *key);
eai_status_t eai_fw_mem_delete(eai_fw_memory_t *mem, const char *ns, const char *key);
int          eai_fw_mem_gc(eai_fw_memory_t *mem);
eai_status_t eai_fw_mem_save(const eai_fw_memory_t *mem);
eai_status_t eai_fw_mem_load(eai_fw_memory_t *mem);

#endif /* EAI_FW_MEMORY_H */
