// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file eos_multicore.h
 * @brief Multicore and multiprocessor boot support
 *
 * Provides APIs for:
 * - SMP: Bringing up secondary cores on symmetric multiprocessor systems
 * - AMP: Booting different firmware images on different cores
 * - Heterogeneous: Managing mixed-architecture cores (e.g. Cortex-R5F + Cortex-A53)
 *
 * Platform-specific methods:
 * - ARM: PSCI (Power State Coordination Interface)
 * - RISC-V: HSM SBI extension (Hart State Management)
 * - x86: SIPI (Startup Inter-Processor Interrupt)
 * - ESP32: RTC register release for APP_CPU
 *
 * Usage (SMP — bring up secondary core running same firmware):
 *   eos_core_config_t core1 = {
 *       .core_id    = 1,
 *       .entry_addr = 0x08020000,
 *       .stack_addr = 0x20010000,
 *       .mode       = EOS_CORE_SMP,
 *   };
 *   eos_multicore_start(&core1);
 *
 * Usage (AMP — boot different firmware on each core):
 *   eos_core_config_t r5 = {
 *       .core_id    = 0,
 *       .arch       = EOS_ARCH_ARM_R5,
 *       .entry_addr = 0x00000000,
 *       .stack_addr = 0x00040000,
 *       .image_slot = EOS_SLOT_A,
 *       .mode       = EOS_CORE_AMP,
 *   };
 *   eos_core_config_t a53 = {
 *       .core_id    = 1,
 *       .arch       = EOS_ARCH_ARM_A53,
 *       .entry_addr = 0x80000000,
 *       .stack_addr = 0x80100000,
 *       .image_slot = EOS_SLOT_B,
 *       .mode       = EOS_CORE_AMP,
 *   };
 *   eos_multicore_start(&r5);
 *   eos_multicore_start(&a53);
 */

#ifndef EOS_MULTICORE_H
#define EOS_MULTICORE_H

#include "eos_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================
 * Core Architecture Identifiers
 * ============================================================ */

typedef enum {
    EOS_ARCH_ARM_M4    = 0,
    EOS_ARCH_ARM_M7    = 1,
    EOS_ARCH_ARM_R5    = 2,
    EOS_ARCH_ARM_A53   = 3,
    EOS_ARCH_ARM_A72   = 4,
    EOS_ARCH_RISCV32   = 5,
    EOS_ARCH_RISCV64   = 6,
    EOS_ARCH_XTENSA    = 7,
    EOS_ARCH_X86_64    = 8,
    EOS_ARCH_SAME_AS_PRIMARY = 0xFF,
} eos_core_arch_t;

/* ============================================================
 * Core Boot Mode
 * ============================================================ */

typedef enum {
    EOS_CORE_SMP  = 0,   /* Symmetric — same firmware, shared address space */
    EOS_CORE_AMP  = 1,   /* Asymmetric — different firmware per core */
    EOS_CORE_LOCK = 2,   /* Lockstep — safety mode, cores run identical code */
} eos_core_mode_t;

/* ============================================================
 * Core State
 * ============================================================ */

typedef enum {
    EOS_CORE_STATE_OFF       = 0,
    EOS_CORE_STATE_STARTING  = 1,
    EOS_CORE_STATE_RUNNING   = 2,
    EOS_CORE_STATE_STOPPED   = 3,
    EOS_CORE_STATE_ERROR     = 4,
    EOS_CORE_STATE_SUSPENDED = 5,
} eos_core_state_t;

/* ============================================================
 * Start Method — how the secondary core is released
 * ============================================================ */

typedef enum {
    EOS_START_AUTO     = 0,    /* Auto-detect from platform */
    EOS_START_PSCI     = 1,    /* ARM PSCI CPU_ON */
    EOS_START_SBI_HSM  = 2,    /* RISC-V SBI Hart State Management */
    EOS_START_SIPI     = 3,    /* x86 Startup IPI */
    EOS_START_REG      = 4,    /* Direct register write (ESP32, custom) */
    EOS_START_MAILBOX  = 5,    /* Shared-memory mailbox handshake */
} eos_core_start_method_t;

