// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "ebot_client.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#ifdef EOSUITE_HAS_EOS_SDK
#include "eos_sdk.h"
#endif

/* ── Suggestions / Help System ── */

static const char *suggestions[] = {
    "How to configure GPIO on STM32?",
    "Explain the A/B firmware update flow in eboot",
    "What HAL peripherals does EoS support?",
    "How to set up SPI communication?",
    "Explain multicore SMP boot sequence",
    "How to create a custom product profile?",
    "What is the OTA update workflow?",
    "How to configure CAN bus for automotive?",
    "Explain the EIPC security model",
    "How to add a new board port to eboot?",
    "What RTOS backends does ebuild support?",
    "How to use the sensor framework?",
    "Explain BLE integration for IoT devices",
    "How to cross-compile for RISC-V?",
    "What is the EAI agent loop?",
    NULL
};

static void print_banner(void) {
    printf("\n");
    printf("  ╔══════════════════════════════════════════════╗\n");
    printf("  ║        Ebot — EoS AI Assistant               ║\n");
    printf("  ║        v%s                                ║\n", EBOT_CLIENT_VERSION);
    printf("  ╠══════════════════════════════════════════════╣\n");
    printf("  ║  Server: %s:%d              ║\n", EBOT_DEFAULT_HOST, EBOT_DEFAULT_PORT);
#ifdef EOSUITE_HAS_EOS_SDK
    printf("  ║  SDK:    EoS SDK %s                      ║\n", eos_sdk_version());
#endif
    printf("  ╚══════════════════════════════════════════════╝\n\n");
}

static void print_help(void) {
    print_banner();
    printf("  Commands:\n");
    printf("  ─────────────────────────────────────────────\n");
    printf("  ebot chat \"message\"       Chat with Ebot AI\n");
    printf("  ebot ask \"question\"       Same as chat\n");
    printf("  ebot complete \"prompt\"    Text completion\n");
    printf("  ebot interactive          Interactive chat window\n");
    printf("  ebot suggest              Show prompt suggestions\n");
    printf("  ebot status               Server status\n");
    printf("  ebot tools                List available tools\n");
    printf("  ebot models               List available models\n");
    printf("  ebot reset                Reset conversation\n");
    printf("  ebot help                 Show this help\n");
    printf("  ebot version              Version info\n");
    printf("\n");
    printf("  Options:\n");
    printf("  ─────────────────────────────────────────────\n");
    printf("  --host HOST    Server host (default: %s)\n", EBOT_DEFAULT_HOST);
    printf("  --port PORT    Server port (default: %d)\n", EBOT_DEFAULT_PORT);
    printf("\n");
    printf("  Examples:\n");
    printf("  ─────────────────────────────────────────────\n");
    printf("  ebot chat \"How to configure PWM on STM32?\"\n");
    printf("  ebot ask \"Explain CAN bus protocol\"\n");
    printf("  ebot --host 10.0.0.50 chat \"hello\"\n");
    printf("  ebot interactive\n");
    printf("\n");
}

static void print_suggestions(void) {
    printf("\n  ╔══════════════════════════════════════════════╗\n");
    printf("  ║            Suggested Prompts                 ║\n");
    printf("  ╠══════════════════════════════════════════════╣\n");
    for (int i = 0; suggestions[i]; i++) {
        printf("  ║  [%2d] %-39s║\n", i+1, suggestions[i]);
    }
    printf("  ╚══════════════════════════════════════════════╝\n");
    printf("\n  Usage: ebot chat \"%s\"\n", suggestions[0]);
    printf("  Or:    ebot interactive  (then pick a number)\n\n");
}

static void extract_content(const char *json, char *out, int max) {
    const char *p = strstr(json, "\"content\":\"");
    if (!p) { strncpy(out, json, max - 1); out[max-1] = '\0'; return; }
    p += 11;
    int i = 0;
    while (*p && *p != '"' && i < max - 1) {
        if (*p == '\\' && *(p+1) == 'n')  { out[i++] = '\n'; p += 2; continue; }
        if (*p == '\\' && *(p+1) == '"')  { out[i++] = '"';  p += 2; continue; }
        if (*p == '\\' && *(p+1) == 't')  { out[i++] = '\t'; p += 2; continue; }
        if (*p == '\\' && *(p+1) == '\\') { out[i++] = '\\'; p += 2; continue; }
        out[i++] = *p++;
    }
    out[i] = '\0';
}

/* ── Interactive Chat Window ── */

