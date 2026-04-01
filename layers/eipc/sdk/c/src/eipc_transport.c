// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/*
 * EIPC Transport Layer — stub implementation
 * Provides TCP / Unix socket framing (length-prefixed).
 * TODO: Replace stubs with real socket I/O.
 */

#include "eipc.h"
#include <string.h>

eipc_status_t eipc_transport_connect(eipc_socket_t *sock,
                                     const char *address) {
    if (!sock || !address)
        return EIPC_ERR_INVALID;

    /* TODO: parse address, create socket, connect */
    *sock = EIPC_INVALID_SOCKET;
    return EIPC_ERR_CONNECT;
}

eipc_status_t eipc_transport_listen(eipc_socket_t *sock,
                                    const char *address) {
    if (!sock || !address)
        return EIPC_ERR_INVALID;

    /* TODO: parse address, bind, listen */
    *sock = EIPC_INVALID_SOCKET;
    return EIPC_ERR_CONNECT;
}

eipc_status_t eipc_transport_accept(eipc_socket_t listen_sock,
                                    eipc_socket_t *client_sock,
                                    char *remote_addr,
                                    size_t remote_addr_size) {
    if (!client_sock)
        return EIPC_ERR_INVALID;

    (void)listen_sock;
    (void)remote_addr;
    (void)remote_addr_size;

    /* TODO: accept incoming connection */
    *client_sock = EIPC_INVALID_SOCKET;
    return EIPC_ERR_CONNECT;
}

eipc_status_t eipc_transport_send_frame(eipc_socket_t sock,
                                        const eipc_frame_t *frame) {
    if (!frame)
        return EIPC_ERR_INVALID;

    (void)sock;

    /* TODO: encode frame and send over socket */
    return EIPC_ERR_IO;
}

eipc_status_t eipc_transport_recv_frame(eipc_socket_t sock,
                                        eipc_frame_t *frame) {
    if (!frame)
        return EIPC_ERR_INVALID;

    (void)sock;

    /* TODO: read length-prefixed frame from socket */
    memset(frame, 0, sizeof(*frame));
    return EIPC_ERR_IO;
}

void eipc_transport_close(eipc_socket_t sock) {
    (void)sock;
    /* TODO: close socket */
}
