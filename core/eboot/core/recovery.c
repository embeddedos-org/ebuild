// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file recovery.c
 * @brief Recovery mode state machine
 *
 * Recovery mode is entered when no valid firmware can be booted,
 * or when explicitly requested. It provides a UART-based protocol
 * for image upload, verification, and device diagnostics.
 */

#include "eos_bootctl.h"
#include "eos_image.h"
#include "eos_hal.h"
#include <string.h>

/* Recovery protocol commands */
#define RCVR_CMD_PING       0x01
#define RCVR_CMD_INFO       0x02
#define RCVR_CMD_ERASE      0x03
#define RCVR_CMD_WRITE      0x04
#define RCVR_CMD_VERIFY     0x05
#define RCVR_CMD_BOOT       0x06
#define RCVR_CMD_LOG        0x07
#define RCVR_CMD_RESET      0x08
#define RCVR_CMD_FACTORY    0x09

#define RCVR_ACK            0xAA
#define RCVR_NACK           0x55

#define RCVR_BAUD_RATE      115200
#define RCVR_TIMEOUT_MS     5000
#define RCVR_WRITE_CHUNK    256

/* Recovery protocol packet header */
#ifdef _MSC_VER
#pragma pack(push, 1)
#endif
typedef struct {
    uint8_t  cmd;
    uint8_t  slot;
    uint16_t len;
    uint32_t offset;
}
#if defined(__GNUC__) || defined(__clang__)
__attribute__((packed))
#endif
rcvr_packet_t;
#ifdef _MSC_VER
#pragma pack(pop)
#endif

/* Forward declarations from slot_manager */
extern int  eos_slot_scan_all(void);
extern bool eos_slot_is_valid(eos_slot_t slot);
extern int  eos_slot_erase(eos_slot_t slot);

/* Forward declarations from boot_log */
extern void eos_boot_log_append(uint32_t event, uint32_t slot, uint32_t detail);

static int recovery_send_ack(void)
{
    uint8_t ack = RCVR_ACK;
    return eos_hal_uart_send(&ack, 1);
}

static int recovery_send_nack(void)
{
    uint8_t nack = RCVR_NACK;
    return eos_hal_uart_send(&nack, 1);
}

static int recovery_handle_ping(void)
{
    uint8_t response[] = { RCVR_ACK, 'E', 'O', 'S', EOS_BOOTCTL_VERSION };
    return eos_hal_uart_send(response, sizeof(response));
}

static int recovery_handle_info(void)
{
    const eos_board_ops_t *ops = eos_hal_get_ops();
    if (!ops)
        return recovery_send_nack();

    struct {
        uint8_t  ack;
        uint32_t flash_size;
        uint32_t slot_a_addr;
        uint32_t slot_a_size;
        uint32_t slot_b_addr;
        uint32_t slot_b_size;
    } info;

    info.ack         = RCVR_ACK;
    info.flash_size  = ops->flash_size;
    info.slot_a_addr = ops->slot_a_addr;
    info.slot_a_size = ops->slot_a_size;
    info.slot_b_addr = ops->slot_b_addr;
    info.slot_b_size = ops->slot_b_size;

    return eos_hal_uart_send(&info, sizeof(info));
}

static int recovery_handle_erase(eos_slot_t slot)
{
    if (slot != EOS_SLOT_A && slot != EOS_SLOT_B)
        return recovery_send_nack();

    int rc = eos_slot_erase(slot);
    return (rc == EOS_OK) ? recovery_send_ack() : recovery_send_nack();
}

static int recovery_handle_write(eos_slot_t slot, uint32_t offset, uint16_t len)
{
    if (slot != EOS_SLOT_A && slot != EOS_SLOT_B)
        return recovery_send_nack();

    uint32_t base = eos_hal_slot_addr(slot);
    if (base == 0)
        return recovery_send_nack();

    uint8_t buf[RCVR_WRITE_CHUNK];
    if (len > sizeof(buf))
        return recovery_send_nack();

    /* ACK to signal ready for data */
    recovery_send_ack();

    /* Receive data payload */
    int rc = eos_hal_uart_recv(buf, len, RCVR_TIMEOUT_MS);
    if (rc != EOS_OK)
        return recovery_send_nack();

    /* Write to flash */
    rc = eos_hal_flash_write(base + offset, buf, len);
    return (rc == EOS_OK) ? recovery_send_ack() : recovery_send_nack();
}

