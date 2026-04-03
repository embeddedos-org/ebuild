// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/* epaint.c - ePaint: Lightweight terminal ASCII art drawing tool */
#include "eosuite.h"
#include "platform.h"

#define CANVAS_W 60
#define CANVAS_H 20

static char canvas[CANVAS_H][CANVAS_W];
static int  colors[CANVAS_H][CANVAS_W];
static int  cursor_x, cursor_y;
static int  current_color;
static char current_brush;
static int  pen_down;

static const char brushes[] = " .oO#@*+=~|/\\-_";
static const int  color_list[] = {
    COLOR_WHITE, COLOR_RED, COLOR_GREEN, COLOR_YELLOW,
    COLOR_BLUE, COLOR_MAGENTA, COLOR_CYAN, COLOR_WHITE
};
static const char *color_names[] = {
    "White", "Red", "Green", "Yellow",
    "Blue", "Magenta", "Cyan", "Bright"
};

static void canvas_clear(void) {
    int y, x;
    for (y = 0; y < CANVAS_H; y++)
        for (x = 0; x < CANVAS_W; x++) {
            canvas[y][x] = ' ';
            colors[y][x] = COLOR_WHITE;
        }
    cursor_x = CANVAS_W / 2;
    cursor_y = CANVAS_H / 2;
    current_color = 0;
    current_brush = '#';
    pen_down = 0;
}

static void canvas_draw_screen(void) {
    int x, y, p;
    int rows, cols;
    term_get_size(&rows, &cols);

    term_set_cursor(1, 1);

    /* Title bar */
    term_set_color(COLOR_BLACK, COLOR_CYAN);
    printf(" ePaint | Brush:'%c' Color:%-7s Pos:%02d,%02d Pen:%s ",
           current_brush, color_names[current_color],
           cursor_x, cursor_y, pen_down ? "DOWN" : "UP");
    for (p = 55; p < cols; p++) printf(" ");
    term_reset_color();

    /* Top border */
    term_set_cursor(2, 2);
    printf("+");
    for (x = 0; x < CANVAS_W; x++) printf("-");
    printf("+");

    /* Canvas rows */
    for (y = 0; y < CANVAS_H; y++) {
        term_set_cursor(3 + y, 2);
        printf("|");
        for (x = 0; x < CANVAS_W; x++) {
            if (x == cursor_x && y == cursor_y) {
                term_set_color(COLOR_BLACK, COLOR_WHITE);
                printf("%c", canvas[y][x] == ' ' ? '+' : canvas[y][x]);
                term_reset_color();
            } else if (canvas[y][x] != ' ') {
                term_set_color(colors[y][x], COLOR_BLACK);
                printf("%c", canvas[y][x]);
                term_reset_color();
            } else {
                printf(" ");
            }
        }
        printf("|");
    }

    /* Bottom border */
    term_set_cursor(3 + CANVAS_H, 2);
    printf("+");
    for (x = 0; x < CANVAS_W; x++) printf("-");
    printf("+");

    /* Help bar */
    term_set_cursor(4 + CANVAS_H, 2);
    term_set_color(COLOR_BLACK, COLOR_GREEN);
    printf(" Arrows:Move Space:Stamp D:PenDown E:Erase B:Brush C:Color F:Fill X:Clear ");
    term_reset_color();

    term_set_cursor(5 + CANVAS_H, 2);
    term_set_color(COLOR_BLACK, COLOR_GREEN);
    printf(" R:Rect L:Line S:Save O:Open Q:Quit                                       ");
    for (p = 78; p < cols; p++) printf(" ");
    term_reset_color();

    /* Brush row */
    term_set_cursor(6 + CANVAS_H, 2);
    printf(" Brushes: ");
    int i;
    for (i = 0; brushes[i]; i++) {
        if (brushes[i] == current_brush)
            term_set_color(COLOR_BLACK, COLOR_YELLOW);
        printf("[%c]", brushes[i] == ' ' ? '_' : brushes[i]);
        if (brushes[i] == current_brush)
            term_reset_color();
    }

    /* Color row */
    term_set_cursor(7 + CANVAS_H, 2);
    printf(" Colors:  ");
    for (i = 0; i < 8; i++) {
        if (i == current_color)
            term_set_color(COLOR_BLACK, color_list[i]);
        else
            term_set_color(color_list[i], COLOR_BLACK);
        printf(" %d ", i);
        term_reset_color();
    }

    fflush(stdout);
}

static void paint_stamp(void) {
    canvas[cursor_y][cursor_x] = current_brush;
    colors[cursor_y][cursor_x] = color_list[current_color];
}

