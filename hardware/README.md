# Hardware Design Intake

This folder is where hardware teams place design documents for ebuild's
EoS AI analyzer (`ebuild analyze`) to process.

## Required Files

| File | Description | Used By |
|---|---|---|
| `soc/datasheet.pdf` | MCU/SoC datasheet — memory map, clocks, peripherals | eos + eboot |
| `soc/trm.pdf` | Technical Reference Manual — registers, boot modes, MMU/MPU | eos + eboot |
| `board/schematic.pdf` | Board schematic — pin wiring, flash, PMIC, debug port | eos + eboot |
| `board/bom.xlsx` | Bill of Materials — exact part numbers, values | ebuild analyze |
| `boot/image_layout.yaml` | Partition/slot layout for bootloader | eboot |

## Optional Files

| File | Description |
|---|---|
| `soc/errata.pdf` | Known silicon bugs |
| `board/pinmap.xlsx` | Signal-to-pin mapping spreadsheet |
| `board/bringup.md` | Power-up sequence, debug notes, known issues |
| `storage/nor_flash.pdf` | SPI NOR/NAND flash datasheet |
| `storage/emmc.pdf` | eMMC/SD storage datasheet |
| `boot/boot_flow.md` | ROM → stage-0 → stage-1 → app handoff |
| `boot/secure_boot.md` | Signing, key provisioning, anti-rollback |
| `software/board.dts` | Device tree source |
| `software/linker.ld` | Linker script |
| `software/board_config.yaml` | Board config (EoS format) |
| `software/defconfig` | Kernel or RTOS defconfig |

## Usage

```bash
# Analyze hardware design from text
ebuild analyze "STM32H743 with 2MB flash, 1MB RAM, UART, SPI, CAN, motor control PWM"

# Analyze from a file
ebuild analyze --file hardware/board/bom.xlsx

# Analyze KiCad schematic
ebuild analyze --file hardware/board/schematic.kicad_sch

# Point to eos schemas for better accuracy
ebuild analyze --file hardware/board/bom.xlsx --eos-schemas ../eos/schemas/
```

## Output

The analyzer generates configs in `_generated/`:
- `board.yaml` — eos board definition
- `boot.yaml` — eboot flash layout + policy
- `build.yaml` — ebuild project config
- `eos_product_config.h` — C header with `EOS_ENABLE_*` flags
- `eboot_flash_layout.h` — C header with flash constants
- `eboot_memory.ld` — Linker script memory regions
- `eboot_config.cmake` — CMake definitions for eboot build
- `pack_image.sh` — Image packing + signing script
- `llm_prompt.txt` — Optional LLM prompt for deeper analysis
