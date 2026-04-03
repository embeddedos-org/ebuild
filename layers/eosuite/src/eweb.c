// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/* eweb.c - eWeb: Lightweight terminal web browser */
#include "eosuite.h"
#include "platform.h"
#include <ctype.h>

#ifdef _WIN32
  #define strncasecmp _strnicmp
#endif

#define EWEB_BUF_SIZE    65536
#define EWEB_MAX_URL     512
#define EWEB_HISTORY_MAX 32

static char history[EWEB_HISTORY_MAX][EWEB_MAX_URL];
static int  history_count = 0;
static int  history_pos   = -1;

static void history_push(const char *url) {
    if (history_count > 0 && strcmp(history[history_count - 1], url) == 0)
        return;
    if (history_count < EWEB_HISTORY_MAX) {
        strncpy(history[history_count], url, EWEB_MAX_URL - 1);
        history_count++;
    } else {
        int i;
        for (i = 0; i < EWEB_HISTORY_MAX - 1; i++)
            strcpy(history[i], history[i + 1]);
        strncpy(history[EWEB_HISTORY_MAX - 1], url, EWEB_MAX_URL - 1);
    }
    history_pos = history_count - 1;
}

static void strip_html(const char *html, char *out, size_t out_size) {
    const char *p = html;
    char *o = out;
    char *end = out + out_size - 1;
    int in_tag = 0;
    int in_script = 0;
    int in_style = 0;
    int last_was_space = 0;
    int newline_count = 0;

    while (*p && o < end) {
        if (in_script) {
            if (strncasecmp(p, "</script", 8) == 0) in_script = 0;
            p++;
            continue;
        }
        if (in_style) {
            if (strncasecmp(p, "</style", 7) == 0) in_style = 0;
            p++;
            continue;
        }

        if (*p == '<') {
            in_tag = 1;
            if (strncasecmp(p, "<script", 7) == 0) in_script = 1;
            if (strncasecmp(p, "<style", 6) == 0) in_style = 1;

            if (strncasecmp(p, "<br", 3) == 0 ||
                strncasecmp(p, "<p", 2) == 0 ||
                strncasecmp(p, "<div", 4) == 0 ||
                strncasecmp(p, "<li", 3) == 0 ||
                strncasecmp(p, "<h1", 3) == 0 ||
                strncasecmp(p, "<h2", 3) == 0 ||
                strncasecmp(p, "<h3", 3) == 0 ||
                strncasecmp(p, "<tr", 3) == 0) {
                if (newline_count < 2 && o > out) {
                    *o++ = '\n';
                    newline_count++;
                    last_was_space = 1;
                }
            }
            p++;
            continue;
        }

        if (*p == '>') {
            in_tag = 0;
            p++;
            continue;
        }

        if (in_tag) { p++; continue; }

        if (*p == '&') {
            if (strncmp(p, "&amp;", 5) == 0) { *o++ = '&'; p += 5; }
            else if (strncmp(p, "&lt;", 4) == 0) { *o++ = '<'; p += 4; }
            else if (strncmp(p, "&gt;", 4) == 0) { *o++ = '>'; p += 4; }
            else if (strncmp(p, "&quot;", 6) == 0) { *o++ = '"'; p += 6; }
            else if (strncmp(p, "&nbsp;", 6) == 0) { *o++ = ' '; p += 6; }
            else if (strncmp(p, "&#", 2) == 0) {
                while (*p && *p != ';') p++;
                if (*p == ';') p++;
                *o++ = ' ';
            }
            else { *o++ = '&'; p++; }
            last_was_space = 0;
            newline_count = 0;
            continue;
        }

        if (isspace((unsigned char)*p)) {
            if (!last_was_space && o > out) {
                if (*p == '\n') {
                    if (newline_count < 2) { *o++ = '\n'; newline_count++; }
                } else {
                    *o++ = ' ';
                }
                last_was_space = 1;
            }
            p++;
            continue;
        }

        *o++ = *p++;
        last_was_space = 0;
        newline_count = 0;
    }
    *o = '\0';
}

