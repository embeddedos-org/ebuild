// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eosuite.h"
#include "platform.h"
#include <ctype.h>

#define BYTES_PER_LINE 16
#define LINES_PER_PAGE 16

static void display_hex_page(FILE *f, long offset, long file_size) {
    unsigned char buf[BYTES_PER_LINE];

    fseek(f, offset, SEEK_SET);

    int rows, cols;
    term_get_size(&rows, &cols);
    int page_lines = rows - 8;
    if (page_lines < LINES_PER_PAGE) page_lines = LINES_PER_PAGE;

    CLEAR_SCREEN();
    term_set_color(COLOR_CYAN, COLOR_BLACK);
    printf("  +==============================+\n");
    printf("  |        HEX VIEWER            |\n");
    printf("  +==============================+\n");
    term_reset_color();

    term_set_color(COLOR_YELLOW, COLOR_BLACK);
    printf("  Offset: 0x%08lX  Size: %ld bytes\n", offset, file_size);
    term_reset_color();
    printf("  %-10s", "Address");
    for (int i = 0; i < BYTES_PER_LINE; i++) printf("%02X ", i);
    printf(" ASCII\n");
    printf("  ----------");
    for (int i = 0; i < BYTES_PER_LINE; i++) printf("---");
    printf("-----------------\n");

    for (int line = 0; line < page_lines; line++) {
        long addr = offset + line * BYTES_PER_LINE;
        if (addr >= file_size) break;

        size_t n = fread(buf, 1, BYTES_PER_LINE, f);
        if (n == 0) break;

        term_set_color(COLOR_MAGENTA, COLOR_BLACK);
        printf("  %08lX  ", addr);
        term_reset_color();

        for (size_t i = 0; i < BYTES_PER_LINE; i++) {
            if (i < n) {
                if (buf[i] == 0x00) {
                    term_set_color(COLOR_BLUE, COLOR_BLACK);
                } else if (isprint(buf[i])) {
                    term_set_color(COLOR_GREEN, COLOR_BLACK);
                } else {
                    term_set_color(COLOR_YELLOW, COLOR_BLACK);
                }
                printf("%02X ", buf[i]);
                term_reset_color();
            } else {
                printf("   ");
            }
        }

        printf(" ");
        term_set_color(COLOR_WHITE, COLOR_BLACK);
        for (size_t i = 0; i < n; i++) {
            if (isprint(buf[i]))
                putchar(buf[i]);
            else
                putchar('.');
        }
        term_reset_color();
        printf("\n");
    }

    printf("\n  [n]ext [p]rev [g]oto [q]uit\n");
}

void run_hex_viewer(void) {
    char path[MAX_PATH_LEN];
    char input[MAX_INPUT_LEN];

    CLEAR_SCREEN();
    term_set_color(COLOR_CYAN, COLOR_BLACK);
    printf("\n  +==============================+\n");
    printf("  |        HEX VIEWER            |\n");
    printf("  +==============================+\n");
    term_reset_color();
    printf("\n  Enter file path: ");
    fflush(stdout);

    if (!fgets(path, sizeof(path), stdin)) return;
    path[strcspn(path, "\r\n")] = '\0';
    if (strlen(path) == 0) return;

    FILE *f = fopen(path, "rb");
    if (!f) {
        term_set_color(COLOR_RED, COLOR_BLACK);
        printf("  Error: cannot open '%s'\n", path);
        term_reset_color();
        printf("  Press any key...\n");
        key_flush();
        while (!key_available()) SLEEP_MS(50);
        key_read();
        return;
    }

    fseek(f, 0, SEEK_END);
    long file_size = ftell(f);
    fseek(f, 0, SEEK_SET);

    int rows, cols;
    term_get_size(&rows, &cols);
    int page_lines = rows - 8;
    if (page_lines < LINES_PER_PAGE) page_lines = LINES_PER_PAGE;
    long page_size = page_lines * BYTES_PER_LINE;

    long offset = 0;

    for (;;) {
        display_hex_page(f, offset, file_size);
        printf("  hex> ");
        fflush(stdout);

        if (!fgets(input, sizeof(input), stdin)) break;
        input[strcspn(input, "\r\n")] = '\0';

        if (strcmp(input, "q") == 0 || strcmp(input, "quit") == 0) break;

        if (strcmp(input, "n") == 0) {
            offset += page_size;
            if (offset >= file_size) offset = (file_size > page_size) ? file_size - page_size : 0;
            if (offset < 0) offset = 0;
        } else if (strcmp(input, "p") == 0) {
            offset -= page_size;
            if (offset < 0) offset = 0;
        } else if (strcmp(input, "g") == 0) {
            printf("  Goto offset (hex or decimal): ");
            fflush(stdout);
            if (fgets(input, sizeof(input), stdin)) {
                input[strcspn(input, "\r\n")] = '\0';
                long new_off = 0;
                if (strncmp(input, "0x", 2) == 0 || strncmp(input, "0X", 2) == 0) {
                    new_off = strtol(input, NULL, 16);
                } else {
                    new_off = strtol(input, NULL, 10);
                }
                if (new_off >= 0 && new_off < file_size) {
                    offset = (new_off / BYTES_PER_LINE) * BYTES_PER_LINE;
                }
            }
        }
    }

    fclose(f);
}