static void interactive_mode(ebot_client_t *c) {
    char input[4096], response[65536], content[65536];
    int turn = 0;

    print_banner();
    printf("  Interactive Chat Window\n");
    printf("  ─────────────────────────────────────────────\n");
    printf("  Type a message, or use these commands:\n");
    printf("    /help        Show help\n");
    printf("    /suggest     Show prompt suggestions\n");
    printf("    /status      Server status\n");
    printf("    /tools       List tools\n");
    printf("    /models      List models\n");
    printf("    /reset       Reset conversation\n");
    printf("    /clear       Clear screen\n");
    printf("    /quit        Exit\n");
    printf("  ─────────────────────────────────────────────\n\n");

    while (1) {
        printf("  You [%d]> ", ++turn);
        fflush(stdout);
        if (!fgets(input, sizeof(input), stdin)) break;
        input[strcspn(input, "\n")] = '\0';
        if (input[0] == '\0') { turn--; continue; }

        /* Handle slash commands */
        if (strcmp(input, "/quit") == 0 || strcmp(input, "/exit") == 0 ||
            strcmp(input, "quit") == 0 || strcmp(input, "exit") == 0) break;
        if (strcmp(input, "/help") == 0) { print_help(); turn--; continue; }
        if (strcmp(input, "/suggest") == 0) { print_suggestions(); turn--; continue; }
        if (strcmp(input, "/clear") == 0) {
            #ifdef _WIN32
            system("cls");
            #else
            system("clear");
            #endif
            turn = 0; continue;
        }
        if (strcmp(input, "/reset") == 0) {
            ebot_client_reset(c, response, sizeof(response));
            printf("\n  [Conversation reset]\n\n");
            turn = 0; continue;
        }
        if (strcmp(input, "/status") == 0) {
            if (ebot_client_status(c, response, sizeof(response)) == 0)
                printf("\n  %s\n\n", response);
            else printf("\n  [Cannot reach server]\n\n");
            turn--; continue;
        }
        if (strcmp(input, "/tools") == 0) {
            if (ebot_client_tools(c, response, sizeof(response)) == 0)
                printf("\n  %s\n\n", response);
            turn--; continue;
        }
        if (strcmp(input, "/models") == 0) {
            if (ebot_client_models(c, response, sizeof(response)) == 0)
                printf("\n  %s\n\n", response);
            turn--; continue;
        }

        /* Handle suggestion numbers */
        if (input[0] >= '1' && input[0] <= '9' && strlen(input) <= 2) {
            int idx = atoi(input) - 1;
            int count = 0;
            while (suggestions[count]) count++;
            if (idx >= 0 && idx < count) {
                printf("  → Using suggestion: %s\n", suggestions[idx]);
                strncpy(input, suggestions[idx], sizeof(input) - 1);
            }
        }

        /* Send to Ebot server */
        if (ebot_client_chat(c, input, response, sizeof(response)) == 0) {
            extract_content(response, content, sizeof(content));
            printf("\n  Ebot> %s\n\n", content);
        } else {
            printf("\n  [Error: cannot reach Ebot server at %s:%d]\n", c->host, c->port);
            printf("  [Try: ebot --host 127.0.0.1 interactive  for local testing]\n\n");
        }
    }
    printf("\n  Goodbye! 👋\n\n");
}

/* ── Main ── */

int main(int argc, char *argv[]) {
    if (argc < 2) { print_help(); print_suggestions(); return 0; }

    const char *host = NULL;
    uint16_t port = 0;
    int arg_start = 1;
    for (int i = 1; i < argc - 1; i++) {
        if (strcmp(argv[i], "--host") == 0) { host = argv[++i]; arg_start = i + 1; }
        else if (strcmp(argv[i], "--port") == 0) { port = (uint16_t)atoi(argv[++i]); arg_start = i + 1; }
    }

    ebot_client_t client;
    ebot_client_init(&client, host, port);

    const char *cmd = argv[arg_start];
    char response[65536], content[65536];

    if (strcmp(cmd, "help") == 0 || strcmp(cmd, "--help") == 0 || strcmp(cmd, "-h") == 0) {
        print_help();
    } else if (strcmp(cmd, "version") == 0 || strcmp(cmd, "--version") == 0) {
        print_banner();
    } else if (strcmp(cmd, "suggest") == 0) {
        print_suggestions();
    } else if (strcmp(cmd, "interactive") == 0) {
        interactive_mode(&client);
    } else if (strcmp(cmd, "chat") == 0 || strcmp(cmd, "ask") == 0) {
        if (arg_start + 1 >= argc) {
            printf("Usage: ebot chat \"your message\"\n\n");
            printf("Try one of these:\n");
            for (int i = 0; i < 5 && suggestions[i]; i++)
                printf("  ebot chat \"%s\"\n", suggestions[i]);
            return 1;
        }
        if (ebot_client_chat(&client, argv[arg_start + 1], response, sizeof(response)) == 0) {
            extract_content(response, content, sizeof(content));
            printf("%s\n", content);
        } else {
            fprintf(stderr, "Error: cannot connect to %s:%d\n", client.host, client.port);
            return 1;
        }
    } else if (strcmp(cmd, "complete") == 0) {
        if (arg_start + 1 >= argc) { printf("Usage: ebot complete \"prompt\"\n"); return 1; }
        if (ebot_client_complete(&client, argv[arg_start + 1], response, sizeof(response)) == 0) {
            extract_content(response, content, sizeof(content));
            printf("%s\n", content);
        } else { fprintf(stderr, "Error: cannot connect to %s:%d\n", client.host, client.port); return 1; }
    } else if (strcmp(cmd, "status") == 0) {
        if (ebot_client_status(&client, response, sizeof(response)) == 0) printf("%s\n", response);
        else fprintf(stderr, "Error: cannot connect\n");
    } else if (strcmp(cmd, "tools") == 0) {
        if (ebot_client_tools(&client, response, sizeof(response)) == 0) printf("%s\n", response);
    } else if (strcmp(cmd, "models") == 0) {
        if (ebot_client_models(&client, response, sizeof(response)) == 0) printf("%s\n", response);
    } else if (strcmp(cmd, "reset") == 0) {
        if (ebot_client_reset(&client, response, sizeof(response)) == 0) printf("Conversation reset.\n");
    } else {
        printf("Unknown command: %s\n\n", cmd);
        print_help();
    }
    return 0;
}