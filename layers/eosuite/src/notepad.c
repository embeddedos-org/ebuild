// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eosuite.h"
#include "platform.h"

#define MAX_LINES 1000
#define MAX_LINE_LEN 256

static char lines[MAX_LINES][MAX_LINE_LEN];
static int line_count = 0;
static int scroll_offset = 0;
static int modified = 0;
static char current_file[MAX_PATH_LEN] = {0};

static void clear_buffer(void) {
    line_count = 0;
    scroll_offset = 0;
    modified = 0;
    current_file[0] = '\0';
    memset(lines, 0, sizeof(lines));
}

static int load_file(const char *path) {
    FILE *f = fopen(path, "r");
    if (!f) return 0;

    line_count = 0;
    while (line_count < MAX_LINES && fgets(lines[line_count], MAX_LINE_LEN, f)) {
        lines[line_count][strcspn(lines[line_count], "\r\n")] = '\0';
        line_count++;
    }
    fclose(f);

    strncpy(current_file, path, MAX_PATH_LEN - 1);
    current_file[MAX_PATH_LEN - 1] = '\0';
    scroll_offset = 0;
    modified = 0;
    return 1;
}

static int save_file(const char *path) {
    FILE *f = fopen(path, "w");
    if (!f) return 0;

    for (int i = 0; i < line_count; i++) {
        fprintf(f, "%s\n", lines[i]);
    }
    fclose(f);

    strncpy(current_file, path, MAX_PATH_LEN - 1);
    current_file[MAX_PATH_LEN - 1] = '\0';
    modified = 0;
    return 1;
}

static void display_buffer(void) {
    int rows, cols;
    term_get_size(&rows, &cols);
    int display_lines = rows - 6;
    if (display_lines < 5) display_lines = 5;

    CLEAR_SCREEN();
    term_set_color(COLOR_CYAN, COLOR_BLACK);
    printf("  +==============================+\n");
    printf("  |          NOTEPAD             |\n");
    printf("  +==============================+\n");
    term_reset_color();

    term_set_color(COLOR_YELLOW, COLOR_BLACK);
    printf("  File: %s%s  Lines: %d\n",
           current_file[0] ? current_file : "[untitled]",
           modified ? " [modified]" : "",
           line_count);
    term_reset_color();

    printf("  ----------------------------------------\n");

    for (int i = 0; i < display_lines; i++) {
        int ln = scroll_offset + i;
        if (ln < line_count) {
            term_set_color(COLOR_BLUE, COLOR_BLACK);
            printf("  %4d | ", ln + 1);
            term_reset_color();
            printf("%s\n", lines[ln]);
        } else {
            term_set_color(COLOR_BLUE, COLOR_BLACK);
            printf("       ~ \n");
            term_reset_color();
        }
    }

    printf("  ----------------------------------------\n");
    term_set_color(COLOR_GREEN, COLOR_BLACK);
    printf("  :w save :q quit :wq save+quit :o open :d N del :n new :+/- scroll\n");
    term_reset_color();
}

static void delete_line(int n) {
    if (n < 1 || n > line_count) return;
    int idx = n - 1;
    for (int i = idx; i < line_count - 1; i++) {
        strcpy(lines[i], lines[i + 1]);
    }
    line_count--;
    modified = 1;
}

