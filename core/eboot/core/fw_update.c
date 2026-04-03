// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file fw_update.c
 * @brief Firmware update pipeline — stream-based image install
 */

#include "eos_fw_update.h"
#include "eos_hal.h"
#include "eos_fwsvc.h"
#include <string.h>

int eos_fw_update_begin(eos_fw_update_ctx_t *ctx, eos_slot_t slot)
{
    if (!ctx) return EOS_ERR_INVALID;
    if (slot != EOS_SLOT_A && slot != EOS_SLOT_B) return EOS_ERR_INVALID;

    memset(ctx, 0, sizeof(*ctx));
    ctx->target_slot = slot;
    ctx->target_addr = eos_hal_slot_addr(slot);
    ctx->slot_size = eos_hal_slot_size(slot);

    if (ctx->target_addr == 0 || ctx->slot_size == 0) {
        ctx->state = EOS_FW_STATE_ERROR;
        ctx->last_error = EOS_ERR_INVALID;
        return EOS_ERR_INVALID;
    }

    /* Erase target slot */
    int rc = eos_hal_flash_erase(ctx->target_addr, ctx->slot_size);
    if (rc != EOS_OK) {
        ctx->state = EOS_FW_STATE_ERROR;
        ctx->last_error = rc;
        return rc;
    }

    ctx->state = EOS_FW_STATE_HEADER;
    ctx->write_addr = ctx->target_addr;
    eos_sha256_init(&ctx->sha_ctx);
    ctx->crc_accum = 0xFFFFFFFF;

    return EOS_OK;
}

static void update_crc(eos_fw_update_ctx_t *ctx, const uint8_t *data, size_t len)
{
    uint32_t crc = ctx->crc_accum;
    for (size_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (int bit = 0; bit < 8; bit++) {
            if (crc & 1) crc = (crc >> 1) ^ 0xEDB88320;
            else         crc >>= 1;
        }
    }
    ctx->crc_accum = crc;
}

int eos_fw_update_write(eos_fw_update_ctx_t *ctx, const uint8_t *data, size_t len)
{
    if (!ctx || !data || len == 0) return EOS_ERR_INVALID;
    if (ctx->state == EOS_FW_STATE_ERROR || ctx->state == EOS_FW_STATE_COMPLETE) {
        return EOS_ERR_INVALID;
    }

    size_t offset = 0;

    /* Accumulate header bytes first */
    if (ctx->state == EOS_FW_STATE_HEADER) {
        size_t hdr_remaining = sizeof(eos_image_header_t) - ctx->hdr_received;
        size_t copy = (len < hdr_remaining) ? len : hdr_remaining;

        memcpy(ctx->hdr_buf + ctx->hdr_received, data, copy);
        ctx->hdr_received += (uint32_t)copy;
        offset = copy;

        if (ctx->hdr_received >= sizeof(eos_image_header_t)) {
            /* Parse header */
            memcpy(&ctx->header, ctx->hdr_buf, sizeof(eos_image_header_t));

            if (ctx->header.magic != EOS_IMG_MAGIC) {
                ctx->state = EOS_FW_STATE_ERROR;
                ctx->last_error = EOS_ERR_NO_IMAGE;
                return EOS_ERR_NO_IMAGE;
            }

            if (ctx->header.image_size == 0 ||
                ctx->header.image_size > ctx->slot_size - sizeof(eos_image_header_t)) {
                ctx->state = EOS_FW_STATE_ERROR;
                ctx->last_error = EOS_ERR_FULL;
                return EOS_ERR_FULL;
            }

            ctx->header_parsed = true;
            ctx->payload_total = ctx->header.image_size;
            ctx->payload_written = 0;

            /* Write header to flash */
            int rc = eos_hal_flash_write(ctx->target_addr, ctx->hdr_buf,
                                          sizeof(eos_image_header_t));
            if (rc != EOS_OK) {
                ctx->state = EOS_FW_STATE_ERROR;
                ctx->last_error = rc;
                return rc;
            }

            ctx->write_addr = ctx->target_addr + sizeof(eos_image_header_t);
            ctx->state = EOS_FW_STATE_PAYLOAD;
        }
    }

    /* Write payload bytes */
    if (ctx->state == EOS_FW_STATE_PAYLOAD && offset < len) {
        const uint8_t *payload_data = data + offset;
        size_t payload_len = len - offset;
        size_t remaining = ctx->payload_total - ctx->payload_written;

        if (payload_len > remaining) payload_len = remaining;

        /* Write to flash */
        int rc = eos_hal_flash_write(ctx->write_addr, payload_data, payload_len);
        if (rc != EOS_OK) {
            ctx->state = EOS_FW_STATE_ERROR;
            ctx->last_error = rc;
            return rc;
        }

        /* Update integrity trackers */
        eos_sha256_update(&ctx->sha_ctx, payload_data, payload_len);
        update_crc(ctx, payload_data, payload_len);

        ctx->write_addr += (uint32_t)payload_len;
        ctx->payload_written += (uint32_t)payload_len;

        if (ctx->payload_written >= ctx->payload_total) {
            ctx->state = EOS_FW_STATE_VERIFY;
        }
    }

    ctx->total_received += (uint32_t)len;
    return EOS_OK;
}

