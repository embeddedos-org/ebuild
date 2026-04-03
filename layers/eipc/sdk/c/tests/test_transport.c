// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eipc.h"
#include <stdio.h>
#include <string.h>
#include <stdint.h>

#ifdef _WIN32
#  include <winsock2.h>
#  include <ws2tcpip.h>
#  pragma comment(lib, "ws2_32.lib")
#else
#  include <pthread.h>
#  include <unistd.h>
#  include <sys/socket.h>
#  include <netinet/in.h>
#  include <arpa/inet.h>
#endif

static int g_pass = 0;
static int g_fail = 0;

#define TEST(name) printf("  TEST  %s ...\n", name)
#define PASS(name) do { printf("  PASS  %s\n", name); g_pass++; } while(0)
#define FAIL(name, msg) do { printf("  FAIL  %s: %s\n", name, msg); g_fail++; } while(0)

#ifndef _WIN32

struct server_args {
    int listen_fd;
    eipc_frame_t received;
    int success;
};

static void *server_thread(void *arg) {
    struct server_args *sa = (struct server_args *)arg;
    sa->success = 0;

    struct sockaddr_in client_addr;
    socklen_t addr_len = sizeof(client_addr);
    int conn_fd = accept(sa->listen_fd, (struct sockaddr *)&client_addr, &addr_len);
    if (conn_fd < 0) return NULL;

    eipc_conn_t conn;
    memset(&conn, 0, sizeof(conn));
    conn.fd = conn_fd;

    eipc_message_t msg;
    memset(&msg, 0, sizeof(msg));
    eipc_status_t rc = eipc_transport_receive(conn_fd, &sa->received);
    if (rc == EIPC_OK) {
        sa->success = 1;
    }

    close(conn_fd);
    return NULL;
}

static void test_loopback_send_receive(void) {
    const char *name = "loopback_send_receive";
    TEST(name);

    int listen_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (listen_fd < 0) {
        FAIL(name, "socket() failed");
        return;
    }

    int opt = 1;
    setsockopt(listen_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = 0;

    if (bind(listen_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        close(listen_fd);
        FAIL(name, "bind() failed");
        return;
    }

    if (listen(listen_fd, 1) < 0) {
        close(listen_fd);
        FAIL(name, "listen() failed");
        return;
    }

    socklen_t alen = sizeof(addr);
    getsockname(listen_fd, (struct sockaddr *)&addr, &alen);
    int port = ntohs(addr.sin_port);

    struct server_args sa;
    memset(&sa, 0, sizeof(sa));
    sa.listen_fd = listen_fd;

    pthread_t tid;
    if (pthread_create(&tid, NULL, server_thread, &sa) != 0) {
        close(listen_fd);
        FAIL(name, "pthread_create() failed");
        return;
    }

    int client_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (client_fd < 0) {
        close(listen_fd);
        FAIL(name, "client socket() failed");
        return;
    }

    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    server_addr.sin_port = htons(port);

    if (connect(client_fd, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) {
        close(client_fd);
        close(listen_fd);
        FAIL(name, "connect() failed");
        return;
    }

    eipc_frame_t frame;
    memset(&frame, 0, sizeof(frame));
    frame.version = 1;
    frame.msg_type = 'i';
    frame.flags = 0;
    frame.header = (uint8_t *)"test-hdr";
    frame.header_len = 8;
    frame.payload = (uint8_t *)"test-payload";
    frame.payload_len = 12;

    eipc_status_t rc = eipc_transport_send(client_fd, &frame);
    close(client_fd);

    pthread_join(tid, NULL);
    close(listen_fd);

    if (rc != EIPC_OK) {
        FAIL(name, "transport_send failed");
        return;
    }

    if (!sa.success) {
        FAIL(name, "server failed to receive frame");
        return;
    }

    if (sa.received.version != 1) {
        FAIL(name, "version mismatch");
        return;
    }
    if (sa.received.msg_type != 'i') {
        FAIL(name, "msg_type mismatch");
        return;
    }
    if (sa.received.header_len != 8) {
        FAIL(name, "header_len mismatch");
        return;
    }
    if (sa.received.payload_len != 12) {
        FAIL(name, "payload_len mismatch");
        return;
    }

    PASS(name);
}

#else /* _WIN32 */

static void test_loopback_send_receive(void) {
    const char *name = "loopback_connect_close (win32)";
    TEST(name);

    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        FAIL(name, "WSAStartup failed");
        return;
    }

    SOCKET listen_sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (listen_sock == INVALID_SOCKET) {
        WSACleanup();
        FAIL(name, "socket() failed");
        return;
    }

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = 0;

    if (bind(listen_sock, (struct sockaddr *)&addr, sizeof(addr)) == SOCKET_ERROR) {
        closesocket(listen_sock);
        WSACleanup();
        FAIL(name, "bind() failed");
        return;
    }

    if (listen(listen_sock, 1) == SOCKET_ERROR) {
        closesocket(listen_sock);
        WSACleanup();
        FAIL(name, "listen() failed");
        return;
    }

    int alen = sizeof(addr);
    getsockname(listen_sock, (struct sockaddr *)&addr, &alen);
    int port = ntohs(addr.sin_port);

    SOCKET client_sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (client_sock == INVALID_SOCKET) {
        closesocket(listen_sock);
        WSACleanup();
        FAIL(name, "client socket() failed");
        return;
    }

    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    server_addr.sin_port = htons(port);

    if (connect(client_sock, (struct sockaddr *)&server_addr, sizeof(server_addr)) == SOCKET_ERROR) {
        closesocket(client_sock);
        closesocket(listen_sock);
        WSACleanup();
        FAIL(name, "connect() failed");
        return;
    }

    SOCKET accepted = accept(listen_sock, NULL, NULL);
    if (accepted == INVALID_SOCKET) {
        closesocket(client_sock);
        closesocket(listen_sock);
        WSACleanup();
        FAIL(name, "accept() failed");
        return;
    }

    closesocket(accepted);
    closesocket(client_sock);
    closesocket(listen_sock);
    WSACleanup();

    PASS(name);
}

#endif /* _WIN32 */

int main(void) {
    printf("=== EIPC Transport Tests ===\n");

    test_loopback_send_receive();

    printf("\nResults: %d passed, %d failed\n", g_pass, g_fail);
    return g_fail > 0 ? 1 : 0;
}
