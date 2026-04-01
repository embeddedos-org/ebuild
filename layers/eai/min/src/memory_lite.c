// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eai_min/memory_lite.h"
#include "eai/log.h"
#include <string.h>
#include <stdio.h>
#include <time.h>

#define LOG_MOD "mem-lite"

eai_status_t eai_mem_lite_init(eai_mem_lite_t *mem, const char *storage_path)
{
    if (!mem) return EAI_ERR_INVALID;
    memset(mem, 0, sizeof(*mem));
    mem->storage_path = storage_path;
    return EAI_OK;
}

eai_status_t eai_mem_lite_set(eai_mem_lite_t *mem, const char *key, const char *value,
                               bool persistent)
{
    if (!mem || !key || !value) return EAI_ERR_INVALID;

    /* update existing entry */
    for (int i = 0; i < mem->count; i++) {
        if (strcmp(mem->entries[i].key, key) == 0) {
            strncpy(mem->entries[i].value, value, EAI_MEM_VALUE_MAX - 1);
            mem->entries[i].value[EAI_MEM_VALUE_MAX - 1] = '\0';
            mem->entries[i].timestamp = (uint64_t)time(NULL);
            mem->entries[i].persistent = persistent;
            return EAI_OK;
        }
    }

    /* add new entry */
    if (mem->count >= EAI_MEM_MAX_ENTRIES) {
        EAI_LOG_WARN(LOG_MOD, "memory full (%d entries), evicting oldest", mem->count);
        /* evict oldest non-persistent entry */
        int oldest = -1;
        uint64_t oldest_ts = UINT64_MAX;
        for (int i = 0; i < mem->count; i++) {
            if (!mem->entries[i].persistent && mem->entries[i].timestamp < oldest_ts) {
                oldest = i;
                oldest_ts = mem->entries[i].timestamp;
            }
        }
        if (oldest < 0) return EAI_ERR_NOMEM;
        /* shift entries */
        if (oldest < mem->count - 1) {
            memmove(&mem->entries[oldest], &mem->entries[oldest + 1],
                    (size_t)(mem->count - oldest - 1) * sizeof(eai_mem_entry_t));
        }
        mem->count--;
    }

    eai_mem_entry_t *e = &mem->entries[mem->count];
    strncpy(e->key, key, EAI_MEM_KEY_MAX - 1);
    e->key[EAI_MEM_KEY_MAX - 1] = '\0';
    strncpy(e->value, value, EAI_MEM_VALUE_MAX - 1);
    e->value[EAI_MEM_VALUE_MAX - 1] = '\0';
    e->timestamp  = (uint64_t)time(NULL);
    e->persistent = persistent;
    mem->count++;

    return EAI_OK;
}

const char *eai_mem_lite_get(const eai_mem_lite_t *mem, const char *key)
{
    if (!mem || !key) return NULL;
    for (int i = 0; i < mem->count; i++) {
        if (strcmp(mem->entries[i].key, key) == 0) {
            return mem->entries[i].value;
        }
    }
    return NULL;
}

eai_status_t eai_mem_lite_delete(eai_mem_lite_t *mem, const char *key)
{
    if (!mem || !key) return EAI_ERR_INVALID;
    for (int i = 0; i < mem->count; i++) {
        if (strcmp(mem->entries[i].key, key) == 0) {
            if (i < mem->count - 1) {
                memmove(&mem->entries[i], &mem->entries[i + 1],
                        (size_t)(mem->count - i - 1) * sizeof(eai_mem_entry_t));
            }
            mem->count--;
            return EAI_OK;
        }
    }
    return EAI_ERR_NOT_FOUND;
}

eai_status_t eai_mem_lite_save(const eai_mem_lite_t *mem)
{
    if (!mem || !mem->storage_path) return EAI_ERR_INVALID;

    FILE *fp = fopen(mem->storage_path, "w");
    if (!fp) return EAI_ERR_IO;

    for (int i = 0; i < mem->count; i++) {
        if (mem->entries[i].persistent) {
            fprintf(fp, "%s=%s\n", mem->entries[i].key, mem->entries[i].value);
        }
    }

    fclose(fp);
    EAI_LOG_INFO(LOG_MOD, "saved memory to %s", mem->storage_path);
    return EAI_OK;
}

eai_status_t eai_mem_lite_load(eai_mem_lite_t *mem)
{
    if (!mem || !mem->storage_path) return EAI_ERR_INVALID;

    FILE *fp = fopen(mem->storage_path, "r");
    if (!fp) return EAI_ERR_IO;

    char line[EAI_MEM_KEY_MAX + EAI_MEM_VALUE_MAX + 2];
    while (fgets(line, sizeof(line), fp)) {
        char *eq = strchr(line, '=');
        if (!eq) continue;
        *eq = '\0';
        char *val = eq + 1;
        /* strip newline */
        size_t vlen = strlen(val);
        if (vlen > 0 && val[vlen - 1] == '\n') val[vlen - 1] = '\0';

        eai_mem_lite_set(mem, line, val, true);
    }

    fclose(fp);
    EAI_LOG_INFO(LOG_MOD, "loaded memory from %s", mem->storage_path);
    return EAI_OK;
}

void eai_mem_lite_clear(eai_mem_lite_t *mem)
{
    if (!mem) return;
    mem->count = 0;
    memset(mem->entries, 0, sizeof(mem->entries));
}

int eai_mem_lite_count(const eai_mem_lite_t *mem)
{
    return mem ? mem->count : 0;
}
