// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eosuite.h"
#include "platform.h"

static void quick_connect(void) {
    char input[MAX_INPUT_LEN];
    char user[128] = {0};
    char host[256] = {0};
    int port = 22;
    char cmd[MAX_PATH_LEN];

    printf("\n  Enter connection (user@host[:port]): ");
    fflush(stdout);
    if (!fgets(input, sizeof(input), stdin)) return;
    input[strcspn(input, "\r\n")] = '\0';
    if (strlen(input) == 0) return;

    char *at = strchr(input, '@');
    if (at) {
        *at = '\0';
        strncpy(user, input, sizeof(user) - 1);
        char *host_part = at + 1;

        char *colon = strchr(host_part, ':');
        if (colon) {
            *colon = '\0';
            port = atoi(colon + 1);
            if (port <= 0 || port > 65535) port = 22;
        }
        strncpy(host, host_part, sizeof(host) - 1);
    } else {
        char *colon = strchr(input, ':');
        if (colon) {
            *colon = '\0';
            port = atoi(colon + 1);
            if (port <= 0 || port > 65535) port = 22;
        }
        strncpy(host, input, sizeof(host) - 1);
    }

    if (strlen(host) == 0) {
        term_set_color(COLOR_RED, COLOR_BLACK);
        printf("  Invalid host.\n");
        term_reset_color();
        SLEEP_MS(1500);
        return;
    }

    term_set_color(COLOR_GREEN, COLOR_BLACK);
    if (strlen(user) > 0)
        printf("  Connecting to %s@%s:%d...\n", user, host, port);
    else
        printf("  Connecting to %s:%d...\n", host, port);
    term_reset_color();

    if (strlen(user) > 0)
        snprintf(cmd, sizeof(cmd), "ssh -p %d %s@%s", port, user, host);
    else
        snprintf(cmd, sizeof(cmd), "ssh -p %d %s", port, host);

    system(cmd);

    printf("\n  SSH session ended. Press any key...\n");
    key_flush();
    while (!key_available()) SLEEP_MS(50);
    key_read();
}

static void custom_connect(void) {
    char host[256] = {0};
    char user[128] = {0};
    char port_str[16] = {0};
    char identity[MAX_PATH_LEN] = {0};
    char cmd[MAX_PATH_LEN * 2];
    char input[MAX_INPUT_LEN];

    printf("\n  Host: ");
    fflush(stdout);
    if (!fgets(host, sizeof(host), stdin)) return;
    host[strcspn(host, "\r\n")] = '\0';
    if (strlen(host) == 0) return;

    printf("  Username (blank for default): ");
    fflush(stdout);
    if (fgets(user, sizeof(user), stdin))
        user[strcspn(user, "\r\n")] = '\0';

    printf("  Port (default 22): ");
    fflush(stdout);
    if (fgets(port_str, sizeof(port_str), stdin))
        port_str[strcspn(port_str, "\r\n")] = '\0';
    int port = atoi(port_str);
    if (port <= 0 || port > 65535) port = 22;

    printf("  Identity file (blank for default): ");
    fflush(stdout);
    if (fgets(identity, sizeof(identity), stdin))
        identity[strcspn(identity, "\r\n")] = '\0';

    int offset = snprintf(cmd, sizeof(cmd), "ssh -p %d", port);

    if (strlen(identity) > 0)
        offset += snprintf(cmd + offset, sizeof(cmd) - offset, " -i \"%s\"", identity);

    if (strlen(user) > 0)
        snprintf(cmd + offset, sizeof(cmd) - offset, " %s@%s", user, host);
    else
        snprintf(cmd + offset, sizeof(cmd) - offset, " %s", host);

    term_set_color(COLOR_GREEN, COLOR_BLACK);
    printf("  Connecting...\n");
    printf("  Command: %s\n", cmd);
    term_reset_color();

    printf("  Proceed? [Y/n]: ");
    fflush(stdout);
    if (fgets(input, sizeof(input), stdin)) {
        input[strcspn(input, "\r\n")] = '\0';
        if (input[0] == 'n' || input[0] == 'N') return;
    }

    system(cmd);

    printf("\n  SSH session ended. Press any key...\n");
    key_flush();
    while (!key_available()) SLEEP_MS(50);
    key_read();
}

void run_ssh_client(void) {
    char input[MAX_INPUT_LEN];

    for (;;) {
        CLEAR_SCREEN();
        term_set_color(COLOR_CYAN, COLOR_BLACK);
        printf("\n  +==============================+\n");
        printf("  |        SSH CLIENT            |\n");
        printf("  +==============================+\n");
        term_reset_color();
        printf("\n  1. Quick Connect (user@host[:port])\n");
        printf("  2. Custom Connection\n");
        printf("  0. Back\n\n");
        printf("  Select: ");
        fflush(stdout);

        if (!fgets(input, sizeof(input), stdin)) break;
        input[strcspn(input, "\r\n")] = '\0';

        if (strcmp(input, "1") == 0) quick_connect();
        else if (strcmp(input, "2") == 0) custom_connect();
        else if (strcmp(input, "0") == 0) break;
    }
}
