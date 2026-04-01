// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/* platform_win.c - Windows platform implementation */
#ifdef _WIN32

#include "platform.h"

#ifndef ENABLE_VIRTUAL_TERMINAL_PROCESSING
#define ENABLE_VIRTUAL_TERMINAL_PROCESSING 0x0004
#endif

static HANDLE hStdOut;
static HANDLE hStdIn;
static DWORD  origConsoleMode;

void platform_init(void) {
    hStdOut = GetStdHandle(STD_OUTPUT_HANDLE);
    hStdIn  = GetStdHandle(STD_INPUT_HANDLE);
    GetConsoleMode(hStdIn, &origConsoleMode);
    DWORD mode = 0;
    GetConsoleMode(hStdOut, &mode);
    mode |= ENABLE_VIRTUAL_TERMINAL_PROCESSING;
    SetConsoleMode(hStdOut, mode);
    SetConsoleOutputCP(CP_UTF8);
}

void platform_cleanup(void) {
    SetConsoleMode(hStdIn, origConsoleMode);
    term_reset_color();
    term_show_cursor();
}

void term_set_cursor(int row, int col) { printf("\033[%d;%dH", row, col); }
void term_hide_cursor(void) { printf("\033[?25l"); }
void term_show_cursor(void) { printf("\033[?25h"); }

void term_get_size(int *rows, int *cols) {
    CONSOLE_SCREEN_BUFFER_INFO csbi;
    if (GetConsoleScreenBufferInfo(hStdOut, &csbi)) {
        *cols = csbi.srWindow.Right - csbi.srWindow.Left + 1;
        *rows = csbi.srWindow.Bottom - csbi.srWindow.Top + 1;
    } else { *cols = 80; *rows = 24; }
}

void term_set_color(int fg, int bg) { printf("\033[%d;%dm", 30 + fg, 40 + bg); }
void term_reset_color(void) { printf("\033[0m"); }

int key_available(void) { return _kbhit(); }

int key_read(void) {
    int ch = _getch();
    if (ch == 0 || ch == 0xE0) {
        ch = _getch();
        switch (ch) {
            case 72: return KEY_UP;
            case 80: return KEY_DOWN;
            case 75: return KEY_LEFT;
            case 77: return KEY_RIGHT;
            default: return 0;
        }
    }
    if (ch == 13) return KEY_ENTER;
    if (ch == 8)  return KEY_BACKSPACE;
    return ch;
}

void key_flush(void) { while (_kbhit()) _getch(); }

#endif
