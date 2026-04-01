// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/* evpn.c - eVPN: Lightweight VPN connection manager */
#include "eosuite.h"
#include "platform.h"

static void trim_nl(char *s) {
    size_t len = strlen(s);
    if (len > 0 && s[len - 1] == '\n') s[len - 1] = '\0';
}

static void vpn_status(void) {
    char input[MAX_INPUT_LEN];

    term_set_color(COLOR_CYAN, COLOR_BLACK);
    printf("\n  VPN Status:\n");
    printf("  ----------------------------------------\n");
    term_reset_color();

#ifdef _WIN32
    system("powershell -NoProfile -Command \""
           "Get-VpnConnection -ErrorAction SilentlyContinue | "
           "Format-Table Name,ServerAddress,ConnectionStatus -AutoSize; "
           "if(-not $?){Write-Host '  No built-in VPN connections found.'}\"");

    printf("\n  Network adapters:\n");
    system("powershell -NoProfile -Command \""
           "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | "
           "Format-Table Name,InterfaceDescription,Status,LinkSpeed -AutoSize\"");
#else
    printf("  Active interfaces:\n");
    system("ip addr show 2>/dev/null | grep -E '^[0-9]+:|inet ' | head -20 || "
           "ifconfig 2>/dev/null | grep -E '^[a-z]|inet ' | head -20");

    printf("\n  VPN tunnels:\n");
    system("ip link show type tun 2>/dev/null || echo '  No TUN devices found'");
    system("ip link show type wireguard 2>/dev/null || true");

    if (system("command -v wg > /dev/null 2>&1") == 0) {
        printf("\n  WireGuard status:\n");
        system("sudo wg show 2>/dev/null || echo '  WireGuard: not active or no permissions'");
    }
#endif

    printf("\n  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

static void vpn_connect_openvpn(void) {
    char input[MAX_INPUT_LEN];
    char config[MAX_PATH_LEN];

    printf("\n  OpenVPN config file path (.ovpn): ");
    fflush(stdout);
    if (fgets(config, sizeof(config), stdin) == NULL) return;
    trim_nl(config);
    if (strlen(config) == 0) return;

    char cmd[MAX_PATH_LEN * 2];

#ifdef _WIN32
    printf("\n  Checking for OpenVPN...\n");
    snprintf(cmd, sizeof(cmd),
        "where openvpn >nul 2>nul && (openvpn --config \"%s\") || "
        "(echo   OpenVPN not found. Install from https://openvpn.net)", config);
#else
    snprintf(cmd, sizeof(cmd),
        "command -v openvpn > /dev/null 2>&1 && "
        "sudo openvpn --config '%s' || "
        "echo '  OpenVPN not found. Install: sudo apt install openvpn'", config);
#endif

    term_set_color(COLOR_YELLOW, COLOR_BLACK);
    printf("  Connecting via OpenVPN...\n");
    printf("  Press Ctrl+C to disconnect.\n\n");
    term_reset_color();

    system(cmd);

    printf("\n  VPN session ended. Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

static void vpn_connect_wireguard(void) {
    char input[MAX_INPUT_LEN];
    char iface[64];

    printf("\n  WireGuard interface name (e.g. wg0): ");
    fflush(stdout);
    if (fgets(iface, sizeof(iface), stdin) == NULL) return;
    trim_nl(iface);
    if (strlen(iface) == 0) strcpy(iface, "wg0");

    char cmd[MAX_PATH_LEN];

#ifdef _WIN32
    printf("\n  WireGuard on Windows: use the WireGuard GUI app.\n");
    printf("  Or install wireguard-tools for CLI.\n");
    snprintf(cmd, sizeof(cmd),
        "where wireguard >nul 2>nul && (wireguard /installtunnelservice \"%s\") || "
        "(echo   WireGuard not found.)", iface);
#else
    printf("\n  1. Bring UP interface\n");
    printf("  2. Bring DOWN interface\n");
    printf("  Select: ");
    fflush(stdout);
    if (fgets(input, sizeof(input), stdin) == NULL) return;

    if (atoi(input) == 1) {
        snprintf(cmd, sizeof(cmd), "sudo wg-quick up %s 2>/dev/null || "
                 "echo '  Failed. Check config at /etc/wireguard/%s.conf'", iface, iface);
    } else {
        snprintf(cmd, sizeof(cmd), "sudo wg-quick down %s 2>/dev/null || "
                 "echo '  Failed to bring down %s'", iface, iface);
    }
#endif

    term_set_color(COLOR_YELLOW, COLOR_BLACK);
    printf("  Executing...\n");
    term_reset_color();

    system(cmd);

    printf("\n  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

static void vpn_ssh_tunnel(void) {
    char input[MAX_INPUT_LEN];
    char host[128], user[64];
    int local_port, remote_port;

    printf("\n  SSH SOCKS Tunnel (lightweight VPN alternative)\n\n");

    printf("  SSH host: ");
    fflush(stdout);
    if (fgets(host, sizeof(host), stdin) == NULL) return;
    trim_nl(host);
    if (strlen(host) == 0) return;

    printf("  Username: ");
    fflush(stdout);
    if (fgets(user, sizeof(user), stdin) == NULL) return;
    trim_nl(user);

    printf("  Local SOCKS port [1080]: ");
    fflush(stdout);
    if (fgets(input, sizeof(input), stdin) == NULL) return;
    local_port = atoi(input);
    if (local_port <= 0) local_port = 1080;

    char cmd[MAX_PATH_LEN];
    snprintf(cmd, sizeof(cmd),
        "ssh -D %d -C -N %s@%s", local_port, user, host);

    term_set_color(COLOR_GREEN, COLOR_BLACK);
    printf("\n  Starting SOCKS proxy on localhost:%d\n", local_port);
    printf("  Configure browser proxy: SOCKS5 127.0.0.1:%d\n", local_port);
    term_reset_color();
    printf("  Command: %s\n", cmd);
    printf("  Press Ctrl+C to stop.\n\n");

    system(cmd);

    printf("\n  Tunnel closed. Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

static void vpn_test_connection(void) {
    char input[MAX_INPUT_LEN];

    term_set_color(COLOR_YELLOW, COLOR_BLACK);
    printf("\n  Testing connection...\n\n");
    term_reset_color();

    printf("  Public IP: ");
    fflush(stdout);
#ifdef _WIN32
    system("curl -s https://api.ipify.org 2>nul || echo unknown");
#else
    system("curl -s https://api.ipify.org 2>/dev/null || echo unknown");
#endif
    printf("\n\n");

    printf("  DNS resolution:\n");
#ifdef _WIN32
    system("nslookup google.com 2>nul | findstr /i \"Address\" || echo   DNS failed");
#else
    system("dig +short google.com 2>/dev/null | head -1 || "
           "nslookup google.com 2>/dev/null | grep Address | tail -1 || echo '  DNS failed'");
#endif

    printf("\n  Ping test:\n");
#ifdef _WIN32
    system("ping -n 3 8.8.8.8");
#else
    system("ping -c 3 8.8.8.8 2>/dev/null");
#endif

    printf("\n  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

void run_evpn(void) {
    char input[MAX_INPUT_LEN];

    while (1) {
        CLEAR_SCREEN();
        term_set_color(COLOR_CYAN, COLOR_BLACK);
        printf("  +========================================+\n");
        printf("  |       eVPN - VPN Connection Tool       |\n");
        printf("  +========================================+\n");
        term_reset_color();

        printf("\n  Supports: OpenVPN, WireGuard, SSH Tunnel\n\n");
        printf("   1. VPN / Network Status\n");
        printf("   2. Connect via OpenVPN\n");
        printf("   3. WireGuard (up/down)\n");
        printf("   4. SSH SOCKS Tunnel\n");
        printf("   5. Test Connection (IP/DNS/Ping)\n");
        printf("   0. Back to Menu\n");
        printf("\n  Select: ");
        fflush(stdout);

        if (fgets(input, sizeof(input), stdin) == NULL) return;

        CLEAR_SCREEN();
        term_set_color(COLOR_CYAN, COLOR_BLACK);
        printf("  eVPN\n");
        printf("  ----------------------------------------\n");
        term_reset_color();

        switch (atoi(input)) {
        case 1: vpn_status(); break;
        case 2: vpn_connect_openvpn(); break;
        case 3: vpn_connect_wireguard(); break;
        case 4: vpn_ssh_tunnel(); break;
        case 5: vpn_test_connection(); break;
        case 0: return;
        }
    }
}
