// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file eos_storage.h
 * @brief Unified storage abstraction — SPI NOR, NAND, eMMC, SD, NVMe
 *
 * Provides a single API for all boot media types. The bootloader
 * uses this to read firmware images regardless of storage technology.
 */

#ifndef EOS_STORAGE_H
#define EOS_STORAGE_H

#include "eos_types.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    EOS_STORAGE_SPI_NOR,
    EOS_STORAGE_SPI_NAND,
    EOS_STORAGE_EMMC,
    EOS_STORAGE_SD,
    EOS_STORAGE_NVME,
    EOS_STORAGE_PARALLEL_NOR,
    EOS_STORAGE_INTERNAL_FLASH
} eos_storage_type_t;

typedef struct eos_storage_ops {
    int  (*init)(void *ctx);
    int  (*read)(void *ctx, uint32_t offset, void *buf, uint32_t len);
    int  (*write)(void *ctx, uint32_t offset, const void *buf, uint32_t len);
    int  (*erase)(void *ctx, uint32_t offset, uint32_t len);
    uint32_t (*get_size)(void *ctx);
    uint32_t (*get_erase_size)(void *ctx);
} eos_storage_ops_t;

typedef struct {
    const char *name;
    eos_storage_type_t type;
    const eos_storage_ops_t *ops;
    void *ctx;
    uint32_t total_size;
    uint32_t sector_size;
    uint32_t page_size;
    bool     initialized;
    bool     write_protect;
} eos_storage_dev_t;

int  eos_storage_init(eos_storage_dev_t *dev);
int  eos_storage_read(eos_storage_dev_t *dev, uint32_t off, void *buf, uint32_t len);
int  eos_storage_write(eos_storage_dev_t *dev, uint32_t off, const void *buf, uint32_t len);
int  eos_storage_erase(eos_storage_dev_t *dev, uint32_t off, uint32_t len);
void eos_storage_dump(const eos_storage_dev_t *dev);

#ifdef __cplusplus
}
#endif
#endif /* EOS_STORAGE_H */
