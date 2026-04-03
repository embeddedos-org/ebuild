// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file crypto_boot.c
 * @brief Self-contained SHA-256 + image verification for secure boot
 */

#include "eos_crypto_boot.h"
#include "eos_hal.h"
#include <string.h>

/* SHA-256 constants */
static const uint32_t K[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
};

#define ROTR(x, n) (((x) >> (n)) | ((x) << (32 - (n))))
#define CH(x, y, z) (((x) & (y)) ^ (~(x) & (z)))
#define MAJ(x, y, z) (((x) & (y)) ^ ((x) & (z)) ^ ((y) & (z)))
#define EP0(x) (ROTR(x, 2) ^ ROTR(x, 13) ^ ROTR(x, 22))
#define EP1(x) (ROTR(x, 6) ^ ROTR(x, 11) ^ ROTR(x, 25))
#define SIG0(x) (ROTR(x, 7) ^ ROTR(x, 18) ^ ((x) >> 3))
#define SIG1(x) (ROTR(x, 17) ^ ROTR(x, 19) ^ ((x) >> 10))

static void sha256_transform(eos_sha256_ctx_t *ctx)
{
    uint32_t w[64];
    uint32_t a, b, c, d, e, f, g, h;
    uint32_t t1, t2;

    for (int i = 0; i < 16; i++) {
        w[i] = ((uint32_t)ctx->buffer[i * 4 + 0] << 24) |
               ((uint32_t)ctx->buffer[i * 4 + 1] << 16) |
               ((uint32_t)ctx->buffer[i * 4 + 2] << 8)  |
               ((uint32_t)ctx->buffer[i * 4 + 3]);
    }

    for (int i = 16; i < 64; i++) {
        w[i] = SIG1(w[i - 2]) + w[i - 7] + SIG0(w[i - 15]) + w[i - 16];
    }

    a = ctx->state[0]; b = ctx->state[1]; c = ctx->state[2]; d = ctx->state[3];
    e = ctx->state[4]; f = ctx->state[5]; g = ctx->state[6]; h = ctx->state[7];

    for (int i = 0; i < 64; i++) {
        t1 = h + EP1(e) + CH(e, f, g) + K[i] + w[i];
        t2 = EP0(a) + MAJ(a, b, c);
        h = g; g = f; f = e; e = d + t1;
        d = c; c = b; b = a; a = t1 + t2;
    }

    ctx->state[0] += a; ctx->state[1] += b; ctx->state[2] += c; ctx->state[3] += d;
    ctx->state[4] += e; ctx->state[5] += f; ctx->state[6] += g; ctx->state[7] += h;
}

void eos_sha256_init(eos_sha256_ctx_t *ctx)
{
    ctx->state[0] = 0x6a09e667; ctx->state[1] = 0xbb67ae85;
    ctx->state[2] = 0x3c6ef372; ctx->state[3] = 0xa54ff53a;
    ctx->state[4] = 0x510e527f; ctx->state[5] = 0x9b05688c;
    ctx->state[6] = 0x1f83d9ab; ctx->state[7] = 0x5be0cd19;
    ctx->count = 0;
}

void eos_sha256_update(eos_sha256_ctx_t *ctx, const uint8_t *data, size_t len)
{
    for (size_t i = 0; i < len; i++) {
        ctx->buffer[ctx->count % EOS_SHA256_BLOCK_SIZE] = data[i];
        ctx->count++;
        if ((ctx->count % EOS_SHA256_BLOCK_SIZE) == 0) {
            sha256_transform(ctx);
        }
    }
}

void eos_sha256_final(eos_sha256_ctx_t *ctx, uint8_t digest[EOS_SHA256_DIGEST_SIZE])
{
    uint64_t bits = ctx->count * 8;
    size_t pad_idx = ctx->count % EOS_SHA256_BLOCK_SIZE;

    ctx->buffer[pad_idx++] = 0x80;

    if (pad_idx > 56) {
        while (pad_idx < EOS_SHA256_BLOCK_SIZE) ctx->buffer[pad_idx++] = 0;
        sha256_transform(ctx);
        pad_idx = 0;
    }

    while (pad_idx < 56) ctx->buffer[pad_idx++] = 0;

    for (int i = 7; i >= 0; i--) {
        ctx->buffer[pad_idx++] = (uint8_t)(bits >> (i * 8));
    }
    sha256_transform(ctx);

    for (int i = 0; i < 8; i++) {
        digest[i * 4 + 0] = (uint8_t)(ctx->state[i] >> 24);
        digest[i * 4 + 1] = (uint8_t)(ctx->state[i] >> 16);
        digest[i * 4 + 2] = (uint8_t)(ctx->state[i] >> 8);
        digest[i * 4 + 3] = (uint8_t)(ctx->state[i]);
    }
}

int eos_crypto_hash(const uint8_t *data, size_t len,
                     uint8_t digest[EOS_SHA256_DIGEST_SIZE])
{
    if (!data || !digest) return EOS_ERR_INVALID;

    eos_sha256_ctx_t ctx;
    eos_sha256_init(&ctx);
    eos_sha256_update(&ctx, data, len);
    eos_sha256_final(&ctx, digest);

    return EOS_OK;
}

int eos_crypto_verify_image(uint32_t image_addr, uint32_t image_size,
                             const uint8_t expected_hash[EOS_SHA256_DIGEST_SIZE])
{
    if (!expected_hash || image_size == 0) return EOS_ERR_INVALID;

    eos_sha256_ctx_t ctx;
    eos_sha256_init(&ctx);

    uint8_t buf[256];
    uint32_t offset = 0;
    while (offset < image_size) {
        uint32_t chunk = image_size - offset;
        if (chunk > sizeof(buf)) chunk = sizeof(buf);
        int rc = eos_hal_flash_read(image_addr + offset, buf, chunk);
        if (rc != EOS_OK) return rc;
        eos_sha256_update(&ctx, buf, chunk);
        offset += chunk;
    }

    uint8_t computed[EOS_SHA256_DIGEST_SIZE];
    eos_sha256_final(&ctx, computed);

    if (memcmp(computed, expected_hash, EOS_SHA256_DIGEST_SIZE) != 0) {
        return EOS_ERR_SIGNATURE;
    }

    return EOS_OK;
}

int eos_crypto_verify_signature(const uint8_t *data, size_t data_len,
                                 const uint8_t *signature, size_t sig_len,
                                 const uint8_t *public_key, size_t key_len)
{
    (void)data; (void)data_len;
    (void)signature; (void)sig_len;
    (void)public_key; (void)key_len;

    /* Stub — Ed25519/ECDSA implementation goes here */
    return EOS_ERR_GENERIC;
}
