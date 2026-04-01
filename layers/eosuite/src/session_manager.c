// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eosuite.h"
#include "platform.h"

typedef struct {
    char name[64];
    char type[16];
    char host[256];
    int  port;
    char username[128];
    char device[MAX_PATH_LEN];
    int  baud;
} Session;

static Session sessions[MAX_SESSIONS];
static int session_count = 0;
static char config_dir[MAX_PATH_LEN] = {0};
static char config_file[MAX_PATH_LEN] = {0};

static void init_config_path(void) {
#ifdef _WIN32
    const char *appdata = getenv("APPDATA");
    if (appdata) {
        snprintf(config_dir, sizeof(config_dir), "%s\\EOSUITE", appdata);
        snprintf(config_file, sizeof(config_file), "%s\\sessions.cfg", config_dir);
    } else {
        snprintf(config_dir, sizeof(config_dir), ".\\EOSUITE");
        snprintf(config_file, sizeof(config_file), ".\\EOSUITE\\sessions.cfg");
    }
    CreateDirectoryA(config_dir, NULL);
#else
    const char *home = getenv("HOME");
    if (home) {
        snprintf(config_dir, sizeof(config_dir), "%s/.config/EOSUITE", home);
        snprintf(config_file, sizeof(config_file), "%s/.config/EOSUITE/sessions.cfg", home);
    } else {
        snprintf(config_dir, sizeof(config_dir), "./.config/EOSUITE");
        snprintf(config_file, sizeof(config_file), "./.config/EOSUITE/sessions.cfg");
    }
    char mkdir_cmd[MAX_PATH_LEN + 16];
    snprintf(mkdir_cmd, sizeof(mkdir_cmd), "mkdir -p \"%s\"", config_dir);
    system(mkdir_cmd);
#endif
}

static void load_sessions(void) {
    session_count = 0;
    FILE *f = fopen(config_file, "r");
    if (!f) return;

    char line[1024];
    while (session_count < MAX_SESSIONS && fgets(line, sizeof(line), f)) {
        line[strcspn(line, "\r\n")] = '\0';
        if (strlen(line) == 0) continue;

        Session *s = &sessions[session_count];
        memset(s, 0, sizeof(Session));

        char port_str[16] = {0};
        char baud_str[16] = {0};

        char *fields[7] = {NULL};
        int fi = 0;
        char *tok = line;
        for (int i = 0; i < 7 && tok; i++) {
            fields[i] = tok;
            char *pipe = strchr(tok, '|');
            if (pipe) {
                *pipe = '\0';
                tok = pipe + 1;
            } else {
                tok = NULL;
            }
            fi++;
        }

        if (fi >= 1 && fields[0]) strncpy(s->name, fields[0], sizeof(s->name) - 1);
        if (fi >= 2 && fields[1]) strncpy(s->type, fields[1], sizeof(s->type) - 1);
        if (fi >= 3 && fields[2]) strncpy(s->host, fields[2], sizeof(s->host) - 1);
        if (fi >= 4 && fields[3]) s->port = atoi(fields[3]);
        if (fi >= 5 && fields[4]) strncpy(s->username, fields[4], sizeof(s->username) - 1);
        if (fi >= 6 && fields[5]) strncpy(s->device, fields[5], sizeof(s->device) - 1);
        if (fi >= 7 && fields[6]) s->baud = atoi(fields[6]);

        session_count++;
    }
    fclose(f);
}

static void save_sessions(void) {
    FILE *f = fopen(config_file, "w");
    if (!f) {
        term_set_color(COLOR_RED, COLOR_BLACK);
        printf("  Error: cannot save sessions.\n");
        term_reset_color();
        return;
    }

    for (int i = 0; i < session_count; i++) {
        Session *s = &sessions[i];
        fprintf(f, "%s|%s|%s|%d|%s|%s|%d\n",
                s->name, s->type, s->host, s->port,
                s->username, s->device, s->baud);
    }
    fclose(f);
}

static void list_sessions_display(void) {
    if (session_count == 0) {
        term_set_color(COLOR_YELLOW, COLOR_BLACK);
        printf("  No saved sessions.\n");
        term_reset_color();
        return;
    }

    printf("  %-4s %-20s %-8s %-24s %-6s\n", "#", "Name", "Type", "Host/Device", "Port");
    printf("  ---- -------------------- -------- ------------------------ ------\n");

    for (int i = 0; i < session_count; i++) {
        Session *s = &sessions[i];
        term_set_color(COLOR_GREEN, COLOR_BLACK);
        printf("  %-4d ", i + 1);
        term_reset_color();
        printf("%-20s ", s->name);

        if (strcmp(s->type, "ssh") == 0) {
            term_set_color(COLOR_CYAN, COLOR_BLACK);
            printf("%-8s ", s->type);
            term_reset_color();
            printf("%-24s %-6d\n", s->host, s->port);
        } else if (strcmp(s->type, "serial") == 0) {
            term_set_color(COLOR_MAGENTA, COLOR_BLACK);
            printf("%-8s ", s->type);
            term_reset_color();
            printf("%-24s %-6d\n", s->device, s->baud);
        } else {
            printf("%-8s %-24s %-6d\n", s->type, s->host, s->port);
        }
    }
}

