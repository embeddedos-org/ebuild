// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef EAI_EIPC_LISTENER_H
#define EAI_EIPC_LISTENER_H

#include "eai/types.h"

#ifdef EAI_EIPC_ENABLED

#include "eipc.h"

typedef struct {
    eipc_server_t server;
    eipc_conn_t   active_conn;
    bool          listening;
    bool          has_client;
    uint64_t      received_count;
    uint64_t      ack_count;
} eai_eipc_listener_t;

eai_status_t eai_eipc_listener_init(eai_eipc_listener_t *listener);
eai_status_t eai_eipc_listener_start(eai_eipc_listener_t *listener,
                                      const char *address, const char *hmac_key);
eai_status_t eai_eipc_listener_accept(eai_eipc_listener_t *listener);
eai_status_t eai_eipc_listener_receive_intent(eai_eipc_listener_t *listener,
                                               char *intent, size_t intent_size,
                                               float *confidence);
eai_status_t eai_eipc_listener_send_ack(eai_eipc_listener_t *listener,
                                         const char *request_id, const char *status);
void         eai_eipc_listener_close(eai_eipc_listener_t *listener);
void         eai_eipc_listener_stats(const eai_eipc_listener_t *listener);

#endif /* EAI_EIPC_ENABLED */
#endif /* EAI_EIPC_LISTENER_H */
