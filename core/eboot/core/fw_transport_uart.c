// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file fw_transport_uart.c
 * @brief UART firmware transport — raw, XMODEM, and YMODEM protocols
 */

#include "eos_fw_transport.h"
#include "eos_hal.h"
#include <string.h>

/* ================================================================
 * Common transport wrapper
 * ================================================================ */

int eos_fw_transport_update(eos_fw_transport_t *tp, eos_slot_t slot,
                             eos_upgrade_mode_t mode)
{
    if (!tp || !tp->ops) return EOS_ERR_INVALID;

    eos_fw_update_ctx_t ctx;

    /* Initialize transport */
    if (tp->ops->init) {
        int rc = tp->ops->init(tp);
        if (rc != EOS_OK) return rc;
    }

    /* Begin update */
    int rc = eos_fw_update_begin(&ctx, slot);
    if (rc != EOS_OK) goto cleanup;

    /* Receive via transport */
    rc = tp->ops->receive(tp, &ctx);
    if (rc != EOS_OK) {
        eos_fw_update_abort(&ctx);
        goto cleanup;
    }

    /* Finalize */
    rc = eos_fw_update_finalize(&ctx, mode);

cleanup:
    if (tp->ops->deinit) tp->ops->deinit(tp);
    return rc;
}

/* ================================================================
 * UART Raw Transport — simple length-prefixed byte stream
 *
 * Protocol:
 *   Sender → [4 bytes: total_len LE] [total_len bytes: firmware data]
 *   Receiver → [1 byte: 0x06 ACK or 0x15 NAK]
 * ================================================================ */

#define UART_RAW_ACK  0x06
#define UART_RAW_NAK  0x15
#define UART_RAW_CHUNK 256

static int uart_raw_init(eos_fw_transport_t *tp)
{
    return eos_hal_uart_init(tp->baudrate ? tp->baudrate : 115200);
}

static void uart_raw_deinit(eos_fw_transport_t *tp)
{
    (void)tp;
}

static int uart_raw_receive(eos_fw_transport_t *tp, eos_fw_update_ctx_t *ctx)
{
    uint32_t timeout = tp->timeout_ms ? tp->timeout_ms : 30000;

    /* Read 4-byte length prefix */
    uint8_t len_buf[4];
    int rc = eos_hal_uart_recv(len_buf, 4, timeout);
    if (rc != EOS_OK) return rc;

    uint32_t total_len = (uint32_t)len_buf[0] |
                          ((uint32_t)len_buf[1] << 8) |
                          ((uint32_t)len_buf[2] << 16) |
                          ((uint32_t)len_buf[3] << 24);

    /* Receive firmware in chunks */
    uint8_t chunk[UART_RAW_CHUNK];
    uint32_t remaining = total_len;

    while (remaining > 0) {
        size_t to_read = (remaining > UART_RAW_CHUNK) ? UART_RAW_CHUNK : remaining;

        rc = eos_hal_uart_recv(chunk, to_read, timeout);
        if (rc != EOS_OK) {
            uint8_t nak = UART_RAW_NAK;
            eos_hal_uart_send(&nak, 1);
            return rc;
        }

        rc = eos_fw_update_write(ctx, chunk, to_read);
        if (rc != EOS_OK) {
            uint8_t nak = UART_RAW_NAK;
            eos_hal_uart_send(&nak, 1);
            return rc;
        }

        remaining -= (uint32_t)to_read;
        eos_hal_watchdog_feed();
    }

    uint8_t ack = UART_RAW_ACK;
    eos_hal_uart_send(&ack, 1);

    return EOS_OK;
}

static int uart_raw_send_status(eos_fw_transport_t *tp, uint8_t status)
{
    (void)tp;
    return eos_hal_uart_send(&status, 1);
}

static bool uart_raw_data_available(eos_fw_transport_t *tp)
{
    (void)tp;
    uint8_t probe;
    return (eos_hal_uart_recv(&probe, 0, 0) == EOS_OK);
}

static const eos_fw_transport_ops_t uart_raw_ops = {
    .name           = "uart-raw",
    .type           = EOS_TRANSPORT_UART_RAW,
    .init           = uart_raw_init,
    .deinit         = uart_raw_deinit,
    .receive        = uart_raw_receive,
    .send_status    = uart_raw_send_status,
    .data_available = uart_raw_data_available,
};