static void add_session(void) {
    if (session_count >= MAX_SESSIONS) {
        term_set_color(COLOR_RED, COLOR_BLACK);
        printf("  Maximum sessions reached (%d).\n", MAX_SESSIONS);
        term_reset_color();
        return;
    }

    Session *s = &sessions[session_count];
    memset(s, 0, sizeof(Session));
    char input[MAX_INPUT_LEN];

    printf("\n  Session name: ");
    fflush(stdout);
    if (!fgets(input, sizeof(input), stdin)) return;
    input[strcspn(input, "\r\n")] = '\0';
    if (strlen(input) == 0) return;
    strncpy(s->name, input, sizeof(s->name) - 1);

    printf("  Type (ssh/serial): ");
    fflush(stdout);
    if (!fgets(input, sizeof(input), stdin)) return;
    input[strcspn(input, "\r\n")] = '\0';
    strncpy(s->type, input, sizeof(s->type) - 1);

    if (strcmp(s->type, "ssh") == 0) {
        printf("  Host: ");
        fflush(stdout);
        if (fgets(input, sizeof(input), stdin)) {
            input[strcspn(input, "\r\n")] = '\0';
            strncpy(s->host, input, sizeof(s->host) - 1);
        }

        printf("  Port (default 22): ");
        fflush(stdout);
        if (fgets(input, sizeof(input), stdin)) {
            input[strcspn(input, "\r\n")] = '\0';
            s->port = atoi(input);
            if (s->port <= 0) s->port = 22;
        }

        printf("  Username: ");
        fflush(stdout);
        if (fgets(input, sizeof(input), stdin)) {
            input[strcspn(input, "\r\n")] = '\0';
            strncpy(s->username, input, sizeof(s->username) - 1);
        }
    } else if (strcmp(s->type, "serial") == 0) {
        printf("  Device (e.g. COM3 or /dev/ttyUSB0): ");
        fflush(stdout);
        if (fgets(input, sizeof(input), stdin)) {
            input[strcspn(input, "\r\n")] = '\0';
            strncpy(s->device, input, sizeof(s->device) - 1);
        }

        printf("  Baud rate (default 9600): ");
        fflush(stdout);
        if (fgets(input, sizeof(input), stdin)) {
            input[strcspn(input, "\r\n")] = '\0';
            s->baud = atoi(input);
            if (s->baud <= 0) s->baud = 9600;
        }
    } else {
        term_set_color(COLOR_RED, COLOR_BLACK);
        printf("  Unknown session type.\n");
        term_reset_color();
        SLEEP_MS(1500);
        return;
    }

    session_count++;
    save_sessions();
    term_set_color(COLOR_GREEN, COLOR_BLACK);
    printf("  Session '%s' saved.\n", s->name);
    term_reset_color();
    SLEEP_MS(1000);
}

static void delete_session(void) {
    char input[MAX_INPUT_LEN];

    if (session_count == 0) {
        term_set_color(COLOR_YELLOW, COLOR_BLACK);
        printf("  No sessions to delete.\n");
        term_reset_color();
        SLEEP_MS(1000);
        return;
    }

    printf("  Delete session # (1-%d): ", session_count);
    fflush(stdout);
    if (!fgets(input, sizeof(input), stdin)) return;
    input[strcspn(input, "\r\n")] = '\0';

    int idx = atoi(input) - 1;
    if (idx < 0 || idx >= session_count) {
        term_set_color(COLOR_RED, COLOR_BLACK);
        printf("  Invalid session number.\n");
        term_reset_color();
        SLEEP_MS(1000);
        return;
    }

    char name[64];
    strncpy(name, sessions[idx].name, sizeof(name) - 1);
    name[sizeof(name) - 1] = '\0';

    for (int i = idx; i < session_count - 1; i++) {
        sessions[i] = sessions[i + 1];
    }
    session_count--;
    save_sessions();

    term_set_color(COLOR_YELLOW, COLOR_BLACK);
    printf("  Deleted session '%s'.\n", name);
    term_reset_color();
    SLEEP_MS(1000);
}

static void connect_session(int idx) {
    Session *s = &sessions[idx];
    char cmd[MAX_PATH_LEN * 2];

    if (strcmp(s->type, "ssh") == 0) {
        if (strlen(s->username) > 0)
            snprintf(cmd, sizeof(cmd), "ssh -p %d %s@%s", s->port, s->username, s->host);
        else
            snprintf(cmd, sizeof(cmd), "ssh -p %d %s", s->port, s->host);

        term_set_color(COLOR_GREEN, COLOR_BLACK);
        printf("  Connecting: %s\n", cmd);
        term_reset_color();
        system(cmd);

        printf("\n  Session ended. Press any key...\n");
        key_flush();
        while (!key_available()) SLEEP_MS(50);
        key_read();
    } else if (strcmp(s->type, "serial") == 0) {
        term_set_color(COLOR_YELLOW, COLOR_BLACK);
        printf("  Serial session: %s at %d baud\n", s->device, s->baud);
        printf("  Use the Serial Terminal module for full serial support.\n");
        term_reset_color();
        printf("  Press any key...\n");
        key_flush();
        while (!key_available()) SLEEP_MS(50);
        key_read();
    }
}

void run_session_manager(void) {
    char input[MAX_INPUT_LEN];

    init_config_path();
    load_sessions();

    for (;;) {
        CLEAR_SCREEN();
        term_set_color(COLOR_CYAN, COLOR_BLACK);
        printf("\n  +==============================+\n");
        printf("  |     SESSION MANAGER          |\n");
        printf("  +==============================+\n");
        term_reset_color();
        printf("\n");

        list_sessions_display();

        printf("\n  [#] Connect  [a] Add  [d] Delete  [q] Quit\n\n");
        printf("  Select: ");
        fflush(stdout);

        if (!fgets(input, sizeof(input), stdin)) break;
        input[strcspn(input, "\r\n")] = '\0';

        if (strcmp(input, "q") == 0 || strcmp(input, "0") == 0) break;
        if (strcmp(input, "a") == 0) { add_session(); continue; }
        if (strcmp(input, "d") == 0) { delete_session(); continue; }

        int num = atoi(input);
        if (num >= 1 && num <= session_count) {
            connect_session(num - 1);
        }
    }
}
