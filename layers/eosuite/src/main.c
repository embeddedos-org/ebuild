// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/* main.c - EOSUITE entry point and main menu */
#include "eosuite.h"
#include "platform.h"

void run_calculator(void);
void run_timer(void);
void run_snake(void);
void run_notepad(void);
void run_hex_viewer(void);
void run_ssh_client(void);
void run_serial_terminal(void);
void run_session_manager(void);
void run_eguard(void);
void run_eweb(void);
void run_ezip(void);
void run_ecleaner(void);
void run_evpn(void);
void run_echat(void);
void run_epaint(void);
void run_eplay(void);
void run_ebuffer(void);
void run_econverter(void);
void run_epdf(void);

static void print_banner(void) {
    term_set_color(COLOR_CYAN, COLOR_BLACK);
    printf("\n");
    printf("  +========================================+\n");
    printf("  |          EOSUITE v%s            |\n", EOSUITE_VERSION);
    printf("  |   Super Lightweight Terminal Suite     |\n");
    printf("  +========================================+\n");
    term_reset_color();
}

static void print_menu(void) {
    printf("\n");
    term_set_color(COLOR_GREEN, COLOR_BLACK);
    printf("  -- Connectivity -------------------------\n");
    term_reset_color();
    printf("    1. SSH Terminal\n");
    printf("    2. Serial / UART Terminal\n");
    printf("    3. Session Manager\n");

    term_set_color(COLOR_YELLOW, COLOR_BLACK);
    printf("\n  -- Tools --------------------------------\n");
    term_reset_color();
    printf("    4. Calculator\n");
    printf("    5. Timer / Stopwatch\n");
    printf("    6. eNotepad (Text Editor)\n");
    printf("    7. Hex Viewer\n");
    printf("    8. eGuard  (Keep Awake)\n");
    printf("    9. eWeb    (Browser)\n");
    printf("   10. eZip    (Archive 7z/tar/zip)\n");
    printf("   11. eCleaner(System Cleanup)\n");
    printf("   12. eVPN    (VPN Manager)\n");
    printf("   13. eChat   (IP Chat)\n");
    printf("   14. ePaint  (Drawing)\n");
    printf("   15. ePlay   (Media Player)\n");
    printf("   16. eBuffer (Clipboard)\n");
    printf("   17. eConverter (File Convert)\n");
    printf("   18. ePdf    (PDF Reader/Sign)\n");

    term_set_color(COLOR_MAGENTA, COLOR_BLACK);
    printf("\n  -- Fun ----------------------------------\n");
    term_reset_color();
    printf("   19. Snake Game\n");

    term_set_color(COLOR_RED, COLOR_BLACK);
    printf("\n    0. Exit\n");
    term_reset_color();

    printf("\n  Select option: ");
    fflush(stdout);
}

int main(int argc, char *argv[]) {
    (void)argc;
    (void)argv;

    platform_init();

    char input[MAX_INPUT_LEN];
    int running = 1;

    while (running) {
        CLEAR_SCREEN();
        print_banner();
        print_menu();

        if (fgets(input, sizeof(input), stdin) == NULL) break;

        int choice = atoi(input);
        CLEAR_SCREEN();

        switch (choice) {
            case 1:  run_ssh_client();       break;
            case 2:  run_serial_terminal();  break;
            case 3:  run_session_manager();  break;
            case 4:  run_calculator();       break;
            case 5:  run_timer();            break;
            case 6:  run_notepad();          break;
            case 7:  run_hex_viewer();       break;
            case 8:  run_eguard();           break;
            case 9:  run_eweb();             break;
            case 10: run_ezip();             break;
            case 11: run_ecleaner();         break;
            case 12: run_evpn();             break;
            case 13: run_echat();            break;
            case 14: run_epaint();           break;
            case 15: run_eplay();            break;
            case 16: run_ebuffer();          break;
            case 17: run_econverter();       break;
            case 18: run_epdf();             break;
            case 19: run_snake();            break;
            case 0:  running = 0;            break;
            default:
                term_set_color(COLOR_RED, COLOR_BLACK);
                printf("  Invalid option. Press Enter to continue...\n");
                term_reset_color();
                fgets(input, sizeof(input), stdin);
                break;
        }
    }

    CLEAR_SCREEN();
    term_set_color(COLOR_CYAN, COLOR_BLACK);
    printf("  EOSUITE - Goodbye!\n\n");
    term_reset_color();

    platform_cleanup();
    return 0;
}