static int recovery_handle_verify(eos_slot_t slot)
{
    if (slot != EOS_SLOT_A && slot != EOS_SLOT_B)
        return recovery_send_nack();

    uint32_t addr = eos_hal_slot_addr(slot);
    if (addr == 0)
        return recovery_send_nack();

    eos_image_header_t hdr;
    int rc = eos_image_parse_header(addr, &hdr);
    if (rc != EOS_OK)
        return recovery_send_nack();

    uint32_t payload_addr = addr + hdr.hdr_size;
    rc = eos_image_verify_integrity(&hdr, payload_addr);
    if (rc != EOS_OK)
        return recovery_send_nack();

    return recovery_send_ack();
}

static int recovery_handle_boot(eos_slot_t slot, eos_bootctl_t *bctl)
{
    if (slot != EOS_SLOT_A && slot != EOS_SLOT_B)
        return recovery_send_nack();

    bctl->active_slot = slot;
    bctl->pending_slot = EOS_SLOT_NONE;
    bctl->boot_attempts = 0;
    bctl->flags &= ~EOS_FLAG_FORCE_RECOVERY;
    bctl->flags &= ~EOS_FLAG_FACTORY_RESET;

    int rc = eos_bootctl_save(bctl);
    if (rc != EOS_OK)
        return recovery_send_nack();

    recovery_send_ack();
    eos_hal_system_reset();
    return EOS_OK; /* unreachable */
}

static int recovery_handle_factory_reset(eos_bootctl_t *bctl)
{
    eos_slot_erase(EOS_SLOT_A);
    eos_slot_erase(EOS_SLOT_B);
    eos_bootctl_init_defaults(bctl);
    eos_bootctl_save(bctl);
    eos_boot_log_append(EOS_LOG_FACTORY_RESET, EOS_SLOT_NONE, 0);
    return recovery_send_ack();
}

int eos_recovery_enter(eos_bootctl_t *bctl)
{
    eos_boot_log_append(EOS_LOG_RECOVERY_ENTER, EOS_SLOT_NONE, 0);
    eos_hal_uart_init(RCVR_BAUD_RATE);

    /* Clear recovery flag so we don't loop */
    bctl->flags &= ~EOS_FLAG_FORCE_RECOVERY;
    eos_bootctl_save(bctl);

    /* Recovery command loop */
    while (1) {
        eos_hal_watchdog_feed();

        rcvr_packet_t pkt;
        int rc = eos_hal_uart_recv(&pkt, sizeof(pkt), RCVR_TIMEOUT_MS);
        if (rc != EOS_OK)
            continue;

        switch (pkt.cmd) {
        case RCVR_CMD_PING:
            recovery_handle_ping();
            break;

        case RCVR_CMD_INFO:
            recovery_handle_info();
            break;

        case RCVR_CMD_ERASE:
            recovery_handle_erase((eos_slot_t)pkt.slot);
            break;

        case RCVR_CMD_WRITE:
            recovery_handle_write((eos_slot_t)pkt.slot, pkt.offset, pkt.len);
            break;

        case RCVR_CMD_VERIFY:
            recovery_handle_verify((eos_slot_t)pkt.slot);
            break;

        case RCVR_CMD_BOOT:
            recovery_handle_boot((eos_slot_t)pkt.slot, bctl);
            break;

        case RCVR_CMD_RESET:
            recovery_send_ack();
            eos_hal_system_reset();
            break;

        case RCVR_CMD_FACTORY:
            recovery_handle_factory_reset(bctl);
            break;

        default:
            recovery_send_nack();
            break;
        }
    }

    return EOS_OK; /* unreachable */
}
