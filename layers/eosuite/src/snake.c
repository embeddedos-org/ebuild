// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eosuite.h"
#include "platform.h"

#define BOARD_W 40
#define BOARD_H 20
#define MAX_SNAKE 800

typedef struct { int x, y; } Point;

static Point snake[MAX_SNAKE];
static int snake_len;
static int dir_x, dir_y;
static Point food;
static int score;
static int game_over;
static int speed_ms;

static void place_food(void) {
    int valid;
    do {
        valid = 1;
        food.x = rand() % BOARD_W;
        food.y = rand() % BOARD_H;
        for (int i = 0; i < snake_len; i++) {
            if (snake[i].x == food.x && snake[i].y == food.y) {
                valid = 0;
                break;
            }
        }
    } while (!valid);
}

static void init_game(void) {
    srand((unsigned)time(NULL));
    snake_len = 3;
    snake[0].x = BOARD_W / 2;
    snake[0].y = BOARD_H / 2;
    snake[1].x = snake[0].x - 1;
    snake[1].y = snake[0].y;
    snake[2].x = snake[0].x - 2;
    snake[2].y = snake[0].y;
    dir_x = 1;
    dir_y = 0;
    score = 0;
    game_over = 0;
    speed_ms = 150;
    place_food();
}

static void draw_board(void) {
    term_set_cursor(1, 1);

    term_set_color(COLOR_CYAN, COLOR_BLACK);
    printf(" Score: %d", score);
    term_reset_color();
    printf("   ESC=Quit  Arrows=Move\n");

    term_set_color(COLOR_WHITE, COLOR_BLACK);
    printf("+");
    for (int x = 0; x < BOARD_W; x++) printf("-");
    printf("+\n");

    for (int y = 0; y < BOARD_H; y++) {
        printf("|");
        for (int x = 0; x < BOARD_W; x++) {
            int drawn = 0;

            if (snake[0].x == x && snake[0].y == y) {
                term_set_color(COLOR_GREEN, COLOR_BLACK);
                printf("@");
                term_reset_color();
                drawn = 1;
            }

            if (!drawn) {
                for (int i = 1; i < snake_len; i++) {
                    if (snake[i].x == x && snake[i].y == y) {
                        term_set_color(COLOR_GREEN, COLOR_BLACK);
                        printf("o");
                        term_reset_color();
                        drawn = 1;
                        break;
                    }
                }
            }

            if (!drawn && food.x == x && food.y == y) {
                term_set_color(COLOR_RED, COLOR_BLACK);
                printf("*");
                term_reset_color();
                drawn = 1;
            }

            if (!drawn) printf(" ");
        }
        term_set_color(COLOR_WHITE, COLOR_BLACK);
        printf("|\n");
    }

    printf("+");
    for (int x = 0; x < BOARD_W; x++) printf("-");
    printf("+\n");
    term_reset_color();
}

static void update_game(void) {
    int new_x = snake[0].x + dir_x;
    int new_y = snake[0].y + dir_y;

    if (new_x < 0 || new_x >= BOARD_W || new_y < 0 || new_y >= BOARD_H) {
        game_over = 1;
        return;
    }

    for (int i = 1; i < snake_len; i++) {
        if (snake[i].x == new_x && snake[i].y == new_y) {
            game_over = 1;
            return;
        }
    }

    int ate_food = (new_x == food.x && new_y == food.y);

    for (int i = snake_len; i > 0; i--) {
        snake[i] = snake[i - 1];
    }
    snake[0].x = new_x;
    snake[0].y = new_y;

    if (ate_food) {
        snake_len++;
        if (snake_len >= MAX_SNAKE) snake_len = MAX_SNAKE - 1;
        score += 10;
        if (speed_ms > 50) speed_ms -= 5;
        place_food();
    }
}

void run_snake(void) {
    CLEAR_SCREEN();
    term_set_color(COLOR_CYAN, COLOR_BLACK);
    printf("\n  +==============================+\n");
    printf("  |         SNAKE GAME           |\n");
    printf("  +==============================+\n");
    term_reset_color();
    printf("\n  Arrow keys to move, ESC to quit.\n");
    printf("  Press any key to start...\n");
    key_flush();
    while (!key_available()) SLEEP_MS(50);
    key_read();

    init_game();
    term_hide_cursor();
    CLEAR_SCREEN();

    while (!game_over) {
        draw_board();

        int wait = speed_ms;
        while (wait > 0) {
            if (key_available()) {
                int k = key_read();
                switch (k) {
                    case KEY_UP:    if (dir_y != 1)  { dir_x = 0;  dir_y = -1; } break;
                    case KEY_DOWN:  if (dir_y != -1) { dir_x = 0;  dir_y = 1;  } break;
                    case KEY_LEFT:  if (dir_x != 1)  { dir_x = -1; dir_y = 0;  } break;
                    case KEY_RIGHT: if (dir_x != -1) { dir_x = 1;  dir_y = 0;  } break;
                    case KEY_ESCAPE:
                        game_over = 1;
                        break;
                }
            }
            if (game_over) break;
            SLEEP_MS(10);
            wait -= 10;
        }

        if (!game_over) update_game();
    }

    term_show_cursor();
    CLEAR_SCREEN();
    term_set_color(COLOR_RED, COLOR_BLACK);
    printf("\n  +==============================+\n");
    printf("  |         GAME OVER            |\n");
    printf("  +==============================+\n");
    term_reset_color();
    printf("\n  Final Score: %d\n", score);
    printf("  Snake Length: %d\n", snake_len);
    printf("\n  Press any key to continue...\n");
    key_flush();
    while (!key_available()) SLEEP_MS(50);
    key_read();
}