void run_notepad(void) {
    char input[MAX_INPUT_LEN];
    char path[MAX_PATH_LEN];

    clear_buffer();

    for (;;) {
        display_buffer();
        printf("  > ");
        fflush(stdout);

        if (!fgets(input, sizeof(input), stdin)) break;
        input[strcspn(input, "\r\n")] = '\0';

        if (strlen(input) == 0) continue;

        if (strcmp(input, ":q") == 0) {
            if (modified) {
                printf("  Unsaved changes! Use :wq to save and quit, or :q! to force quit.\n");
                printf("  Press any key...\n");
                key_flush();
                while (!key_available()) SLEEP_MS(50);
                key_read();
                continue;
            }
            break;
        }

        if (strcmp(input, ":q!") == 0) {
            break;
        }

        if (strcmp(input, ":w") == 0) {
            if (current_file[0] == '\0') {
                printf("  Save as: ");
                fflush(stdout);
                if (!fgets(path, sizeof(path), stdin)) continue;
                path[strcspn(path, "\r\n")] = '\0';
                if (strlen(path) == 0) continue;
            } else {
                strcpy(path, current_file);
            }
            if (save_file(path)) {
                term_set_color(COLOR_GREEN, COLOR_BLACK);
                printf("  Saved: %s (%d lines)\n", path, line_count);
            } else {
                term_set_color(COLOR_RED, COLOR_BLACK);
                printf("  Error saving file!\n");
            }
            term_reset_color();
            SLEEP_MS(1000);
            continue;
        }

        if (strcmp(input, ":wq") == 0) {
            if (current_file[0] == '\0') {
                printf("  Save as: ");
                fflush(stdout);
                if (!fgets(path, sizeof(path), stdin)) continue;
                path[strcspn(path, "\r\n")] = '\0';
                if (strlen(path) == 0) continue;
            } else {
                strcpy(path, current_file);
            }
            if (save_file(path)) {
                term_set_color(COLOR_GREEN, COLOR_BLACK);
                printf("  Saved: %s (%d lines)\n", path, line_count);
                term_reset_color();
                SLEEP_MS(800);
                break;
            } else {
                term_set_color(COLOR_RED, COLOR_BLACK);
                printf("  Error saving file!\n");
                term_reset_color();
                SLEEP_MS(1000);
            }
            continue;
        }

        if (strcmp(input, ":o") == 0) {
            printf("  Open file: ");
            fflush(stdout);
            if (!fgets(path, sizeof(path), stdin)) continue;
            path[strcspn(path, "\r\n")] = '\0';
            if (strlen(path) == 0) continue;
            if (load_file(path)) {
                term_set_color(COLOR_GREEN, COLOR_BLACK);
                printf("  Loaded: %s (%d lines)\n", path, line_count);
            } else {
                term_set_color(COLOR_RED, COLOR_BLACK);
                printf("  Error opening file!\n");
            }
            term_reset_color();
            SLEEP_MS(1000);
            continue;
        }

        if (strncmp(input, ":d ", 3) == 0) {
            int n = atoi(input + 3);
            if (n >= 1 && n <= line_count) {
                delete_line(n);
                term_set_color(COLOR_YELLOW, COLOR_BLACK);
                printf("  Deleted line %d\n", n);
                term_reset_color();
            } else {
                term_set_color(COLOR_RED, COLOR_BLACK);
                printf("  Invalid line number\n");
                term_reset_color();
            }
            SLEEP_MS(500);
            continue;
        }

        if (strcmp(input, ":n") == 0) {
            clear_buffer();
            continue;
        }

        if (strcmp(input, ":+") == 0) {
            int rows, cols;
            term_get_size(&rows, &cols);
            int page = rows - 6;
            if (page < 5) page = 5;
            scroll_offset += page;
            if (scroll_offset >= line_count) scroll_offset = (line_count > 0) ? line_count - 1 : 0;
            continue;
        }

        if (strcmp(input, ":-") == 0) {
            int rows, cols;
            term_get_size(&rows, &cols);
            int page = rows - 6;
            if (page < 5) page = 5;
            scroll_offset -= page;
            if (scroll_offset < 0) scroll_offset = 0;
            continue;
        }

        if (input[0] == ':') {
            term_set_color(COLOR_RED, COLOR_BLACK);
            printf("  Unknown command: %s\n", input);
            term_reset_color();
            SLEEP_MS(800);
            continue;
        }

        if (line_count < MAX_LINES) {
            strncpy(lines[line_count], input, MAX_LINE_LEN - 1);
            lines[line_count][MAX_LINE_LEN - 1] = '\0';
            line_count++;
            modified = 1;

            int rows, cols;
            term_get_size(&rows, &cols);
            int display_lines = rows - 6;
            if (display_lines < 5) display_lines = 5;
            if (line_count > display_lines + scroll_offset) {
                scroll_offset = line_count - display_lines;
            }
        } else {
            term_set_color(COLOR_RED, COLOR_BLACK);
            printf("  Buffer full! (max %d lines)\n", MAX_LINES);
            term_reset_color();
            SLEEP_MS(1000);
        }
    }
}
