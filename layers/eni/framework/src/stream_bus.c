// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eni_fw/stream_bus.h"
#include "eni/log.h"
#include <string.h>
#include <stdio.h>

eni_status_t eni_fw_stream_bus_init(eni_fw_stream_bus_t *bus)
{
    if (!bus) return ENI_ERR_INVALID;
    memset(bus, 0, sizeof(*bus));
    return ENI_OK;
}

eni_status_t eni_fw_stream_bus_push(eni_fw_stream_bus_t *bus, const eni_event_t *ev)
{
    if (!bus || !ev) return ENI_ERR_INVALID;

    if (bus->count >= ENI_FW_STREAM_BUS_CAPACITY) {
        bus->total_dropped++;
        ENI_LOG_WARN("fw.bus", "event dropped (bus full, total_dropped=%llu)",
                     (unsigned long long)bus->total_dropped);
        return ENI_ERR_OVERFLOW;
    }

    memcpy(&bus->events[bus->tail], ev, sizeof(*ev));
    bus->tail = (bus->tail + 1) % ENI_FW_STREAM_BUS_CAPACITY;
    bus->count++;
    bus->total_enqueued++;

    return ENI_OK;
}

eni_status_t eni_fw_stream_bus_pop(eni_fw_stream_bus_t *bus, eni_event_t *ev)
{
    if (!bus || !ev) return ENI_ERR_INVALID;

    if (bus->count == 0) {
        return ENI_ERR_TIMEOUT;
    }

    memcpy(ev, &bus->events[bus->head], sizeof(*ev));
    bus->head = (bus->head + 1) % ENI_FW_STREAM_BUS_CAPACITY;
    bus->count--;

    return ENI_OK;
}

int eni_fw_stream_bus_pending(const eni_fw_stream_bus_t *bus)
{
    return bus ? bus->count : 0;
}

bool eni_fw_stream_bus_empty(const eni_fw_stream_bus_t *bus)
{
    return !bus || bus->count == 0;
}

void eni_fw_stream_bus_stats(const eni_fw_stream_bus_t *bus)
{
    if (!bus) return;
    printf("[stream_bus] pending=%d enqueued=%llu dropped=%llu\n",
           bus->count,
           (unsigned long long)bus->total_enqueued,
           (unsigned long long)bus->total_dropped);
}
