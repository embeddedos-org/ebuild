// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/* echat.c - eChat: Lightweight IP-based chat over TCP sockets */
#include "eosuite.h"
#include "platform.h"

#ifdef _WIN32

#if defined(__TINYC__) || defined(NO_WINSOCK)

/* TCC stub - compile with GCC/MSVC for full chat support */
void run_echat(void) {
    char input[MAX_INPUT_LEN];
    CLEAR_SCREEN();
    term_set_color(COLOR_CYAN, COLOR_BLACK);
    printf("  +========================================+\n");
    printf("  |      eChat - IP Chat Application       |\n");
    printf("  +========================================+\n");
    term_reset_color();
    printf("\n  eChat requires WinSock2 headers.\n");
    printf("  Compile with GCC (MinGW) or MSVC for full support.\n\n");
    printf("  Build command (MinGW):\n");
    term_set_color(COLOR_GREEN, COLOR_BLACK);
    printf("  gcc -Os -o EOSUITE.exe src/*.c -Iinclude -lws2_32\n\n");
    term_reset_color();
    printf("  Press Enter to return...\n");
    fgets(input, sizeof(input), stdin);
}

#else /* Full WinSock2 implementation */

typedef SOCKET sock_t;
#define SOCK_INVALID INVALID_SOCKET
#define sock_close closesocket
static int wsa_init_done = 0;
static void wsa_init(void) {
    if (!wsa_init_done) { WSADATA w; WSAStartup(MAKEWORD(2,2), &w); wsa_init_done = 1; }
}

#define CHAT_PORT    9876
#define CHAT_BUFSIZE 1024

static void trim_chat_nl(char *s) {
    size_t len = strlen(s);
    if (len > 0 && s[len-1] == '\n') s[len-1] = '\0';
}

static void set_nonblocking(sock_t s) {
    u_long mode = 1;
    ioctlsocket(s, FIONBIO, &mode);
}

static void chat_server(int port) {
    char input[MAX_INPUT_LEN];
    wsa_init();
    sock_t server = socket(AF_INET, SOCK_STREAM, 0);
    if (server == SOCK_INVALID) { printf("  Error creating socket\n"); printf("  Press Enter...\n"); fgets(input,sizeof(input),stdin); return; }
    int opt = 1;
    setsockopt(server, SOL_SOCKET, SO_REUSEADDR, (const char*)&opt, sizeof(opt));
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET; addr.sin_addr.s_addr = INADDR_ANY; addr.sin_port = htons(port);
    if (bind(server, (struct sockaddr*)&addr, sizeof(addr)) < 0) { printf("  Cannot bind port %d\n",port); sock_close(server); printf("  Press Enter...\n"); fgets(input,sizeof(input),stdin); return; }
    listen(server, 1);
    term_set_color(COLOR_GREEN,COLOR_BLACK); printf("\n  Listening on port %d...\n",port); term_reset_color(); fflush(stdout);
    struct sockaddr_in ca; int cl=sizeof(ca);
    sock_t client = accept(server,(struct sockaddr*)&ca,&cl);
    if (client == SOCK_INVALID) { sock_close(server); return; }
    term_set_color(COLOR_GREEN,COLOR_BLACK); printf("  Connected from: %s\n\n",inet_ntoa(ca.sin_addr)); term_reset_color();
    printf("  Type messages. 'quit' to exit.\n\n");
    set_nonblocking(client);
    char buf[CHAT_BUFSIZE], msg[CHAT_BUFSIZE];
    while (1) {
        int n = recv(client, buf, CHAT_BUFSIZE-1, 0);
        if (n > 0) { buf[n]='\0'; term_set_color(COLOR_CYAN,COLOR_BLACK); printf("  [peer] %s\n",buf); term_reset_color(); fflush(stdout); }
        else if (n == 0) { printf("  Peer disconnected.\n"); break; }
        if (_kbhit()) {
            printf("  [you] "); fflush(stdout);
            if (!fgets(msg,sizeof(msg),stdin)) break;
            trim_chat_nl(msg);
            if (strcmp(msg,"quit")==0) { send(client,"** left **",10,0); break; }
            send(client, msg, (int)strlen(msg), 0);
        }
        SLEEP_MS(50);
    }
    sock_close(client); sock_close(server);
    printf("\n  Chat ended. Press Enter...\n"); fgets(input,sizeof(input),stdin);
}

