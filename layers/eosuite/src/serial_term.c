// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eosuite.h"
#include "platform.h"

#ifdef _WIN32

static void list_com_ports(void) {
    printf("\n  Available COM ports:\n");
    int found = 0;
    char port_name[32];

    for (int i = 1; i <= 256; i++) {
        snprintf(port_name, sizeof(port_name), "\\\\.\\COM%d", i);
        HANDLE h = CreateFileA(port_name, GENERIC_READ | GENERIC_WRITE,
                               0, NULL, OPEN_EXISTING, 0, NULL);
        if (h != INVALID_HANDLE_VALUE) {
            printf("    COM%d\n", i);
            CloseHandle(h);
            found++;
        }
    }

    if (!found) {
        term_set_color(COLOR_YELLOW, COLOR_BLACK);
        printf("    No COM ports found.\n");
        term_reset_color();
    }
}

static void connect_serial(void) {
    char port_name[64];
    char baud_str[32];
    char parity_str[16];
    char input[MAX_INPUT_LEN];

    printf("\n  Port (e.g. COM3): ");
    fflush(stdout);
    if (!fgets(input, sizeof(input), stdin)) return;
    input[strcspn(input, "\r\n")] = '\0';
    if (strlen(input) == 0) return;
    snprintf(port_name, sizeof(port_name), "\\\\.\\%s", input);

    printf("  Baud rate (default 9600): ");
    fflush(stdout);
    if (fgets(baud_str, sizeof(baud_str), stdin))
        baud_str[strcspn(baud_str, "\r\n")] = '\0';
    int baud = atoi(baud_str);
    if (baud <= 0) baud = 9600;

    printf("  Parity (N/E/O, default N): ");
    fflush(stdout);
    if (fgets(parity_str, sizeof(parity_str), stdin))
        parity_str[strcspn(parity_str, "\r\n")] = '\0';

    HANDLE hSerial = CreateFileA(port_name, GENERIC_READ | GENERIC_WRITE,
                                  0, NULL, OPEN_EXISTING, 0, NULL);
    if (hSerial == INVALID_HANDLE_VALUE) {
        term_set_color(COLOR_RED, COLOR_BLACK);
        printf("  Error: cannot open %s\n", port_name);
        term_reset_color();
        SLEEP_MS(2000);
        return;
    }

    DCB dcb = {0};
    dcb.DCBlength = sizeof(DCB);
    GetCommState(hSerial, &dcb);
    dcb.BaudRate = baud;
    dcb.ByteSize = 8;
    dcb.StopBits = ONESTOPBIT;
    if (parity_str[0] == 'E' || parity_str[0] == 'e')
        dcb.Parity = EVENPARITY;
    else if (parity_str[0] == 'O' || parity_str[0] == 'o')
        dcb.Parity = ODDPARITY;
    else
        dcb.Parity = NOPARITY;
    SetCommState(hSerial, &dcb);

    COMMTIMEOUTS timeouts = {0};
    timeouts.ReadIntervalTimeout = 1;
    timeouts.ReadTotalTimeoutConstant = 1;
    timeouts.ReadTotalTimeoutMultiplier = 0;
    SetCommTimeouts(hSerial, &timeouts);

    CLEAR_SCREEN();
    term_set_color(COLOR_GREEN, COLOR_BLACK);
    printf("  Connected to %s at %d baud. Ctrl+] to exit.\n\n", input, baud);
    term_reset_color();

    for (;;) {
        unsigned char rx_buf[256];
        DWORD bytes_read = 0;
        if (ReadFile(hSerial, rx_buf, sizeof(rx_buf), &bytes_read, NULL) && bytes_read > 0) {
            for (DWORD i = 0; i < bytes_read; i++)
                putchar(rx_buf[i]);
            fflush(stdout);
        }

        if (key_available()) {
            int k = key_read();
            if (k == 29) break; /* Ctrl+] = ASCII 29 */
            unsigned char tx = (unsigned char)k;
            DWORD written;
            WriteFile(hSerial, &tx, 1, &written, NULL);
        }

        SLEEP_MS(1);
    }

    CloseHandle(hSerial);
    printf("\n\n  Serial session ended. Press any key...\n");
    key_flush();
    while (!key_available()) SLEEP_MS(50);
    key_read();
}

#else /* Unix */

#include <dirent.h>
#include <fcntl.h>
#include <errno.h>

static void list_com_ports(void) {
    printf("\n  Available serial ports:\n");
    int found = 0;

    DIR *d = opendir("/dev");
    if (d) {
        struct dirent *entry;
        while ((entry = readdir(d)) != NULL) {
            if (strncmp(entry->d_name, "ttyUSB", 6) == 0 ||
                strncmp(entry->d_name, "ttyACM", 6) == 0 ||
                strncmp(entry->d_name, "ttyS", 4) == 0 ||
                strncmp(entry->d_name, "tty.usb", 7) == 0 ||
                strncmp(entry->d_name, "tty.usbserial", 13) == 0 ||
                strncmp(entry->d_name, "cu.", 3) == 0) {
                printf("    /dev/%s\n", entry->d_name);
                found++;
            }
        }
        closedir(d);
    }

    if (!found) {
        term_set_color(COLOR_YELLOW, COLOR_BLACK);
        printf("    No serial ports found.\n");
        term_reset_color();
    }
}

