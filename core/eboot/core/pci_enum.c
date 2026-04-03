// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file pci_enum.c
 * @brief PCI/PCIe bus enumeration and device discovery
 */

#include "eos_pci.h"
#include <string.h>
#ifdef EBOOT_ENABLE_PRINTF
#include <stdio.h>
#endif

/* ECAM config space access (memory-mapped) */
static volatile uint32_t *pci_ecam_addr(uint32_t ecam_base,
                                         uint8_t bus, uint8_t dev, uint8_t func,
                                         uint16_t reg)
{
    uint32_t addr = ecam_base
        | ((uint32_t)bus << 20)
        | ((uint32_t)dev << 15)
        | ((uint32_t)func << 12)
        | (reg & 0xFFC);
    return (volatile uint32_t *)(uintptr_t)addr;
}

static uint32_t pci_read32(uint32_t ecam, uint8_t bus, uint8_t dev,
                           uint8_t func, uint16_t reg)
{
    volatile uint32_t *p = pci_ecam_addr(ecam, bus, dev, func, reg);
    return *p;
}

int eos_pci_init(eos_pci_bus_t *bus, uint32_t ecam_base)
{
    if (!bus) return -1;
    memset(bus, 0, sizeof(*bus));
    bus->ecam_base = ecam_base;
    return 0;
}

int eos_pci_enumerate(eos_pci_bus_t *bus)
{
    if (!bus || !bus->ecam_base) return -1;

    bus->count = 0;

    for (uint8_t b = 0; b < 4 && bus->count < EOS_PCI_MAX_DEVICES; b++) {
        for (uint8_t d = 0; d < 32 && bus->count < EOS_PCI_MAX_DEVICES; d++) {
            uint32_t id = pci_read32(bus->ecam_base, b, d, 0, 0);
            if (id == 0xFFFFFFFF || id == 0) continue;

            eos_pci_device_t *dev = &bus->devices[bus->count];
            dev->vendor_id = (uint16_t)(id & 0xFFFF);
            dev->device_id = (uint16_t)(id >> 16);
            dev->bus = b;
            dev->dev = d;
            dev->func = 0;

            uint32_t class_rev = pci_read32(bus->ecam_base, b, d, 0, 0x08);
            dev->class_code = (uint16_t)(class_rev >> 16);

            uint32_t hdr = pci_read32(bus->ecam_base, b, d, 0, 0x0C);
            dev->header_type = (uint8_t)((hdr >> 16) & 0x7F);
            dev->is_bridge = (dev->header_type == 1);

            for (int i = 0; i < 6; i++) {
                dev->bar[i] = pci_read32(bus->ecam_base, b, d, 0,
                                         (uint16_t)(0x10 + i * 4));
            }

            uint32_t irq = pci_read32(bus->ecam_base, b, d, 0, 0x3C);
            dev->irq_line = (uint8_t)(irq & 0xFF);

            bus->count++;
        }
    }
    return bus->count;
}

const eos_pci_device_t *eos_pci_find_device(const eos_pci_bus_t *bus,
                                             uint16_t vendor, uint16_t device)
{
    for (int i = 0; i < bus->count; i++) {
        if (bus->devices[i].vendor_id == vendor &&
            bus->devices[i].device_id == device)
            return &bus->devices[i];
    }
    return NULL;
}

const eos_pci_device_t *eos_pci_find_class(const eos_pci_bus_t *bus,
                                            uint16_t class_code)
{
    for (int i = 0; i < bus->count; i++) {
        if (bus->devices[i].class_code == class_code)
            return &bus->devices[i];
    }
    return NULL;
}

void eos_pci_dump(const eos_pci_bus_t *bus)
{
#ifdef EBOOT_ENABLE_PRINTF
    printf("PCI: %d devices (ECAM @ 0x%08x)\n", bus->count, bus->ecam_base);
    for (int i = 0; i < bus->count; i++) {
        const eos_pci_device_t *d = &bus->devices[i];
        printf("  %02x:%02x.%x  %04x:%04x  class=%04x  IRQ=%d%s\n",
               d->bus, d->dev, d->func,
               d->vendor_id, d->device_id, d->class_code,
               d->irq_line, d->is_bridge ? " [bridge]" : "");
    }
#else
    (void)bus;
#endif
}
