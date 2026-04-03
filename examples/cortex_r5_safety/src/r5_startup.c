/**
 * @file r5_startup.c
 * @brief Cortex-R5 minimal startup — ARM exception vectors + C runtime init
 *
 * Key differences from Cortex-M startup:
 *   - ARM exception vector table (not NVIC vector table)
 *   - Vectors are branch instructions, not addresses
 *   - No MSP load at offset 0 (Cortex-R sets SP in reset handler)
 *   - Must zero BSS and copy .data before calling main()
 */

#include <stdint.h>

/* Linker-provided symbols */
extern uint32_t _sidata;   /* .data load address (in flash) */
extern uint32_t _sdata;    /* .data start (in RAM) */
extern uint32_t _edata;    /* .data end (in RAM) */
extern uint32_t _sbss;     /* .bss start */
extern uint32_t _ebss;     /* .bss end */
extern uint32_t _estack;   /* top of stack */

extern int main(void);

/* ---- Default exception handlers ---- */

static void hang(void) { while (1) {} }

void __attribute__((weak)) undef_handler(void)    { hang(); }
void __attribute__((weak)) swi_handler(void)      { hang(); }
void __attribute__((weak)) prefetch_handler(void)  { hang(); }
void __attribute__((weak)) data_abort_handler(void){ hang(); }
void __attribute__((weak)) irq_handler(void)       { hang(); }
void __attribute__((weak)) fiq_handler(void)       { hang(); }

/* ---- Reset handler: C runtime init ---- */

void _reset_handler(void) __attribute__((naked, noreturn));
void _reset_handler(void)
{
    /* Set up supervisor-mode stack pointer */
    __asm volatile ("ldr sp, =_estack");

    /* Copy .data from flash to RAM */
    uint32_t *src = &_sidata;
    uint32_t *dst = &_sdata;
    while (dst < &_edata)
        *dst++ = *src++;

    /* Zero .bss */
    dst = &_sbss;
    while (dst < &_ebss)
        *dst++ = 0;

    main();

    hang();
}

/* ---- ARM exception vector table ----
 *
 * Cortex-R5 vectors at address 0x00000000 (or FLASH base via SCTLR[V]):
 *   0x00  Reset
 *   0x04  Undefined Instruction
 *   0x08  Software Interrupt (SWI/SVC)
 *   0x0C  Prefetch Abort
 *   0x10  Data Abort
 *   0x14  Reserved
 *   0x18  IRQ
 *   0x1C  FIQ
 */

void __attribute__((naked, section(".vectors"))) _vector_table(void)
{
    __asm volatile (
        "ldr pc, =_reset_handler    \n"
        "ldr pc, =undef_handler     \n"
        "ldr pc, =swi_handler       \n"
        "ldr pc, =prefetch_handler  \n"
        "ldr pc, =data_abort_handler\n"
        "nop                        \n"  /* Reserved */
        "ldr pc, =irq_handler       \n"
        "ldr pc, =fiq_handler       \n"
    );
}
