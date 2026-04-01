// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/* eplay.c - ePlay: Lightweight media player (audio/video via system players) */
#include "eosuite.h"
#include "platform.h"

static void trim_nl(char *s) {
    size_t len = strlen(s);
    if (len > 0 && s[len - 1] == '\n') s[len - 1] = '\0';
}

static void play_file(const char *filepath) {
    char cmd[MAX_PATH_LEN * 2];

#ifdef _WIN32
    /* Try ffplay (lightweight), then vlc, then Windows default */
    snprintf(cmd, sizeof(cmd),
        "where ffplay >nul 2>nul && (ffplay -autoexit -nodisp \"%s\" 2>nul) || "
        "where vlc >nul 2>nul && (vlc --play-and-exit \"%s\" 2>nul) || "
        "start \"\" \"%s\"", filepath, filepath, filepath);
#else
    /* Try ffplay, mpv, vlc, then xdg-open/open */
    snprintf(cmd, sizeof(cmd),
        "command -v ffplay >/dev/null 2>&1 && ffplay -autoexit -nodisp '%s' 2>/dev/null || "
        "command -v mpv >/dev/null 2>&1 && mpv --no-video '%s' 2>/dev/null || "
        "command -v vlc >/dev/null 2>&1 && cvlc --play-and-exit '%s' 2>/dev/null || "
#ifdef __APPLE__
        "open '%s'", filepath, filepath, filepath, filepath);
#else
        "xdg-open '%s' 2>/dev/null", filepath, filepath, filepath, filepath);
#endif
#endif

    system(cmd);
}

