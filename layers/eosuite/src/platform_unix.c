// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/* platform_unix.c - Linux/macOS platform implementation */
#ifndef _WIN32
#include "platform.h"

static struct termios orig_termios;
static int raw_mode_enabled = 0;

static void enable_raw_mode(void) {
    if (raw_mode_enabled) return;
    struct termios raw;
    tcgetattr(STDIN_FILENO, &orig_termios);
    raw = orig_termios;
    raw.c_lflag &= ~(ECHO | ICANON | ISIG);
    raw.c_iflag &= ~(IXON | ICRNL);
    raw.c_cc[VMIN] = 0; raw.c_cc[VTIME] = 0;
    tcsetattr(STDIN_FILENO, TCSAFLUSH, &raw);
    raw_mode_enabled = 1;
}
static void disable_raw_mode(void) {
    if (!raw_mode_enabled) return;
    tcsetattr(STDIN_FILENO, TCSAFLUSH, &orig_termios);
    raw_mode_enabled = 0;
}
void platform_init(void) { setvbuf(stdout, NULL, _IONBF, 0); }
void platform_cleanup(void) { disable_raw_mode(); term_reset_color(); term_show_cursor(); }
void term_set_cursor(int r, int c) { printf("\033[%d;%dH",r,c); fflush(stdout); }
void term_hide_cursor(void) { printf("\033[?25l"); fflush(stdout); }
void term_show_cursor(void) { printf("\033[?25h"); fflush(stdout); }
void term_get_size(int *rows, int *cols) {
    struct winsize ws;
    if (ioctl(STDOUT_FILENO, TIOCGWINSZ, &ws)==0) { *cols=ws.ws_col; *rows=ws.ws_row; }
    else { *cols=80; *rows=24; }
}
void term_set_color(int fg, int bg) { printf("\033[%d;%dm",30+fg,40+bg); fflush(stdout); }
void term_reset_color(void) { printf("\033[0m"); fflush(stdout); }
int key_available(void) {
    enable_raw_mode();
    fd_set fds; struct timeval tv={0,0};
    FD_ZERO(&fds); FD_SET(STDIN_FILENO, &fds);
    return select(STDIN_FILENO+1, &fds, NULL, NULL, &tv) > 0;
}
int key_read(void) {
    enable_raw_mode();
    unsigned char ch;
    if (read(STDIN_FILENO, &ch, 1) != 1) return 0;
    if (ch == 27) {
        unsigned char seq[2];
        if (read(STDIN_FILENO, &seq[0], 1) != 1) return KEY_ESCAPE;
        if (read(STDIN_FILENO, &seq[1], 1) != 1) return KEY_ESCAPE;
        if (seq[0]=='[') { switch(seq[1]) { case 'A': return KEY_UP; case 'B': return KEY_DOWN; case 'C': return KEY_RIGHT; case 'D': return KEY_LEFT; } }
        return KEY_ESCAPE;
    }
    if (ch==13) return KEY_ENTER;
    if (ch==127) return KEY_BACKSPACE;
    return (int)ch;
}
void key_flush(void) { enable_raw_mode(); while(key_available()) { unsigned char c; (void)read(STDIN_FILENO,&c,1); } }
#endif
