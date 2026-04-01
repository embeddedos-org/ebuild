// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "ebot_client.h"
#include <stdio.h>
#include <string.h>

#define ASSERT(c,m) do{if(!(c)){printf("  FAIL: %s\n",m);return 1;}}while(0)
#define RUN(fn) do{printf("  %s ... ",#fn);if(fn()==0){printf("PASS\n");p++;}else f++;t++;}while(0)

static int test_init_defaults(void) {
    ebot_client_t c; ebot_client_init(&c, NULL, 0);
    ASSERT(strcmp(c.host,"192.168.1.100")==0, "default host");
    ASSERT(c.port==8420, "default port");
    ASSERT(c.timeout_ms==30000, "default timeout");
    return 0;
}
static int test_init_custom(void) {
    ebot_client_t c; ebot_client_init(&c, "10.0.0.1", 9090);
    ASSERT(strcmp(c.host,"10.0.0.1")==0, "custom host");
    ASSERT(c.port==9090, "custom port");
    return 0;
}
static int test_init_null(void) {
    ASSERT(ebot_client_init(NULL,NULL,0)==-1, "null returns -1");
    return 0;
}
static int test_chat_no_server(void) {
    ebot_client_t c; ebot_client_init(&c,"127.0.0.1",19999);
    char r[256]; ASSERT(ebot_client_chat(&c,"hi",r,sizeof(r))==-1, "no server");
    return 0;
}
static int test_status_no_server(void) {
    ebot_client_t c; ebot_client_init(&c,"127.0.0.1",19999);
    char r[256]; ASSERT(ebot_client_status(&c,r,sizeof(r))==-1, "no server");
    return 0;
}
static int test_tools_no_server(void) {
    ebot_client_t c; ebot_client_init(&c,"127.0.0.1",19999);
    char r[256]; ASSERT(ebot_client_tools(&c,r,sizeof(r))==-1, "no server");
    return 0;
}
static int test_models_no_server(void) {
    ebot_client_t c; ebot_client_init(&c,"127.0.0.1",19999);
    char r[256]; ASSERT(ebot_client_models(&c,r,sizeof(r))==-1, "no server");
    return 0;
}
static int test_reset_no_server(void) {
    ebot_client_t c; ebot_client_init(&c,"127.0.0.1",19999);
    char r[256]; ASSERT(ebot_client_reset(&c,r,sizeof(r))==-1, "no server");
    return 0;
}
static int test_complete_no_server(void) {
    ebot_client_t c; ebot_client_init(&c,"127.0.0.1",19999);
    char r[256]; ASSERT(ebot_client_complete(&c,"test",r,sizeof(r))==-1, "no server");
    return 0;
}
static int test_multi_clients(void) {
    ebot_client_t a,b;
    ebot_client_init(&a,"10.0.0.1",8420); ebot_client_init(&b,"10.0.0.2",8421);
    ASSERT(strcmp(a.host,"10.0.0.1")==0,"a host"); ASSERT(strcmp(b.host,"10.0.0.2")==0,"b host");
    ASSERT(a.port==8420,"a port"); ASSERT(b.port==8421,"b port");
    return 0;
}
static int test_version(void) {
    ASSERT(strcmp(EBOT_CLIENT_VERSION,"0.1.0")==0, "version");
    ASSERT(EBOT_DEFAULT_PORT==8420, "port const");
    ASSERT(strcmp(EBOT_DEFAULT_HOST,"192.168.1.100")==0, "host const");
    return 0;
}
int main(void) {
    int p=0,f=0,t=0;
    printf("=== EoSuite Ebot Client Tests ===\n\n");
    RUN(test_init_defaults); RUN(test_init_custom); RUN(test_init_null);
    RUN(test_chat_no_server); RUN(test_status_no_server); RUN(test_tools_no_server);
    RUN(test_models_no_server); RUN(test_reset_no_server); RUN(test_complete_no_server);
    RUN(test_multi_clients); RUN(test_version);
    printf("\n%d/%d passed, %d failed\n",p,t,f);
    return f>0?1:0;
}