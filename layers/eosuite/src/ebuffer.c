// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/* ebuffer.c - eBuffer: Lightweight clipboard & text buffer manager */
#include "eosuite.h"
#include "platform.h"

#define BUFFER_SLOTS    10
#define BUFFER_SIZE     4096

static char buffers[BUFFER_SLOTS][BUFFER_SIZE];
static char buffer_names[BUFFER_SLOTS][64];
static int  buffer_used[BUFFER_SLOTS];

static void trim_nl(char *s) {
    size_t len = strlen(s);
    if (len > 0 && s[len - 1] == '\n') s[len - 1] = '\0';
}

static void buffer_init(void) {
    static int inited = 0;
    if (inited) return;
    int i;
    for (i = 0; i < BUFFER_SLOTS; i++) {
        buffers[i][0] = '\0';
        snprintf(buffer_names[i], sizeof(buffer_names[i]), "Slot %d", i + 1);
        buffer_used[i] = 0;
    }
    inited = 1;
}

static void buffer_list(void) {
    printf("\n");
    term_set_color(COLOR_CYAN, COLOR_BLACK);
    printf("  %-4s %-20s %-8s %s\n", "#", "Name", "Status", "Preview");
    printf("  ---- -------------------- -------- --------------------------------\n");
    term_reset_color();

    int i;
    for (i = 0; i < BUFFER_SLOTS; i++) {
        if (buffer_used[i]) {
            term_set_color(COLOR_GREEN, COLOR_BLACK);
            printf("  %-4d %-20s %-8s ", i + 1, buffer_names[i], "USED");
            term_reset_color();
            /* Show first 30 chars */
            int j;
            for (j = 0; j < 30 && buffers[i][j]; j++) {
                printf("%c", buffers[i][j] == '\n' ? ' ' : buffers[i][j]);
            }
            if (strlen(buffers[i]) > 30) printf("...");
        } else {
            term_set_color(COLOR_YELLOW, COLOR_BLACK);
            printf("  %-4d %-20s %-8s ", i + 1, buffer_names[i], "empty");
            term_reset_color();
        }
        printf("\n");
    }
}

static void buffer_store(void) {
    char input[MAX_INPUT_LEN];

    buffer_list();
    printf("\n  Store to slot (1-%d): ", BUFFER_SLOTS);
    fflush(stdout);
    if (fgets(input, sizeof(input), stdin) == NULL) return;
    int slot = atoi(input) - 1;
    if (slot < 0 || slot >= BUFFER_SLOTS) { printf("  Invalid slot.\n"); return; }

    printf("  Name for this buffer [%s]: ", buffer_names[slot]);
    fflush(stdout);
    if (fgets(input, sizeof(input), stdin) && strlen(input) > 1) {
        trim_nl(input);
        strncpy(buffer_names[slot], input, sizeof(buffer_names[slot]) - 1);
    }

    printf("  Enter text (type END on a new line to finish):\n");
    buffers[slot][0] = '\0';
    char line[512];
    while (fgets(line, sizeof(line), stdin)) {
        trim_nl(line);
        if (strcmp(line, "END") == 0) break;
        if (strlen(buffers[slot]) + strlen(line) + 2 < BUFFER_SIZE) {
            strcat(buffers[slot], line);
            strcat(buffers[slot], "\n");
        }
    }
    buffer_used[slot] = (strlen(buffers[slot]) > 0);

    term_set_color(COLOR_GREEN, COLOR_BLACK);
    printf("  Stored %d bytes to slot %d.\n", (int)strlen(buffers[slot]), slot + 1);
    term_reset_color();
    SLEEP_MS(500);
}

