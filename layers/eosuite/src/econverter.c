// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/* econverter.c - eConverter: Lightweight file format converter */
#include "eosuite.h"
#include "platform.h"

static void trim_nl(char *s) {
    size_t len = strlen(s);
    if (len > 0 && s[len - 1] == '\n') s[len - 1] = '\0';
}

static void convert_image(void) {
    char input_file[MAX_PATH_LEN], output_file[MAX_PATH_LEN];
    char input[MAX_INPUT_LEN], cmd[MAX_PATH_LEN * 3];

    printf("\n  Image Converter\n");
    printf("  Supported: PNG, JPG, BMP, GIF, TIFF, WebP, ICO\n\n");

    printf("  Input file: ");
    fflush(stdout);
    if (fgets(input_file, sizeof(input_file), stdin) == NULL) return;
    trim_nl(input_file);
    if (strlen(input_file) == 0) return;

    printf("  Output file (with extension): ");
    fflush(stdout);
    if (fgets(output_file, sizeof(output_file), stdin) == NULL) return;
    trim_nl(output_file);
    if (strlen(output_file) == 0) return;

    printf("  Resize? (e.g. 800x600, or blank to keep): ");
    fflush(stdout);
    char resize[64] = "";
    if (fgets(resize, sizeof(resize), stdin)) trim_nl(resize);

#ifdef _WIN32
    if (strlen(resize) > 0)
        snprintf(cmd, sizeof(cmd),
            "where magick >nul 2>nul && (magick convert \"%s\" -resize %s \"%s\") || "
            "where ffmpeg >nul 2>nul && (ffmpeg -i \"%s\" -vf scale=%s \"%s\" -y 2>nul) || "
            "(echo   Install ImageMagick or FFmpeg for image conversion)",
            input_file, resize, output_file,
            input_file, resize, output_file);
    else
        snprintf(cmd, sizeof(cmd),
            "where magick >nul 2>nul && (magick convert \"%s\" \"%s\") || "
            "where ffmpeg >nul 2>nul && (ffmpeg -i \"%s\" \"%s\" -y 2>nul) || "
            "(echo   Install ImageMagick or FFmpeg for image conversion)",
            input_file, output_file, input_file, output_file);
#else
    if (strlen(resize) > 0)
        snprintf(cmd, sizeof(cmd),
            "command -v convert >/dev/null 2>&1 && convert '%s' -resize %s '%s' || "
            "command -v ffmpeg >/dev/null 2>&1 && ffmpeg -i '%s' -vf scale=%s '%s' -y 2>/dev/null || "
            "echo '  Install ImageMagick or FFmpeg'",
            input_file, resize, output_file,
            input_file, resize, output_file);
    else
        snprintf(cmd, sizeof(cmd),
            "command -v convert >/dev/null 2>&1 && convert '%s' '%s' || "
            "command -v ffmpeg >/dev/null 2>&1 && ffmpeg -i '%s' '%s' -y 2>/dev/null || "
            "echo '  Install ImageMagick or FFmpeg'",
            input_file, output_file, input_file, output_file);
#endif

    term_set_color(COLOR_YELLOW, COLOR_BLACK);
    printf("\n  Converting...\n");
    term_reset_color();

    int ret = system(cmd);
    if (ret == 0) {
        term_set_color(COLOR_GREEN, COLOR_BLACK);
        printf("  Done: %s\n", output_file);
    } else {
        term_set_color(COLOR_RED, COLOR_BLACK);
        printf("  Conversion failed.\n");
    }
    term_reset_color();
    printf("  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

static void convert_document(void) {
    char input_file[MAX_PATH_LEN], output_file[MAX_PATH_LEN];
    char input[MAX_INPUT_LEN], cmd[MAX_PATH_LEN * 3];

    printf("\n  Document Converter\n");
    printf("  PDF <-> Word, Text, HTML, Markdown\n\n");

    printf("  Input file: ");
    fflush(stdout);
    if (fgets(input_file, sizeof(input_file), stdin) == NULL) return;
    trim_nl(input_file);
    if (strlen(input_file) == 0) return;

    const char *ext = strrchr(input_file, '.');
    printf("\n  Output format:\n");
    printf("   1. PDF\n");
    printf("   2. DOCX (Word)\n");
    printf("   3. TXT (plain text)\n");
    printf("   4. HTML\n");
    printf("  Select: ");
    fflush(stdout);
    if (fgets(input, sizeof(input), stdin) == NULL) return;

    const char *out_ext;
    switch (atoi(input)) {
    case 1: out_ext = ".pdf"; break;
    case 2: out_ext = ".docx"; break;
    case 3: out_ext = ".txt"; break;
    case 4: out_ext = ".html"; break;
    default: printf("  Invalid.\n"); return;
    }

    /* Build output filename */
    strncpy(output_file, input_file, MAX_PATH_LEN - 10);
    char *dot = strrchr(output_file, '.');
    if (dot) *dot = '\0';
    strcat(output_file, out_ext);

    printf("  Output: %s\n", output_file);

    /* Try pandoc (universal converter), then libreoffice */
#ifdef _WIN32
    snprintf(cmd, sizeof(cmd),
        "where pandoc >nul 2>nul && (pandoc \"%s\" -o \"%s\" 2>nul && echo   Done!) || "
        "where soffice >nul 2>nul && (soffice --headless --convert-to %s \"%s\" 2>nul && echo   Done!) || "
        "(echo   Install pandoc or LibreOffice for document conversion)",
        input_file, output_file,
        out_ext + 1, input_file);
#else
    snprintf(cmd, sizeof(cmd),
        "command -v pandoc >/dev/null 2>&1 && pandoc '%s' -o '%s' 2>/dev/null && echo '  Done!' || "
        "command -v soffice >/dev/null 2>&1 && soffice --headless --convert-to %s '%s' 2>/dev/null && echo '  Done!' || "
        "echo '  Install pandoc or LibreOffice'",
        input_file, output_file,
        out_ext + 1, input_file);
#endif

    term_set_color(COLOR_YELLOW, COLOR_BLACK);
    printf("\n  Converting...\n");
    term_reset_color();

    system(cmd);

    printf("  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

static void convert_audio_video(void) {
    char input_file[MAX_PATH_LEN], output_file[MAX_PATH_LEN];
    char input[MAX_INPUT_LEN], cmd[MAX_PATH_LEN * 3];

    printf("\n  Audio/Video Converter (via FFmpeg)\n");
    printf("  Audio: mp3, wav, flac, ogg, aac, m4a\n");
    printf("  Video: mp4, avi, mkv, webm, mov\n\n");

    printf("  Input file: ");
    fflush(stdout);
    if (fgets(input_file, sizeof(input_file), stdin) == NULL) return;
    trim_nl(input_file);
    if (strlen(input_file) == 0) return;

    printf("  Output file (with extension): ");
    fflush(stdout);
    if (fgets(output_file, sizeof(output_file), stdin) == NULL) return;
    trim_nl(output_file);
    if (strlen(output_file) == 0) return;

    printf("  Quality (1=best, 5=smallest) [3]: ");
    fflush(stdout);
    int quality = 3;
    if (fgets(input, sizeof(input), stdin) && strlen(input) > 1) {
        int q = atoi(input);
        if (q >= 1 && q <= 5) quality = q;
    }

    int crf = 18 + (quality - 1) * 5;

#ifdef _WIN32
    snprintf(cmd, sizeof(cmd),
        "where ffmpeg >nul 2>nul && (ffmpeg -i \"%s\" -crf %d \"%s\" -y 2>&1) || "
        "(echo   FFmpeg not found. Install from https://ffmpeg.org)",
        input_file, crf, output_file);
#else
    snprintf(cmd, sizeof(cmd),
        "command -v ffmpeg >/dev/null 2>&1 && ffmpeg -i '%s' -crf %d '%s' -y 2>&1 || "
        "echo '  FFmpeg not found. Install: sudo apt install ffmpeg'",
        input_file, crf, output_file);
#endif

    term_set_color(COLOR_YELLOW, COLOR_BLACK);
    printf("\n  Converting (quality CRF=%d)...\n", crf);
    term_reset_color();

    system(cmd);

    printf("\n  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

static void convert_text_encoding(void) {
    char input_file[MAX_PATH_LEN];
    char input[MAX_INPUT_LEN], cmd[MAX_PATH_LEN * 3];

    printf("\n  Text Encoding Converter\n\n");

    printf("  Input file: ");
    fflush(stdout);
    if (fgets(input_file, sizeof(input_file), stdin) == NULL) return;
    trim_nl(input_file);
    if (strlen(input_file) == 0) return;

    /* Detect current encoding */
    printf("\n  Detecting encoding...\n");
#ifdef _WIN32
    snprintf(cmd, sizeof(cmd),
        "where file >nul 2>nul && (file --mime-encoding \"%s\") || (echo   Cannot detect)", input_file);
#else
    snprintf(cmd, sizeof(cmd), "file --mime-encoding '%s' 2>/dev/null || echo '  Cannot detect'", input_file);
#endif
    system(cmd);

    printf("\n  Convert to:\n");
    printf("   1. UTF-8\n");
    printf("   2. UTF-16\n");
    printf("   3. ASCII\n");
    printf("   4. ISO-8859-1 (Latin-1)\n");
    printf("  Select [1]: ");
    fflush(stdout);
    if (fgets(input, sizeof(input), stdin) == NULL) return;

    const char *target;
    switch (atoi(input)) {
    case 2: target = "UTF-16"; break;
    case 3: target = "ASCII"; break;
    case 4: target = "ISO-8859-1"; break;
    default: target = "UTF-8"; break;
    }

    char output_file[MAX_PATH_LEN];
    snprintf(output_file, sizeof(output_file), "%s.converted", input_file);

#ifdef _WIN32
    snprintf(cmd, sizeof(cmd),
        "powershell -NoProfile -Command \""
        "$c=Get-Content -Path '%s' -Raw -Encoding Default;"
        "[IO.File]::WriteAllText('%s',$c,[Text.Encoding]::GetEncoding('%s'));"
        "Write-Host '  Converted to %s'\"",
        input_file, output_file, target, target);
#else
    snprintf(cmd, sizeof(cmd),
        "iconv -t %s '%s' > '%s' 2>/dev/null && echo '  Converted to %s: %s' || "
        "echo '  Conversion failed (iconv not available?)'",
        target, input_file, output_file, target, output_file);
#endif

    system(cmd);

    printf("  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

void run_econverter(void) {
    char input[MAX_INPUT_LEN];

    while (1) {
        CLEAR_SCREEN();
        term_set_color(COLOR_CYAN, COLOR_BLACK);
        printf("  +========================================+\n");
        printf("  |    eConverter - File Format Converter   |\n");
        printf("  +========================================+\n");
        term_reset_color();

        printf("\n  Convert between file formats.\n\n");
        printf("   1. Image  (PNG/JPG/BMP/GIF/WebP/TIFF)\n");
        printf("   2. Document (PDF/Word/TXT/HTML)\n");
        printf("   3. Audio/Video (MP3/WAV/MP4/AVI/MKV)\n");
        printf("   4. Text Encoding (UTF-8/UTF-16/ASCII)\n");
        printf("   0. Back to Menu\n");
        printf("\n  Select: ");
        fflush(stdout);

        if (fgets(input, sizeof(input), stdin) == NULL) return;

        CLEAR_SCREEN();
        switch (atoi(input)) {
        case 1: convert_image(); break;
        case 2: convert_document(); break;
        case 3: convert_audio_video(); break;
        case 4: convert_text_encoding(); break;
        case 0: return;
        }
    }
}
