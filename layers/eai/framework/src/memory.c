// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eai_fw/memory.h"
#include "eai/log.h"
#include <string.h>
#include <stdio.h>
#include <time.h>

#define LOG_MOD "fw-mem"

eai_status_t eai_fw_mem_init(eai_fw_memory_t *mem, const char *storage_dir)
{
    if (!mem) return EAI_ERR_INVALID;
    memset(mem, 0, sizeof(*mem));
    mem->storage_dir = storage_dir;
    return EAI_OK;
}

eai_status_t eai_fw_mem_set(eai_fw_memory_t *mem, const char *ns, const char *key,
                             const char *value, uint32_t ttl_sec)
{
    if (!mem || !ns || !key || !value) return EAI_ERR_INVALID;

    /* update existing */
    for (int i = 0; i < mem->count; i++) {
        if (strcmp(mem->entries[i].namespace_name, ns) == 0 &&
            strcmp(mem->entries[i].key, key) == 0) {
            strncpy(mem->entries[i].value, value, EAI_FW_MEM_VALUE_MAX - 1);
            mem->entries[i].timestamp = (uint64_t)time(NULL);
            mem->entries[i].ttl_sec = ttl_sec;
            return EAI_OK;
        }
    }

    if (mem->count >= EAI_FW_MEM_MAX_ENTRIES) {
        int gc_count = eai_fw_mem_gc(mem);
        if (gc_count == 0) return EAI_ERR_NOMEM;
    }

    eai_fw_mem_entry_t *e = &mem->entries[mem->count];
    strncpy(e->namespace_name, ns, EAI_FW_MEM_NS_MAX - 1);
    strncpy(e->key, key, EAI_FW_MEM_KEY_MAX - 1);
    strncpy(e->value, value, EAI_FW_MEM_VALUE_MAX - 1);
    e->timestamp = (uint64_t)time(NULL);
    e->ttl_sec = ttl_sec;
    e->persistent = (ttl_sec == 0);
    mem->count++;

    return EAI_OK;
}

const char *eai_fw_mem_get(const eai_fw_memory_t *mem, const char *ns, const char *key)
{
    if (!mem || !ns || !key) return NULL;
    uint64_t now = (uint64_t)time(NULL);

    for (int i = 0; i < mem->count; i++) {
        if (strcmp(mem->entries[i].namespace_name, ns) == 0 &&
            strcmp(mem->entries[i].key, key) == 0) {
            /* check expiry */
            if (mem->entries[i].ttl_sec > 0 &&
                now - mem->entries[i].timestamp > mem->entries[i].ttl_sec) {
                return NULL;
            }
            return mem->entries[i].value;
        }
    }
    return NULL;
}

eai_status_t eai_fw_mem_delete(eai_fw_memory_t *mem, const char *ns, const char *key)
{
    if (!mem || !ns || !key) return EAI_ERR_INVALID;
    for (int i = 0; i < mem->count; i++) {
        if (strcmp(mem->entries[i].namespace_name, ns) == 0 &&
            strcmp(mem->entries[i].key, key) == 0) {
            if (i < mem->count - 1) {
                memmove(&mem->entries[i], &mem->entries[i + 1],
                        (size_t)(mem->count - i - 1) * sizeof(eai_fw_mem_entry_t));
            }
            mem->count--;
            return EAI_OK;
        }
    }
    return EAI_ERR_NOT_FOUND;
}

int eai_fw_mem_gc(eai_fw_memory_t *mem)
{
    if (!mem) return 0;
    uint64_t now = (uint64_t)time(NULL);
    int removed = 0;

    for (int i = mem->count - 1; i >= 0; i--) {
        if (mem->entries[i].ttl_sec > 0 &&
            now - mem->entries[i].timestamp > mem->entries[i].ttl_sec) {
            if (i < mem->count - 1) {
                memmove(&mem->entries[i], &mem->entries[i + 1],
                        (size_t)(mem->count - i - 1) * sizeof(eai_fw_mem_entry_t));
            }
            mem->count--;
            removed++;
        }
    }

    if (removed > 0)
        EAI_LOG_DEBUG(LOG_MOD, "GC removed %d expired entries", removed);
    return removed;
}

eai_status_t eai_fw_mem_save(const eai_fw_memory_t *mem)
{
    if (!mem || !mem->storage_dir) return EAI_ERR_INVALID;

    char path[512];
    snprintf(path, sizeof(path), "%s/memory.dat", mem->storage_dir);

    FILE *fp = fopen(path, "w");
    if (!fp) return EAI_ERR_IO;

    for (int i = 0; i < mem->count; i++) {
        if (mem->entries[i].persistent) {
            fprintf(fp, "%s|%s|%s\n",
                    mem->entries[i].namespace_name,
                    mem->entries[i].key,
                    mem->entries[i].value);
        }
    }

    fclose(fp);
    EAI_LOG_INFO(LOG_MOD, "saved memory to %s", path);
    return EAI_OK;
}

eai_status_t eai_fw_mem_load(eai_fw_memory_t *mem)
{
    if (!mem || !mem->storage_dir) return EAI_ERR_INVALID;

    char path[512];
    snprintf(path, sizeof(path), "%s/memory.dat", mem->storage_dir);

    FILE *fp = fopen(path, "r");
    if (!fp) return EAI_ERR_IO;

    char line[EAI_FW_MEM_NS_MAX + EAI_FW_MEM_KEY_MAX + EAI_FW_MEM_VALUE_MAX + 4];
    while (fgets(line, sizeof(line), fp)) {
        char ns[EAI_FW_MEM_NS_MAX], key[EAI_FW_MEM_KEY_MAX], val[EAI_FW_MEM_VALUE_MAX];
        if (sscanf(line, "%31[^|]|%127[^|]|%2047[^\n]", ns, key, val) == 3) {
            eai_fw_mem_set(mem, ns, key, val, 0);
        }
    }

    fclose(fp);
    EAI_LOG_INFO(LOG_MOD, "loaded memory from %s", path);
    return EAI_OK;
}
