// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/*
 * EIPC HMAC-SHA256 Implementation
 * Standard HMAC construction per RFC 2104 using the internal SHA-256.
 */

#include "eipc_sha256.h"
#include "eipc.h"
#include <string.h>
#include <stdlib.h>
#include <stdlib.h>

#define HMAC_BLOCK_SIZE 64
#define HMAC_HASH_SIZE  32

void eipc_hmac_sign(const uint8_t *key, size_t key_len,
                    const uint8_t *data, size_t data_len,
                    uint8_t mac[32]) {
    uint8_t k[HMAC_BLOCK_SIZE];
    uint8_t ipad[HMAC_BLOCK_SIZE];
    uint8_t opad[HMAC_BLOCK_SIZE];
    uint8_t inner_hash[HMAC_HASH_SIZE];
    uint8_t inner_buf[HMAC_BLOCK_SIZE + 65536];
    uint8_t outer_buf[HMAC_BLOCK_SIZE + HMAC_HASH_SIZE];
    size_t i;

    memset(k, 0, HMAC_BLOCK_SIZE);

    if (key_len > HMAC_BLOCK_SIZE) {
        eipc_sha256(key, key_len, k);
    } else {
        memcpy(k, key, key_len);
    }

    for (i = 0; i < HMAC_BLOCK_SIZE; i++) {
        ipad[i] = k[i] ^ 0x36;
        opad[i] = k[i] ^ 0x5c;
    }

    /* Inner hash: SHA256(ipad_key || data) */
    /* For large data, we need a streaming approach. Use stack for small data,
       heap-free two-pass SHA256 for arbitrary sizes. */
    /* We'll compute this by doing SHA256 in two update calls conceptually.
       Since our eipc_sha256 takes a single buffer, we need a combined buffer
       or we need to expose the streaming API. Let's use a simple combined approach
       with a reasonable limit, and fall back to a manual two-part hash. */

    /* Actually, let's just implement a proper streaming HMAC using the internal
       sha256 ctx. But since sha256 is static in eipc_sha256.c, we'll compose
       with the public API by building combined buffers.
       For production use, the data sizes in EIPC are bounded (frames < 64KB). */

    if (data_len <= sizeof(inner_buf) - HMAC_BLOCK_SIZE) {
        memcpy(inner_buf, ipad, HMAC_BLOCK_SIZE);
        memcpy(inner_buf + HMAC_BLOCK_SIZE, data, data_len);
        eipc_sha256(inner_buf, HMAC_BLOCK_SIZE + data_len, inner_hash);
    } else {
        /* For oversized data, allocate on stack in chunks.
           This shouldn't happen in practice for EIPC frames. */
        uint8_t *buf = (uint8_t *)malloc(HMAC_BLOCK_SIZE + data_len);
        if (buf) {
            memcpy(buf, ipad, HMAC_BLOCK_SIZE);
            memcpy(buf + HMAC_BLOCK_SIZE, data, data_len);
            eipc_sha256(buf, HMAC_BLOCK_SIZE + data_len, inner_hash);
            free(buf);
        } else {
            memset(mac, 0, 32);
            return;
        }
    }

    /* Outer hash: SHA256(opad_key || inner_hash) */
    memcpy(outer_buf, opad, HMAC_BLOCK_SIZE);
    memcpy(outer_buf + HMAC_BLOCK_SIZE, inner_hash, HMAC_HASH_SIZE);
    eipc_sha256(outer_buf, HMAC_BLOCK_SIZE + HMAC_HASH_SIZE, mac);

    /* Scrub sensitive data */
    memset(k, 0, sizeof(k));
    memset(ipad, 0, sizeof(ipad));
    memset(opad, 0, sizeof(opad));
    memset(inner_hash, 0, sizeof(inner_hash));
}

bool eipc_hmac_verify(const uint8_t *key, size_t key_len,
                      const uint8_t *data, size_t data_len,
                      const uint8_t mac[32]) {
    uint8_t computed[32];
    volatile uint8_t diff = 0;
    int i;

    eipc_hmac_sign(key, key_len, data, data_len, computed);

    /* Constant-time comparison to prevent timing attacks */
    for (i = 0; i < 32; i++) {
        diff |= computed[i] ^ mac[i];
    }

    memset(computed, 0, sizeof(computed));
    return diff == 0;
}