const eos_fw_transport_ops_t *eos_fw_transport_uart_raw(void)
{
    return &uart_raw_ops;
}

/* ================================================================
 * XMODEM Transport — 128-byte blocks with CRC-16
 *
 * Protocol:
 *   Receiver sends 'C' to request CRC mode
 *   Sender → [SOH][blk#][~blk#][128 bytes data][CRC-H][CRC-L]
 *   Receiver → ACK (0x06) or NAK (0x15)
 *   Sender → EOT (0x04) when done
 * ================================================================ */

#define XMODEM_SOH  0x01
#define XMODEM_EOT  0x04
#define XMODEM_ACK  0x06
#define XMODEM_NAK  0x15
#define XMODEM_CAN  0x18
#define XMODEM_CRC  'C'
#define XMODEM_BLOCK_SIZE 128

static uint16_t xmodem_crc16(const uint8_t *data, size_t len)
{
    uint16_t crc = 0;
    for (size_t i = 0; i < len; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (int bit = 0; bit < 8; bit++) {
            if (crc & 0x8000) crc = (crc << 1) ^ 0x1021;
            else              crc <<= 1;
        }
    }
    return crc;
}

static int xmodem_receive(eos_fw_transport_t *tp, eos_fw_update_ctx_t *ctx)
{
    uint32_t timeout = tp->timeout_ms ? tp->timeout_ms : 60000;
    uint8_t expected_blk = 1;

    /* Request CRC mode */
    uint8_t c = XMODEM_CRC;
    eos_hal_uart_send(&c, 1);

    while (1) {
        uint8_t soh;
        int rc = eos_hal_uart_recv(&soh, 1, timeout);
        if (rc != EOS_OK) return rc;

        if (soh == XMODEM_EOT) {
            c = XMODEM_ACK;
            eos_hal_uart_send(&c, 1);
            break;
        }

        if (soh == XMODEM_CAN) return EOS_ERR_GENERIC;
        if (soh != XMODEM_SOH) continue;

        /* Read block number + complement */
        uint8_t blk_hdr[2];
        rc = eos_hal_uart_recv(blk_hdr, 2, timeout);
        if (rc != EOS_OK) return rc;

        /* Read 128 data bytes + 2 CRC bytes */
        uint8_t block[XMODEM_BLOCK_SIZE + 2];
        rc = eos_hal_uart_recv(block, XMODEM_BLOCK_SIZE + 2, timeout);
        if (rc != EOS_OK) return rc;

        /* Verify block number */
        if (blk_hdr[0] != expected_blk || blk_hdr[1] != (uint8_t)(~expected_blk)) {
            c = XMODEM_NAK;
            eos_hal_uart_send(&c, 1);
            continue;
        }

        /* Verify CRC */
        uint16_t received_crc = ((uint16_t)block[XMODEM_BLOCK_SIZE] << 8) |
                                 block[XMODEM_BLOCK_SIZE + 1];
        uint16_t computed_crc = xmodem_crc16(block, XMODEM_BLOCK_SIZE);

        if (received_crc != computed_crc) {
            c = XMODEM_NAK;
            eos_hal_uart_send(&c, 1);
            continue;
        }

        /* Write to update context */
        rc = eos_fw_update_write(ctx, block, XMODEM_BLOCK_SIZE);
        if (rc != EOS_OK) {
            c = XMODEM_CAN;
            eos_hal_uart_send(&c, 1);
            return rc;
        }

        c = XMODEM_ACK;
        eos_hal_uart_send(&c, 1);
        expected_blk++;
        eos_hal_watchdog_feed();
    }

    return EOS_OK;
}

static const eos_fw_transport_ops_t uart_xmodem_ops = {
    .name           = "uart-xmodem",
    .type           = EOS_TRANSPORT_UART_XMODEM,
    .init           = uart_raw_init,
    .deinit         = uart_raw_deinit,
    .receive        = xmodem_receive,
    .send_status    = uart_raw_send_status,
    .data_available = uart_raw_data_available,
};