static int fetch_url(const char *url, char *output, size_t output_size) {
    char tmpfile[MAX_PATH_LEN];
    char cmd[EWEB_MAX_URL + 256];

#ifdef _WIN32
    const char *temp = getenv("TEMP");
    if (!temp) temp = ".";
    snprintf(tmpfile, sizeof(tmpfile), "%s\\eweb_page.tmp", temp);
    snprintf(cmd, sizeof(cmd),
        "curl -sL -m 10 -A \"eWeb/1.0\" -o \"%s\" \"%s\" 2>nul",
        tmpfile, url);
#else
    snprintf(tmpfile, sizeof(tmpfile), "/tmp/eweb_page.tmp");
    snprintf(cmd, sizeof(cmd),
        "curl -sL -m 10 -A 'eWeb/1.0' -o '%s' '%s' 2>/dev/null",
        tmpfile, url);
#endif

    int ret = system(cmd);
    if (ret != 0) return 0;

    FILE *f = fopen(tmpfile, "rb");
    if (!f) return 0;

    size_t bytes = fread(output, 1, output_size - 1, f);
    output[bytes] = '\0';
    fclose(f);

#ifdef _WIN32
    snprintf(cmd, sizeof(cmd), "del /q \"%s\" 2>nul", tmpfile);
#else
    snprintf(cmd, sizeof(cmd), "rm -f '%s' 2>/dev/null", tmpfile);
#endif
    system(cmd);

    return (int)bytes;
}

static void display_page(const char *url, const char *text, int scroll) {
    int rows, cols, p;
    term_get_size(&rows, &cols);
    if (cols < 20) cols = 80;
    if (rows < 10) rows = 24;

    CLEAR_SCREEN();

    term_set_color(COLOR_BLACK, COLOR_CYAN);
    printf(" eWeb | %s", url);
    int used = 9 + (int)strlen(url);
    for (p = used; p < cols; p++) printf(" ");
    term_reset_color();
    printf("\n");

    /* Skip lines for scroll */
    const char *line = text;
    int skip = 0;
    while (*line && skip < scroll) {
        if (*line == '\n') skip++;
        line++;
    }

    int line_num = 0;
    int max_lines = rows - 4;
    while (*line && line_num < max_lines) {
        const char *eol = strchr(line, '\n');
        int len = eol ? (int)(eol - line) : (int)strlen(line);
        if (len > cols - 2) len = cols - 2;
        printf("  %.*s\n", len, line);
        line_num++;
        line = eol ? eol + 1 : line + strlen(line);
    }

    term_set_color(COLOR_BLACK, COLOR_GREEN);
    printf(" [u]rl [b]ack [j]down [k]up [s]ave [h]ome [q]uit ");
    for (p = 50; p < cols; p++) printf(" ");
    term_reset_color();
}

