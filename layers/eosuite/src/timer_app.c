// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eosuite.h"
#include "platform.h"

static void format_time(int total_secs, char *buf, int buflen) {
    int h = total_secs / 3600;
    int m = (total_secs % 3600) / 60;
    int s = total_secs % 60;
    snprintf(buf, buflen, "%02d:%02d:%02d", h, m, s);
}

static void run_stopwatch(void) {
    CLEAR_SCREEN();
    term_set_color(COLOR_CYAN, COLOR_BLACK);
    printf("\n  +==============================+\n");
    printf("  |         STOPWATCH            |\n");
    printf("  +==============================+\n");
    term_reset_color();
    printf("\n  Press any key to stop...\n\n");

    time_t start = time(NULL);
    char timebuf[32];

    term_hide_cursor();
    key_flush();

    for (;;) {
        int elapsed = (int)difftime(time(NULL), start);
        format_time(elapsed, timebuf, sizeof(timebuf));

        term_set_cursor(7, 3);
        term_set_color(COLOR_GREEN, COLOR_BLACK);
        printf("  Elapsed: %s  ", timebuf);
        term_reset_color();
        fflush(stdout);

        if (key_available()) {
            key_read();
            break;
        }
        SLEEP_MS(200);
    }

    int total = (int)difftime(time(NULL), start);
    format_time(total, timebuf, sizeof(timebuf));

    term_show_cursor();
    printf("\n\n");
    term_set_color(COLOR_YELLOW, COLOR_BLACK);
    printf("  Stopped at: %s\n", timebuf);
    term_reset_color();
    printf("  Press any key to continue...\n");
    key_flush();
    while (!key_available()) SLEEP_MS(50);
    key_read();
}

static int parse_time_input(const char *input) {
    int a, b;
    if (sscanf(input, "%d:%d", &a, &b) == 2) {
        return a * 60 + b;
    }
    int secs = atoi(input);
    return (secs > 0) ? secs : -1;
}

static void run_countdown(void) {
    char input[MAX_INPUT_LEN];

    CLEAR_SCREEN();
    term_set_color(COLOR_CYAN, COLOR_BLACK);
    printf("\n  +==============================+\n");
    printf("  |         COUNTDOWN            |\n");
    printf("  +==============================+\n");
    term_reset_color();
    printf("\n  Enter time (seconds or MM:SS): ");
    fflush(stdout);

    if (!fgets(input, sizeof(input), stdin)) return;
    input[strcspn(input, "\r\n")] = '\0';

    int total = parse_time_input(input);
    if (total <= 0) {
        term_set_color(COLOR_RED, COLOR_BLACK);
        printf("  Invalid time input.\n");
        term_reset_color();
        SLEEP_MS(1500);
        return;
    }

    term_hide_cursor();
    key_flush();

    char timebuf[32];
    int remaining = total;

    while (remaining >= 0) {
        format_time(remaining, timebuf, sizeof(timebuf));

        int color;
        if (remaining > 30) color = COLOR_GREEN;
        else if (remaining > 10) color = COLOR_YELLOW;
        else color = COLOR_RED;

        term_set_cursor(8, 3);
        term_set_color(color, COLOR_BLACK);
        printf("  Remaining: %s  ", timebuf);
        term_reset_color();
        fflush(stdout);

        if (remaining == 0) break;

        if (key_available()) {
            key_read();
            term_show_cursor();
            printf("\n\n");
            term_set_color(COLOR_YELLOW, COLOR_BLACK);
            printf("  Countdown cancelled.\n");
            term_reset_color();
            printf("  Press any key to continue...\n");
            key_flush();
            while (!key_available()) SLEEP_MS(50);
            key_read();
            return;
        }

        SLEEP_MS(1000);
        remaining--;
    }

    term_show_cursor();
    printf("\n\n");
    term_set_color(COLOR_RED, COLOR_BLACK);
    printf("  ** TIME'S UP! **\a\a\a\n");
    term_reset_color();
    printf("  Press any key to continue...\n");
    key_flush();
    while (!key_available()) SLEEP_MS(50);
    key_read();
}

void run_timer(void) {
    char input[MAX_INPUT_LEN];

    for (;;) {
        CLEAR_SCREEN();
        term_set_color(COLOR_CYAN, COLOR_BLACK);
        printf("\n  +==============================+\n");
        printf("  |       TIMER / STOPWATCH      |\n");
        printf("  +==============================+\n");
        term_reset_color();
        printf("\n  1. Stopwatch\n");
        printf("  2. Countdown Timer\n");
        printf("  0. Back\n\n");
        printf("  Select: ");
        fflush(stdout);

        if (!fgets(input, sizeof(input), stdin)) break;
        input[strcspn(input, "\r\n")] = '\0';

        if (strcmp(input, "1") == 0) run_stopwatch();
        else if (strcmp(input, "2") == 0) run_countdown();
        else if (strcmp(input, "0") == 0) break;
    }
}
