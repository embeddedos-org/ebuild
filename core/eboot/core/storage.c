// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file storage.c
 * @brief Unified storage abstraction for boot media
 */

#include "eos_storage.h"
#ifdef EBOOT_ENABLE_PRINTF
#include <stdio.h>
#endif
#include <string.h>

int eos_storage_init(eos_storage_dev_t *dev)
{
    if (!dev || !dev->ops || !dev->ops->init)
        return -1;

    int rc = dev->ops->init(dev->ctx);
    if (rc == 0) {
        dev->initialized = true;
        if (dev->ops->get_size)
            dev->total_size = dev->ops->get_size(dev->ctx);
        if (dev->ops->get_erase_size)
            dev->sector_size = dev->ops->get_erase_size(dev->ctx);
    }
    return rc;
}

int eos_storage_read(eos_storage_dev_t *dev, uint32_t off, void *buf, uint32_t len)
{
    if (!dev || !dev->initialized || !dev->ops->read) return -1;
    if (off + len > dev->total_size) return -1;
    return dev->ops->read(dev->ctx, off, buf, len);
}

int eos_storage_write(eos_storage_dev_t *dev, uint32_t off, const void *buf, uint32_t len)
{
    if (!dev || !dev->initialized || !dev->ops->write) return -1;
    if (dev->write_protect) return -1;
    if (off + len > dev->total_size) return -1;
    return dev->ops->write(dev->ctx, off, buf, len);
}

int eos_storage_erase(eos_storage_dev_t *dev, uint32_t off, uint32_t len)
{
    if (!dev || !dev->initialized || !dev->ops->erase) return -1;
    if (dev->write_protect) return -1;
    return dev->ops->erase(dev->ctx, off, len);
}

void eos_storage_dump(const eos_storage_dev_t *dev)
{
#ifdef EBOOT_ENABLE_PRINTF
    const char *types[] = {"SPI_NOR","SPI_NAND","eMMC","SD","NVMe","PNOR","INTERNAL"};
    printf("Storage: %s [%s] %uKB sector=%u page=%u %s%s\n",
           dev->name ? dev->name : "(unnamed)",
           types[dev->type], dev->total_size / 1024,
           dev->sector_size, dev->page_size,
           dev->initialized ? "init" : "uninit",
           dev->write_protect ? " WP" : "");
#else
    (void)dev;
#endif
}
