// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/* ecleaner.c - eCleaner: Lightweight system cleanup tool */
#include "eosuite.h"
#include "platform.h"

static void trim_nl(char *s) {
    size_t len = strlen(s);
    if (len > 0 && s[len - 1] == '\n') s[len - 1] = '\0';
}

#ifdef _WIN32

static void clean_temp_files(void) {
    char input[MAX_INPUT_LEN];
    const char *temp = getenv("TEMP");
    if (!temp) { printf("  TEMP not found.\n"); return; }

    term_set_color(COLOR_YELLOW, COLOR_BLACK);
    printf("\n  Scanning temp folder: %s\n", temp);
    term_reset_color();

    char cmd[MAX_PATH_LEN];
    snprintf(cmd, sizeof(cmd),
        "powershell -NoProfile -Command \""
        "$files=Get-ChildItem -Path '%s' -Recurse -File -ErrorAction SilentlyContinue;"
        "$size=($files | Measure-Object -Property Length -Sum).Sum;"
        "Write-Host ('  Files: {0}' -f $files.Count);"
        "Write-Host ('  Size:  {0:N2} MB' -f ($size/1MB))\"", temp);
    system(cmd);

    printf("\n  Delete temp files? (y/n): ");
    fflush(stdout);
    if (fgets(input, sizeof(input), stdin) == NULL) return;
    trim_nl(input);

    if (input[0] == 'y' || input[0] == 'Y') {
        snprintf(cmd, sizeof(cmd),
            "powershell -NoProfile -Command \""
            "Get-ChildItem -Path '%s' -Recurse -File -ErrorAction SilentlyContinue | "
            "Remove-Item -Force -ErrorAction SilentlyContinue;"
            "Write-Host '  Cleaned!'\"", temp);
        system(cmd);
    }

    printf("  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

static void clean_recycle_bin(void) {
    char input[MAX_INPUT_LEN];
    printf("\n  Empty Recycle Bin? (y/n): ");
    fflush(stdout);
    if (fgets(input, sizeof(input), stdin) == NULL) return;
    trim_nl(input);

    if (input[0] == 'y' || input[0] == 'Y') {
        system("powershell -NoProfile -Command \"Clear-RecycleBin -Force -ErrorAction SilentlyContinue; Write-Host '  Recycle Bin emptied!'\"");
    }

    printf("  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

static void clean_browser_cache(void) {
    char input[MAX_INPUT_LEN];
    const char *localappdata = getenv("LOCALAPPDATA");
    if (!localappdata) { printf("  LOCALAPPDATA not found.\n"); return; }

    term_set_color(COLOR_YELLOW, COLOR_BLACK);
    printf("\n  Browser cache locations:\n");
    term_reset_color();

    char path[MAX_PATH_LEN];
    const char *browsers[][2] = {
        {"Chrome",  "\\Google\\Chrome\\User Data\\Default\\Cache"},
        {"Edge",    "\\Microsoft\\Edge\\User Data\\Default\\Cache"},
        {"Firefox", ""},
    };

    int i;
    for (i = 0; i < 2; i++) {
        snprintf(path, sizeof(path), "%s%s", localappdata, browsers[i][1]);
        char cmd[MAX_PATH_LEN * 2];
        snprintf(cmd, sizeof(cmd),
            "powershell -NoProfile -Command \""
            "if(Test-Path '%s'){"
            "$s=(Get-ChildItem '%s' -Recurse -File -ErrorAction SilentlyContinue | "
            "Measure-Object -Property Length -Sum).Sum;"
            "Write-Host ('   %s: {0:N2} MB' -f ($s/1MB))"
            "} else { Write-Host '   %s: not found' }\"",
            path, path, browsers[i][0], browsers[i][0]);
        system(cmd);
    }

    printf("\n  Clear browser caches? (y/n): ");
    fflush(stdout);
    if (fgets(input, sizeof(input), stdin) == NULL) return;
    trim_nl(input);

    if (input[0] == 'y' || input[0] == 'Y') {
        for (i = 0; i < 2; i++) {
            snprintf(path, sizeof(path), "%s%s", localappdata, browsers[i][1]);
            char cmd[MAX_PATH_LEN * 2];
            snprintf(cmd, sizeof(cmd),
                "powershell -NoProfile -Command \""
                "if(Test-Path '%s'){"
                "Get-ChildItem '%s' -Recurse -File -ErrorAction SilentlyContinue | "
                "Remove-Item -Force -ErrorAction SilentlyContinue;"
                "Write-Host '   %s cache cleared'}\"",
                path, path, browsers[i][0]);
            system(cmd);
        }
    }

    printf("  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

static void clean_windows_update(void) {
    char input[MAX_INPUT_LEN];
    printf("\n  Clean Windows Update cache? (requires admin) (y/n): ");
    fflush(stdout);
    if (fgets(input, sizeof(input), stdin) == NULL) return;
    trim_nl(input);

    if (input[0] == 'y' || input[0] == 'Y') {
        term_set_color(COLOR_YELLOW, COLOR_BLACK);
        printf("  Attempting cleanup (may need admin rights)...\n");
        term_reset_color();
        system("powershell -NoProfile -Command \""
               "Start-Process -Verb RunAs -FilePath cleanmgr.exe -ArgumentList '/d C /sagerun:1' "
               "-ErrorAction SilentlyContinue\" 2>nul");
    }

    printf("  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

static void show_disk_usage(void) {
    char input[MAX_INPUT_LEN];
    term_set_color(COLOR_CYAN, COLOR_BLACK);
    printf("\n  Disk Usage:\n");
    printf("  ----------------------------------------\n");
    term_reset_color();

    system("powershell -NoProfile -Command \""
           "Get-PSDrive -PSProvider FileSystem | "
           "Format-Table Name,@{N='Used(GB)';E={'{0:N2}' -f ($_.Used/1GB)}},"
           "@{N='Free(GB)';E={'{0:N2}' -f ($_.Free/1GB)}},"
           "@{N='Total(GB)';E={'{0:N2}' -f (($_.Used+$_.Free)/1GB)}} -AutoSize\"");

    printf("  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

#else /* Linux / macOS */

static void clean_temp_files(void) {
    char input[MAX_INPUT_LEN];
    term_set_color(COLOR_YELLOW, COLOR_BLACK);
    printf("\n  Scanning /tmp ...\n");
    term_reset_color();

    system("du -sh /tmp 2>/dev/null");
    system("echo \"  Files: $(find /tmp -type f 2>/dev/null | wc -l)\"");

    printf("\n  Clean old temp files (>7 days)? (y/n): ");
    fflush(stdout);
    if (fgets(input, sizeof(input), stdin) == NULL) return;
    trim_nl(input);

    if (input[0] == 'y' || input[0] == 'Y') {
        system("find /tmp -type f -atime +7 -delete 2>/dev/null");
        term_set_color(COLOR_GREEN, COLOR_BLACK);
        printf("  Old temp files cleaned!\n");
        term_reset_color();
    }

    printf("  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

static void clean_recycle_bin(void) {
    char input[MAX_INPUT_LEN];
    const char *home = getenv("HOME");
    if (!home) return;

    char trash[MAX_PATH_LEN];
#ifdef __APPLE__
    snprintf(trash, sizeof(trash), "%s/.Trash", home);
#else
    snprintf(trash, sizeof(trash), "%s/.local/share/Trash", home);
#endif

    char cmd[MAX_PATH_LEN * 2];
    snprintf(cmd, sizeof(cmd), "du -sh '%s' 2>/dev/null", trash);
    system(cmd);

    printf("\n  Empty trash? (y/n): ");
    fflush(stdout);
    if (fgets(input, sizeof(input), stdin) == NULL) return;
    trim_nl(input);

    if (input[0] == 'y' || input[0] == 'Y') {
        snprintf(cmd, sizeof(cmd), "rm -rf '%s'/* '%s'/.[!.]* 2>/dev/null", trash, trash);
        system(cmd);
        term_set_color(COLOR_GREEN, COLOR_BLACK);
        printf("  Trash emptied!\n");
        term_reset_color();
    }

    printf("  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

static void clean_browser_cache(void) {
    char input[MAX_INPUT_LEN];
    const char *home = getenv("HOME");
    if (!home) return;

    term_set_color(COLOR_YELLOW, COLOR_BLACK);
    printf("\n  Browser cache sizes:\n");
    term_reset_color();

    char cmd[MAX_PATH_LEN * 2];
#ifdef __APPLE__
    snprintf(cmd, sizeof(cmd), "du -sh '%s/Library/Caches/Google/Chrome' 2>/dev/null || echo '   Chrome: not found'", home);
    system(cmd);
    snprintf(cmd, sizeof(cmd), "du -sh '%s/Library/Caches/Firefox' 2>/dev/null || echo '   Firefox: not found'", home);
    system(cmd);
#else
    snprintf(cmd, sizeof(cmd), "du -sh '%s/.cache/google-chrome' 2>/dev/null || echo '   Chrome: not found'", home);
    system(cmd);
    snprintf(cmd, sizeof(cmd), "du -sh '%s/.cache/mozilla/firefox' 2>/dev/null || echo '   Firefox: not found'", home);
    system(cmd);
#endif

    printf("\n  Clear browser caches? (y/n): ");
    fflush(stdout);
    if (fgets(input, sizeof(input), stdin) == NULL) return;
    trim_nl(input);

    if (input[0] == 'y' || input[0] == 'Y') {
#ifdef __APPLE__
        snprintf(cmd, sizeof(cmd), "rm -rf '%s/Library/Caches/Google/Chrome/Default/Cache' 2>/dev/null", home);
#else
        snprintf(cmd, sizeof(cmd), "rm -rf '%s/.cache/google-chrome/Default/Cache' 2>/dev/null", home);
#endif
        system(cmd);
        term_set_color(COLOR_GREEN, COLOR_BLACK);
        printf("  Caches cleared!\n");
        term_reset_color();
    }

    printf("  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

static void clean_windows_update(void) {
    char input[MAX_INPUT_LEN];
    term_set_color(COLOR_YELLOW, COLOR_BLACK);
    printf("\n  Package manager cache cleanup:\n");
    term_reset_color();

#ifdef __APPLE__
    printf("   brew cleanup (if installed)\n");
    printf("\n  Run cleanup? (y/n): ");
    fflush(stdout);
    if (fgets(input, sizeof(input), stdin) == NULL) return;
    trim_nl(input);
    if (input[0] == 'y' || input[0] == 'Y') {
        system("brew cleanup 2>/dev/null || echo '  brew not found'");
    }
#else
    printf("   apt/dnf cache cleanup\n");
    printf("\n  Run cleanup? (y/n): ");
    fflush(stdout);
    if (fgets(input, sizeof(input), stdin) == NULL) return;
    trim_nl(input);
    if (input[0] == 'y' || input[0] == 'Y') {
        system("sudo apt-get clean 2>/dev/null || sudo dnf clean all 2>/dev/null || echo '  No package manager found'");
    }
#endif

    printf("  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

static void show_disk_usage(void) {
    char input[MAX_INPUT_LEN];
    term_set_color(COLOR_CYAN, COLOR_BLACK);
    printf("\n  Disk Usage:\n");
    printf("  ----------------------------------------\n");
    term_reset_color();

    system("df -h 2>/dev/null");

    printf("\n  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

#endif /* _WIN32 */

void run_ecleaner(void) {
    char input[MAX_INPUT_LEN];

    while (1) {
        CLEAR_SCREEN();
        term_set_color(COLOR_CYAN, COLOR_BLACK);
        printf("  +========================================+\n");
        printf("  |     eCleaner - System Cleanup Tool     |\n");
        printf("  +========================================+\n");
        term_reset_color();

        printf("\n  Safe cleanup - no settings modified.\n\n");
        printf("   1. Clean Temp Files\n");
        printf("   2. Empty Recycle Bin / Trash\n");
        printf("   3. Clean Browser Cache\n");
        printf("   4. Package / Update Cache\n");
        printf("   5. Show Disk Usage\n");
        printf("   6. Run All Cleanups\n");
        printf("   0. Back to Menu\n");
        printf("\n  Select: ");
        fflush(stdout);

        if (fgets(input, sizeof(input), stdin) == NULL) return;

        CLEAR_SCREEN();
        term_set_color(COLOR_CYAN, COLOR_BLACK);
        printf("  eCleaner\n");
        printf("  ----------------------------------------\n");
        term_reset_color();

        switch (atoi(input)) {
        case 1: clean_temp_files(); break;
        case 2: clean_recycle_bin(); break;
        case 3: clean_browser_cache(); break;
        case 4: clean_windows_update(); break;
        case 5: show_disk_usage(); break;
        case 6:
            clean_temp_files();
            clean_recycle_bin();
            clean_browser_cache();
            clean_windows_update();
            show_disk_usage();
            break;
        case 0: return;
        }
    }
}
