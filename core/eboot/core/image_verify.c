// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file image_verify.c
 * @brief Image header parsing and integrity verification
 */

#include "eos_image.h"
#include "eos_hal.h"
#include <string.h>

/* CRC32 computation — no lookup table needed */
static uint32_t crc32_byte(uint32_t crc, uint8_t byte)
{
    crc ^= byte;
    for (int i = 0; i < 8; i++) {
        if (crc & 1) crc = (crc >> 1) ^ 0xEDB88320;
        else         crc >>= 1;
    }
    return crc;
}

uint32_t eos_crc32(uint32_t addr, size_t len)
{
    uint32_t crc = 0xFFFFFFFF;
    uint8_t buf[256];

    while (len > 0) {
        size_t chunk = (len > sizeof(buf)) ? sizeof(buf) : len;

        if (eos_hal_flash_read(addr, buf, chunk) != EOS_OK)
            return 0;

        for (size_t i = 0; i < chunk; i++) {
            crc = crc32_byte(crc, buf[i]);
        }

        addr += (uint32_t)chunk;
        len -= chunk;
    }

    return ~crc;
}

int eos_image_parse_header(uint32_t addr, eos_image_header_t *out)
{
    if (!out)
        return EOS_ERR_INVALID;

    int rc = eos_hal_flash_read(addr, out, sizeof(*out));
    if (rc != EOS_OK)
        return EOS_ERR_FLASH;

    if (out->magic != EOS_IMG_MAGIC)
        return EOS_ERR_NO_IMAGE;

    if (out->hdr_size < sizeof(eos_image_header_t))
        return EOS_ERR_INVALID;

    if (out->image_size == 0)
        return EOS_ERR_INVALID;

    if (out->entry_addr == 0)
        return EOS_ERR_INVALID;

    return EOS_OK;
}

int eos_image_verify_integrity(const eos_image_header_t *hdr, uint32_t addr)
{
    if (!hdr)
        return EOS_ERR_INVALID;

    /* Phase 1: CRC32 verification */
    uint32_t payload_addr = addr;
    uint32_t computed_crc = eos_crc32(payload_addr, hdr->image_size);

    /* For CRC mode, the hash field stores the CRC32 in the first 4 bytes */
    uint32_t stored_crc;
    memcpy(&stored_crc, hdr->hash, sizeof(stored_crc));

    if (computed_crc != stored_crc)
        return EOS_ERR_CRC;

    return EOS_OK;
}

int eos_image_verify_signature(const eos_image_header_t *hdr)
{
    if (!hdr)
        return EOS_ERR_INVALID;

    /* Phase 1: No signature verification — accept CRC-only images */
    if (hdr->sig_type == EOS_SIG_NONE || hdr->sig_type == EOS_SIG_CRC32)
        return EOS_OK;

    /* Phase 2+: SHA-256 / Ed25519 / ECDSA — not yet implemented */
    return EOS_ERR_SIGNATURE;
}

int eos_image_check_version(uint32_t candidate_version, uint32_t min_version)
{
    if (candidate_version < min_version)
        return EOS_ERR_VERSION;

    return EOS_OK;
}
