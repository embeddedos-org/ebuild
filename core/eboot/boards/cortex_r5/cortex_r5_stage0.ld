/**
 * Cortex-R5F Linker Script for eBootloader Stage-0
 *
 * Stage-0 runs from ATCM (Tightly Coupled Memory) for
 * deterministic, zero-wait-state execution.
 *
 * ATCM: 64K code (0x00000000)
 * BTCM: 64K data (0x00080000)
 */

MEMORY
{
    ATCM  (rx)  : ORIGIN = 0x00000000, LENGTH = 64K
    BTCM  (rwx) : ORIGIN = 0x00080000, LENGTH = 64K
}

_estack = ORIGIN(BTCM) + LENGTH(BTCM);

SECTIONS
{
    .vectors :
    {
        . = ALIGN(4);
        KEEP(*(.vectors))
        . = ALIGN(4);
    } > ATCM

    .text :
    {
        . = ALIGN(4);
        *(.text)
        *(.text*)
        *(.rodata)
        *(.rodata*)
        . = ALIGN(4);
        _etext = .;
    } > ATCM

    _sidata = LOADADDR(.data);

    .data :
    {
        . = ALIGN(4);
        _sdata = .;
        *(.data)
        *(.data*)
        . = ALIGN(4);
        _edata = .;
    } > BTCM AT> ATCM

    .bss :
    {
        . = ALIGN(4);
        _sbss = .;
        *(.bss)
        *(.bss*)
        *(COMMON)
        . = ALIGN(4);
        _ebss = .;
    } > BTCM
}
