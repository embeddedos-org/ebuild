// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file multicore.c
 * @brief Multicore boot — core management, SMP/AMP/lockstep dispatch
 *
 * Platform-agnostic orchestration layer. Actual core bring-up
 * is delegated to eos_multicore_ops_t provided by the board port.
 */

#include "eos_multicore.h"
#include "eos_hal.h"
#include "eos_image.h"
#include <string.h>

static const eos_multicore_ops_t *mc_ops = NULL;
static eos_core_config_t core_table[EOS_MAX_CORES];
static uint8_t registered_cores = 0;
static bool mc_initialized = false;

int eos_multicore_init(const eos_multicore_ops_t *ops)
{
    if (!ops) return EOS_ERR_INVALID;

    mc_ops = ops;
    memset(core_table, 0, sizeof(core_table));
    registered_cores = 0;
    mc_initialized = true;

    /* Mark core 0 (primary) as running */
    core_table[0].core_id = 0;
    core_table[0].state = EOS_CORE_STATE_RUNNING;
    core_table[0].arch = EOS_ARCH_SAME_AS_PRIMARY;
    core_table[0].mode = EOS_CORE_SMP;
    registered_cores = 1;

    return EOS_OK;
}

uint8_t eos_multicore_count(void)
{
    if (!mc_initialized || !mc_ops) return 1;
    if (mc_ops->get_core_count) return mc_ops->get_core_count();
    return 1;
}

uint8_t eos_multicore_current(void)
{
    if (!mc_initialized || !mc_ops) return 0;
    if (mc_ops->get_current_core) return mc_ops->get_current_core();
    return 0;
}

int eos_multicore_start(const eos_core_config_t *cfg)
{
    if (!cfg || !mc_initialized || !mc_ops) return EOS_ERR_INVALID;
    if (cfg->core_id == 0) return EOS_ERR_INVALID; /* can't restart primary */
    if (cfg->core_id >= EOS_MAX_CORES) return EOS_ERR_INVALID;
    if (cfg->entry_addr == 0) return EOS_ERR_INVALID;

    /* For AMP mode, verify the firmware image exists in the slot */
    if (cfg->mode == EOS_CORE_AMP && cfg->image_slot != EOS_SLOT_NONE) {
        uint32_t slot_addr = eos_hal_slot_addr(cfg->image_slot);
        if (slot_addr == 0) return EOS_ERR_NO_IMAGE;

        eos_image_header_t hdr;
        int rc = eos_image_parse_header(slot_addr, &hdr);
        if (rc != EOS_OK) return rc;
    }

    /* Store config */
    core_table[cfg->core_id] = *cfg;
    core_table[cfg->core_id].state = EOS_CORE_STATE_STARTING;

    if (cfg->core_id >= registered_cores) {
        registered_cores = cfg->core_id + 1;
    }

    /* Delegate to platform */
    if (!mc_ops->start_core) return EOS_ERR_GENERIC;

    int rc = mc_ops->start_core(cfg);
    if (rc != EOS_OK) {
        core_table[cfg->core_id].state = EOS_CORE_STATE_ERROR;
        return rc;
    }

    core_table[cfg->core_id].state = EOS_CORE_STATE_RUNNING;
    return EOS_OK;
}

int eos_multicore_stop(uint8_t core_id)
{
    if (!mc_initialized || !mc_ops) return EOS_ERR_INVALID;
    if (core_id == 0) return EOS_ERR_INVALID;
    if (core_id >= EOS_MAX_CORES) return EOS_ERR_INVALID;

    if (mc_ops->stop_core) {
        int rc = mc_ops->stop_core(core_id);
        if (rc != EOS_OK) return rc;
    }

    core_table[core_id].state = EOS_CORE_STATE_STOPPED;
    return EOS_OK;
}

int eos_multicore_reset(uint8_t core_id)
{
    if (!mc_initialized || !mc_ops) return EOS_ERR_INVALID;
    if (core_id == 0) return EOS_ERR_INVALID;
    if (core_id >= EOS_MAX_CORES) return EOS_ERR_INVALID;

    if (mc_ops->reset_core) {
        return mc_ops->reset_core(core_id);
    }

    /* Fallback: stop + restart */
    int rc = eos_multicore_stop(core_id);
    if (rc != EOS_OK) return rc;

    return eos_multicore_start(&core_table[core_id]);
}

