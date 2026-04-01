// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file jump_stage1.c
 * @brief Stage-0 jump to Stage-1 (E-Boot)
 *
 * Performs the clean handoff from stage-0 to stage-1.
 * Disables interrupts, deinitializes peripherals, and
 * branches to the stage-1 vector table.
 */

#include "eos_hal.h"
#include "eos_bootctl.h"

/* Forward declarations */
extern void ebldr_watchdog_init(void);
extern void ebldr_watchdog_feed(void);
extern bool ebldr_recovery_triggered(const eos_bootctl_t *bctl);
extern int  eos_recovery_enter(eos_bootctl_t *bctl);

/* Forward declarations from boot_log */
extern void eos_boot_log_append(uint32_t event, uint32_t slot, uint32_t detail);

/**
 * @brief Stage-0 main entry point.
 *
 * Called after hw_init_minimal(). Loads boot control block,
 * checks recovery triggers, and jumps to stage-1.
 */
void ebldr_stage0_main(void)
{
    eos_bootctl_t bctl;

    /* Initialize watchdog */
    ebldr_watchdog_init();
    ebldr_watchdog_feed();

    /* Load boot control block */
    int rc = eos_bootctl_load(&bctl);
    (void)rc; /* defaults applied if both copies corrupt */

    /* Record reset reason */
    bctl.last_reset_reason = eos_hal_get_reset_reason();

    /* Log boot start */
    eos_boot_log_append(EOS_LOG_BOOT_START, EOS_SLOT_NONE,
                        bctl.last_reset_reason);

    /* Check for recovery triggers */
    if (ebldr_recovery_triggered(&bctl)) {
        eos_recovery_enter(&bctl);
        /* Does not return unless recovery instructs a reboot */
    }

    ebldr_watchdog_feed();

    /* Jump to stage-1 (E-Boot) */
    const eos_board_ops_t *ops = eos_hal_get_ops();
    if (ops && ops->jump) {
        /* Stage-1 is located immediately after stage-0 in flash */
        eos_hal_disable_interrupts();
        eos_hal_deinit_peripherals();
        ops->jump(ops->flash_base + ops->app_vector_offset);
    }

    /* If jump fails, enter recovery */
    eos_recovery_enter(&bctl);
}
