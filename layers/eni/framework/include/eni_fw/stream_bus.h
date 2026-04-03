// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef ENI_FW_STREAM_BUS_H
#define ENI_FW_STREAM_BUS_H

#include "eni/common.h"

#define ENI_FW_STREAM_BUS_CAPACITY 256

typedef struct {
    eni_event_t events[ENI_FW_STREAM_BUS_CAPACITY];
    int         head;
    int         tail;
    int         count;
    uint64_t    total_enqueued;
    uint64_t    total_dropped;
} eni_fw_stream_bus_t;

eni_status_t eni_fw_stream_bus_init(eni_fw_stream_bus_t *bus);
eni_status_t eni_fw_stream_bus_push(eni_fw_stream_bus_t *bus, const eni_event_t *ev);
eni_status_t eni_fw_stream_bus_pop(eni_fw_stream_bus_t *bus, eni_event_t *ev);
int          eni_fw_stream_bus_pending(const eni_fw_stream_bus_t *bus);
bool         eni_fw_stream_bus_empty(const eni_fw_stream_bus_t *bus);
void         eni_fw_stream_bus_stats(const eni_fw_stream_bus_t *bus);

#endif /* ENI_FW_STREAM_BUS_H */
