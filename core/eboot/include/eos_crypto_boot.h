// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file eos_crypto_boot.h
 * @brief Embedded crypto for secure boot — SHA-256 + signature verification
 */

#ifndef EOS_CRYPTO_BOOT_H
#define EOS_CRYPTO_BOOT_H

#include "eos_types.h"

#ifdef __cplusplus
extern "C" {
#endif

#define EOS_SHA256_BLOCK_SIZE  64
#define EOS_SHA256_DIGEST_SIZE 32

typedef struct {
    uint32_t state[8];
    uint64_t count;
    uint8_t  buffer[EOS_SHA256_BLOCK_SIZE];
} eos_sha256_ctx_t;

void eos_sha256_init(eos_sha256_ctx_t *ctx);
void eos_sha256_update(eos_sha256_ctx_t *ctx, const uint8_t *data, size_t len);
void eos_sha256_final(eos_sha256_ctx_t *ctx, uint8_t digest[EOS_SHA256_DIGEST_SIZE]);

/**
 * Compute SHA-256 hash of a memory region.
 */
int eos_crypto_hash(const uint8_t *data, size_t len,
                     uint8_t digest[EOS_SHA256_DIGEST_SIZE]);

/**
 * Verify an image's integrity using its embedded hash.
 */
int eos_crypto_verify_image(uint32_t image_addr, uint32_t image_size,
                             const uint8_t expected_hash[EOS_SHA256_DIGEST_SIZE]);

/**
 * Verify a digital signature (Ed25519-style stub).
 */
int eos_crypto_verify_signature(const uint8_t *data, size_t data_len,
                                 const uint8_t *signature, size_t sig_len,
                                 const uint8_t *public_key, size_t key_len);

#ifdef __cplusplus
}
#endif

#endif /* EOS_CRYPTO_BOOT_H */