static void paint_erase(void) {
    canvas[cursor_y][cursor_x] = ' ';
}

static void paint_fill(int sx, int sy, char target) {
    if (sx < 0 || sx >= CANVAS_W || sy < 0 || sy >= CANVAS_H) return;
    if (canvas[sy][sx] != target) return;
    if (canvas[sy][sx] == current_brush && colors[sy][sx] == color_list[current_color]) return;

    canvas[sy][sx] = current_brush;
    colors[sy][sx] = color_list[current_color];

    paint_fill(sx + 1, sy, target);
    paint_fill(sx - 1, sy, target);
    paint_fill(sx, sy + 1, target);
    paint_fill(sx, sy - 1, target);
}

static void paint_rect(void) {
    int x1 = cursor_x, y1 = cursor_y;
    int x2, y2, x, y;

    term_set_cursor(8 + CANVAS_H, 2);
    printf("  Move to opposite corner, press Enter...");
    fflush(stdout);

    while (1) {
        while (!key_available()) SLEEP_MS(30);
        int k = key_read();
        if (k == KEY_UP && cursor_y > 0) cursor_y--;
        else if (k == KEY_DOWN && cursor_y < CANVAS_H-1) cursor_y++;
        else if (k == KEY_LEFT && cursor_x > 0) cursor_x--;
        else if (k == KEY_RIGHT && cursor_x < CANVAS_W-1) cursor_x++;
        else if (k == KEY_ENTER || k == ' ') break;
        else if (k == KEY_ESCAPE) return;
        canvas_draw_screen();
        term_set_cursor(8 + CANVAS_H, 2);
        printf("  Rect: (%d,%d)->(%d,%d) Enter=draw Esc=cancel", x1, y1, cursor_x, cursor_y);
        fflush(stdout);
    }

    x2 = cursor_x; y2 = cursor_y;
    int minx = x1 < x2 ? x1 : x2, maxx = x1 > x2 ? x1 : x2;
    int miny = y1 < y2 ? y1 : y2, maxy = y1 > y2 ? y1 : y2;

    for (x = minx; x <= maxx; x++) {
        canvas[miny][x] = current_brush; colors[miny][x] = color_list[current_color];
        canvas[maxy][x] = current_brush; colors[maxy][x] = color_list[current_color];
    }
    for (y = miny; y <= maxy; y++) {
        canvas[y][minx] = current_brush; colors[y][minx] = color_list[current_color];
        canvas[y][maxx] = current_brush; colors[y][maxx] = color_list[current_color];
    }
}

static void paint_line(void) {
    int x1 = cursor_x, y1 = cursor_y;

    term_set_cursor(8 + CANVAS_H, 2);
    printf("  Move to end point, press Enter...");
    fflush(stdout);

    while (1) {
        while (!key_available()) SLEEP_MS(30);
        int k = key_read();
        if (k == KEY_UP && cursor_y > 0) cursor_y--;
        else if (k == KEY_DOWN && cursor_y < CANVAS_H-1) cursor_y++;
        else if (k == KEY_LEFT && cursor_x > 0) cursor_x--;
        else if (k == KEY_RIGHT && cursor_x < CANVAS_W-1) cursor_x++;
        else if (k == KEY_ENTER || k == ' ') break;
        else if (k == KEY_ESCAPE) return;
        canvas_draw_screen();
        term_set_cursor(8 + CANVAS_H, 2);
        printf("  Line: (%d,%d)->(%d,%d) Enter=draw Esc=cancel", x1, y1, cursor_x, cursor_y);
        fflush(stdout);
    }

    int x2 = cursor_x, y2 = cursor_y;
    int dx = abs(x2 - x1), dy = abs(y2 - y1);
    int sx = x1 < x2 ? 1 : -1, sy = y1 < y2 ? 1 : -1;
    int err = dx - dy;

    while (1) {
        if (x1 >= 0 && x1 < CANVAS_W && y1 >= 0 && y1 < CANVAS_H) {
            canvas[y1][x1] = current_brush;
            colors[y1][x1] = color_list[current_color];
        }
        if (x1 == x2 && y1 == y2) break;
        int e2 = 2 * err;
        if (e2 > -dy) { err -= dy; x1 += sx; }
        if (e2 < dx)  { err += dx; y1 += sy; }
    }
}