void run_eweb(void) {
    char input[MAX_INPUT_LEN];
    char url[EWEB_MAX_URL] = "";
    char *raw_html = NULL;
    char *page_text = NULL;
    int scroll = 0;

    raw_html = (char *)malloc(EWEB_BUF_SIZE);
    page_text = (char *)malloc(EWEB_BUF_SIZE);
    if (!raw_html || !page_text) {
        printf("  Error: Out of memory\n");
        free(raw_html); free(page_text);
        return;
    }
    raw_html[0] = '\0';
    page_text[0] = '\0';

    int page_loaded = 0;

    while (1) {
        if (!page_loaded) {
            CLEAR_SCREEN();
            term_set_color(COLOR_CYAN, COLOR_BLACK);
            printf("  +========================================+\n");
            printf("  |        eWeb - Terminal Browser         |\n");
            printf("  +========================================+\n");
            term_reset_color();

            printf("\n  Text-mode browser. Fetches via curl, strips HTML.\n\n");
            printf("  Quick links:\n");
            term_set_color(COLOR_GREEN, COLOR_BLACK);
            printf("   1. example.com\n");
            printf("   2. wikipedia.org\n");
            printf("   3. Enter custom URL\n");
            term_reset_color();
            printf("   0. Back to Menu\n");
            printf("\n  Select: ");
            fflush(stdout);

            if (fgets(input, sizeof(input), stdin) == NULL) break;

            switch (atoi(input)) {
            case 1: strcpy(url, "https://example.com"); break;
            case 2: strcpy(url, "https://en.wikipedia.org"); break;
            case 3:
                printf("  URL: ");
                fflush(stdout);
                if (fgets(url, sizeof(url), stdin) == NULL) { url[0] = '\0'; continue; }
                { size_t l = strlen(url); if (l > 0 && url[l-1] == '\n') url[l-1] = '\0'; }
                break;
            case 0:
                free(raw_html); free(page_text);
                return;
            default: continue;
            }

            if (strlen(url) == 0) continue;
            if (strncmp(url, "http://", 7) != 0 && strncmp(url, "https://", 8) != 0) {
                char tmp[EWEB_MAX_URL];
                snprintf(tmp, sizeof(tmp), "https://%s", url);
                strcpy(url, tmp);
            }
        }

        CLEAR_SCREEN();
        term_set_color(COLOR_YELLOW, COLOR_BLACK);
        printf("\n  Loading: %s ...\n", url);
        term_reset_color();
        fflush(stdout);

        int bytes = fetch_url(url, raw_html, EWEB_BUF_SIZE);
        if (bytes <= 0) {
            term_set_color(COLOR_RED, COLOR_BLACK);
            printf("\n  Error: Failed to load. Ensure 'curl' is installed.\n");
            term_reset_color();
            printf("  Press Enter...\n");
            fgets(input, sizeof(input), stdin);
            page_loaded = 0;
            url[0] = '\0';
            continue;
        }

        strip_html(raw_html, page_text, EWEB_BUF_SIZE);
        history_push(url);
        page_loaded = 1;
        scroll = 0;

        /* Page viewing loop */
        while (page_loaded) {
            display_page(url, page_text, scroll);
            printf("\n> ");
            fflush(stdout);

            if (fgets(input, sizeof(input), stdin) == NULL) { page_loaded = 0; break; }
            { size_t l = strlen(input); if (l > 0 && input[l-1] == '\n') input[l-1] = '\0'; }

            if (strcmp(input, "q") == 0) {
                free(raw_html); free(page_text);
                return;
            } else if (strcmp(input, "j") == 0 || strcmp(input, "down") == 0) {
                scroll += 5;
            } else if (strcmp(input, "k") == 0 || strcmp(input, "up") == 0) {
                scroll -= 5;
                if (scroll < 0) scroll = 0;
            } else if (strcmp(input, "u") == 0) {
                printf("  URL: ");
                fflush(stdout);
                if (fgets(url, sizeof(url), stdin)) {
                    size_t l = strlen(url);
                    if (l > 0 && url[l-1] == '\n') url[l-1] = '\0';
                    if (strncmp(url, "http", 4) != 0) {
                        char tmp[EWEB_MAX_URL];
                        snprintf(tmp, sizeof(tmp), "https://%s", url);
                        strcpy(url, tmp);
                    }
                }
                page_loaded = 0;
            } else if (strcmp(input, "b") == 0) {
                if (history_pos > 0) {
                    history_pos--;
                    strcpy(url, history[history_pos]);
                    page_loaded = 0;
                }
            } else if (strcmp(input, "s") == 0) {
                printf("  Save as: ");
                fflush(stdout);
                char fname[MAX_PATH_LEN];
                if (fgets(fname, sizeof(fname), stdin)) {
                    size_t l = strlen(fname);
                    if (l > 0 && fname[l-1] == '\n') fname[l-1] = '\0';
                    if (strlen(fname) > 0) {
                        FILE *sf = fopen(fname, "w");
                        if (sf) {
                            fprintf(sf, "URL: %s\n\n%s", url, page_text);
                            fclose(sf);
                            term_set_color(COLOR_GREEN, COLOR_BLACK);
                            printf("  Saved!\n");
                            term_reset_color();
                            SLEEP_MS(600);
                        }
                    }
                }
            } else if (strcmp(input, "h") == 0) {
                page_loaded = 0;
                url[0] = '\0';
            } else if (strlen(input) > 3 && strchr(input, '.')) {
                strncpy(url, input, EWEB_MAX_URL - 1);
                if (strncmp(url, "http", 4) != 0) {
                    char tmp[EWEB_MAX_URL];
                    snprintf(tmp, sizeof(tmp), "https://%s", url);
                    strcpy(url, tmp);
                }
                page_loaded = 0;
            }
        }
    }

    free(raw_html);
    free(page_text);
}