/* ============================================================
 * Per-Core Configuration
 * ============================================================ */

#define EOS_MAX_CORES 8

typedef struct {
    uint8_t  core_id;                /* Logical core index (0 = primary) */
    eos_core_arch_t arch;            /* Core architecture (or SAME_AS_PRIMARY) */
    eos_core_mode_t mode;            /* SMP / AMP / Lockstep */
    eos_core_start_method_t method;  /* How to start this core */
    eos_core_state_t state;          /* Current state (managed internally) */

    uint32_t entry_addr;             /* Entry point address */
    uint32_t stack_addr;             /* Initial stack pointer */
    uint32_t stack_size;             /* Stack size in bytes */

    /* AMP mode: boot a different firmware image */
    eos_slot_t image_slot;           /* Firmware slot (AMP only) */
    uint32_t   image_load_addr;      /* Load address for AMP image */

    /* Memory isolation */
    uint32_t mem_base;               /* Start of this core's memory region */
    uint32_t mem_size;               /* Size of this core's memory region */
    bool     mpu_enabled;            /* Enable MPU for this core */

    /* IPC */
    uint32_t mailbox_addr;           /* Shared mailbox address for inter-core comm */
    uint32_t mailbox_size;           /* Mailbox region size */

    /* Context (opaque, passed to entry point) */
    void *boot_arg;

    /* Platform-specific extension */
    void *platform_data;
} eos_core_config_t;

/* ============================================================
 * Multicore Boot Operations (provided by board port)
 * ============================================================ */

typedef struct {
    int  (*start_core)(const eos_core_config_t *cfg);
    int  (*stop_core)(uint8_t core_id);
    int  (*reset_core)(uint8_t core_id);
    eos_core_state_t (*get_core_state)(uint8_t core_id);
    int  (*send_ipi)(uint8_t core_id, uint32_t message);
    uint8_t (*get_core_count)(void);
    uint8_t (*get_current_core)(void);
} eos_multicore_ops_t;

/* ============================================================
 * Multicore API
 * ============================================================ */

/**
 * Initialize multicore subsystem and register platform ops.
 */
int eos_multicore_init(const eos_multicore_ops_t *ops);

/**
 * Get the number of cores available on this platform.
 */
uint8_t eos_multicore_count(void);

/**
 * Get the ID of the currently executing core.
 */
uint8_t eos_multicore_current(void);

/**
 * Start a secondary core with the given configuration.
 * For SMP: core runs from entry_addr with stack_addr.
 * For AMP: core loads and runs firmware from image_slot.
 */
int eos_multicore_start(const eos_core_config_t *cfg);

/**
 * Stop a running secondary core.
 */
int eos_multicore_stop(uint8_t core_id);

/**
 * Reset a secondary core (stop + restart).
 */
int eos_multicore_reset(uint8_t core_id);

/**
 * Get the state of a specific core.
 */
eos_core_state_t eos_multicore_get_state(uint8_t core_id);

/**
 * Send an inter-processor interrupt / message to a core.
 */
int eos_multicore_send_ipi(uint8_t core_id, uint32_t message);

/**
 * Boot all configured cores from a core config array.
 * Starts cores in order of core_id.
 */
int eos_multicore_boot_all(const eos_core_config_t *configs, uint8_t count);

/**
 * Wait for a core to reach a specific state (with timeout).
 */
int eos_multicore_wait_state(uint8_t core_id, eos_core_state_t target,
                              uint32_t timeout_ms);

/**
 * Convenience: configure and start a secondary core (SMP mode).
 */
int eos_multicore_start_smp(uint8_t core_id, uint32_t entry_addr,
                             uint32_t stack_addr);

/**
 * Convenience: configure and start a secondary core (AMP mode)
 * with firmware from a specific slot.
 */
int eos_multicore_start_amp(uint8_t core_id, eos_slot_t slot,
                             eos_core_arch_t arch);

#ifdef __cplusplus
}
#endif

#endif /* EOS_MULTICORE_H */