int eos_fw_update_finalize(eos_fw_update_ctx_t *ctx, eos_upgrade_mode_t mode)
{
    if (!ctx) return EOS_ERR_INVALID;
    if (ctx->state != EOS_FW_STATE_VERIFY) return EOS_ERR_INVALID;

    /* Verify SHA-256 hash */
    if (ctx->header.flags & EOS_IMG_FLAG_HASH_SHA256) {
        uint8_t computed_hash[EOS_SHA256_DIGEST_SIZE];
        eos_sha256_final(&ctx->sha_ctx, computed_hash);

        if (memcmp(computed_hash, ctx->header.hash, EOS_SHA256_DIGEST_SIZE) != 0) {
            ctx->state = EOS_FW_STATE_ERROR;
            ctx->last_error = EOS_ERR_CRC;
            return EOS_ERR_CRC;
        }
    } else {
        /* Verify CRC32 */
        uint32_t final_crc = ~ctx->crc_accum;
        uint32_t stored_crc;
        memcpy(&stored_crc, ctx->header.hash, sizeof(stored_crc));

        if (final_crc != stored_crc) {
            ctx->state = EOS_FW_STATE_ERROR;
            ctx->last_error = EOS_ERR_CRC;
            return EOS_ERR_CRC;
        }
    }

    /* Request upgrade through firmware services */
    int rc = eos_fw_request_upgrade(ctx->target_slot, mode);
    if (rc != EOS_OK) {
        ctx->state = EOS_FW_STATE_ERROR;
        ctx->last_error = rc;
        return rc;
    }

    ctx->state = EOS_FW_STATE_COMPLETE;
    return EOS_OK;
}

void eos_fw_update_abort(eos_fw_update_ctx_t *ctx)
{
    if (!ctx) return;
    ctx->state = EOS_FW_STATE_IDLE;
    memset(ctx, 0, sizeof(*ctx));
}

uint8_t eos_fw_update_progress(const eos_fw_update_ctx_t *ctx)
{
    if (!ctx || ctx->payload_total == 0) return 0;
    if (ctx->state == EOS_FW_STATE_COMPLETE) return 100;

    uint32_t total = (uint32_t)sizeof(eos_image_header_t) + ctx->payload_total;
    uint32_t done = ctx->total_received;
    if (done > total) done = total;

    return (uint8_t)((done * 100) / total);
}

eos_fw_update_state_t eos_fw_update_get_state(const eos_fw_update_ctx_t *ctx)
{
    if (!ctx) return EOS_FW_STATE_IDLE;
    return ctx->state;
}
