# Cortex-R5 Safety Demo

Bare-metal firmware example for **TMS570LC43x / RM57Lx** Cortex-R5F safety MCUs.

Demonstrates R5-specific patterns that differ from Cortex-M examples:

| Feature | Cortex-M (STM32) | Cortex-R5 (TMS570) |
|---------|-------------------|--------------------|
| Instruction set | Thumb-2 (`-mthumb`) | ARM mode (no `-mthumb`) |
| Tick timer | SysTick | RTI Compare 0 |
| Interrupt control | `cpsid i` (IRQ only) | `cpsid if` (IRQ + FIQ) |
| Watchdog | IWDG (simple reload) | RTI DWD (windowed, key sequence) |
| UART | USART peripheral | SCI module |
| Vector table | Address table + MSP | Branch instruction table |
| Startup | Load MSP from vector[0] | Direct branch to reset handler |

## Hardware Target

- **TMS570LC4357** — dual Cortex-R5F in lockstep, 300 MHz, 4 MB flash, 256 KB RAM
- **RM57L843** — pin-compatible variant
- Any TMS570-class Cortex-R5F with SCI, RTI, DCAN, ESM

## What's Included

```
cortex_r5_safety/
├── build.yaml              # ebuild project config
├── linker/
│   └── tms570_app.ld       # Linker script (Flash slot A + SRAM)
├── include/
│   └── app_config.h        # Peripheral base addresses, timing, safety flags
└── src/
    ├── main.c              # RTI watchdog, SCI UART, DCAN heartbeat, ESM check
    └── r5_startup.c        # ARM vector table + C runtime init
```

## Build

```bash
# Via ebuild:
cd examples/cortex_r5_safety
ebuild build

# Or directly with GCC:
arm-none-eabi-gcc -mcpu=cortex-r5 -mfloat-abi=hard -mfpu=vfpv3-d16 -Os \
    -Iinclude -T linker/tms570_app.ld -nostartfiles \
    src/main.c src/r5_startup.c -o r5_safety_demo.elf

arm-none-eabi-objcopy -O binary r5_safety_demo.elf r5_safety_demo.bin
arm-none-eabi-size r5_safety_demo.elf
```

## Flash

```bash
# TI Code Composer Studio (CCS) UniFlash:
dslite.sh --config=TMS570LC4357.ccxml --flash r5_safety_demo.bin

# OpenOCD with XDS110:
openocd -f interface/xds110.cfg -f target/tms570.cfg \
    -c "program r5_safety_demo.elf verify reset exit"

# Or use the JTAG debug probe in your IDE (CCS, IAR, Lauterbach).
```

## Memory Map

Addresses match `eboot/boards/cortex_r5/board_cortex_r5.h`:

| Region | Address | Size | Usage |
|--------|---------|------|-------|
| ATCM | 0x00000000 | 64K | Vectors + stage-0 code |
| BTCM | 0x00080000 | 64K | Fast data / stack |
| Flash | 0x00200000 | 2 MB | eboot + application |
| **Slot A** | **0x00210000** | **448K** | **This firmware** |
| RAM | 0x08000000 | 256K | Application SRAM |

## Key Patterns in main.c

- **DWD watchdog**: `RTI_DWDPRLD` + `RTI_DWDCTRL` to enable, two-key sequence (`0xE51A` then `0xA35C`) to feed
- **SCI UART**: `SCI_GCR0/1`, `SCI_BRS` for baud, `SCI_TD/RD` for TX/RX, `SCI_FLR` for status
- **ESM check**: Read `ESM_SR1` for latched errors, W1C to clear, `ESM_EKR` to reset error pin
- **DCAN heartbeat**: Periodic CAN frame via IF1 registers (message object 1)
- **Interrupt guards**: `cpsid if` / `cpsie if` disable/enable both IRQ and FIQ

## Next Steps

- Add RTI Compare 0 interrupt setup to drive `tick_ms`
- Connect to eboot for secure boot + OTA via `eos_hal_init()`
- Add ECC scrubbing for SRAM safety (see `eboot/core/ecc_scrub.c`)
- Add lockstep compare error handling via ESM channel 2