static void chat_client(const char *host, int port) {
    char input[MAX_INPUT_LEN];
    wsa_init();
    sock_t s = socket(AF_INET, SOCK_STREAM, 0);
    if (s == SOCK_INVALID) { printf("  Error creating socket\n"); printf("  Press Enter...\n"); fgets(input,sizeof(input),stdin); return; }
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET; addr.sin_port = htons(port);
    if (inet_pton(AF_INET, host, &addr.sin_addr) <= 0) {
        struct hostent *he = gethostbyname(host);
        if (!he) { printf("  Cannot resolve '%s'\n",host); sock_close(s); printf("  Press Enter...\n"); fgets(input,sizeof(input),stdin); return; }
        memcpy(&addr.sin_addr, he->h_addr_list[0], he->h_length);
    }
    term_set_color(COLOR_YELLOW,COLOR_BLACK); printf("\n  Connecting to %s:%d...\n",host,port); term_reset_color(); fflush(stdout);
    if (connect(s,(struct sockaddr*)&addr,sizeof(addr))<0) { printf("  Connection failed\n"); sock_close(s); printf("  Press Enter...\n"); fgets(input,sizeof(input),stdin); return; }
    term_set_color(COLOR_GREEN,COLOR_BLACK); printf("  Connected!\n\n"); term_reset_color();
    printf("  Type messages. 'quit' to exit.\n\n");
    set_nonblocking(s);
    char buf[CHAT_BUFSIZE], msg[CHAT_BUFSIZE];
    while (1) {
        int n = recv(s, buf, CHAT_BUFSIZE-1, 0);
        if (n > 0) { buf[n]='\0'; term_set_color(COLOR_CYAN,COLOR_BLACK); printf("  [peer] %s\n",buf); term_reset_color(); fflush(stdout); }
        else if (n == 0) { printf("  Disconnected.\n"); break; }
        if (_kbhit()) {
            printf("  [you] "); fflush(stdout);
            if (!fgets(msg,sizeof(msg),stdin)) break;
            trim_chat_nl(msg);
            if (strcmp(msg,"quit")==0) break;
            send(s, msg, (int)strlen(msg), 0);
        }
        SLEEP_MS(50);
    }
    sock_close(s);
    printf("\n  Chat ended. Press Enter...\n"); fgets(input,sizeof(input),stdin);
}

void run_echat(void) {
    char input[MAX_INPUT_LEN];
    while (1) {
        CLEAR_SCREEN();
        term_set_color(COLOR_CYAN,COLOR_BLACK);
        printf("  +========================================+\n");
        printf("  |      eChat - IP Chat Application       |\n");
        printf("  +========================================+\n");
        term_reset_color();
        printf("\n  Direct peer-to-peer TCP chat.\n\n");
        printf("   1. Host a chat (listen)\n");
        printf("   2. Connect to a chat (join)\n");
        printf("   0. Back to Menu\n");
        printf("\n  Select: ");
        fflush(stdout);
        if (fgets(input,sizeof(input),stdin)==NULL) return;
        switch(atoi(input)) {
        case 1: { int port=9876; printf("  Port [9876]: "); fflush(stdout); if(fgets(input,sizeof(input),stdin)&&strlen(input)>1){int p=atoi(input);if(p>0&&p<65536)port=p;} CLEAR_SCREEN(); chat_server(port); break; }
        case 2: { char host[128]; int port=9876; printf("  Host: "); fflush(stdout); if(!fgets(host,sizeof(host),stdin)) continue; trim_chat_nl(host); if(!strlen(host)) continue; printf("  Port [9876]: "); fflush(stdout); if(fgets(input,sizeof(input),stdin)&&strlen(input)>1){int p=atoi(input);if(p>0&&p<65536)port=p;} CLEAR_SCREEN(); chat_client(host,port); break; }
        case 0: return;
        }
    }
}

#endif /* __TINYC__ */

#else /* Linux / macOS */

#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <fcntl.h>
#include <errno.h>
typedef int sock_t;
#define SOCK_INVALID (-1)
#define sock_close close

#define CHAT_PORT    9876
#define CHAT_BUFSIZE 1024

static void trim_chat_nl(char *s) { size_t l=strlen(s); if(l>0&&s[l-1]=='\n') s[l-1]='\0'; }