const eos_fw_transport_ops_t *eos_fw_transport_uart_xmodem(void)
{
    return &uart_xmodem_ops;
}

/* ================================================================
 * YMODEM Transport — 1024-byte blocks, filename/size header
 * ================================================================ */

#define YMODEM_STX  0x02
#define YMODEM_BLOCK_SIZE 1024

static int ymodem_receive(eos_fw_transport_t *tp, eos_fw_update_ctx_t *ctx)
{
    uint32_t timeout = tp->timeout_ms ? tp->timeout_ms : 60000;
    uint8_t expected_blk = 0;

    /* Request CRC mode */
    uint8_t c = XMODEM_CRC;
    eos_hal_uart_send(&c, 1);

    bool first_block = true;
    uint32_t file_size = 0;
    uint32_t total_received = 0;

    while (1) {
        uint8_t soh;
        int rc = eos_hal_uart_recv(&soh, 1, timeout);
        if (rc != EOS_OK) return rc;

        if (soh == XMODEM_EOT) {
            c = XMODEM_ACK;
            eos_hal_uart_send(&c, 1);

            if (first_block) break;

            /* YMODEM sends a second EOT */
            c = XMODEM_CRC;
            eos_hal_uart_send(&c, 1);
            break;
        }

        if (soh == XMODEM_CAN) return EOS_ERR_GENERIC;

        size_t block_size;
        if (soh == XMODEM_SOH) block_size = 128;
        else if (soh == YMODEM_STX) block_size = YMODEM_BLOCK_SIZE;
        else continue;

        /* Read block header */
        uint8_t blk_hdr[2];
        rc = eos_hal_uart_recv(blk_hdr, 2, timeout);
        if (rc != EOS_OK) return rc;

        /* Read data + CRC */
        uint8_t block[YMODEM_BLOCK_SIZE + 2];
        rc = eos_hal_uart_recv(block, block_size + 2, timeout);
        if (rc != EOS_OK) return rc;

        /* Verify CRC */
        uint16_t received_crc = ((uint16_t)block[block_size] << 8) | block[block_size + 1];
        uint16_t computed_crc = xmodem_crc16(block, block_size);
        if (received_crc != computed_crc) {
            c = XMODEM_NAK;
            eos_hal_uart_send(&c, 1);
            continue;
        }

        if (first_block && expected_blk == 0) {
            /* Block 0 = filename + size string */
            /* Parse file size from after null-terminated filename */
            const char *name = (const char *)block;
            size_t name_len = strlen(name);
            if (name_len > 0 && name_len < block_size - 1) {
                const char *size_str = name + name_len + 1;
                file_size = 0;
                while (*size_str >= '0' && *size_str <= '9') {
                    file_size = file_size * 10 + (*size_str - '0');
                    size_str++;
                }
            }
            first_block = false;
            expected_blk = 1;
            c = XMODEM_ACK;
            eos_hal_uart_send(&c, 1);
            c = XMODEM_CRC;
            eos_hal_uart_send(&c, 1);
            continue;
        }

        /* Write data block */
        size_t write_len = block_size;
        if (file_size > 0 && total_received + write_len > file_size) {
            write_len = file_size - total_received;
        }

        rc = eos_fw_update_write(ctx, block, write_len);
        if (rc != EOS_OK) {
            c = XMODEM_CAN;
            eos_hal_uart_send(&c, 1);
            return rc;
        }

        total_received += (uint32_t)write_len;
        c = XMODEM_ACK;
        eos_hal_uart_send(&c, 1);
        expected_blk++;
        eos_hal_watchdog_feed();

        if (file_size > 0 && total_received >= file_size) {
            /* File complete — wait for EOT */
        }
    }

    return EOS_OK;
}

static const eos_fw_transport_ops_t uart_ymodem_ops = {
    .name           = "uart-ymodem",
    .type           = EOS_TRANSPORT_UART_YMODEM,
    .init           = uart_raw_init,
    .deinit         = uart_raw_deinit,
    .receive        = ymodem_receive,
    .send_status    = uart_raw_send_status,
    .data_available = uart_raw_data_available,
};

const eos_fw_transport_ops_t *eos_fw_transport_uart_ymodem(void)
{
    return &uart_ymodem_ops;
}
