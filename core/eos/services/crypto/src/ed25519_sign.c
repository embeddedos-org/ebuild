/* SPDX-License-Identifier: MIT
 * Copyright (c) 2026 EoS Project
 *
 * @file ed25519_sign.c
 * @brief Ed25519 key generation and signing (ref10 formulation).
 *
 * ed25519.h has always declared ed25519_create_keypair() and ed25519_sign(),
 * but no translation unit implemented them: the tree could verify signatures
 * and never produce one. That made the declarations a trap -- any .eapp
 * producer tooling (see #162, which needs producers to sign the v2 envelope)
 * would fail at link time. This file implements both on top of the existing
 * field/scalar/curve primitives.
 *
 * The private key layout is seed || public_key (64 bytes), the ref10
 * convention: ed25519_sign() re-derives the expanded secret (az) from the
 * seed on every call, so the stored private key never holds the expanded
 * scalar at rest.
 */

#include "ed25519.h"
#include "sha512.h"
#include "ge.h"
#include "sc.h"

#include <string.h>

void ed25519_create_keypair(unsigned char *public_key,
                            unsigned char *private_key,
                            const unsigned char *seed)
{
    sha512_context hash;
    unsigned char expanded[64];
    ge_p3 A;

    sha512_init(&hash);
    sha512_update(&hash, seed, 32);
    sha512_final(&hash, expanded);

    expanded[0] &= 248;
    expanded[31] &= 63;
    expanded[31] |= 64;

    ge_scalarmult_base(&A, expanded);
    ge_p3_tobytes(public_key, &A);

    memcpy(private_key, seed, 32);
    memcpy(private_key + 32, public_key, 32);

    memset(expanded, 0, sizeof(expanded));
}

void ed25519_sign(unsigned char *signature,
                  const unsigned char *message, size_t message_len,
                  const unsigned char *public_key,
                  const unsigned char *private_key)
{
    sha512_context hash;
    unsigned char az[64];
    unsigned char nonce[64];
    unsigned char hram[64];
    ge_p3 R;

    /* az = SHA-512(seed), clamped; seed is the first half of private_key. */
    sha512_init(&hash);
    sha512_update(&hash, private_key, 32);
    sha512_final(&hash, az);
    az[0] &= 248;
    az[31] &= 63;
    az[31] |= 64;

    /* nonce = SHA-512(az[32..64] || message), reduced mod L. */
    sha512_init(&hash);
    sha512_update(&hash, az + 32, 32);
    sha512_update(&hash, message, message_len);
    sha512_final(&hash, nonce);
    sc_reduce(nonce);

    ge_scalarmult_base(&R, nonce);
    ge_p3_tobytes(signature, &R);

    /* hram = SHA-512(R || public_key || message), reduced mod L. */
    sha512_init(&hash);
    sha512_update(&hash, signature, 32);
    sha512_update(&hash, public_key, 32);
    sha512_update(&hash, message, message_len);
    sha512_final(&hash, hram);
    sc_reduce(hram);

    /* S = hram * az + nonce (mod L). */
    sc_muladd(signature + 32, hram, az, nonce);

    memset(az, 0, sizeof(az));
    memset(nonce, 0, sizeof(nonce));
}
