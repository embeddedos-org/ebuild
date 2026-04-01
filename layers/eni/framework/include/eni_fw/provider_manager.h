// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef ENI_FW_PROVIDER_MANAGER_H
#define ENI_FW_PROVIDER_MANAGER_H

#include "eni/common.h"

#define ENI_FW_MAX_PROVIDERS 16

typedef struct {
    eni_provider_t providers[ENI_FW_MAX_PROVIDERS];
    int            count;
    int            active_count;
} eni_fw_provider_manager_t;

eni_status_t eni_fw_provider_manager_init(eni_fw_provider_manager_t *mgr);
eni_status_t eni_fw_provider_manager_add(eni_fw_provider_manager_t *mgr,
                                          const eni_provider_ops_t *ops,
                                          const char *name,
                                          const void *config);
eni_status_t eni_fw_provider_manager_start_all(eni_fw_provider_manager_t *mgr);
eni_status_t eni_fw_provider_manager_stop_all(eni_fw_provider_manager_t *mgr);
eni_status_t eni_fw_provider_manager_poll_any(eni_fw_provider_manager_t *mgr,
                                               eni_event_t *ev, int *provider_index);
void         eni_fw_provider_manager_shutdown(eni_fw_provider_manager_t *mgr);

#endif /* ENI_FW_PROVIDER_MANAGER_H */
