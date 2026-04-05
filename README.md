# ⚙️ eBuild — EoS Embedded OS Build Tool

[![CI](https://github.com/embeddedos-org/ebuild/actions/workflows/ci.yml/badge.svg)](https://github.com/embeddedos-org/ebuild/actions/workflows/ci.yml)
[![Version](https://img.shields.io/github/v/tag/embeddedos-org/ebuild?label=version)](https://github.com/embeddedos-org/ebuild/releases/latest)

> **⚠️ Not Gentoo ebuilds.** This is the **EmbeddedOS Build Tool** — a unified build system for the EoS embedded OS. Not related to [Gentoo's ebuild format](https://wiki.gentoo.org/wiki/Ebuild).

**One clone, one build command — from hardware description to deployable firmware.**

`ebuild` orchestrates cross-compilation across multiple backends (CMake, Make, Ninja, Meson, Cargo, Kbuild), analyzes hardware schematics, generates board configs, and manages packages for 73+ embedded targets.

---

## Quick Start

### Prerequisites

- Python 3.8+
- GCC (host compiler)
- CMake 3.16+ and Ninja (installed automatically as pip deps)

### Install

```bash
git clone https://github.com/embeddedos-org/ebuild.git
cd ebuild
pip install -e .
ebuild --version
# ebuild, version 0.1.0
```

---

## Hands-On Examples (Try These Now!)

### Example 1: Build Hello World

```bash
cd examples/hello_world
ebuild info         # Show project targets and build order
ebuild build        # Compile with auto-detected ninja backend
./_build/hello      # Run it → "Hello from EoS Build System!"
```

### Example 2: Build Multi-Target (Library + Executable)

```bash
cd examples/multi_target
ebuild build        # Builds libmathlib.a then links myapp
./_build/myapp      # Run it → add=17, subtract=7, multiply=60, factorial=120
```

### Example 3: Analyze a Hardware Board File

Analyze a sample board YAML and auto-generate all config files:

```bash
cd /path/to/ebuild

# STM32H7 IoT Gateway (18 peripherals — UART, SPI, I2C, CAN, WiFi, BLE, ETH...)
ebuild analyze --file hardware/board/sample_iot_gateway.yaml --output-dir /tmp/iot_configs

# nRF52840 BLE Sensor Node (ultra-low-power, coin cell, BLE 5.0 Long Range)
ebuild analyze --file hardware/board/sample_ble_sensor.yaml --output-dir /tmp/ble_configs

# ESP32-S3 Smart Display (WiFi, LCD, touch, camera, audio)
ebuild analyze --file hardware/board/sample_esp32s3_display.yaml --output-dir /tmp/esp32_configs

# RISC-V Industrial Controller (CAN bus, RS485, 4-20mA, 24V DIN-rail)
ebuild analyze --file hardware/board/sample_riscv_industrial.yaml --output-dir /tmp/riscv_configs

# Raspberry Pi 4 Linux Gateway (Gigabit ETH, WiFi, 4GB RAM)
ebuild analyze --file hardware/board/sample_rpi4_gateway.yaml --output-dir /tmp/rpi4_configs
```

Each `analyze` command generates **9 files** in ~260ms:

| File | Purpose |
|------|---------|
| `board.yaml` | MCU, arch, core, clock, memory, peripherals |
| `boot.yaml` | Flash layout, A/B slots, signing policy |
| `build.yaml` | Toolchain and backend config |
| `eos_product_config.h` | C header with `#define EOS_ENABLE_*` for each peripheral |
| `eboot_flash_layout.h` | C header with flash addresses for eBoot bootloader |
| `eboot_memory.ld` | Linker script with memory regions |
| `eboot_config.cmake` | CMake definitions for eBoot |
| `pack_image.sh` | Image packing + signing script |
| `llm_prompt.txt` | Optional LLM enhancement prompt |

---

### Generated Files — Detailed Explanation

Here's what each file contains and how it's used, using `sample_stm32f4_sensor.kicad_sch` as an example:

#### 1. `board.yaml` — Hardware Board Description

**Who uses it:** EoS build system, device drivers, board support packages.

Describes the MCU, architecture, and every peripheral detected from your schematic. This is the "source of truth" for what hardware the firmware needs to support.

```yaml
board:
  name: stm32f4
  mcu: STM32F4
  family: STM32F4
  arch: arm
  core: cortex-m4
  vendor: ST
  clock_hz: 168000000
  memory:
    flash: 1048576     # 1MB
    ram: 196608        # 192KB
  peripherals:
  - name: BME280       # Detected from KiCad component U2
    type: i2c
    bus: i2c
  - name: W25Q128      # Detected from component U3
    type: spi
    bus: spi
  - name: SN65HVD230   # CAN transceiver U6
    type: can
  - name: UART
    type: uart
```

#### 2. `boot.yaml` — Bootloader Flash Layout

**Who uses it:** eBoot bootloader, OTA update system, factory provisioning tools.

Defines how the MCU's flash memory is partitioned for secure boot with A/B firmware slots. eBoot reads this to know where Stage-0, Stage-1, boot control blocks, and firmware slots live in flash.

```yaml
boot:
  board: stm32f4
  arch: arm
  flash_base: '0x08000000'        # STM32F4 flash starts here
  flash_size: 1048576              # 1MB total
  layout:
    stage0:                        # First-stage bootloader (runs from reset)
      offset: '0x00000000'
      size: 16384                  # 16KB
    stage1:                        # Boot manager (selects firmware slot)
      offset: '0x4000'
      size: 65536                  # 64KB
    bootctl_primary:               # Boot control block (active slot, attempt count)
      offset: '0x14000'
      size: 4096                   # 4KB
    bootctl_backup:                # Redundant copy (corruption protection)
      offset: '0x15000'
      size: 4096
    slot_a:                        # Firmware slot A (active)
      offset: '0x16000'
      size: 479232                 # ~468KB
    slot_b:                        # Firmware slot B (update target)
      offset: '0x8b000'
      size: 479232
  policy:
    max_boot_attempts: 3           # Rollback after 3 failed boots
    watchdog_timeout_ms: 5000      # 5-second watchdog
    require_signature: true        # Ed25519 signature required
    anti_rollback: true            # Monotonic counter prevents downgrades
  image:
    header_version: 1
    hash_algo: sha256
    sign_algo: ed25519
```

#### 3. `build.yaml` — Build Configuration

**Who uses it:** `ebuild build` command, CI/CD pipelines.

Tells ebuild how to compile the firmware: which backend (cmake), which toolchain (arm-none-eabi-gcc), and which EoS features to enable based on detected peripherals.

```yaml
project:
  name: stm32f4-firmware
  version: 0.1.0
backend: cmake
toolchain:
  compiler: gcc
  arch: arm
  prefix: arm-none-eabi           # Cross-compiler prefix
cmake:
  build_type: Release
  defines:
    EOS_PLATFORM: rtos
    EOS_ENABLE_I2C: 'ON'          # For BME280 sensor
    EOS_ENABLE_SPI: 'ON'          # For W25Q128 flash
    EOS_ENABLE_USB: 'ON'          # For CP2102N USB-UART
    EOS_ENABLE_CAN: 'ON'          # For SN65HVD230 CAN bus
    EOS_ENABLE_UART: 'ON'         # For debug console
```

#### 4. `eos_product_config.h` — C Feature Header

**Who uses it:** EoS firmware source code (`#include "eos_product_config.h"`).

A C header that the firmware includes to know what hardware is available. EoS drivers use these `#define`s to conditionally compile only the drivers your board actually needs.

```c
#ifndef EOS_GENERATED_CONFIG_H
#define EOS_GENERATED_CONFIG_H

#define EOS_PRODUCT_NAME    "stm32f4"
#define EOS_MCU             "STM32F4"
#define EOS_ARCH            "arm"
#define EOS_CORE            "cortex-m4"
#define EOS_VENDOR          "ST"
#define EOS_CLOCK_HZ         168000000
#define EOS_FLASH_SIZE       1048576
#define EOS_RAM_SIZE         196608

#define EOS_ENABLE_CAN               1
#define EOS_ENABLE_I2C               1
#define EOS_ENABLE_SPI               1
#define EOS_ENABLE_UART              1
#define EOS_ENABLE_USB               1

#endif
```

In your firmware code:
```c
#include "eos_product_config.h"

void app_init(void) {
#if EOS_ENABLE_I2C
    bme280_init();    // Only compiled if I2C detected on board
#endif
#if EOS_ENABLE_CAN
    can_bus_init();   // Only compiled if CAN detected
#endif
}
```

#### 5. `eboot_flash_layout.h` — Bootloader Flash Constants

**Who uses it:** eBoot bootloader C code (`#include "eboot_flash_layout.h"`).

Gives eBoot the exact memory addresses for each flash partition. Without this, the bootloader wouldn't know where to find firmware images or where to write OTA updates.

```c
#define EBOOT_FLASH_BASE        0x8000000    // Flash start
#define EBOOT_FLASH_SIZE        1048576      // 1MB total

#define EBOOT_STAGE0_OFFSET  0x0             // Stage-0 at flash start
#define EBOOT_STAGE0_ADDR    (0x8000000 + 0x0)
#define EBOOT_STAGE0_SIZE    16384           // 16KB

#define EBOOT_STAGE1_OFFSET  0x4000          // Stage-1 at 16KB
#define EBOOT_STAGE1_ADDR    (0x8000000 + 0x4000)
#define EBOOT_STAGE1_SIZE    65536           // 64KB

#define EBOOT_SLOT_A_OFFSET  0x16000         // Firmware slot A
#define EBOOT_SLOT_A_SIZE    479232          // ~468KB

#define EBOOT_SLOT_B_OFFSET  0x8b000         // Firmware slot B
#define EBOOT_SLOT_B_SIZE    479232

#define EBOOT_MAX_BOOT_ATTEMPTS 3
#define EBOOT_REQUIRE_SIGNATURE 1            // Ed25519 required
#define EBOOT_ANTI_ROLLBACK     1            // Version must increase
```

#### 6. `eboot_memory.ld` — Linker Script Memory Regions

**Who uses it:** GCC linker (passed via `-T eboot_memory.ld`).

Tells the linker exactly where each bootloader component lives in flash memory. The compiler uses this to place code at the correct addresses so Stage-0 runs from reset, Stage-1 runs after verification, etc.

```ld
MEMORY
{
  stage0          (rx)  : ORIGIN = 0x8000000,  LENGTH = 16384
  stage1          (rx)  : ORIGIN = 0x8004000,  LENGTH = 65536
  bootctl_primary (rw)  : ORIGIN = 0x8014000,  LENGTH = 4096
  bootctl_backup  (rw)  : ORIGIN = 0x8015000,  LENGTH = 4096
  slot_a          (rw)  : ORIGIN = 0x8016000,  LENGTH = 479232
  slot_b          (rw)  : ORIGIN = 0x808b000,  LENGTH = 479232
}
```

#### 7. `eboot_config.cmake` — CMake Build Definitions

**Who uses it:** CMake build system when building eBoot for this board.

Passes the board name, flash sizes, and security settings to CMake so eBoot compiles with the correct configuration for your specific board.

```cmake
set(EBLDR_BOARD "stm32f4")
set(EBLDR_FLASH_SIZE 1048576)
set(EBLDR_STAGE0_SIZE 16384)
set(EBLDR_STAGE1_SIZE 65536)
set(EBLDR_SLOT_A_SIZE 479232)
set(EBLDR_SLOT_B_SIZE 479232)
set(EBLDR_MAX_BOOT_ATTEMPTS 3)
set(EBLDR_REQUIRE_SIGNATURE ON)
```

#### 8. `pack_image.sh` — Firmware Packing Script

**Who uses it:** Build pipeline / CI — run after compiling firmware to create a signed image.

Takes a raw firmware `.bin` file, computes its SHA-256 hash, prepends an eBoot-compatible image header, and produces a `.signed.bin` ready for flashing or OTA delivery.

```bash
#!/bin/bash
# Usage: ./pack_image.sh firmware.bin [signing_key.pem]

FIRMWARE=$1
OUTPUT="${FIRMWARE%.bin}.signed.bin"

sha256sum $FIRMWARE > ${FIRMWARE}.sha256

python3 -c "
import struct, hashlib, sys
fw = open(sys.argv[1], 'rb').read()
h = hashlib.sha256(fw).digest()
header = struct.pack('<4sII32s', b'EBOOT', 1, len(fw), h)
out = open(sys.argv[2], 'wb')
out.write(header)
out.write(fw)
" $FIRMWARE $OUTPUT
```

#### 9. `llm_prompt.txt` — LLM Enhancement Prompt

**Who uses it:** Optional — pass to an LLM (Ollama/OpenAI) for deeper hardware analysis.

If you have a local LLM running, ebuild can send this prompt to get enhanced peripheral configuration suggestions (pin muxing, DMA channels, interrupt priorities) beyond what the rule engine detects.

```text
Analyze this embedded hardware design and suggest optimal configuration:

MCU: STM32F4 (cortex-m4)
Architecture: arm
Peripherals: i2c, spi, usb, can, uart

Suggest: pin assignments, DMA channels, interrupt priorities,
clock tree configuration, and power optimization.
```

---

### How the Files Flow Together

```
                     Your Hardware
                    ┌─────────────┐
                    │ .kicad_sch  │  ← KiCad schematic
                    │ .yaml       │  ← or manual board description
                    │ .csv        │  ← or BOM export
                    └──────┬──────┘
                           │
                    ebuild analyze
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
    ┌──────────┐    ┌──────────┐    ┌──────────────┐
    │board.yaml│    │boot.yaml │    │build.yaml    │
    │          │    │          │    │              │
    │ MCU info │    │ Flash    │    │ Toolchain    │
    │ Periphs  │    │ layout   │    │ CMake defs   │
    └────┬─────┘    └────┬─────┘    └──────┬───────┘
         │               │                │
         ▼               ▼                ▼
 ┌───────────────┐ ┌────────────────┐ ┌──────────────┐
 │eos_product_   │ │eboot_flash_    │ │eboot_config. │
 │config.h       │ │layout.h        │ │cmake         │
 │               │ │eboot_memory.ld │ │              │
 │ C #defines    │ │                │ │ CMake vars   │
 │ for firmware  │ │ C #defines +   │ │ for eBoot    │
 │               │ │ linker script  │ │ build        │
 └───────┬───────┘ │ for bootloader │ └──────┬───────┘
         │         └────────┬───────┘        │
         │                  │                │
         ▼                  ▼                ▼
    ┌─────────────────────────────────────────────┐
    │           ebuild build / cmake              │
    │  Compiles EoS firmware + eBoot bootloader   │
    │  with the correct config for YOUR board     │
    └─────────────────────┬───────────────────────┘
                          │
                          ▼
                  ┌───────────────┐
                  │pack_image.sh  │
                  │               │
                  │ Signs firmware│
                  │ with eBoot    │
                  │ image header  │
                  └───────┬───────┘
                          │
                          ▼
                   firmware.signed.bin
                   Ready to flash! 🚀
```

### Example 4: Scaffold a New Project

```bash
# Bare-metal blink + UART echo for STM32F4
ebuild new my_sensor --template bare-metal --board stm32f4

# BLE sensor application for nRF52
ebuild new my_ble_app --template ble-sensor --board nrf52

# RTOS application for STM32H7
ebuild new my_controller --template rtos-app --board stm32h7

# Linux application for Raspberry Pi 4
ebuild new my_gateway --template linux-app --board rpi4

# Safety-critical for TMS570 Cortex-R5
ebuild new my_safety_app --template safety-critical --board tms570

# Secure boot project
ebuild new my_secure_app --template secure-boot --board stm32f4
```

Each generates a ready-to-build project:
```
my_sensor/
├── build.yaml    # Build configuration
├── eos.yaml      # EoS platform config
├── src/main.c    # Board-specific HAL code (GPIO blink + UART echo)
└── README.md     # Getting started guide
```

### Example 5: List Available Packages

```bash
ebuild list-packages
# freertos v11.1.0 [cmake] — Real-time operating system kernel
# littlefs v2.9.3  [make]  — Fail-safe filesystem for MCUs
# lwip     v2.2.0  [cmake] — Lightweight TCP/IP stack
# mbedtls  v3.6.0  [cmake] — TLS/SSL library
# zlib     v1.3.1  [cmake] — Lossless data compression
```

### Example 6: Build EoS + eBoot (Single-Phase Integration)

```bash
# Clone eos (it auto-resolves eboot at build time)
git clone https://github.com/embeddedos-org/eos.git
cd eos

# Option A: Use ebuild CLI
pip install -e ../ebuild    # or wherever ebuild is
ebuild build                # cmake backend, auto-detects eBoot sibling

# Option B: Use cmake directly
cmake -B build -DEOS_BUILD_TESTS=ON
cmake --build build
cd build && ctest           # Run 20 unit tests
```

This builds the full platform in a single phase:
```
eboot_hal → eboot_core → eboot_stage1    (eBoot — 30 modules)
eos_hal → eos_kernel → eos_drivers       (EoS core)
eos_core → eos_toolchains → eos_systems  (Build pipelines)
eos_crypto → eos_security → eos_ota      (Services)
eos_sensor → eos_motor → eos_filesystem  (Runtime)
+ 20 test executables
```

---

## Sample Board Files

5 sample hardware board descriptions are included for testing:

| File | MCU | Arch | Use Case |
|------|-----|------|----------|
| `hardware/board/sample_iot_gateway.yaml` | STM32H743 | ARM Cortex-M7 | Industrial IoT gateway with CAN, WiFi, BLE, ETH |
| `hardware/board/sample_ble_sensor.yaml` | nRF52840 | ARM Cortex-M4 | Ultra-low-power BLE sensor, coin cell, 2yr battery |
| `hardware/board/sample_esp32s3_display.yaml` | ESP32-S3 | Xtensa LX7 | Smart display with WiFi, LCD, touch, camera |
| `hardware/board/sample_riscv_industrial.yaml` | GD32VF103 | RISC-V RV32 | Industrial PLC with RS485, CAN, 4-20mA inputs |
| `hardware/board/sample_rpi4_gateway.yaml` | BCM2711 | ARM Cortex-A72 | Linux gateway, Gigabit ETH, WiFi, 4GB RAM |

### Writing Your Own Board File

Create a YAML file describing your hardware:

```yaml
board_name: my-custom-board
revision: "A"

mcu:
  part: STM32F407VGT6
  family: STM32F4
  core: cortex-m4
  clock: 168 MHz
  flash: 1MB
  ram: 192KB SRAM
  voltage: 3.3V

peripherals:
  - UART0: PA9/PA10 (debug console, 115200 baud)
  - SPI0: PA5/PA6/PA7 (external flash)
  - I2C0: PB6/PB7 (sensor)
  - ADC: PA0 (battery monitor)
  - Watchdog: IWDG (5 second timeout)

memory_map:
  flash_base: 0x08000000
  flash_size: 0x100000
  ram_base: 0x20000000
  ram_size: 0x30000

boot:
  recovery_pin: PC0 (active low)
  led_status: PD12

use_case: |
  Your board description here.
```

Then run:
```bash
ebuild analyze --file my-custom-board.yaml --output-dir my_configs/
```

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `ebuild build` | Build project (auto-detects backend: cmake/ninja/make) |
| `ebuild info` | Show project targets, dependencies, build order |
| `ebuild analyze --file <hw.yaml>` | Analyze hardware → generate board/boot/build configs |
| `ebuild new <name> --template <t> --board <b>` | Scaffold a new project from template |
| `ebuild list-packages` | List available package recipes |
| `ebuild install` | Resolve, fetch, and build all declared packages |
| `ebuild clean` | Remove build output directory |
| `ebuild configure` | Generate build files without building |
| `ebuild firmware` | Build RTOS firmware for embedded target |
| `ebuild system` | Build complete Linux system image |
| `ebuild setup` | Clone eos + eboot repos to local cache |
| `ebuild repos` | Manage cached repositories |
| `ebuild generate-board` | Generate board YAML from hardware analysis |
| `ebuild generate-boot` | Generate eBoot C headers and linker scripts |
| `ebuild generate-project` | Generate stripped-down eos/eboot for a board |
| `ebuild add <package>` | Add a package dependency to build.yaml |

---

## Performance

Measured on WSL2 Ubuntu 20.04 (x86_64):

| Operation | Time |
|-----------|------|
| Hardware analyze → 9 config files | **261 ms** |
| Build hello_world (ninja) | **748 ms** |
| Build multi_target lib+exe (ninja) | **794 ms** |
| Scaffold new project | **242 ms** |
| List packages | **223 ms** |
| Full eos+eboot cmake build (100 .c files) | **4.4 sec** |
| Full eos+eboot+tests single-phase | **26.6 sec** |

---

## Architecture

```
ebuild/
├── ebuild/                        Python CLI + build system
│   ├── cli/                       Click-based CLI commands
│   ├── build/                     Multi-backend dispatch (cmake/ninja/make/meson/cargo)
│   │   ├── dispatch.py            Auto-detect + run external build systems
│   │   └── ninja_backend.py       Generate build.ninja from build.yaml
│   ├── packages/                  Package recipe/registry/resolver/cache
│   ├── eos_ai/                    Hardware analyzer + project generator
│   │   ├── hardware_analyzer.py   Parse KiCad/Eagle/YAML/BOM → HardwareProfile
│   │   ├── config_generator.py    HardwareProfile → board.yaml/boot.yaml/eos_config.h
│   │   ├── config_validator.py    Schema validation for generated configs
│   │   └── boot_integrator.py     Generate eBoot flash headers + linker scripts
│   └── plugins/                   Extensible plugin system (5 hooks)
├── hardware/board/                Sample board YAML files (5 boards)
├── recipes/                       Package recipes (freertos, lwip, mbedtls, zlib, littlefs)
├── templates/                     Project templates (6 types)
├── examples/                      Working build examples
│   ├── hello_world/               Simple executable
│   ├── multi_target/              Library + executable with dependencies
│   ├── rtos_firmware/             FreeRTOS firmware config
│   ├── linux_image/               Linux system image config
│   └── cortex_r5_safety/          Safety-critical RTOS example
├── layers/                        Optional components (--with flag)
│   ├── eai/                       AI inference (12 LLM models, Ebot server)
│   ├── eni/                       Neural interface (Neuralink adapter)
│   ├── eipc/                      Secure IPC (Go + C SDK)
│   └── eosuite/                   Dev tools (Ebot client, GUI apps)
├── sdk/                           SDK generator + header-only API
└── tests/                         Test suite
```

---

## Related Repos

| Repo | Description |
|------|-------------|
| [eos](https://github.com/embeddedos-org/eos) | Embedded OS — HAL, kernel, drivers, services, networking |
| [eBoot](https://github.com/embeddedos-org/eBoot) | Secure bootloader — 83 boards, A/B update, chain of trust |
| **ebuild** (this repo) | Build system, hardware analyzer, SDK generator |

The three repos work together but are independently buildable. Clone just `eos` and it auto-fetches `eBoot` at build time. Use `ebuild` for the full CLI tooling.

## License

MIT License — see [LICENSE](LICENSE) for details.
