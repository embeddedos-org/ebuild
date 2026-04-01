// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file test_crypto.c
 * @brief Unit tests for SHA-256 and image verification
 */

#include "eos_crypto_boot.h"
#include "eos_types.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static int tests_run = 0;
static int tests_passed = 0;

#define TEST(name) \
    static void name(void); \
    static void run_##name(void) { \
        printf("  %-50s ", #name); \
        name(); \
        tests_passed++; \
        printf("[PASS]\n"); \
    } \
    static void name(void)

#define ASSERT(cond) do { \
    if (!(cond)) { \
        printf("[FAIL] %s:%d: %s\n", __FILE__, __LINE__, #cond); \
        exit(1); \
    } \
} while(0)

/* Known SHA-256 test vectors from NIST FIPS 180-4 */

TEST(test_sha256_empty)
{
    /* SHA-256("") = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 */
    uint8_t digest[EOS_SHA256_DIGEST_SIZE];
    int rc = eos_crypto_hash((const uint8_t *)"", 0, digest);
    ASSERT(rc == EOS_OK);

    uint8_t expected[] = {
        0xe3, 0xb0, 0xc4, 0x42, 0x98, 0xfc, 0x1c, 0x14,
        0x9a, 0xfb, 0xf4, 0xc8, 0x99, 0x6f, 0xb9, 0x24,
        0x27, 0xae, 0x41, 0xe4, 0x64, 0x9b, 0x93, 0x4c,
        0xa4, 0x95, 0x99, 0x1b, 0x78, 0x52, 0xb8, 0x55,
    };
    ASSERT(memcmp(digest, expected, EOS_SHA256_DIGEST_SIZE) == 0);
}

TEST(test_sha256_abc)
{
    /* SHA-256("abc") = ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad */
    uint8_t digest[EOS_SHA256_DIGEST_SIZE];
    int rc = eos_crypto_hash((const uint8_t *)"abc", 3, digest);
    ASSERT(rc == EOS_OK);

    uint8_t expected[] = {
        0xba, 0x78, 0x16, 0xbf, 0x8f, 0x01, 0xcf, 0xea,
        0x41, 0x41, 0x40, 0xde, 0x5d, 0xae, 0x22, 0x23,
        0xb0, 0x03, 0x61, 0xa3, 0x96, 0x17, 0x7a, 0x9c,
        0xb4, 0x10, 0xff, 0x61, 0xf2, 0x00, 0x15, 0xad,
    };
    ASSERT(memcmp(digest, expected, EOS_SHA256_DIGEST_SIZE) == 0);
}

TEST(test_sha256_long)
{
    /* SHA-256("abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq") */
    const char *msg = "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq";
    uint8_t digest[EOS_SHA256_DIGEST_SIZE];
    int rc = eos_crypto_hash((const uint8_t *)msg, strlen(msg), digest);
    ASSERT(rc == EOS_OK);

    uint8_t expected[] = {
        0x24, 0x8d, 0x6a, 0x61, 0xd2, 0x06, 0x38, 0xb8,
        0xe5, 0xc0, 0x26, 0x93, 0x0c, 0x3e, 0x60, 0x39,
        0xa3, 0x3c, 0xe4, 0x59, 0x64, 0xff, 0x21, 0x67,
        0xf6, 0xec, 0xed, 0xd4, 0x19, 0xdb, 0x06, 0xc1,
    };
    ASSERT(memcmp(digest, expected, EOS_SHA256_DIGEST_SIZE) == 0);
}

TEST(test_sha256_incremental)
{
    /* Hash "abc" incrementally: "a" + "bc" */
    eos_sha256_ctx_t ctx;
    uint8_t digest[EOS_SHA256_DIGEST_SIZE];
    uint8_t digest_oneshot[EOS_SHA256_DIGEST_SIZE];

    eos_sha256_init(&ctx);
    eos_sha256_update(&ctx, (const uint8_t *)"a", 1);
    eos_sha256_update(&ctx, (const uint8_t *)"bc", 2);
    eos_sha256_final(&ctx, digest);

    eos_crypto_hash((const uint8_t *)"abc", 3, digest_oneshot);

    ASSERT(memcmp(digest, digest_oneshot, EOS_SHA256_DIGEST_SIZE) == 0);
}

TEST(test_crypto_null_args)
{
    uint8_t digest[EOS_SHA256_DIGEST_SIZE];
    ASSERT(eos_crypto_hash(NULL, 10, digest) == EOS_ERR_INVALID);
    ASSERT(eos_crypto_hash((const uint8_t *)"abc", 3, NULL) == EOS_ERR_INVALID);
}

int main(void)
{
    printf("=== eBootloader: Crypto / SHA-256 Unit Tests ===\n\n");

    run_test_sha256_empty();
    run_test_sha256_abc();
    run_test_sha256_long();
    run_test_sha256_incremental();
    run_test_crypto_null_args();

    tests_run = 5;
    printf("\n%d/%d tests passed\n", tests_passed, tests_run);
    return (tests_passed == tests_run) ? 0 : 1;
}
