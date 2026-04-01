// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eipc.h"
#include <stdio.h>
#include <string.h>
#include <stdint.h>

static int g_pass = 0;
static int g_fail = 0;

#define TEST(name) printf("  TEST  %s ...\n", name)
#define PASS(name) do { printf("  PASS  %s\n", name); g_pass++; } while(0)
#define FAIL(name, msg) do { printf("  FAIL  %s: %s\n", name, msg); g_fail++; } while(0)

static void test_frame_encode_decode(void) {
    const char *name = "frame_encode_decode";
    TEST(name);

    eipc_frame_t frame;
    memset(&frame, 0, sizeof(frame));
    frame.version = 1;
    frame.msg_type = 'i';
    frame.flags = 0;
    frame.header = (uint8_t *)"test-hdr";
    frame.header_len = 8;
    frame.payload = (uint8_t *)"test-payload";
    frame.payload_len = 12;

    uint8_t buf[1024];
    size_t encoded_len = 0;
    eipc_status_t rc = eipc_frame_encode(&frame, buf, sizeof(buf), &encoded_len);
    if (rc != EIPC_OK) {
        FAIL(name, "encode failed");
        return;
    }

    eipc_frame_t decoded;
    memset(&decoded, 0, sizeof(decoded));
    rc = eipc_frame_decode(buf, encoded_len, &decoded);
    if (rc != EIPC_OK) {
        FAIL(name, "decode failed");
        return;
    }

    if (decoded.version != 1) {
        FAIL(name, "version mismatch");
        return;
    }
    if (decoded.msg_type != 'i') {
        FAIL(name, "msg_type mismatch");
        return;
    }
    if (decoded.flags != 0) {
        FAIL(name, "flags mismatch");
        return;
    }
    if (decoded.header_len != 8 || memcmp(decoded.header, "test-hdr", 8) != 0) {
        FAIL(name, "header mismatch");
        return;
    }
    if (decoded.payload_len != 12 || memcmp(decoded.payload, "test-payload", 12) != 0) {
        FAIL(name, "payload mismatch");
        return;
    }

    PASS(name);
}

static void test_frame_magic_validation(void) {
    const char *name = "frame_magic_validation";
    TEST(name);

    eipc_frame_t frame;
    memset(&frame, 0, sizeof(frame));
    frame.version = 1;
    frame.msg_type = 'i';
    frame.flags = 0;
    frame.header = (uint8_t *)"hdr";
    frame.header_len = 3;
    frame.payload = (uint8_t *)"pay";
    frame.payload_len = 3;

    uint8_t buf[1024];
    size_t encoded_len = 0;
    eipc_status_t rc = eipc_frame_encode(&frame, buf, sizeof(buf), &encoded_len);
    if (rc != EIPC_OK) {
        FAIL(name, "encode failed");
        return;
    }

    buf[0] = 0xFF;
    buf[1] = 0xFF;
    buf[2] = 0xFF;
    buf[3] = 0xFF;

    eipc_frame_t decoded;
    memset(&decoded, 0, sizeof(decoded));
    rc = eipc_frame_decode(buf, encoded_len, &decoded);
    if (rc != EIPC_ERR_PROTOCOL) {
        FAIL(name, "expected EIPC_ERR_PROTOCOL for corrupted magic");
        return;
    }

    PASS(name);
}

static void test_frame_signable_bytes(void) {
    const char *name = "frame_signable_bytes";
    TEST(name);

    eipc_frame_t frame;
    memset(&frame, 0, sizeof(frame));
    frame.version = 1;
    frame.msg_type = 'a';
    frame.flags = 0;
    frame.header = (uint8_t *)"my-header";
    frame.header_len = 9;
    frame.payload = (uint8_t *)"my-payload-data";
    frame.payload_len = 15;

    uint8_t sbuf[1024];
    size_t slen = 0;
    eipc_status_t rc = eipc_frame_signable_bytes(&frame, sbuf, sizeof(sbuf), &slen);
    if (rc != EIPC_OK) {
        FAIL(name, "signable_bytes failed");
        return;
    }

    size_t expected = EIPC_PREAMBLE_SIZE + frame.header_len + frame.payload_len;
    if (slen != expected) {
        char msg[128];
        snprintf(msg, sizeof(msg), "length mismatch: got %zu, expected %zu", slen, expected);
        FAIL(name, msg);
        return;
    }

    PASS(name);
}

static void test_frame_with_hmac_flag(void) {
    const char *name = "frame_with_hmac_flag";
    TEST(name);

    eipc_frame_t frame;
    memset(&frame, 0, sizeof(frame));
    frame.version = 1;
    frame.msg_type = 'i';
    frame.flags = EIPC_FLAG_HMAC;
    frame.header = (uint8_t *)"hdr";
    frame.header_len = 3;
    frame.payload = (uint8_t *)"pay";
    frame.payload_len = 3;
    memset(frame.mac, 0xAA, EIPC_HMAC_SIZE);

    uint8_t buf[1024];
    size_t encoded_len = 0;
    eipc_status_t rc = eipc_frame_encode(&frame, buf, sizeof(buf), &encoded_len);
    if (rc != EIPC_OK) {
        FAIL(name, "encode failed");
        return;
    }

    eipc_frame_t decoded;
    memset(&decoded, 0, sizeof(decoded));
    rc = eipc_frame_decode(buf, encoded_len, &decoded);
    if (rc != EIPC_OK) {
        FAIL(name, "decode failed");
        return;
    }

    if (!(decoded.flags & EIPC_FLAG_HMAC)) {
        FAIL(name, "HMAC flag not preserved");
        return;
    }

    uint8_t expected_mac[EIPC_HMAC_SIZE];
    memset(expected_mac, 0xAA, EIPC_HMAC_SIZE);
    if (memcmp(decoded.mac, expected_mac, EIPC_HMAC_SIZE) != 0) {
        FAIL(name, "MAC bytes not preserved");
        return;
    }

    PASS(name);
}

int main(void) {
    printf("=== EIPC Frame Tests ===\n");

    test_frame_encode_decode();
    test_frame_magic_validation();
    test_frame_signable_bytes();
    test_frame_with_hmac_flag();

    printf("\nResults: %d passed, %d failed\n", g_pass, g_fail);
    return g_fail > 0 ? 1 : 0;
}
