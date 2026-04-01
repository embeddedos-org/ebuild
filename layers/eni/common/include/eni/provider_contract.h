// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef ENI_PROVIDER_CONTRACT_H
#define ENI_PROVIDER_CONTRACT_H

#include "eni/types.h"
#include "eni/event.h"

#define ENI_PROVIDER_NAME_MAX 64

typedef struct eni_provider_s eni_provider_t;

typedef eni_status_t (*eni_provider_poll_fn)(eni_provider_t *prov, eni_event_t *ev);

typedef struct {
    const char          *name;
    eni_status_t       (*init)(eni_provider_t *prov, const void *config);
    eni_provider_poll_fn poll;
    eni_status_t       (*start)(eni_provider_t *prov);
    eni_status_t       (*stop)(eni_provider_t *prov);
    void               (*shutdown)(eni_provider_t *prov);
} eni_provider_ops_t;

struct eni_provider_s {
    char                     name[ENI_PROVIDER_NAME_MAX];
    const eni_provider_ops_t *ops;
    void                     *ctx;
    bool                      running;
    eni_transport_t           transport;
};

eni_status_t eni_provider_init(eni_provider_t *prov, const eni_provider_ops_t *ops,
                               const char *name, const void *config);
eni_status_t eni_provider_start(eni_provider_t *prov);
eni_status_t eni_provider_poll(eni_provider_t *prov, eni_event_t *ev);
eni_status_t eni_provider_stop(eni_provider_t *prov);
void         eni_provider_shutdown(eni_provider_t *prov);

#endif /* ENI_PROVIDER_CONTRACT_H */
