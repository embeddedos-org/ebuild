// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "ebot_client.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef EOSUITE_HAS_EOS_SDK
#include "eos_sdk.h"
#endif

#ifdef _WIN32
  #include <winsock2.h>
  #include <ws2tcpip.h>
  #pragma comment(lib, "ws2_32.lib")
  #define CLOSE_SOCKET closesocket
#else
  #include <sys/socket.h>
  #include <netinet/in.h>
  #include <arpa/inet.h>
  #include <unistd.h>
  #define CLOSE_SOCKET close
#endif

int ebot_client_init(ebot_client_t *c, const char *host, uint16_t port) {
    if (!c) return -1;
    memset(c, 0, sizeof(*c));
    strncpy(c->host, host ? host : EBOT_DEFAULT_HOST, 255);
    c->port = port ? port : EBOT_DEFAULT_PORT;
    c->timeout_ms = 30000;
#ifdef _WIN32
    WSADATA wsa; WSAStartup(MAKEWORD(2,2), &wsa);
#endif
#ifdef EOSUITE_HAS_EOS_SDK
    eos_sdk_init();
#endif
    return 0;
}

static int http_request(ebot_client_t *c, const char *method, const char *path,
                        const char *body, char *response, int max_len) {
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) return -1;

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(c->port);
    inet_pton(AF_INET, c->host, &addr.sin_addr);

    if (connect(fd, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        CLOSE_SOCKET(fd);
        return -1;
    }

    char request[EBOT_CLIENT_BUF];
    int rlen;
    if (body && strlen(body) > 0) {
        rlen = snprintf(request, sizeof(request),
            "%s %s HTTP/1.1\r\nHost: %s:%d\r\nContent-Type: application/json\r\n"
            "Content-Length: %d\r\nConnection: close\r\n\r\n%s",
            method, path, c->host, c->port, (int)strlen(body), body);
    } else {
        rlen = snprintf(request, sizeof(request),
            "%s %s HTTP/1.1\r\nHost: %s:%d\r\nConnection: close\r\n\r\n",
            method, path, c->host, c->port);
    }
    send(fd, request, rlen, 0);

    int total = 0;
    char buf[4096];
    while (total < max_len - 1) {
        int n = recv(fd, buf, sizeof(buf) - 1, 0);
        if (n <= 0) break;
        buf[n] = '\0';
        int copy = (total + n < max_len - 1) ? n : max_len - 1 - total;
        memcpy(response + total, buf, copy);
        total += copy;
    }
    response[total] = '\0';
    CLOSE_SOCKET(fd);

    char *json = strstr(response, "\r\n\r\n");
    if (json) { json += 4; memmove(response, json, strlen(json) + 1); }
    return 0;
}

int ebot_client_chat(ebot_client_t *c, const char *message, char *response, int max_len) {
    char body[8192];
    snprintf(body, sizeof(body), "{\"message\":\"%s\"}", message);
    return http_request(c, "POST", "/v1/chat", body, response, max_len);
}

int ebot_client_complete(ebot_client_t *c, const char *prompt, char *response, int max_len) {
    char body[8192];
    snprintf(body, sizeof(body), "{\"prompt\":\"%s\"}", prompt);
    return http_request(c, "POST", "/v1/complete", body, response, max_len);
}

int ebot_client_status(ebot_client_t *c, char *r, int m) { return http_request(c,"GET","/v1/status",NULL,r,m); }
int ebot_client_tools(ebot_client_t *c, char *r, int m)  { return http_request(c,"GET","/v1/tools",NULL,r,m); }
int ebot_client_models(ebot_client_t *c, char *r, int m) { return http_request(c,"GET","/v1/models",NULL,r,m); }
int ebot_client_reset(ebot_client_t *c, char *r, int m)  { return http_request(c,"POST","/v1/reset","{}",r,m); }