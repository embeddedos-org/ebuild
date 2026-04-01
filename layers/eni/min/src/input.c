// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eni_min/input.h"
#include "eni/log.h"
#include <string.h>

eni_status_t eni_min_input_init(eni_min_input_t *input, const eni_provider_ops_t *ops,
                                 const char *provider_name, eni_transport_t transport)
{
    if (!input || !ops || !provider_name) return ENI_ERR_INVALID;

    memset(input, 0, sizeof(*input));
    input->transport = transport;
    input->connected = false;

    return eni_provider_init(&input->provider, ops, provider_name, NULL);
}

eni_status_t eni_min_input_connect(eni_min_input_t *input)
{
    if (!input) return ENI_ERR_INVALID;

    eni_status_t st = eni_provider_start(&input->provider);
    if (st == ENI_OK) {
        input->connected = true;
        ENI_LOG_INFO("min.input", "connected to provider: %s", input->provider.name);
    }
    return st;
}

eni_status_t eni_min_input_poll(eni_min_input_t *input, eni_event_t *ev)
{
    if (!input || !ev) return ENI_ERR_INVALID;
    if (!input->connected) return ENI_ERR_RUNTIME;

    return eni_provider_poll(&input->provider, ev);
}

eni_status_t eni_min_input_disconnect(eni_min_input_t *input)
{
    if (!input) return ENI_ERR_INVALID;

    eni_status_t st = eni_provider_stop(&input->provider);
    input->connected = false;
    ENI_LOG_INFO("min.input", "disconnected from provider: %s", input->provider.name);
    return st;
}

void eni_min_input_shutdown(eni_min_input_t *input)
{
    if (!input) return;
    if (input->connected) {
        eni_min_input_disconnect(input);
    }
    eni_provider_shutdown(&input->provider);
}