static speed_t baud_to_speed(int baud) {
    switch (baud) {
        case 300:    return B300;
        case 1200:   return B1200;
        case 2400:   return B2400;
        case 4800:   return B4800;
        case 9600:   return B9600;
        case 19200:  return B19200;
        case 38400:  return B38400;
        case 57600:  return B57600;
        case 115200: return B115200;
        case 230400: return B230400;
        default:     return B9600;
    }
}

static void connect_serial(void) {
    char device[MAX_PATH_LEN];
    char baud_str[32];
    char parity_str[16];
    char input[MAX_INPUT_LEN];

    printf("\n  Port (e.g. /dev/ttyUSB0): ");
    fflush(stdout);
    if (!fgets(device, sizeof(device), stdin)) return;
    device[strcspn(device, "\r\n")] = '\0';
    if (strlen(device) == 0) return;

    printf("  Baud rate (default 9600): ");
    fflush(stdout);
    if (fgets(baud_str, sizeof(baud_str), stdin))
        baud_str[strcspn(baud_str, "\r\n")] = '\0';
    int baud = atoi(baud_str);
    if (baud <= 0) baud = 9600;

    printf("  Parity (N/E/O, default N): ");
    fflush(stdout);
    if (fgets(parity_str, sizeof(parity_str), stdin))
        parity_str[strcspn(parity_str, "\r\n")] = '\0';

    int fd = open(device, O_RDWR | O_NOCTTY | O_NONBLOCK);
    if (fd < 0) {
        term_set_color(COLOR_RED, COLOR_BLACK);
        printf("  Error: cannot open %s: %s\n", device, strerror(errno));
        term_reset_color();
        SLEEP_MS(2000);
        return;
    }

    struct termios tty;
    memset(&tty, 0, sizeof(tty));
    tcgetattr(fd, &tty);

    speed_t speed = baud_to_speed(baud);
    cfsetospeed(&tty, speed);
    cfsetispeed(&tty, speed);

    tty.c_cflag &= ~PARENB;
    tty.c_cflag &= ~CSTOPB;
    tty.c_cflag &= ~CSIZE;
    tty.c_cflag |= CS8;
    tty.c_cflag |= (CLOCAL | CREAD);

    if (parity_str[0] == 'E' || parity_str[0] == 'e') {
        tty.c_cflag |= PARENB;
        tty.c_cflag &= ~PARODD;
    } else if (parity_str[0] == 'O' || parity_str[0] == 'o') {
        tty.c_cflag |= PARENB;
        tty.c_cflag |= PARODD;
    }

    tty.c_lflag = 0;
    tty.c_iflag = 0;
    tty.c_oflag = 0;
    tty.c_cc[VMIN] = 0;
    tty.c_cc[VTIME] = 0;

    tcsetattr(fd, TCSANOW, &tty);

    CLEAR_SCREEN();
    term_set_color(COLOR_GREEN, COLOR_BLACK);
    printf("  Connected to %s at %d baud. Ctrl+] to exit.\n\n", device, baud);
    term_reset_color();

    for (;;) {
        unsigned char rx_buf[256];
        int n = read(fd, rx_buf, sizeof(rx_buf));
        if (n > 0) {
            for (int i = 0; i < n; i++)
                putchar(rx_buf[i]);
            fflush(stdout);
        }

        if (key_available()) {
            int k = key_read();
            if (k == 29) break; /* Ctrl+] */
            unsigned char tx = (unsigned char)k;
            write(fd, &tx, 1);
        }

        SLEEP_MS(1);
    }

    close(fd);
    printf("\n\n  Serial session ended. Press any key...\n");
    key_flush();
    while (!key_available()) SLEEP_MS(50);
    key_read();
}

#endif /* _WIN32 */

void run_serial_terminal(void) {
    char input[MAX_INPUT_LEN];

    for (;;) {
        CLEAR_SCREEN();
        term_set_color(COLOR_CYAN, COLOR_BLACK);
        printf("\n  +==============================+\n");
        printf("  |      SERIAL TERMINAL         |\n");
        printf("  +==============================+\n");
        term_reset_color();
        printf("\n  1. List Ports\n");
        printf("  2. Connect\n");
        printf("  0. Back\n\n");
        printf("  Select: ");
        fflush(stdout);

        if (!fgets(input, sizeof(input), stdin)) break;
        input[strcspn(input, "\r\n")] = '\0';

        if (strcmp(input, "1") == 0) {
            list_com_ports();
            printf("\n  Press any key...\n");
            key_flush();
            while (!key_available()) SLEEP_MS(50);
            key_read();
        } else if (strcmp(input, "2") == 0) {
            connect_serial();
        } else if (strcmp(input, "0") == 0) {
            break;
        }
    }
}
