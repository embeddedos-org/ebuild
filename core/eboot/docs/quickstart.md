# eboot Quickstart

Build and flash the eboot bootloader for your board in 3 commands.

---

## What is eboot?

eboot is a multi-stage bootloader that provides:
- **Staged boot:** Stage-0 (minimal init) → Stage-1 (full bootloader)
- **Secure boot:** RSA/ECC signature verification
- **A/B slot management:** Dual firmware slots for safe OTA updates
- **Recovery:** Rollback to known-good firmware on failure

## Prerequisites

```bash
# ARM toolchain (for ARM targets)
sudo apt install gcc-arm-none-eabi cmake
```

---

## Build in 3 Commands

```bash
cd EoS/eboot

# Configure for your board
cmake -B build -DEBLDR_BOARD=nrf52

# Build
cmake --build build

# Flash (nRF52 example)
nrfjprog --program build/eboot.hex --chiperase --verify
nrfjprog --reset
```

## Supported Boards

| Board | Architecture | Flash Tool |
|-------|-------------|-----------|
| `nrf52` | ARM Cortex-M4F | nrfjprog / J-Link |
| `stm32h7` | ARM Cortex-M7 | OpenOCD / ST-Link |
| `stm32f4` | ARM Cortex-M4F | OpenOCD / ST-Link |
| `rpi4` | ARM64 Cortex-A72 | SD card |
| `x86` | x86_64 | BIOS/UEFI |
| `sparc` | SPARC LEON3 | GRMON |

---

## Flash Layout

eboot organizes flash into regions. For a 512 KB flash (e.g., nRF52):

```
Address     Size    Region
---------   -----   ------------------
0x00000     16 KB   Stage-0 (first-stage loader)
0x04000     64 KB   Stage-1 (full bootloader)
0x14000     8 KB    Boot Control (2 x 4 KB blocks)
0x16000     212 KB  Slot A (primary firmware)
0x4B000     212 KB  Slot B (OTA update slot)
```

For larger flash devices, slot sizes scale proportionally.

## Generating Flash Layout Headers

```bash
cd EoS/ebuild
ebuild generate-boot ../eboot/configs/nrf52_boot.yaml --output-dir _generated
```

This produces:
- `eboot_flash_layout.h` — C header with flash region addresses and sizes
- `eboot_linker.ld` — Linker script for placing firmware in Slot A

## Signing Firmware Images

```bash
cd EoS/eboot/tools

# Generate a signing key (first time only)
python3 sign_image.py --generate-key my-key.pem

# Sign a firmware binary
python3 sign_image.py --key my-key.pem --input firmware.bin --output signed.bin
```

## Boot Flow

```
Power On
   |
   v
Stage-0 (16 KB)
   |-- Minimal hardware init (clock, memory)
   |-- Verify Stage-1 integrity
   |-- Jump to Stage-1
   v
Stage-1 (64 KB)
   |-- Full hardware init
   |-- Read boot control block
   |-- Verify firmware signature (RSA/ECC)
   |-- Select active slot (A or B)
   |-- Jump to application
   v
Application (Slot A or B)
   |-- eos_hal_init()
   |-- Your firmware runs here
```

## Next Steps

- [Integration Guide](../../docs/integration-guide.md) — how eboot works with eos and ebuild
- [Security Documentation](security.md) — key management, chain of trust
- [Memory Map](memory-map.md) — detailed flash and RAM layout
- [Update Flow](update-flow.md) — OTA update sequence diagram
