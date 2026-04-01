// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file eos_board_registry.h
 * @brief Board registry — runtime multi-hardware selection
 *
 * Allows multiple board ports to be compiled into a single binary.
 * Each board self-registers via EBOOT_REGISTER_BOARD(). At boot time,
 * the registry can auto-detect the active board or select by name.
 *
 * Usage:
 *   // In board_stm32f4.c — self-registration at file scope:
 *   EBOOT_REGISTER_BOARD(stm32f4, board_get_ops);
 *
 *   // In main.c — find and activate a board:
 *   const eos_board_info_t *info = eos_board_find("stm32f4");
 *   eos_hal_init(info->get_ops());
 *
 *   // Or auto-detect:
 *   const eos_board_info_t *info = eos_board_detect();
 */

#ifndef EOS_BOARD_REGISTRY_H
#define EOS_BOARD_REGISTRY_H

#include "eos_hal.h"

#ifdef __cplusplus
extern "C" {
#endif

#define EOS_MAX_BOARDS 16

typedef struct {
    const char *name;
    eos_platform_t platform;
    uint32_t board_id;
    const eos_board_ops_t *(*get_ops)(void);
    bool (*detect)(void);   /* Optional: returns true if this board is active */
} eos_board_info_t;

/**
 * Register a board at runtime. Called by EBOOT_REGISTER_BOARD or manually.
 */
int eos_board_register(const eos_board_info_t *info);

/**
 * Find a registered board by name.
 */
const eos_board_info_t *eos_board_find(const char *name);

/**
 * Auto-detect the active board by calling each board's detect() callback.
 * Returns the first board whose detect() returns true, or NULL.
 */
const eos_board_info_t *eos_board_detect(void);

/**
 * Get the number of registered boards.
 */
uint32_t eos_board_count(void);

/**
 * Get a registered board by index (0-based).
 */
const eos_board_info_t *eos_board_get(uint32_t index);

/**
 * Initialize the HAL with a named board.
 * Shortcut for: eos_hal_init(eos_board_find(name)->get_ops());
 */
int eos_board_activate(const char *name);

/**
 * Initialize the HAL with auto-detected board.
 */
int eos_board_activate_auto(void);

/* ---- Registration macro ----
 *
 * Place at file scope in each board_*.c:
 *   EBOOT_REGISTER_BOARD("stm32f4", EOS_PLATFORM_ARM_CM4, 0x0413,
 *                         board_get_ops, board_detect);
 *
 * Uses GCC constructor attribute to auto-register before main().
 */
#if defined(__GNUC__) || defined(__clang__)
#define EBOOT_REGISTER_BOARD(name_str, plat, id, ops_fn, detect_fn)     \
    static const eos_board_info_t _board_info_##ops_fn = {              \
        .name     = name_str,                                           \
        .platform = plat,                                               \
        .board_id = id,                                                 \
        .get_ops  = ops_fn,                                             \
        .detect   = detect_fn,                                          \
    };                                                                  \
    __attribute__((constructor))                                         \
    static void _board_register_##ops_fn(void) {                        \
        eos_board_register(&_board_info_##ops_fn);                      \
    }
#else
/* For MSVC or compilers without constructor: manual registration needed */
#define EBOOT_REGISTER_BOARD(name_str, plat, id, ops_fn, detect_fn)     \
    static const eos_board_info_t _board_info_##ops_fn = {              \
        .name     = name_str,                                           \
        .platform = plat,                                               \
        .board_id = id,                                                 \
        .get_ops  = ops_fn,                                             \
        .detect   = detect_fn,                                          \
    };
#endif

#ifdef __cplusplus
}
#endif

#endif /* EOS_BOARD_REGISTRY_H */
