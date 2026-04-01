// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file reset_entry.c
 * @brief Stage-0 reset entry point
 *
 * First code to execute after hardware reset. Sets up the
 * initial stack pointer and branches to hw_init_minimal.
 * This file should remain as small as possible.
 */

#include "eos_hal.h"
#include <stdint.h>

/* Forward declarations */
extern void ebldr_hw_init_minimal(void);
extern void ebldr_stage0_main(void);

/* Minimal fault handlers */
static void default_handler(void)
{
    while (1) {
        /* Halt on unhandled fault */
    }
}

void NMI_Handler(void)        __attribute__((weak, alias("default_handler")));
void HardFault_Handler(void)  __attribute__((weak, alias("default_handler")));
void MemManage_Handler(void)  __attribute__((weak, alias("default_handler")));
void BusFault_Handler(void)   __attribute__((weak, alias("default_handler")));
void UsageFault_Handler(void) __attribute__((weak, alias("default_handler")));

/* Provided by linker script */
extern uint32_t _estack;
extern uint32_t _sdata, _edata, _sidata;
extern uint32_t _sbss, _ebss;

/**
 * @brief Reset handler — entry point from hardware reset vector.
 *
 * Copies .data from flash to RAM, zeros .bss, then enters
 * the stage-0 initialization sequence.
 */
void Reset_Handler(void)
{
    /* Copy .data section from flash to RAM */
    uint32_t *src = &_sidata;
    uint32_t *dst = &_sdata;
    while (dst < &_edata)
        *dst++ = *src++;

    /* Zero .bss section */
    dst = &_sbss;
    while (dst < &_ebss)
        *dst++ = 0;

    /* Enter stage-0 */
    ebldr_hw_init_minimal();
    ebldr_stage0_main();

    /* Should never reach here */
    while (1);
}

/**
 * @brief Minimal vector table for stage-0.
 *
 * Only includes reset + core fault vectors. The application
 * firmware will provide its own full vector table.
 */
__attribute__((section(".isr_vector"), used))
const uint32_t stage0_vector_table[] = {
    (uint32_t)&_estack,           /* Initial stack pointer */
    (uint32_t)Reset_Handler,       /* Reset handler */
    (uint32_t)NMI_Handler,         /* NMI */
    (uint32_t)HardFault_Handler,   /* Hard fault */
    (uint32_t)MemManage_Handler,   /* Memory management fault */
    (uint32_t)BusFault_Handler,    /* Bus fault */
    (uint32_t)UsageFault_Handler,  /* Usage fault */
};
