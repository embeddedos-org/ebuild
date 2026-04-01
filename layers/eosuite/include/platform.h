// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef PLATFORM_H
#define PLATFORM_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #include <windows.h>
    #include <conio.h>
    #define CLEAR_SCREEN() system("cls")
    #define SLEEP_MS(ms) Sleep(ms)
#else
    #include <unistd.h>
    #include <termios.h>
    #include <sys/ioctl.h>
    #include <sys/select.h>
    #define CLEAR_SCREEN() printf("\033[2J\033[H")
    #define SLEEP_MS(ms) usleep((ms) * 1000)
#endif

void platform_init(void);
void platform_cleanup(void);
void term_set_cursor(int row, int col);
void term_hide_cursor(void);
void term_show_cursor(void);
void term_get_size(int *rows, int *cols);
void term_set_color(int fg, int bg);
void term_reset_color(void);
int  key_available(void);
int  key_read(void);
void key_flush(void);

#define COLOR_BLACK   0
#define COLOR_RED     1
#define COLOR_GREEN   2
#define COLOR_YELLOW  3
#define COLOR_BLUE    4
#define COLOR_MAGENTA 5
#define COLOR_CYAN    6
#define COLOR_WHITE   7

#define KEY_UP        256
#define KEY_DOWN      257
#define KEY_LEFT      258
#define KEY_RIGHT     259
#define KEY_ENTER     10
#define KEY_ESCAPE    27
#define KEY_BACKSPACE 8

#endif
