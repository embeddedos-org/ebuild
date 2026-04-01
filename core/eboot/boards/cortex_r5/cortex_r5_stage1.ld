/**
 * Cortex-R5F Linker Script for eBootloader Stage-1
 *
 * Stage-1 runs from Flash (after Stage-0 region) with
 * data in SRAM.
 *
 * Flash: 48K starting at 0x00204000 (after 16K stage-0)
 * RAM:   256K at 0x08000000
 */

MEMORY
{
    FLASH (rx)  : ORIGIN = 0x00204000, LENGTH = 48K
    RAM   (rwx) : ORIGIN = 0x08000000, LENGTH = 256K
}

_estack = ORIGIN(RAM) + LENGTH(RAM);

SECTIONS
{
    .text :
    {
        . = ALIGN(4);
        *(.text)
        *(.text*)
        *(.rodata)
        *(.rodata*)
        . = ALIGN(4);
        _etext = .;
    } > FLASH

    _sidata = LOADADDR(.data);

    .data :
    {
        . = ALIGN(4);
        _sdata = .;
        *(.data)
        *(.data*)
        . = ALIGN(4);
        _edata = .;
    } > RAM AT> FLASH

    .bss :
    {
        . = ALIGN(4);
        _sbss = .;
        *(.bss)
        *(.bss*)
        *(COMMON)
        . = ALIGN(4);
        _ebss = .;
    } > RAM
}
