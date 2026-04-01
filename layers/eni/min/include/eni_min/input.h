// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef ENI_MIN_INPUT_H
#define ENI_MIN_INPUT_H

#include "eni/common.h"

typedef struct {
    eni_provider_t   provider;
    eni_transport_t  transport;
    bool             connected;
} eni_min_input_t;

eni_status_t eni_min_input_init(eni_min_input_t *input, const eni_provider_ops_t *ops,
                                 const char *provider_name, eni_transport_t transport);
eni_status_t eni_min_input_connect(eni_min_input_t *input);
eni_status_t eni_min_input_poll(eni_min_input_t *input, eni_event_t *ev);
eni_status_t eni_min_input_disconnect(eni_min_input_t *input);
void         eni_min_input_shutdown(eni_min_input_t *input);

#endif /* ENI_MIN_INPUT_H */
