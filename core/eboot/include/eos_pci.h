// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file eos_pci.h
 * @brief PCI/PCIe bus enumeration and device discovery
 *
 * Required for x86_64 UEFI platforms and SoCs with PCIe controllers
 * (i.MX8M, AM64x, RPi4 CM4). MCUs without PCIe skip this.
 */

#ifndef EOS_PCI_H
#define EOS_PCI_H

#include "eos_types.h"

#ifdef __cplusplus
extern "C" {
#endif

#define EOS_PCI_MAX_DEVICES  32
#define EOS_PCI_MAX_BARS     6

typedef struct {
    uint16_t vendor_id;
    uint16_t device_id;
    uint16_t class_code;
    uint8_t  bus;
    uint8_t  dev;
    uint8_t  func;
    uint8_t  header_type;
    uint32_t bar[EOS_PCI_MAX_BARS];
    uint32_t bar_size[EOS_PCI_MAX_BARS];
    uint8_t  irq_line;
    bool     is_bridge;
    bool     is_64bit;
} eos_pci_device_t;

typedef struct {
    eos_pci_device_t devices[EOS_PCI_MAX_DEVICES];
    int count;
    uint32_t ecam_base;
} eos_pci_bus_t;

int  eos_pci_init(eos_pci_bus_t *bus, uint32_t ecam_base);
int  eos_pci_enumerate(eos_pci_bus_t *bus);
const eos_pci_device_t *eos_pci_find_device(const eos_pci_bus_t *bus,
                                             uint16_t vendor, uint16_t device);
const eos_pci_device_t *eos_pci_find_class(const eos_pci_bus_t *bus,
                                            uint16_t class_code);
void eos_pci_dump(const eos_pci_bus_t *bus);

#ifdef __cplusplus
}
#endif
#endif /* EOS_PCI_H */