static void paint_save(void) {
    char filename[MAX_PATH_LEN];
    term_show_cursor();
    term_set_cursor(8 + CANVAS_H, 2);
    printf("  Save as: ");
    fflush(stdout);

    if (fgets(filename, sizeof(filename), stdin) == NULL) { term_hide_cursor(); return; }
    size_t len = strlen(filename);
    if (len > 0 && filename[len - 1] == '\n') filename[len - 1] = '\0';
    if (strlen(filename) == 0) { term_hide_cursor(); return; }

    FILE *f = fopen(filename, "w");
    if (!f) {
        term_set_cursor(9 + CANVAS_H, 2);
        term_set_color(COLOR_RED, COLOR_BLACK);
        printf("  Error saving!");
        term_reset_color();
        SLEEP_MS(800);
        term_hide_cursor();
        return;
    }

    int y, x;
    for (y = 0; y < CANVAS_H; y++) {
        int last = -1;
        for (x = CANVAS_W - 1; x >= 0; x--)
            if (canvas[y][x] != ' ') { last = x; break; }
        for (x = 0; x <= last; x++) fputc(canvas[y][x], f);
        fputc('\n', f);
    }
    fclose(f);

    term_set_cursor(9 + CANVAS_H, 2);
    term_set_color(COLOR_GREEN, COLOR_BLACK);
    printf("  Saved: %s", filename);
    term_reset_color();
    SLEEP_MS(600);
    term_hide_cursor();
}

static void paint_load(void) {
    char filename[MAX_PATH_LEN];
    term_show_cursor();
    term_set_cursor(8 + CANVAS_H, 2);
    printf("  Open file: ");
    fflush(stdout);

    if (fgets(filename, sizeof(filename), stdin) == NULL) { term_hide_cursor(); return; }
    size_t len = strlen(filename);
    if (len > 0 && filename[len - 1] == '\n') filename[len - 1] = '\0';
    if (strlen(filename) == 0) { term_hide_cursor(); return; }

    FILE *f = fopen(filename, "r");
    if (!f) {
        term_set_cursor(9 + CANVAS_H, 2);
        term_set_color(COLOR_RED, COLOR_BLACK);
        printf("  Cannot open file!");
        term_reset_color();
        SLEEP_MS(800);
        term_hide_cursor();
        return;
    }

    canvas_clear();
    int y = 0;
    char line[256];
    while (y < CANVAS_H && fgets(line, sizeof(line), f)) {
        int x;
        for (x = 0; x < CANVAS_W && line[x] && line[x] != '\n'; x++) {
            canvas[y][x] = line[x];
            colors[y][x] = COLOR_WHITE;
        }
        y++;
    }
    fclose(f);
    term_hide_cursor();
}

void run_epaint(void) {
    CLEAR_SCREEN();
    canvas_clear();
    term_hide_cursor();
    key_flush();

    int running = 1;

    while (running) {
        canvas_draw_screen();

        while (!key_available()) SLEEP_MS(30);
        int key = key_read();

        switch (key) {
        case KEY_UP:    if (cursor_y > 0) cursor_y--; break;
        case KEY_DOWN:  if (cursor_y < CANVAS_H-1) cursor_y++; break;
        case KEY_LEFT:  if (cursor_x > 0) cursor_x--; break;
        case KEY_RIGHT: if (cursor_x < CANVAS_W-1) cursor_x++; break;

        case ' ': paint_stamp(); break;
        case 'e': case 'E': paint_erase(); break;

        case 'd': case 'D':
            pen_down = !pen_down;
            if (pen_down) paint_stamp();
            break;

        case 'f': case 'F':
            paint_fill(cursor_x, cursor_y, canvas[cursor_y][cursor_x]);
            break;

        case 'r': case 'R': paint_rect(); break;
        case 'l': case 'L': paint_line(); break;

        case 'b': case 'B': {
            int idx = 0, i;
            for (i = 0; brushes[i]; i++)
                if (brushes[i] == current_brush) { idx = i; break; }
            idx = (idx + 1) % ((int)strlen(brushes));
            if (idx == 0) idx = 1;
            current_brush = brushes[idx];
            break;
        }

        case 'c': case 'C':
            current_color = (current_color + 1) % 8;
            break;

        case '0': case '1': case '2': case '3':
        case '4': case '5': case '6': case '7':
            current_color = key - '0';
            break;

        case 'x': case 'X': canvas_clear(); break;
        case 's': case 'S': paint_save(); break;
        case 'o': case 'O': paint_load(); break;
        case 'q': case 'Q': case KEY_ESCAPE: running = 0; break;
        }

        if (pen_down && (key == KEY_UP || key == KEY_DOWN || key == KEY_LEFT || key == KEY_RIGHT)) {
            paint_stamp();
        }
    }

    term_show_cursor();
}
