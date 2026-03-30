/**
 * TMS570 Application Linker Script
 *
 * Runs from Flash Slot A (0x00210000) with data in SRAM.
 * Addresses match eboot/boards/cortex_r5/board_cortex_r5.h.
 *
 * Flash Slot A: 448K at 0x00210000
 * SRAM:         256K at 0x08000000
 */

MEMORY
{
    FLASH (rx)  : ORIGIN = 0x00210000, LENGTH = 448K
    RAM   (rwx) : ORIGIN = 0x08000000, LENGTH = 256K
}

_estack = ORIGIN(RAM) + LENGTH(RAM);

SECTIONS
{
    .vectors :
    {
        . = ALIGN(4);
        KEEP(*(.vectors))
        . = ALIGN(4);
    } > FLASH

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
