// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file jump_app.c
 * @brief Stage-1 jump to application firmware
 *
 * Final handoff from E-Boot to application firmware.
 * Architecture-aware: disables interrupts, clears pending IRQs,
 * sets MSP, and branches to the reset vector.
 */

#include "eos_hal.h"
#include "eos_bootctl.h"
#include "eos_image.h"

/* Forward declarations from boot_log */
extern void eos_boot_log_append(uint32_t event, uint32_t slot, uint32_t detail);

int eboot_jump_to_app(eos_bootctl_t *bctl, eos_slot_t slot)
{
    uint32_t addr = eos_hal_slot_addr(slot);
    if (addr == 0)
        return EOS_ERR_INVALID;

    /* Read the image header to get the entry address */
    eos_image_header_t hdr;
    int rc = eos_image_parse_header(addr, &hdr);
    if (rc != EOS_OK)
        return rc;

    /* Increment boot attempts before jumping */
    eos_bootctl_increment_attempts(bctl);

    /* Update log head in boot control */
    extern uint32_t eos_boot_log_get_head(void);
    bctl->log_head = eos_boot_log_get_head();
    eos_bootctl_save(bctl);

    eos_hal_watchdog_feed();

    /* Perform the jump via HAL */
    uint32_t vector_addr = hdr.load_addr;
    if (vector_addr == 0)
        vector_addr = addr + hdr.hdr_size;

    eos_hal_disable_interrupts();
    eos_hal_deinit_peripherals();
    eos_hal_jump(vector_addr);

    /* Should never reach here */
    return EOS_ERR_GENERIC;
}
