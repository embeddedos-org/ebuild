// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef ENI_EIPC_BRIDGE_H
#define ENI_EIPC_BRIDGE_H

#include "eni/types.h"

#ifdef ENI_EIPC_ENABLED

#include "eipc.h"

typedef enum {
    ENI_EIPC_MODE_FORWARD,
    ENI_EIPC_MODE_DUAL,
} eni_eipc_mode_t;

typedef struct {
    eipc_client_t  client;
    eni_eipc_mode_t mode;
    bool           connected;
    uint64_t       sent_count;
    uint64_t       ack_count;
    uint64_t       error_count;
} eni_eipc_bridge_t;

eni_status_t eni_eipc_bridge_init(eni_eipc_bridge_t *bridge, eni_eipc_mode_t mode);
eni_status_t eni_eipc_bridge_connect(eni_eipc_bridge_t *bridge,
                                      const char *address, const char *hmac_key,
                                      const char *service_id);
eni_status_t eni_eipc_bridge_send_intent(eni_eipc_bridge_t *bridge,
                                          const char *intent, float confidence);
eni_status_t eni_eipc_bridge_send_tool_request(eni_eipc_bridge_t *bridge,
                                                const char *tool,
                                                const eni_kv_t *args, int arg_count);
eni_status_t eni_eipc_bridge_poll_ack(eni_eipc_bridge_t *bridge);
void         eni_eipc_bridge_close(eni_eipc_bridge_t *bridge);
void         eni_eipc_bridge_stats(const eni_eipc_bridge_t *bridge);

#endif /* ENI_EIPC_ENABLED */
#endif /* ENI_EIPC_BRIDGE_H */
