// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file eos_fw_transport.h
 * @brief Firmware transport layer — pluggable receive protocols
 *
 * Defines a transport interface for receiving firmware updates over
 * UART (XMODEM/YMODEM), USB, network, or any custom channel.
 * Each transport implements eos_fw_transport_ops_t.
 */

#ifndef EOS_FW_TRANSPORT_H
#define EOS_FW_TRANSPORT_H

#include "eos_types.h"
#include "eos_fw_update.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ---- Transport Interface ---- */

typedef enum {
    EOS_TRANSPORT_UART_RAW   = 0,
    EOS_TRANSPORT_UART_XMODEM = 1,
    EOS_TRANSPORT_UART_YMODEM = 2,
    EOS_TRANSPORT_USB_DFU    = 3,
    EOS_TRANSPORT_NETWORK    = 4,
    EOS_TRANSPORT_SPI_SLAVE  = 5,
    EOS_TRANSPORT_CUSTOM     = 0xFF,
} eos_transport_type_t;

typedef struct eos_fw_transport eos_fw_transport_t;

typedef struct {
    const char *name;
    eos_transport_type_t type;

    int  (*init)(eos_fw_transport_t *tp);
    void (*deinit)(eos_fw_transport_t *tp);

    /**
     * Receive firmware into the update context. Blocks until complete,
     * error, or timeout. Calls eos_fw_update_write() internally.
     */
    int  (*receive)(eos_fw_transport_t *tp, eos_fw_update_ctx_t *ctx);

    /**
     * Send a status/ACK byte back to the sender.
     */
    int  (*send_status)(eos_fw_transport_t *tp, uint8_t status);

    /**
     * Check if data is available (non-blocking).
     */
    bool (*data_available)(eos_fw_transport_t *tp);
} eos_fw_transport_ops_t;

struct eos_fw_transport {
    const eos_fw_transport_ops_t *ops;
    void *priv;
    uint32_t timeout_ms;
    uint32_t baudrate;
    uint8_t port;
};

/* ---- Transport API ---- */

/**
 * Run a complete firmware update session using the given transport.
 * Combines: begin → transport.receive → finalize.
 */
int eos_fw_transport_update(eos_fw_transport_t *tp, eos_slot_t slot,
                             eos_upgrade_mode_t mode);

/* ---- Built-in Transports ---- */

/**
 * Get the UART raw transport (simple byte stream, no protocol framing).
 * Expects: 4-byte length prefix, then raw firmware bytes.
 */
const eos_fw_transport_ops_t *eos_fw_transport_uart_raw(void);

/**
 * Get the UART XMODEM transport (128-byte blocks, CRC-16).
 */
const eos_fw_transport_ops_t *eos_fw_transport_uart_xmodem(void);

/**
 * Get the UART YMODEM transport (1024-byte blocks, batch support).
 */
const eos_fw_transport_ops_t *eos_fw_transport_uart_ymodem(void);

#ifdef __cplusplus
}
#endif

#endif /* EOS_FW_TRANSPORT_H */