static void chat_server(int port) {
    char input[MAX_INPUT_LEN];
    sock_t server = socket(AF_INET, SOCK_STREAM, 0);
    if (server < 0) { printf("  Error\n"); printf("  Press Enter...\n"); fgets(input,sizeof(input),stdin); return; }
    int opt=1; setsockopt(server,SOL_SOCKET,SO_REUSEADDR,&opt,sizeof(opt));
    struct sockaddr_in addr={0}; addr.sin_family=AF_INET; addr.sin_addr.s_addr=INADDR_ANY; addr.sin_port=htons(port);
    if (bind(server,(struct sockaddr*)&addr,sizeof(addr))<0) { printf("  Cannot bind %d\n",port); close(server); printf("  Press Enter...\n"); fgets(input,sizeof(input),stdin); return; }
    listen(server,1);
    term_set_color(COLOR_GREEN,COLOR_BLACK); printf("\n  Listening on port %d...\n",port); term_reset_color(); fflush(stdout);
    struct sockaddr_in ca; socklen_t cl=sizeof(ca);
    sock_t client=accept(server,(struct sockaddr*)&ca,&cl);
    if (client<0) { close(server); return; }
    printf("  Connected from: %s\n\n",inet_ntoa(ca.sin_addr));
    int flags=fcntl(client,F_GETFL,0); fcntl(client,F_SETFL,flags|O_NONBLOCK);
    char buf[CHAT_BUFSIZE],msg[CHAT_BUFSIZE];
    while(1) {
        int n=read(client,buf,CHAT_BUFSIZE-1);
        if(n>0){buf[n]='\0';term_set_color(COLOR_CYAN,COLOR_BLACK);printf("  [peer] %s\n",buf);term_reset_color();fflush(stdout);}
        else if(n==0){printf("  Disconnected.\n");break;}
        if(key_available()){printf("  [you] ");fflush(stdout);if(!fgets(msg,sizeof(msg),stdin))break;trim_chat_nl(msg);if(strcmp(msg,"quit")==0){send(client,"** left **",10,0);break;}send(client,msg,(int)strlen(msg),0);}
        SLEEP_MS(50);
    }
    close(client);close(server);
    printf("\n  Chat ended. Press Enter...\n"); fgets(input,sizeof(input),stdin);
}

static void chat_client(const char *host, int port) {
    char input[MAX_INPUT_LEN];
    sock_t s=socket(AF_INET,SOCK_STREAM,0);
    if(s<0){printf("  Error\n");printf("  Press Enter...\n");fgets(input,sizeof(input),stdin);return;}
    struct sockaddr_in addr={0};addr.sin_family=AF_INET;addr.sin_port=htons(port);
    if(inet_pton(AF_INET,host,&addr.sin_addr)<=0){struct hostent*he=gethostbyname(host);if(!he){printf("  Cannot resolve '%s'\n",host);close(s);printf("  Press Enter...\n");fgets(input,sizeof(input),stdin);return;}memcpy(&addr.sin_addr,he->h_addr_list[0],he->h_length);}
    printf("  Connecting to %s:%d...\n",host,port);fflush(stdout);
    if(connect(s,(struct sockaddr*)&addr,sizeof(addr))<0){printf("  Failed\n");close(s);printf("  Press Enter...\n");fgets(input,sizeof(input),stdin);return;}
    printf("  Connected!\n\n");
    int flags=fcntl(s,F_GETFL,0);fcntl(s,F_SETFL,flags|O_NONBLOCK);
    char buf[CHAT_BUFSIZE],msg[CHAT_BUFSIZE];
    while(1){int n=read(s,buf,CHAT_BUFSIZE-1);if(n>0){buf[n]='\0';term_set_color(COLOR_CYAN,COLOR_BLACK);printf("  [peer] %s\n",buf);term_reset_color();fflush(stdout);}else if(n==0){printf("  Disconnected.\n");break;}if(key_available()){printf("  [you] ");fflush(stdout);if(!fgets(msg,sizeof(msg),stdin))break;trim_chat_nl(msg);if(strcmp(msg,"quit")==0)break;send(s,msg,(int)strlen(msg),0);}SLEEP_MS(50);}
    close(s);printf("\n  Chat ended. Press Enter...\n");fgets(input,sizeof(input),stdin);
}

void run_echat(void) {
    char input[MAX_INPUT_LEN];
    while(1){CLEAR_SCREEN();term_set_color(COLOR_CYAN,COLOR_BLACK);printf("  +========================================+\n");printf("  |      eChat - IP Chat Application       |\n");printf("  +========================================+\n");term_reset_color();printf("\n  Peer-to-peer TCP chat.\n\n");printf("   1. Host\n   2. Connect\n   0. Back\n\n  Select: ");fflush(stdout);
    if(!fgets(input,sizeof(input),stdin))return;
    switch(atoi(input)){case 1:{int port=9876;printf("  Port [9876]: ");fflush(stdout);if(fgets(input,sizeof(input),stdin)&&strlen(input)>1){int p=atoi(input);if(p>0&&p<65536)port=p;}CLEAR_SCREEN();chat_server(port);break;}case 2:{char host[128];int port=9876;printf("  Host: ");fflush(stdout);if(!fgets(host,sizeof(host),stdin))continue;trim_chat_nl(host);if(!strlen(host))continue;printf("  Port [9876]: ");fflush(stdout);if(fgets(input,sizeof(input),stdin)&&strlen(input)>1){int p=atoi(input);if(p>0&&p<65536)port=p;}CLEAR_SCREEN();chat_client(host,port);break;}case 0:return;}}
}

#endif /* _WIN32 */
