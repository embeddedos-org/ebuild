// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/* ezip.c - eZip: 7-Zip style archive extractor & compressor */
#include "eosuite.h"
#include "platform.h"

static void trim_nl(char *s) {
    size_t len = strlen(s);
    if (len > 0 && s[len - 1] == '\n') s[len - 1] = '\0';
    if (len > 1 && s[len - 2] == '\r') s[len - 2] = '\0';
}

static int has_7z(void) {
#ifdef _WIN32
    return system("where 7z >nul 2>nul") == 0 ||
           system("where \"C:\\Program Files\\7-Zip\\7z.exe\" >nul 2>nul") == 0;
#else
    return system("command -v 7z > /dev/null 2>&1") == 0;
#endif
}

static const char* get_7z_cmd(void) {
#ifdef _WIN32
    if (system("where 7z >nul 2>nul") == 0) return "7z";
    return "\"C:\\Program Files\\7-Zip\\7z.exe\"";
#else
    return "7z";
#endif
}

static void ezip_list(void) {
    char input[MAX_INPUT_LEN];
    char path[MAX_PATH_LEN];

    printf("\n  Enter archive path: ");
    fflush(stdout);
    if (fgets(path, sizeof(path), stdin) == NULL) return;
    trim_nl(path);
    if (strlen(path) == 0) return;

    char cmd[MAX_PATH_LEN * 2];
    const char *ext = strrchr(path, '.');
    int use_7z = has_7z();

    if (use_7z) {
        snprintf(cmd, sizeof(cmd), "%s l \"%s\"", get_7z_cmd(), path);
#ifdef _WIN32
    } else if (ext && _stricmp(ext, ".zip") == 0) {
        snprintf(cmd, sizeof(cmd),
            "powershell -NoProfile -Command \""
            "Add-Type -Assembly System.IO.Compression.FileSystem;"
            "$a=[IO.Compression.ZipFile]::OpenRead('%s');"
            "foreach($e in $a.Entries){"
            "Write-Host ('{0,12} {1,20} {2}' -f $e.Length,$e.LastWriteTime,$e.FullName)};"
            "$a.Dispose()\"", path);
    } else {
        snprintf(cmd, sizeof(cmd), "tar -tvf \"%s\"", path);
#else
    } else if (ext && strcmp(ext, ".zip") == 0) {
        snprintf(cmd, sizeof(cmd), "unzip -l '%s'", path);
    } else if (ext && (strcmp(ext, ".gz") == 0 || strcmp(ext, ".tgz") == 0)) {
        snprintf(cmd, sizeof(cmd), "tar -tzf '%s'", path);
    } else if (ext && strcmp(ext, ".bz2") == 0) {
        snprintf(cmd, sizeof(cmd), "tar -tjf '%s'", path);
    } else if (ext && strcmp(ext, ".xz") == 0) {
        snprintf(cmd, sizeof(cmd), "tar -tJf '%s'", path);
    } else {
        snprintf(cmd, sizeof(cmd), "tar -tf '%s' 2>/dev/null || unzip -l '%s' 2>/dev/null", path, path);
#endif
    }

    term_set_color(COLOR_CYAN, COLOR_BLACK);
    printf("\n  Archive: %s\n", path);
    printf("  ----------------------------------------\n");
    term_reset_color();

    system(cmd);

    printf("\n  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

static void ezip_extract(void) {
    char input[MAX_INPUT_LEN];
    char path[MAX_PATH_LEN];
    char dest[MAX_PATH_LEN];

    printf("\n  Archive to extract: ");
    fflush(stdout);
    if (fgets(path, sizeof(path), stdin) == NULL) return;
    trim_nl(path);
    if (strlen(path) == 0) return;

    printf("  Destination (blank = current dir): ");
    fflush(stdout);
    if (fgets(dest, sizeof(dest), stdin) == NULL) return;
    trim_nl(dest);

    char cmd[MAX_PATH_LEN * 3];
    int use_7z = has_7z();

    if (use_7z) {
        if (strlen(dest) > 0)
            snprintf(cmd, sizeof(cmd), "%s x \"%s\" -o\"%s\" -y", get_7z_cmd(), path, dest);
        else
            snprintf(cmd, sizeof(cmd), "%s x \"%s\" -y", get_7z_cmd(), path);
    } else {
        const char *ext = strrchr(path, '.');
#ifdef _WIN32
        if (ext && _stricmp(ext, ".zip") == 0) {
            if (strlen(dest) > 0)
                snprintf(cmd, sizeof(cmd),
                    "powershell -NoProfile -Command \"Expand-Archive -Path '%s' -DestinationPath '%s' -Force\"", path, dest);
            else
                snprintf(cmd, sizeof(cmd),
                    "powershell -NoProfile -Command \"Expand-Archive -Path '%s' -DestinationPath '.' -Force\"", path);
        } else {
            if (strlen(dest) > 0)
                snprintf(cmd, sizeof(cmd), "tar -xf \"%s\" -C \"%s\"", path, dest);
            else
                snprintf(cmd, sizeof(cmd), "tar -xf \"%s\"", path);
        }
#else
        if (ext && strcmp(ext, ".zip") == 0) {
            if (strlen(dest) > 0)
                snprintf(cmd, sizeof(cmd), "unzip -o '%s' -d '%s'", path, dest);
            else
                snprintf(cmd, sizeof(cmd), "unzip -o '%s'", path);
        } else {
            if (strlen(dest) > 0)
                snprintf(cmd, sizeof(cmd), "tar -xf '%s' -C '%s'", path, dest);
            else
                snprintf(cmd, sizeof(cmd), "tar -xf '%s'", path);
        }
#endif
    }

    term_set_color(COLOR_YELLOW, COLOR_BLACK);
    printf("\n  Extracting...\n");
    term_reset_color();

    int ret = system(cmd);
    if (ret == 0) {
        term_set_color(COLOR_GREEN, COLOR_BLACK);
        printf("  Extraction complete!\n");
    } else {
        term_set_color(COLOR_RED, COLOR_BLACK);
        printf("  Extraction failed (error %d)\n", ret);
    }
    term_reset_color();
    printf("  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

static void ezip_compress(void) {
    char input[MAX_INPUT_LEN];
    char output[MAX_PATH_LEN];
    char sources[MAX_PATH_LEN * 2];
    int format;

    printf("\n  Output format:\n");
    printf("   1. ZIP\n");
    printf("   2. 7Z (requires 7-Zip)\n");
    printf("   3. TAR.GZ\n");
    printf("   4. TAR\n");
    printf("  Select [1]: ");
    fflush(stdout);
    if (fgets(input, sizeof(input), stdin) == NULL) return;
    format = atoi(input);
    if (format < 1 || format > 4) format = 1;

    const char *extensions[] = {".zip", ".7z", ".tar.gz", ".tar"};
    printf("  Output filename (without extension): ");
    fflush(stdout);
    if (fgets(output, sizeof(output), stdin) == NULL) return;
    trim_nl(output);
    if (strlen(output) == 0) return;

    char full_output[MAX_PATH_LEN];
    snprintf(full_output, sizeof(full_output), "%s%s", output, extensions[format - 1]);

    printf("  Files/folders to compress (space-separated): ");
    fflush(stdout);
    if (fgets(sources, sizeof(sources), stdin) == NULL) return;
    trim_nl(sources);
    if (strlen(sources) == 0) return;

    char cmd[MAX_PATH_LEN * 4];
    int use_7z = has_7z();

    switch (format) {
    case 1: /* ZIP */
        if (use_7z)
            snprintf(cmd, sizeof(cmd), "%s a -tzip \"%s\" %s", get_7z_cmd(), full_output, sources);
#ifdef _WIN32
        else
            snprintf(cmd, sizeof(cmd),
                "powershell -NoProfile -Command \"Compress-Archive -Path %s -DestinationPath '%s' -Force\"",
                sources, full_output);
#else
        else
            snprintf(cmd, sizeof(cmd), "zip -r '%s' %s", full_output, sources);
#endif
        break;
    case 2: /* 7Z */
        if (use_7z)
            snprintf(cmd, sizeof(cmd), "%s a \"%s\" %s", get_7z_cmd(), full_output, sources);
        else {
            term_set_color(COLOR_RED, COLOR_BLACK);
            printf("  7-Zip not found! Install from https://7-zip.org\n");
            term_reset_color();
            printf("  Press Enter...\n");
            fgets(input, sizeof(input), stdin);
            return;
        }
        break;
    case 3: /* TAR.GZ */
#ifdef _WIN32
        snprintf(cmd, sizeof(cmd), "tar -czf \"%s\" %s", full_output, sources);
#else
        snprintf(cmd, sizeof(cmd), "tar -czf '%s' %s", full_output, sources);
#endif
        break;
    case 4: /* TAR */
#ifdef _WIN32
        snprintf(cmd, sizeof(cmd), "tar -cf \"%s\" %s", full_output, sources);
#else
        snprintf(cmd, sizeof(cmd), "tar -cf '%s' %s", full_output, sources);
#endif
        break;
    }

    term_set_color(COLOR_YELLOW, COLOR_BLACK);
    printf("\n  Compressing to: %s\n", full_output);
    term_reset_color();

    int ret = system(cmd);
    if (ret == 0) {
        term_set_color(COLOR_GREEN, COLOR_BLACK);
        printf("  Archive created: %s\n", full_output);
    } else {
        term_set_color(COLOR_RED, COLOR_BLACK);
        printf("  Compression failed (error %d)\n", ret);
    }
    term_reset_color();
    printf("  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

static void ezip_test(void) {
    char input[MAX_INPUT_LEN];
    char path[MAX_PATH_LEN];

    printf("\n  Archive to test: ");
    fflush(stdout);
    if (fgets(path, sizeof(path), stdin) == NULL) return;
    trim_nl(path);
    if (strlen(path) == 0) return;

    char cmd[MAX_PATH_LEN * 2];
    if (has_7z()) {
        snprintf(cmd, sizeof(cmd), "%s t \"%s\"", get_7z_cmd(), path);
    } else {
#ifdef _WIN32
        snprintf(cmd, sizeof(cmd), "tar -tf \"%s\" >nul 2>nul && echo   Archive OK || echo   Archive CORRUPT", path);
#else
        snprintf(cmd, sizeof(cmd), "tar -tf '%s' > /dev/null 2>&1 && echo '  Archive OK' || echo '  Archive CORRUPT'", path);
#endif
    }

    term_set_color(COLOR_YELLOW, COLOR_BLACK);
    printf("\n  Testing integrity...\n");
    term_reset_color();

    system(cmd);

    printf("\n  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

void run_ezip(void) {
    char input[MAX_INPUT_LEN];

    while (1) {
        CLEAR_SCREEN();
        term_set_color(COLOR_CYAN, COLOR_BLACK);
        printf("  +========================================+\n");
        printf("  |    eZip - Archive Manager (7-Zip)      |\n");
        printf("  +========================================+\n");
        term_reset_color();

        printf("\n  Formats: .zip .7z .tar .tar.gz .tgz .bz2 .xz .rar\n");
        if (has_7z()) {
            term_set_color(COLOR_GREEN, COLOR_BLACK);
            printf("  7-Zip: INSTALLED\n");
        } else {
            term_set_color(COLOR_YELLOW, COLOR_BLACK);
            printf("  7-Zip: not found (using fallback tools)\n");
        }
        term_reset_color();

        printf("\n   1. List archive contents\n");
        printf("   2. Extract archive\n");
        printf("   3. Compress / Create archive\n");
        printf("   4. Test archive integrity\n");
        printf("   0. Back to Menu\n");
        printf("\n  Select: ");
        fflush(stdout);

        if (fgets(input, sizeof(input), stdin) == NULL) return;

        CLEAR_SCREEN();
        switch (atoi(input)) {
        case 1: ezip_list();     break;
        case 2: ezip_extract();  break;
        case 3: ezip_compress(); break;
        case 4: ezip_test();     break;
        case 0: return;
        }
    }
}
