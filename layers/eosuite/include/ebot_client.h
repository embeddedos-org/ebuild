// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef EBOT_CLIENT_H
#define EBOT_CLIENT_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define EBOT_CLIENT_VERSION  "0.1.0"
#define EBOT_DEFAULT_HOST    "192.168.1.100"
#define EBOT_DEFAULT_PORT    8420
#define EBOT_CLIENT_BUF      65536

/*
 * Network Configuration
 *
 * Default: 192.168.1.100:8420 (EoS device on local network)
 *
 * Override at runtime:
 *   ebot --host 10.0.0.50 --port 9000 chat "hello"
 *
 * Or in code:
 *   ebot_client_init(&c, "10.0.0.50", 9000);
 *
 * Common configurations:
 *   192.168.1.100:8420  — EoS device (default)
 *   127.0.0.1:8420      — local development
 *   0.0.0.0:8420        — bind all interfaces (server)
 */

typedef struct {
    char host[256];
    uint16_t port;
    int timeout_ms;
} ebot_client_t;

int  ebot_client_init(ebot_client_t *c, const char *host, uint16_t port);
int  ebot_client_chat(ebot_client_t *c, const char *message, char *response, int max_len);
int  ebot_client_complete(ebot_client_t *c, const char *prompt, char *response, int max_len);
int  ebot_client_status(ebot_client_t *c, char *response, int max_len);
int  ebot_client_tools(ebot_client_t *c, char *response, int max_len);
int  ebot_client_models(ebot_client_t *c, char *response, int max_len);
int  ebot_client_reset(ebot_client_t *c, char *response, int max_len);

#ifdef __cplusplus
}
#endif
#endif