eos_core_state_t eos_multicore_get_state(uint8_t core_id)
{
    if (!mc_initialized || core_id >= EOS_MAX_CORES) {
        return EOS_CORE_STATE_OFF;
    }

    if (mc_ops && mc_ops->get_core_state) {
        return mc_ops->get_core_state(core_id);
    }

    return core_table[core_id].state;
}

int eos_multicore_send_ipi(uint8_t core_id, uint32_t message)
{
    if (!mc_initialized || !mc_ops) return EOS_ERR_INVALID;
    if (core_id >= EOS_MAX_CORES) return EOS_ERR_INVALID;

    if (mc_ops->send_ipi) {
        return mc_ops->send_ipi(core_id, message);
    }

    /* Fallback: write to mailbox if configured */
    if (core_table[core_id].mailbox_addr != 0) {
        return eos_hal_flash_write(core_table[core_id].mailbox_addr,
                                    &message, sizeof(message));
    }

    return EOS_ERR_GENERIC;
}

int eos_multicore_boot_all(const eos_core_config_t *configs, uint8_t count)
{
    if (!configs || count == 0) return EOS_ERR_INVALID;

    int errors = 0;
    for (uint8_t i = 0; i < count; i++) {
        if (configs[i].core_id == 0) continue; /* skip primary */

        int rc = eos_multicore_start(&configs[i]);
        if (rc != EOS_OK) errors++;
    }

    return errors == 0 ? EOS_OK : EOS_ERR_GENERIC;
}

int eos_multicore_wait_state(uint8_t core_id, eos_core_state_t target,
                              uint32_t timeout_ms)
{
    if (!mc_initialized) return EOS_ERR_INVALID;
    if (core_id >= EOS_MAX_CORES) return EOS_ERR_INVALID;

    uint32_t start = eos_hal_get_tick_ms();

    while (1) {
        eos_core_state_t current = eos_multicore_get_state(core_id);
        if (current == target) return EOS_OK;
        if (current == EOS_CORE_STATE_ERROR) return EOS_ERR_GENERIC;

        uint32_t elapsed = eos_hal_get_tick_ms() - start;
        if (elapsed >= timeout_ms) return EOS_ERR_TIMEOUT;

        eos_hal_watchdog_feed();
    }
}

int eos_multicore_start_smp(uint8_t core_id, uint32_t entry_addr,
                             uint32_t stack_addr)
{
    eos_core_config_t cfg;
    memset(&cfg, 0, sizeof(cfg));
    cfg.core_id    = core_id;
    cfg.arch       = EOS_ARCH_SAME_AS_PRIMARY;
    cfg.mode       = EOS_CORE_SMP;
    cfg.method     = EOS_START_AUTO;
    cfg.entry_addr = entry_addr;
    cfg.stack_addr = stack_addr;
    cfg.stack_size = 4096;
    cfg.image_slot = EOS_SLOT_NONE;

    return eos_multicore_start(&cfg);
}

int eos_multicore_start_amp(uint8_t core_id, eos_slot_t slot,
                             eos_core_arch_t arch)
{
    uint32_t slot_addr = eos_hal_slot_addr(slot);
    if (slot_addr == 0) return EOS_ERR_NO_IMAGE;

    /* Parse header to get entry point */
    eos_image_header_t hdr;
    int rc = eos_image_parse_header(slot_addr, &hdr);
    if (rc != EOS_OK) return rc;

    eos_core_config_t cfg;
    memset(&cfg, 0, sizeof(cfg));
    cfg.core_id        = core_id;
    cfg.arch           = arch;
    cfg.mode           = EOS_CORE_AMP;
    cfg.method         = EOS_START_AUTO;
    cfg.entry_addr     = hdr.entry_addr;
    cfg.stack_addr     = 0; /* firmware manages its own stack */
    cfg.image_slot     = slot;
    cfg.image_load_addr = hdr.load_addr;

    return eos_multicore_start(&cfg);
}
