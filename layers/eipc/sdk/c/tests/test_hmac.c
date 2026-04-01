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

static void test_hmac_sign_verify(void) {
    const char *name = "hmac_sign_verify";
    TEST(name);

    const uint8_t key[] = "my-secret-key-for-testing-12345";
    const uint8_t data[] = "hello eipc world";
    uint8_t mac[EIPC_HMAC_SIZE];

    eipc_status_t rc = eipc_hmac_sign(key, sizeof(key) - 1, data, sizeof(data) - 1, mac);
    if (rc != EIPC_OK) {
        FAIL(name, "sign failed");
        return;
    }

    int valid = eipc_hmac_verify(key, sizeof(key) - 1, data, sizeof(data) - 1, mac);
    if (!valid) {
        FAIL(name, "verify returned false for valid signature");
        return;
    }

    PASS(name);
}

static void test_hmac_tampered_data(void) {
    const char *name = "hmac_tampered_data";
    TEST(name);

    const uint8_t key[] = "my-secret-key-for-testing-12345";
    uint8_t data[] = "hello eipc world";
    uint8_t mac[EIPC_HMAC_SIZE];

    eipc_status_t rc = eipc_hmac_sign(key, sizeof(key) - 1, data, sizeof(data) - 1, mac);
    if (rc != EIPC_OK) {
        FAIL(name, "sign failed");
        return;
    }

    data[0] ^= 0x01;

    int valid = eipc_hmac_verify(key, sizeof(key) - 1, data, sizeof(data) - 1, mac);
    if (valid) {
        FAIL(name, "verify returned true for tampered data");
        return;
    }

    PASS(name);
}

static void test_hmac_wrong_key(void) {
    const char *name = "hmac_wrong_key";
    TEST(name);

    const uint8_t key_a[] = "key-alpha-secret-1234567890abc";
    const uint8_t key_b[] = "key-bravo-secret-0987654321xyz";
    const uint8_t data[] = "message to authenticate";
    uint8_t mac[EIPC_HMAC_SIZE];

    eipc_status_t rc = eipc_hmac_sign(key_a, sizeof(key_a) - 1, data, sizeof(data) - 1, mac);
    if (rc != EIPC_OK) {
        FAIL(name, "sign failed");
        return;
    }

    int valid = eipc_hmac_verify(key_b, sizeof(key_b) - 1, data, sizeof(data) - 1, mac);
    if (valid) {
        FAIL(name, "verify returned true with wrong key");
        return;
    }

    PASS(name);
}

static void test_hmac_known_vector(void) {
    const char *name = "hmac_known_vector";
    TEST(name);

    /* RFC 4231 Test Case 2:
     *   Key  = "Jefe"
     *   Data = "what do ya want for nothing?"
     *   HMAC-SHA256 = 5bdcc146bf60754e6a042426089575c7
     *                 5a003f089d2739839dec58b964ec3843
     */
    const uint8_t key[] = "Jefe";
    const uint8_t data[] = "what do ya want for nothing?";
    const uint8_t expected[32] = {
        0x5b, 0xdc, 0xc1, 0x46, 0xbf, 0x60, 0x75, 0x4e,
        0x6a, 0x04, 0x24, 0x26, 0x08, 0x95, 0x75, 0xc7,
        0x5a, 0x00, 0x3f, 0x08, 0x9d, 0x27, 0x39, 0x83,
        0x9d, 0xec, 0x58, 0xb9, 0x64, 0xec, 0x38, 0x43
    };
    uint8_t mac[EIPC_HMAC_SIZE];

    eipc_status_t rc = eipc_hmac_sign(key, 4, data, 28, mac);
    if (rc != EIPC_OK) {
        FAIL(name, "sign failed");
        return;
    }

    if (memcmp(mac, expected, 32) != 0) {
        printf("    computed: ");
        for (int i = 0; i < 32; i++) printf("%02x", mac[i]);
        printf("\n    expected: ");
        for (int i = 0; i < 32; i++) printf("%02x", expected[i]);
        printf("\n");
        FAIL(name, "MAC does not match RFC 4231 test vector");
        return;
    }

    PASS(name);
}

int main(void) {
    printf("=== EIPC HMAC Tests ===\n");

    test_hmac_sign_verify();
    test_hmac_tampered_data();
    test_hmac_wrong_key();
    test_hmac_known_vector();

    printf("\nResults: %d passed, %d failed\n", g_pass, g_fail);
    return g_fail > 0 ? 1 : 0;
}