static void buffer_view(void) {
    char input[MAX_INPUT_LEN];

    buffer_list();
    printf("\n  View slot (1-%d): ", BUFFER_SLOTS);
    fflush(stdout);
    if (fgets(input, sizeof(input), stdin) == NULL) return;
    int slot = atoi(input) - 1;
    if (slot < 0 || slot >= BUFFER_SLOTS || !buffer_used[slot]) {
        printf("  Empty or invalid slot.\n");
        printf("  Press Enter...\n"); fgets(input, sizeof(input), stdin);
        return;
    }

    term_set_color(COLOR_CYAN, COLOR_BLACK);
    printf("\n  Buffer: %s (slot %d, %d bytes)\n", buffer_names[slot], slot + 1, (int)strlen(buffers[slot]));
    printf("  ----------------------------------------\n");
    term_reset_color();
    printf("%s\n", buffers[slot]);

    printf("  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

static void buffer_copy_clipboard(void) {
    char input[MAX_INPUT_LEN];

    buffer_list();
    printf("\n  Copy slot to system clipboard (1-%d): ", BUFFER_SLOTS);
    fflush(stdout);
    if (fgets(input, sizeof(input), stdin) == NULL) return;
    int slot = atoi(input) - 1;
    if (slot < 0 || slot >= BUFFER_SLOTS || !buffer_used[slot]) {
        printf("  Empty or invalid slot.\n");
        printf("  Press Enter...\n"); fgets(input, sizeof(input), stdin);
        return;
    }

    /* Write buffer to temp file then pipe to clipboard */
    char tmpfile[MAX_PATH_LEN];
    char cmd[MAX_PATH_LEN * 2];

#ifdef _WIN32
    const char *temp = getenv("TEMP");
    if (!temp) temp = ".";
    snprintf(tmpfile, sizeof(tmpfile), "%s\\ebuffer_clip.tmp", temp);
#else
    snprintf(tmpfile, sizeof(tmpfile), "/tmp/ebuffer_clip.tmp");
#endif

    FILE *f = fopen(tmpfile, "w");
    if (f) {
        fputs(buffers[slot], f);
        fclose(f);

#ifdef _WIN32
        snprintf(cmd, sizeof(cmd), "type \"%s\" | clip", tmpfile);
#elif defined(__APPLE__)
        snprintf(cmd, sizeof(cmd), "cat '%s' | pbcopy", tmpfile);
#else
        snprintf(cmd, sizeof(cmd),
            "cat '%s' | xclip -selection clipboard 2>/dev/null || "
            "cat '%s' | xsel --clipboard 2>/dev/null", tmpfile, tmpfile);
#endif
        system(cmd);

#ifdef _WIN32
        snprintf(cmd, sizeof(cmd), "del /q \"%s\" 2>nul", tmpfile);
#else
        snprintf(cmd, sizeof(cmd), "rm -f '%s'", tmpfile);
#endif
        system(cmd);

        term_set_color(COLOR_GREEN, COLOR_BLACK);
        printf("  Copied to system clipboard!\n");
        term_reset_color();
    }

    SLEEP_MS(500);
}

static void buffer_paste_clipboard(void) {
    char input[MAX_INPUT_LEN];

    printf("\n  Paste from system clipboard to slot (1-%d): ", BUFFER_SLOTS);
    fflush(stdout);
    if (fgets(input, sizeof(input), stdin) == NULL) return;
    int slot = atoi(input) - 1;
    if (slot < 0 || slot >= BUFFER_SLOTS) { printf("  Invalid slot.\n"); return; }

    char tmpfile[MAX_PATH_LEN];
    char cmd[MAX_PATH_LEN * 2];

#ifdef _WIN32
    const char *temp = getenv("TEMP");
    if (!temp) temp = ".";
    snprintf(tmpfile, sizeof(tmpfile), "%s\\ebuffer_paste.tmp", temp);
    snprintf(cmd, sizeof(cmd),
        "powershell -NoProfile -Command \"Get-Clipboard | Out-File -Encoding utf8 '%s'\"", tmpfile);
#elif defined(__APPLE__)
    snprintf(tmpfile, sizeof(tmpfile), "/tmp/ebuffer_paste.tmp");
    snprintf(cmd, sizeof(cmd), "pbpaste > '%s'", tmpfile);
#else
    snprintf(tmpfile, sizeof(tmpfile), "/tmp/ebuffer_paste.tmp");
    snprintf(cmd, sizeof(cmd),
        "xclip -selection clipboard -o > '%s' 2>/dev/null || "
        "xsel --clipboard -o > '%s' 2>/dev/null", tmpfile, tmpfile);
#endif

    system(cmd);

    FILE *f = fopen(tmpfile, "r");
    if (f) {
        size_t n = fread(buffers[slot], 1, BUFFER_SIZE - 1, f);
        buffers[slot][n] = '\0';
        fclose(f);
        buffer_used[slot] = (n > 0);

        term_set_color(COLOR_GREEN, COLOR_BLACK);
        printf("  Pasted %d bytes to slot %d.\n", (int)n, slot + 1);
        term_reset_color();
    }

#ifdef _WIN32
    snprintf(cmd, sizeof(cmd), "del /q \"%s\" 2>nul", tmpfile);
#else
    snprintf(cmd, sizeof(cmd), "rm -f '%s'", tmpfile);
#endif
    system(cmd);

    SLEEP_MS(500);
}

static void buffer_save_file(void) {
    char input[MAX_INPUT_LEN];
    char filename[MAX_PATH_LEN];

    buffer_list();
    printf("\n  Save slot (1-%d) to file: ", BUFFER_SLOTS);
    fflush(stdout);
    if (fgets(input, sizeof(input), stdin) == NULL) return;
    int slot = atoi(input) - 1;
    if (slot < 0 || slot >= BUFFER_SLOTS || !buffer_used[slot]) {
        printf("  Empty or invalid slot.\n");
        printf("  Press Enter...\n"); fgets(input, sizeof(input), stdin);
        return;
    }

    printf("  Filename: ");
    fflush(stdout);
    if (fgets(filename, sizeof(filename), stdin) == NULL) return;
    trim_nl(filename);
    if (strlen(filename) == 0) return;

    FILE *f = fopen(filename, "w");
    if (f) {
        fputs(buffers[slot], f);
        fclose(f);
        term_set_color(COLOR_GREEN, COLOR_BLACK);
        printf("  Saved to: %s\n", filename);
        term_reset_color();
    } else {
        term_set_color(COLOR_RED, COLOR_BLACK);
        printf("  Error saving!\n");
        term_reset_color();
    }

    printf("  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

static void buffer_load_file(void) {
    char input[MAX_INPUT_LEN];
    char filename[MAX_PATH_LEN];

    printf("\n  Load file into slot (1-%d): ", BUFFER_SLOTS);
    fflush(stdout);
    if (fgets(input, sizeof(input), stdin) == NULL) return;
    int slot = atoi(input) - 1;
    if (slot < 0 || slot >= BUFFER_SLOTS) { printf("  Invalid slot.\n"); return; }

    printf("  Filename: ");
    fflush(stdout);
    if (fgets(filename, sizeof(filename), stdin) == NULL) return;
    trim_nl(filename);
    if (strlen(filename) == 0) return;

    FILE *f = fopen(filename, "r");
    if (f) {
        size_t n = fread(buffers[slot], 1, BUFFER_SIZE - 1, f);
        buffers[slot][n] = '\0';
        fclose(f);
        buffer_used[slot] = (n > 0);
        snprintf(buffer_names[slot], sizeof(buffer_names[slot]), "%s", filename);

        term_set_color(COLOR_GREEN, COLOR_BLACK);
        printf("  Loaded %d bytes.\n", (int)n);
        term_reset_color();
    } else {
        term_set_color(COLOR_RED, COLOR_BLACK);
        printf("  Cannot open file!\n");
        term_reset_color();
    }

    printf("  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

void run_ebuffer(void) {
    char input[MAX_INPUT_LEN];
    buffer_init();

    while (1) {
        CLEAR_SCREEN();
        term_set_color(COLOR_CYAN, COLOR_BLACK);
        printf("  +========================================+\n");
        printf("  |    eBuffer - Clipboard & Text Buffer   |\n");
        printf("  +========================================+\n");
        term_reset_color();

        buffer_list();

        printf("\n   1. Store text to buffer\n");
        printf("   2. View buffer contents\n");
        printf("   3. Copy buffer to clipboard\n");
        printf("   4. Paste clipboard to buffer\n");
        printf("   5. Save buffer to file\n");
        printf("   6. Load file into buffer\n");
        printf("   0. Back to Menu\n");
        printf("\n  Select: ");
        fflush(stdout);

        if (fgets(input, sizeof(input), stdin) == NULL) return;

        CLEAR_SCREEN();
        switch (atoi(input)) {
        case 1: buffer_store(); break;
        case 2: buffer_view(); break;
        case 3: buffer_copy_clipboard(); break;
        case 4: buffer_paste_clipboard(); break;
        case 5: buffer_save_file(); break;
        case 6: buffer_load_file(); break;
        case 0: return;
        }
    }
}
