// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file boot_scan.c
 * @brief Stage-1 image scanning
 *
 * Scans firmware slots and updates the boot control block with
 * current image metadata (versions, CRCs).
 */

#include "eos_bootctl.h"
#include "eos_image.h"
#include "eos_hal.h"
#include <string.h>

/* Forward declarations from slot_manager */
extern int  eos_slot_scan_all(void);
extern bool eos_slot_is_valid(eos_slot_t slot);
extern uint32_t eos_slot_get_version(eos_slot_t slot);
extern int  eos_slot_get_header(eos_slot_t slot, eos_image_header_t *out);

/* Forward declarations from boot_log */
extern void eos_boot_log_append(uint32_t event, uint32_t slot, uint32_t detail);

int eboot_scan_images(eos_bootctl_t *bctl)
{
    eos_slot_scan_all();

    /* Update boot control with current slot info */
    if (eos_slot_is_valid(EOS_SLOT_A)) {
        eos_image_header_t hdr;
        if (eos_slot_get_header(EOS_SLOT_A, &hdr) == EOS_OK) {
            bctl->img_a_version = hdr.image_version;
            uint32_t crc;
            memcpy(&crc, hdr.hash, sizeof(crc));
            bctl->img_a_crc = crc;
        }
        eos_boot_log_append(EOS_LOG_IMAGE_VALID, EOS_SLOT_A,
                            bctl->img_a_version);
    } else {
        bctl->img_a_version = 0;
        bctl->img_a_crc = 0;
        eos_boot_log_append(EOS_LOG_IMAGE_INVALID, EOS_SLOT_A, 0);
    }

    if (eos_slot_is_valid(EOS_SLOT_B)) {
        eos_image_header_t hdr;
        if (eos_slot_get_header(EOS_SLOT_B, &hdr) == EOS_OK) {
            bctl->img_b_version = hdr.image_version;
            uint32_t crc;
            memcpy(&crc, hdr.hash, sizeof(crc));
            bctl->img_b_crc = crc;
        }
        eos_boot_log_append(EOS_LOG_IMAGE_VALID, EOS_SLOT_B,
                            bctl->img_b_version);
    } else {
        bctl->img_b_version = 0;
        bctl->img_b_crc = 0;
        eos_boot_log_append(EOS_LOG_IMAGE_INVALID, EOS_SLOT_B, 0);
    }

    return EOS_OK;
}