static void play_single(void) {
    char filepath[MAX_PATH_LEN];
    char input[MAX_INPUT_LEN];

    printf("\n  Enter file path (audio or video): ");
    fflush(stdout);
    if (fgets(filepath, sizeof(filepath), stdin) == NULL) return;
    trim_nl(filepath);
    if (strlen(filepath) == 0) return;

    term_set_color(COLOR_GREEN, COLOR_BLACK);
    printf("\n  Playing: %s\n", filepath);
    printf("  (Close the player window or press Ctrl+C to stop)\n\n");
    term_reset_color();

    play_file(filepath);

    printf("\n  Playback finished. Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

static void play_folder(void) {
    char folder[MAX_PATH_LEN];
    char input[MAX_INPUT_LEN];
    char cmd[MAX_PATH_LEN * 2];

    printf("\n  Enter folder path: ");
    fflush(stdout);
    if (fgets(folder, sizeof(folder), stdin) == NULL) return;
    trim_nl(folder);
    if (strlen(folder) == 0) return;

    /* List media files */
    term_set_color(COLOR_CYAN, COLOR_BLACK);
    printf("\n  Media files in: %s\n", folder);
    printf("  ----------------------------------------\n");
    term_reset_color();

#ifdef _WIN32
    snprintf(cmd, sizeof(cmd),
        "dir /b \"%s\\*.mp3\" \"%s\\*.wav\" \"%s\\*.mp4\" \"%s\\*.avi\" "
        "\"%s\\*.mkv\" \"%s\\*.flac\" \"%s\\*.ogg\" \"%s\\*.m4a\" 2>nul",
        folder, folder, folder, folder, folder, folder, folder, folder);
#else
    snprintf(cmd, sizeof(cmd),
        "ls '%s'/*.{mp3,wav,mp4,avi,mkv,flac,ogg,m4a,wma,aac} 2>/dev/null | head -50",
        folder);
#endif
    system(cmd);

    printf("\n  Play all? (y/n): ");
    fflush(stdout);
    if (fgets(input, sizeof(input), stdin) == NULL) return;
    trim_nl(input);

    if (input[0] == 'y' || input[0] == 'Y') {
#ifdef _WIN32
        snprintf(cmd, sizeof(cmd),
            "where ffplay >nul 2>nul && (for %%f in (\"%s\\*.mp3\" \"%s\\*.wav\" \"%s\\*.flac\") do ffplay -autoexit -nodisp \"%%f\" 2>nul) || "
            "start \"\" \"%s\"", folder, folder, folder, folder);
#else
        snprintf(cmd, sizeof(cmd),
            "command -v mpv >/dev/null 2>&1 && mpv --no-video '%s'/*.{mp3,wav,flac,ogg,m4a} 2>/dev/null || "
            "command -v vlc >/dev/null 2>&1 && cvlc '%s'/*.{mp3,wav,flac,ogg} 2>/dev/null",
            folder, folder);
#endif
        term_set_color(COLOR_GREEN, COLOR_BLACK);
        printf("\n  Playing folder...\n");
        term_reset_color();
        system(cmd);
    }

    printf("\n  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

static void play_url(void) {
    char url[MAX_PATH_LEN];
    char input[MAX_INPUT_LEN];

    printf("\n  Enter stream URL (http/https): ");
    fflush(stdout);
    if (fgets(url, sizeof(url), stdin) == NULL) return;
    trim_nl(url);
    if (strlen(url) == 0) return;

    char cmd[MAX_PATH_LEN * 2];

#ifdef _WIN32
    snprintf(cmd, sizeof(cmd),
        "where ffplay >nul 2>nul && (ffplay -autoexit \"%s\" 2>nul) || "
        "where vlc >nul 2>nul && (vlc \"%s\" 2>nul) || "
        "start \"\" \"%s\"", url, url, url);
#else
    snprintf(cmd, sizeof(cmd),
        "command -v mpv >/dev/null 2>&1 && mpv '%s' 2>/dev/null || "
        "command -v ffplay >/dev/null 2>&1 && ffplay '%s' 2>/dev/null || "
        "command -v vlc >/dev/null 2>&1 && cvlc '%s' 2>/dev/null",
        url, url, url);
#endif

    term_set_color(COLOR_GREEN, COLOR_BLACK);
    printf("\n  Streaming: %s\n", url);
    term_reset_color();

    system(cmd);

    printf("\n  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

static void show_media_info(void) {
    char filepath[MAX_PATH_LEN];
    char input[MAX_INPUT_LEN];

    printf("\n  Enter file path: ");
    fflush(stdout);
    if (fgets(filepath, sizeof(filepath), stdin) == NULL) return;
    trim_nl(filepath);
    if (strlen(filepath) == 0) return;

    char cmd[MAX_PATH_LEN * 2];

#ifdef _WIN32
    snprintf(cmd, sizeof(cmd),
        "where ffprobe >nul 2>nul && (ffprobe -hide_banner \"%s\" 2>&1) || "
        "(echo   ffprobe not found. Install FFmpeg for media info.)", filepath);
#else
    snprintf(cmd, sizeof(cmd),
        "command -v ffprobe >/dev/null 2>&1 && ffprobe -hide_banner '%s' 2>&1 || "
        "command -v mediainfo >/dev/null 2>&1 && mediainfo '%s' || "
        "echo '  Install ffprobe or mediainfo for media details'", filepath, filepath);
#endif

    term_set_color(COLOR_CYAN, COLOR_BLACK);
    printf("\n  Media Info: %s\n", filepath);
    printf("  ----------------------------------------\n");
    term_reset_color();

    system(cmd);

    printf("\n  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

void run_eplay(void) {
    char input[MAX_INPUT_LEN];

    while (1) {
        CLEAR_SCREEN();
        term_set_color(COLOR_CYAN, COLOR_BLACK);
        printf("  +========================================+\n");
        printf("  |       ePlay - Media Player             |\n");
        printf("  +========================================+\n");
        term_reset_color();

        printf("\n  Plays audio/video via system players.\n");
        printf("  Supports: ffplay, mpv, vlc, or OS default\n\n");
        printf("   1. Play a file\n");
        printf("   2. Play a folder\n");
        printf("   3. Stream from URL\n");
        printf("   4. Media file info\n");
        printf("   0. Back to Menu\n");
        printf("\n  Select: ");
        fflush(stdout);

        if (fgets(input, sizeof(input), stdin) == NULL) return;

        CLEAR_SCREEN();
        switch (atoi(input)) {
        case 1: play_single();    break;
        case 2: play_folder();    break;
        case 3: play_url();       break;
        case 4: show_media_info(); break;
        case 0: return;
        }
    }
}
