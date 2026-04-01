// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file eos_hal.h
 * @brief Hardware Abstraction Layer for eBootloader
 *
 * Board-agnostic interface for flash, watchdog, UART, reset,
 * and jump operations. Each target board provides its own
 * implementation of eos_board_ops_t.
 */

#ifndef EOS_HAL_H
#define EOS_HAL_H

#include "eos_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ---------------- Board Operations ---------------- */

typedef struct {
    /* Memory map */
    uint32_t flash_base;
    uint32_t flash_size;
    uint32_t slot_a_addr;
    uint32_t slot_a_size;
    uint32_t slot_b_addr;
    uint32_t slot_b_size;
    uint32_t recovery_addr;
    uint32_t recovery_size;
    uint32_t bootctl_addr;
    uint32_t bootctl_backup_addr;
    uint32_t log_addr;
    uint32_t app_vector_offset;

    /* Flash operations */
    int (*flash_read)(uint32_t addr, void *buf, size_t len);
    int (*flash_write)(uint32_t addr, const void *buf, size_t len);
    int (*flash_erase)(uint32_t addr, size_t len);

    /* Watchdog */
    void (*watchdog_init)(uint32_t timeout_ms);
    void (*watchdog_feed)(void);

    /* Reset */
    eos_reset_reason_t (*get_reset_reason)(void);
    void (*system_reset)(void);

    /* Recovery pin */
    bool (*recovery_pin_asserted)(void);

    /* Jump / handoff */
    void (*jump)(uint32_t vector_addr);

    /* UART (for recovery transport) */
    int (*uart_init)(uint32_t baud);
    int (*uart_send)(const void *buf, size_t len);
    int (*uart_recv)(void *buf, size_t len, uint32_t timeout_ms);

    /* Timing */
    uint32_t (*get_tick_ms)(void);

    /* Interrupt control */
    void (*disable_interrupts)(void);
    void (*enable_interrupts)(void);
    void (*deinit_peripherals)(void);
} eos_board_ops_t;

/* ---------------- Global Board Handle ---------------- */

/**
 * @brief Register board operations.
 * Must be called before any HAL function is used.
 * @param ops  Pointer to board operations (must remain valid).
 */
void eos_hal_init(const eos_board_ops_t *ops);

/**
 * @brief Get the registered board operations.
 * @return Pointer to the active board ops, or NULL if not initialized.
 */
const eos_board_ops_t *eos_hal_get_ops(void);

/* ---------------- HAL Convenience Functions ---------------- */

int   eos_hal_flash_read(uint32_t addr, void *buf, size_t len);
int   eos_hal_flash_write(uint32_t addr, const void *buf, size_t len);
int   eos_hal_flash_erase(uint32_t addr, size_t len);

void  eos_hal_watchdog_init(uint32_t timeout_ms);
void  eos_hal_watchdog_feed(void);

eos_reset_reason_t eos_hal_get_reset_reason(void);
void  eos_hal_system_reset(void);

bool  eos_hal_recovery_pin_asserted(void);

void  eos_hal_jump(uint32_t vector_addr);

int   eos_hal_uart_init(uint32_t baud);
int   eos_hal_uart_send(const void *buf, size_t len);
int   eos_hal_uart_recv(void *buf, size_t len, uint32_t timeout_ms);

uint32_t eos_hal_get_tick_ms(void);

void  eos_hal_disable_interrupts(void);
void  eos_hal_enable_interrupts(void);
void  eos_hal_deinit_peripherals(void);

/**
 * @brief Get the flash address for a given slot.
 * @param slot  Slot identifier.
 * @return Flash address of the slot, or 0 if invalid.
 */
uint32_t eos_hal_slot_addr(eos_slot_t slot);

/**
 * @brief Get the size of a given slot.
 * @param slot  Slot identifier.
 * @return Size in bytes, or 0 if invalid.
 */
uint32_t eos_hal_slot_size(eos_slot_t slot);

/* ---------------- Convenience Aliases ---------------- */

#define eos_hal_uart_write(port, data, len) eos_hal_uart_send(data, len)
#define eos_hal_uart_read(port, data, len, timeout) eos_hal_uart_recv(data, len, timeout)
#define eos_hal_disable_irqs()  eos_hal_disable_interrupts()
#define eos_hal_enable_irqs()   eos_hal_enable_interrupts()

static inline void eos_hal_set_msp(uint32_t addr) {
#if defined(__ARM_ARCH_PROFILE) && (__ARM_ARCH_PROFILE == 'M')
    __asm volatile ("MSR MSP, %0" : : "r" (addr));
#elif defined(__ARM_ARCH_PROFILE) && (__ARM_ARCH_PROFILE == 'R')
    __asm volatile ("MOV SP, %0" : : "r" (addr));
#elif defined(__aarch64__)
    __asm volatile ("MOV SP, %0" : : "r" ((uint64_t)addr));
#elif defined(__ARM_ARCH) && (__ARM_ARCH <= 7)
    __asm volatile ("MOV SP, %0" : : "r" (addr));
#elif defined(__riscv)
    __asm volatile ("mv sp, %0" : : "r" (addr));
#else
    (void)addr;
#endif
}

typedef enum {
    EOS_PLATFORM_ARM_CM0   = 0,
    EOS_PLATFORM_ARM_CM3   = 1,
    EOS_PLATFORM_ARM_CM4   = 2,
    EOS_PLATFORM_ARM_CM7   = 3,
    EOS_PLATFORM_ARM_CM33  = 4,
    EOS_PLATFORM_ARM_CA53  = 5,
    EOS_PLATFORM_ARM_CA72  = 6,
    EOS_PLATFORM_ARM_R5F   = 7,
    EOS_PLATFORM_RISCV32   = 8,
    EOS_PLATFORM_RISCV64   = 9,
    EOS_PLATFORM_X86       = 10,
    EOS_PLATFORM_X86_64    = 11,
    EOS_PLATFORM_XTENSA    = 12,
    EOS_PLATFORM_POWERPC   = 13,
    EOS_PLATFORM_SPARC     = 14,
    EOS_PLATFORM_M68K      = 15,
    EOS_PLATFORM_SH4       = 16,
    EOS_PLATFORM_MN103     = 17,
    EOS_PLATFORM_V850      = 18,
    EOS_PLATFORM_FRV       = 19,
    EOS_PLATFORM_H8300     = 20,
    EOS_PLATFORM_STRONGARM = 21,
    EOS_PLATFORM_XSCALE    = 22,
    EOS_PLATFORM_MIPS      = 23,
} eos_platform_t;

#ifdef __cplusplus
}
#endif
#endif /* EOS_HAL_H */
