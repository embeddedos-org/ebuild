// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eosuite.h"
#include "platform.h"

static int guard_active = 0;
static int sleep_prevention = 1;
static int mouse_emulation = 1;
static int interval_sec = 60;

#ifdef _WIN32

static void prevent_sleep_start(void) {
    SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED);
}

static void prevent_sleep_stop(void) {
    SetThreadExecutionState(ES_CONTINUOUS);
}

static void move_mouse(void) {
    POINT pt;
    GetCursorPos(&pt);
    SetCursorPos(pt.x + 1, pt.y);
    SLEEP_MS(50);
    SetCursorPos(pt.x, pt.y);
}

#else /* Unix */

#include <signal.h>

static pid_t inhibit_pid = 0;

static void prevent_sleep_start(void) {
    if (inhibit_pid > 0) return;

    inhibit_pid = fork();
    if (inhibit_pid == 0) {
#ifdef __APPLE__
        execlp("caffeinate", "caffeinate", "-d", "-i", NULL);
#else
        execlp("systemd-inhibit", "systemd-inhibit",
               "--what=idle:sleep", "--who=EOSUITE",
               "--why=eGuard active", "sleep", "infinity", NULL);
#endif
        _exit(1);
    }
}

static void prevent_sleep_stop(void) {
    if (inhibit_pid > 0) {
        kill(inhibit_pid, SIGTERM);
        inhibit_pid = 0;
    }
}

static void move_mouse(void) {
    system("xdotool mousemove_relative -- 1 0 2>/dev/null && "
           "xdotool mousemove_relative -- -1 0 2>/dev/null");
}

#endif /* _WIN32 */

static void display_status(int spinner_idx) {
    const char spinner[] = "|/-\\";

    CLEAR_SCREEN();
    term_set_color(COLOR_CYAN, COLOR_BLACK);
    printf("\n  +==============================+\n");
    printf("  |          eGUARD              |\n");
    printf("  +==============================+\n");
    term_reset_color();

    printf("\n  Status: ");
    if (guard_active) {
        term_set_color(COLOR_GREEN, COLOR_BLACK);
        printf("ACTIVE %c\n", spinner[spinner_idx % 4]);
    } else {
        term_set_color(COLOR_RED, COLOR_BLACK);
        printf("INACTIVE\n");
    }
    term_reset_color();

    printf("  Sleep prevention: %s\n", sleep_prevention ? "ON" : "OFF");
    printf("  Mouse emulation:  %s\n", mouse_emulation ? "ON" : "OFF");
    printf("  Interval:         %d seconds\n", interval_sec);

    printf("\n  1. %s eGuard\n", guard_active ? "Stop" : "Start");
    printf("  2. Toggle sleep prevention\n");
    printf("  3. Toggle mouse emulation\n");
    printf("  4. Set interval\n");
    printf("  0. Back\n\n");
    printf("  Select: ");
    fflush(stdout);
}

void run_eguard(void) {
    char input[MAX_INPUT_LEN];
    int spinner_idx = 0;
    time_t last_action = 0;

    for (;;) {
        if (guard_active) {
            display_status(spinner_idx);

            int wait = 0;
            int got_input = 0;
            while (wait < 1000) {
                if (key_available()) {
                    got_input = 1;
                    break;
                }
                SLEEP_MS(50);
                wait += 50;
            }

            spinner_idx++;

            time_t now = time(NULL);
            if (difftime(now, last_action) >= interval_sec) {
                if (mouse_emulation) move_mouse();
                last_action = now;
            }

            if (!got_input) continue;

            if (!fgets(input, sizeof(input), stdin)) break;
            input[strcspn(input, "\r\n")] = '\0';
        } else {
            display_status(0);
            if (!fgets(input, sizeof(input), stdin)) break;
            input[strcspn(input, "\r\n")] = '\0';
        }

        if (strcmp(input, "0") == 0) {
            if (guard_active) {
                guard_active = 0;
                if (sleep_prevention) prevent_sleep_stop();
            }
            break;
        }

        if (strcmp(input, "1") == 0) {
            if (guard_active) {
                guard_active = 0;
                if (sleep_prevention) prevent_sleep_stop();
                term_set_color(COLOR_YELLOW, COLOR_BLACK);
                printf("  eGuard stopped.\n");
                term_reset_color();
                SLEEP_MS(800);
            } else {
                guard_active = 1;
                last_action = time(NULL);
                if (sleep_prevention) prevent_sleep_start();
                term_set_color(COLOR_GREEN, COLOR_BLACK);
                printf("  eGuard started.\n");
                term_reset_color();
                SLEEP_MS(800);
            }
            continue;
        }

        if (strcmp(input, "2") == 0) {
            sleep_prevention = !sleep_prevention;
            if (guard_active) {
                if (sleep_prevention)
                    prevent_sleep_start();
                else
                    prevent_sleep_stop();
            }
            continue;
        }

        if (strcmp(input, "3") == 0) {
            mouse_emulation = !mouse_emulation;
            continue;
        }

        if (strcmp(input, "4") == 0) {
            printf("  New interval (seconds): ");
            fflush(stdout);
            if (fgets(input, sizeof(input), stdin)) {
                input[strcspn(input, "\r\n")] = '\0';
                int val = atoi(input);
                if (val >= 5 && val <= 3600) {
                    interval_sec = val;
                    term_set_color(COLOR_GREEN, COLOR_BLACK);
                    printf("  Interval set to %d seconds.\n", interval_sec);
                    term_reset_color();
                } else {
                    term_set_color(COLOR_RED, COLOR_BLACK);
                    printf("  Invalid (5-3600 seconds).\n");
                    term_reset_color();
                }
                SLEEP_MS(800);
            }
            continue;
        }
    }
}
