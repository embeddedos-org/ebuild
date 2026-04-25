# ebuild: The Definitive Reference Guide

## EmbeddedOS Build System

**Version 0.1.0**

**Srikanth Patchava & EmbeddedOS Contributors**

**April 2026**

---

*A comprehensive technical reference for the ebuild embedded build system — from hardware schematic to deployable firmware in one command.*

*Published by the EmbeddedOS Project*
*Copyright (c) 2026 EoS Project. MIT License.*

---

## Preface

ebuild is the unified build system for the EmbeddedOS (EoS) ecosystem. Unlike traditional embedded build tools that only compile code, ebuild bridges the gap between hardware design and firmware deployment. It reads your KiCad schematics, Eagle designs, YAML board descriptions, or even plain text hardware descriptions and auto-generates all the configuration files needed to build, flash, and deploy firmware for 73+ embedded targets.

This reference guide covers every aspect of ebuild: from the CLI interface and YAML configuration schema to the hardware analyzer engine, cross-compilation toolchains, package management, SDK generation, and CI/CD integration.

> **Important**: This is the **EmbeddedOS Build Tool** (ebuild). It is **not** related to Gentoo's ebuild package format.

### Who This Book Is For

- **Embedded Developers** building firmware with the EoS ecosystem
- **Hardware Engineers** who want to go from schematic to firmware automatically
- **Build Engineers** setting up CI/CD pipelines for embedded products
- **System Integrators** combining EoS, eBoot, eAI, and eIPC into a complete system
- **DevOps Engineers** managing cross-compilation and SDK distribution

### How This Book Is Organized

- **Part I: Getting Started** — Installation, quick start, and core concepts
- **Part II: Hardware Analysis** — Schematic parsing, config generation, MCU database
- **Part III: Build System** — Multi-backend build, cross-compilation, build configuration
- **Part IV: Project Management** — Scaffolding, templates, package management
- **Part V: Advanced Topics** — SDK generation, CI/CD, ebuild + eBoot integration
- **Part VI: Reference** — Complete CLI reference, YAML schemas, troubleshooting

---

## Table of Contents

- [Part I: Getting Started](#part-i-getting-started)
  - [Chapter 1: Introduction to ebuild](#chapter-1-introduction-to-ebuild)
  - [Chapter 2: Installation and Setup](#chapter-2-installation-and-setup)
  - [Chapter 3: Quick Start Guide](#chapter-3-quick-start-guide)
- [Part II: Hardware Analysis](#part-ii-hardware-analysis)
  - [Chapter 4: Hardware Analyzer Architecture](#chapter-4-hardware-analyzer-architecture)
  - [Chapter 5: Input Formats and Parsers](#chapter-5-input-formats-and-parsers)
  - [Chapter 6: Generated Configuration Files](#chapter-6-generated-configuration-files)
- [Part III: Build System](#part-iii-build-system)
  - [Chapter 7: Build System Architecture](#chapter-7-build-system-architecture)
  - [Chapter 8: YAML Build Configuration](#chapter-8-yaml-build-configuration)
  - [Chapter 9: Cross-Compilation](#chapter-9-cross-compilation)
  - [Chapter 10: Multi-Backend Build Dispatch](#chapter-10-multi-backend-build-dispatch)
- [Part IV: Project Management](#part-iv-project-management)
  - [Chapter 11: Project Scaffolding and Templates](#chapter-11-project-scaffolding-and-templates)
  - [Chapter 12: Package Management](#chapter-12-package-management)
  - [Chapter 13: SDK Generation](#chapter-13-sdk-generation)
- [Part V: Advanced Topics](#part-v-advanced-topics)
  - [Chapter 14: ebuild and eBoot Integration](#chapter-14-ebuild-and-eboot-integration)
  - [Chapter 15: CI/CD Integration](#chapter-15-cicd-integration)
  - [Chapter 16: LLM-Enhanced Configuration](#chapter-16-llm-enhanced-configuration)
- [Part VI: Reference](#part-vi-reference)
  - [Chapter 17: Complete CLI Reference](#chapter-17-complete-cli-reference)
  - [Chapter 18: YAML Configuration Schema](#chapter-18-yaml-configuration-schema)
  - [Chapter 19: MCU and Component Database](#chapter-19-mcu-and-component-database)
  - [Chapter 20: Troubleshooting](#chapter-20-troubleshooting)
- [Appendix A: Glossary](#appendix-a-glossary)
- [Appendix B: Supported Boards and MCUs](#appendix-b-supported-boards-and-mcus)
- [Appendix C: Related Projects](#appendix-c-related-projects)

---

# Part I: Getting Started

---

## Chapter 1: Introduction to ebuild

### 1.1 What Is ebuild?

ebuild is a unified build system that takes embedded development from hardware schematic to deployable firmware in a single command. It serves as the build and configuration backbone for the entire EmbeddedOS ecosystem.

```
Hardware (.kicad_sch / .yaml / .csv / .txt)
         |
  ebuild analyze
         |
    +----+----+
    v    v    v
 board  boot  build     <-- YAML configs
 .yaml  .yaml .yaml
    |    |    |
    v    v    v
 eos_   eboot_ eboot_   <-- C headers + linker + cmake
 config flash  memory
 .h     .h     .ld
         |
    ebuild build
         |
         v
  firmware.signed.bin
```

### 1.2 Key Capabilities

| Capability | Description |
|---|---|
| **Hardware Analysis** | Parse KiCad, Eagle, YAML, CSV, or text to extract MCU, peripherals, pin assignments |
| **Config Generation** | Auto-generate 9 configuration files (YAML, C headers, linker scripts, CMake, signing scripts) |
| **Multi-Backend Build** | Dispatch to CMake, Ninja, Make, Meson, or Cargo backends automatically |
| **Cross-Compilation** | Built-in support for ARM, RISC-V, Xtensa, x86, and more via toolchain files |
| **Project Scaffolding** | Create new projects from 6 templates (bare-metal, BLE, RTOS, Linux, safety-critical, secure-boot) |
| **Package Management** | Recipe-based package system (FreeRTOS, lwIP, mbedTLS, zlib, LittleFS) |
| **SDK Generation** | Generate distributable SDKs with toolchains, libraries, and examples |
| **EoS Integration** | Seamless build of EoS + eBoot with auto-fetching of dependencies |

### 1.3 Performance

| Operation | Time |
|---|---|
| Hardware analyze to 9 files | **261 ms** |
| Build hello_world (ninja) | **748 ms** |
| Build multi_target (ninja) | **794 ms** |
| Scaffold project | **242 ms** |
| Full eos+eboot build (100 .c) | **4.4 sec** |
| Full eos+eboot+tests | **26.6 sec** |

---

## Chapter 2: Installation and Setup

### 2.1 Linux / macOS

```bash
git clone https://github.com/embeddedos-org/ebuild.git
cd ebuild
./install.sh         # or: pip install -e .
ebuild --version     # ebuild, version 0.1.0
```

### 2.2 Windows

```bash
git clone https://github.com/embeddedos-org/ebuild.git
cd ebuild
install.bat
```

### 2.3 Prerequisites

| Requirement | Version | Purpose |
|---|---|---|
| Python | 3.8+ | ebuild CLI runtime |
| CMake | 3.16+ | Build backend |
| GCC | 9+ | Native compilation |
| arm-none-eabi-gcc | 10+ | ARM cross-compilation |
| Ninja | 1.10+ | Fast parallel builds (optional) |

### 2.4 Verifying Installation

```bash
source ~/.bashrc
export PATH="$HOME/.local/bin:$PATH"
ebuild --version && cmake --version | head -1 && gcc --version | head -1
```

---

## Chapter 3: Quick Start Guide

### 3.1 Build Hello World

```bash
cd examples/hello_world
ebuild info && ebuild build && ./_build/hello
# Output: "Hello from EoS Build System!"
```

### 3.2 Build Multi-Target (Library + Executable)

```bash
cd examples/multi_target
ebuild build && ./_build/myapp
# Output: add=17, subtract=7, multiply=60, factorial=120
```

### 3.3 Analyze Hardware and Generate Configs

```bash
# From a KiCad schematic
ebuild analyze --file hardware/board/sample_stm32f4_sensor.kicad_sch \
  --output-dir /tmp/configs

# From a YAML board description
ebuild analyze --file hardware/board/sample_iot_gateway.yaml \
  --output-dir /tmp/iot

# From a CSV BOM
echo "Reference,Value
U1,STM32F407VGT6
U2,BME280" > /tmp/bom.csv
ebuild analyze --file /tmp/bom.csv --output-dir /tmp/bom_out

# From plain text
echo "STM32H743 at 480MHz with SPI flash, I2C sensors, CAN bus" > /tmp/desc.txt
ebuild analyze --file /tmp/desc.txt --output-dir /tmp/txt_out
```

### 3.4 Scaffold a New Project

```bash
ebuild new my_sensor --template bare-metal --board stm32f4
ebuild new my_ble    --template ble-sensor  --board nrf52
ebuild new my_motor  --template rtos-app    --board stm32h7
ebuild new my_gw     --template linux-app   --board rpi4
```

### 3.5 Full EoS + eBoot Build

```bash
git clone https://github.com/embeddedos-org/eos.git && cd eos
ebuild build    # Builds 25 libraries (3 eBoot + 22 EoS) in ~5 seconds
```

---

# Part II: Hardware Analysis

---

## Chapter 4: Hardware Analyzer Architecture

### 4.1 Analysis Pipeline

The hardware analyzer follows a multi-stage pipeline:

```
Input File
    |
    v
+-------------------+
| Format Detection  |  Detect file type (.kicad_sch, .yaml, .csv, .txt)
+-------------------+
    |
    v
+-------------------+
| Parser            |  Extract components, nets, peripherals
+-------------------+
    |
    v
+-------------------+
| MCU Database      |  Look up MCU specs (160+ MCUs)
+-------------------+
    |
    v
+-------------------+
| Component DB      |  Look up IC details (200+ ICs with I2C addrs)
+-------------------+
    |
    v
+-------------------+
| Config Generator  |  Generate 9 configuration files
+-------------------+
    |
    v
9 Output Files
```

### 4.2 Internal Architecture

```
ebuild/
  ebuild/
    eos_ai/                    # Hardware analyzer engine
      __init__.py              # Main analyze entry point
      kicad_parser.py          # KiCad S-expression parser
      eagle_parser.py          # Eagle XML parser
      yaml_parser.py           # YAML board description parser
      csv_parser.py            # BOM CSV parser
      text_parser.py           # Plain text keyword extractor
      mcu_database.py          # MCU specifications (160+ entries)
      component_database.py    # IC database (200+ entries)
      config_generator.py      # Output file generation
```

### 4.3 MCU Detection Strategy

The analyzer uses multiple strategies to identify the target MCU:

1. **Direct match**: Component value matches a known MCU (e.g., "STM32F407VGT6")
2. **Prefix match**: Component value starts with a known MCU family (e.g., "STM32F4")
3. **Keyword extraction**: Text contains MCU-related keywords
4. **Library reference**: KiCad library ID contains MCU information (e.g., "MCU_ST:STM32F407")

---

## Chapter 5: Input Formats and Parsers

### 5.1 Supported Input Formats

| Input | Format | Parser | Detail Level |
|---|---|---|---|
| `.kicad_sch` | KiCad 6/7/8 schematic | S-expression parser | Full: components, nets, wires, MCU, pins |
| `.sch` (XML) | Eagle schematic | XML parser | Full: components, nets, peripherals |
| `.csv` | BOM export | BOM parser + ComponentDB | Components + I2C addresses |
| `.yaml` | Board description | Keyword extraction + MCU DB | Board specs + peripherals |
| `.txt` / `.md` | Any text | Keyword extraction | MCU names, peripherals |

### 5.2 KiCad Schematic Parser

The KiCad parser reads S-expression formatted schematics (KiCad 6, 7, 8):

```lisp
;; Example KiCad schematic fragment
(kicad_sch (version 20230121) (generator eeschema)
  (symbol (lib_id "MCU_ST:STM32F407VGT6") (at 150 100 0)
    (property "Reference" "U1")
    (property "Value" "STM32F407VGT6"))
  (symbol (lib_id "Sensor:BME280") (at 200 100 0)
    (property "Reference" "U2")
    (property "Value" "BME280")))
```

The parser extracts:
- **MCU identification**: Matches component values against the MCU database
- **Peripheral detection**: Identifies sensors, communication ICs, power regulators
- **Net connections**: Traces signal connections between components
- **Pin assignments**: Maps MCU pins to peripheral connections

### 5.3 YAML Board Description

```yaml
board:
  name: iot_gateway
  mcu: STM32H743
  arch: arm
  core: cortex-m7
  clock_hz: 480000000
  memory:
    flash: 2097152      # 2 MB
    ram: 1048576         # 1 MB
  peripherals:
    - name: W5500
      type: ethernet
      interface: spi
    - name: ESP32-WROOM
      type: wifi
      interface: uart
    - name: BME680
      type: i2c
      address: 0x76
    - name: CAN_Transceiver
      type: can
    - name: GPS_Module
      type: uart
```

### 5.4 Component Database

The component database contains 200+ IC entries with metadata:

| Component | Type | Interface | I2C Address | Description |
|---|---|---|---|---|
| BME280 | sensor | I2C | 0x76/0x77 | Temp/humidity/pressure |
| BME680 | sensor | I2C | 0x76/0x77 | Air quality |
| MPU6050 | sensor | I2C | 0x68/0x69 | 6-axis IMU |
| W25Q128 | memory | SPI | -- | 128Mbit SPI flash |
| MCP2515 | can | SPI | -- | CAN controller |
| SN65HVD230 | can | -- | -- | CAN transceiver |
| MAX3232 | uart | -- | -- | RS-232 transceiver |
| W5500 | ethernet | SPI | -- | Ethernet controller |
| ADS1115 | adc | I2C | 0x48 | 16-bit ADC |
| INA219 | sensor | I2C | 0x40 | Current/power monitor |
| SSD1306 | display | I2C | 0x3C | OLED display controller |
| MAX31856 | sensor | SPI | -- | Thermocouple interface |

---

## Chapter 6: Generated Configuration Files

### 6.1 Overview

Each `ebuild analyze` run produces **9 files** in approximately 260ms:

| # | File | Type | Used By |
|---|---|---|---|
| 1 | `board.yaml` | YAML | EoS build system, device drivers |
| 2 | `boot.yaml` | YAML | eBoot bootloader, OTA system |
| 3 | `build.yaml` | YAML | ebuild build, CI/CD |
| 4 | `eos_product_config.h` | C header | Firmware source code |
| 5 | `eboot_flash_layout.h` | C header | eBoot C code |
| 6 | `eboot_memory.ld` | Linker script | GCC linker |
| 7 | `eboot_config.cmake` | CMake | CMake build system |
| 8 | `pack_image.sh` | Shell script | CI pipeline (signing) |
| 9 | `llm_prompt.txt` | Text | Optional LLM enhancement |

### 6.2 board.yaml

```yaml
board:
  name: stm32f4
  mcu: STM32F4
  arch: arm
  core: cortex-m4
  vendor: ST
  clock_hz: 168000000
  memory:
    flash: 1048576     # 1MB
    ram: 196608        # 192KB
  peripherals:
  - name: BME280
    type: i2c
  - name: W25Q128
    type: spi
  - name: SN65HVD230
    type: can
  - name: UART
    type: uart
```

### 6.3 boot.yaml

```yaml
boot:
  flash_base: '0x08000000'
  flash_size: 1048576
  layout:
    stage0:
      offset: '0x0'
      size: 16384
    stage1:
      offset: '0x4000'
      size: 65536
    slot_a:
      offset: '0x16000'
      size: 479232
    slot_b:
      offset: '0x8b000'
      size: 479232
  policy:
    max_boot_attempts: 3
    require_signature: true
    anti_rollback: true
```

### 6.4 build.yaml

```yaml
backend: cmake
toolchain:
  compiler: gcc
  arch: arm
  prefix: arm-none-eabi
cmake:
  defines:
    EOS_ENABLE_I2C: 'ON'
    EOS_ENABLE_SPI: 'ON'
    EOS_ENABLE_CAN: 'ON'
    EOS_ENABLE_UART: 'ON'
```

### 6.5 eos_product_config.h

```c
#define EOS_MCU       "STM32F4"
#define EOS_ARCH      "arm"
#define EOS_CORE      "cortex-m4"
#define EOS_CLOCK_HZ   168000000

#define EOS_ENABLE_CAN   1
#define EOS_ENABLE_I2C   1
#define EOS_ENABLE_SPI   1
#define EOS_ENABLE_UART  1
#define EOS_ENABLE_USB   1
```

Conditional compilation in firmware:

```c
#if EOS_ENABLE_I2C
    bme280_init();    // Only compiled if I2C detected
#endif
```

### 6.6 eboot_flash_layout.h

```c
#define EBOOT_FLASH_BASE     0x8000000
#define EBOOT_STAGE0_ADDR    (0x8000000 + 0x0)
#define EBOOT_STAGE0_SIZE    16384
#define EBOOT_STAGE1_ADDR    (0x8000000 + 0x4000)
#define EBOOT_STAGE1_SIZE    65536
#define EBOOT_SLOT_A_OFFSET  0x16000
#define EBOOT_SLOT_A_SIZE    479232
#define EBOOT_SLOT_B_OFFSET  0x8b000
#define EBOOT_SLOT_B_SIZE    479232
```

### 6.7 eboot_memory.ld

The linker script places bootloader code at correct flash addresses based on the MCU flash layout:

```ld
MEMORY
{
    FLASH_STAGE0 (rx) : ORIGIN = 0x08000000, LENGTH = 16K
    FLASH_STAGE1 (rx) : ORIGIN = 0x08004000, LENGTH = 64K
    FLASH_APP    (rx) : ORIGIN = 0x08014000, LENGTH = 448K
    SRAM         (rw) : ORIGIN = 0x20000000, LENGTH = 192K
}

SECTIONS
{
    .text : { *(.text*) } > FLASH_STAGE0
    .data : { *(.data*) } > SRAM AT > FLASH_STAGE0
    .bss  : { *(.bss*)  } > SRAM
}
```

### 6.8 pack_image.sh

Computes SHA-256, prepends eBoot header, and produces `firmware.signed.bin`. Keys are passed as arguments, never embedded.

### 6.9 llm_prompt.txt

Optional prompt file for LLM-enhanced pin muxing, DMA, and interrupt suggestions.

---

# Part III: Build System

---

## Chapter 7: Build System Architecture

### 7.1 Architecture Overview

```
ebuild/
  ebuild/
    cli/             # Click commands (build, info, analyze, new, etc.)
    build/           # Multi-backend dispatch
      __init__.py    # Backend selection
      cmake.py       # CMake backend
      ninja.py       # Ninja backend
      make.py        # Make backend
      meson.py       # Meson backend
      cargo.py       # Cargo/Rust backend
    packages/        # Recipe registry, resolver, cache, fetcher
    eos_ai/          # Hardware analyzer + config generator
    plugins/         # Extensible plugin system
```

### 7.2 Build Flow

```
ebuild build
    |
    v
+-------------------+
| Read build.yaml   |  Detect backend, targets, deps
+-------------------+
    |
    v
+-------------------+
| Backend Dispatch  |  cmake / ninja / make / meson / cargo
+-------------------+
    |
    v
+-------------------+
| Configure         |  Generate build files
+-------------------+
    |
    v
+-------------------+
| Compile           |  Parallel compilation
+-------------------+
    |
    v
+-------------------+
| Link              |  Produce binaries
+-------------------+
    |
    v
Output: _build/
```

### 7.3 Backend Selection

ebuild automatically selects the build backend based on project configuration:

| Backend | Detected By | Use Case |
|---|---|---|
| CMake | `CMakeLists.txt` present | C/C++ projects (default) |
| Ninja | `build.ninja` or CMake+Ninja generator | Fast parallel builds |
| Make | `Makefile` present | Legacy projects |
| Meson | `meson.build` present | Modern C/C++ alternative |
| Cargo | `Cargo.toml` present | Rust projects |

---

## Chapter 8: YAML Build Configuration

### 8.1 build.yaml Schema

```yaml
# Project metadata
project:
  name: my_firmware
  version: 1.0.0

# Build backend
backend: cmake

# Toolchain
toolchain:
  compiler: gcc
  arch: arm
  prefix: arm-none-eabi

# CMake-specific options
cmake:
  generator: Ninja
  build_type: Release
  defines:
    EOS_ENABLE_I2C: 'ON'
    EOS_ENABLE_SPI: 'ON'
    EOS_BUILD_TESTS: 'OFF'

# Targets
targets:
  - name: my_firmware
    type: executable
    sources:
      - src/main.c
      - src/app.c
    includes:
      - include/
    libraries:
      - eos_hal
      - eos_driver
    defines:
      - BOARD_STM32F4

# Dependencies
dependencies:
  - name: freertos
    version: ">=10.5"
  - name: lwip
    version: "2.2.0"
```

### 8.2 Conditional Configuration

```yaml
# Board-specific overrides
boards:
  stm32f4:
    cmake:
      defines:
        BOARD_HAS_CAN: 'ON'
        BOARD_HAS_BLE: 'OFF'
  nrf52:
    cmake:
      defines:
        BOARD_HAS_CAN: 'OFF'
        BOARD_HAS_BLE: 'ON'
```

---

## Chapter 9: Cross-Compilation

### 9.1 Toolchain Files

ebuild provides CMake toolchain files for all supported architectures:

| Architecture | Toolchain File | Compiler Prefix |
|---|---|---|
| ARM Cortex-M | `toolchains/arm-none-eabi.cmake` | `arm-none-eabi-` |
| ARM Cortex-A (Linux) | `toolchains/aarch64-linux-gnu.cmake` | `aarch64-linux-gnu-` |
| RISC-V 32 | `toolchains/riscv32-unknown-elf.cmake` | `riscv32-unknown-elf-` |
| RISC-V 64 | `toolchains/riscv64-unknown-elf.cmake` | `riscv64-unknown-elf-` |
| Xtensa (ESP32) | `toolchains/xtensa-esp32-elf.cmake` | `xtensa-esp32-elf-` |
| x86_64 | `toolchains/x86_64-linux-gnu.cmake` | System default |

### 9.2 Cross-Compilation Example

```bash
# Build for STM32F4
cmake -B build-arm -DEBLDR_BOARD=stm32f4 \
  -DCMAKE_TOOLCHAIN_FILE=toolchains/arm-none-eabi.cmake
cmake --build build-arm

# Build for RISC-V 64
cmake -B build-rv -DEBLDR_BOARD=riscv64_virt \
  -DCMAKE_TOOLCHAIN_FILE=toolchains/riscv64-unknown-elf.cmake
cmake --build build-rv
```

### 9.3 Using ebuild for Cross-Compilation

```bash
# ebuild handles toolchain selection automatically when board is set
cd examples/hello_world
ebuild build --board stm32f4
# Automatically selects arm-none-eabi-gcc and correct flags
```

---

## Chapter 10: Multi-Backend Build Dispatch

### 10.1 CMake Backend

The default backend for C/C++ projects:

```bash
ebuild build                      # Auto-detect and build
ebuild build --backend cmake      # Explicit CMake
ebuild configure                  # Generate only, no compile
ebuild clean                      # Remove build directory
```

### 10.2 Build Output Structure

```
_build/
  CMakeCache.txt                  # CMake cache
  build.ninja                     # Ninja build rules
  compile_commands.json           # IDE support
  my_firmware                     # Final binary
  my_firmware.bin                 # Raw binary
  my_firmware.hex                 # Intel HEX
  my_firmware.map                 # Linker map
```

### 10.3 Ninja Backend

Ninja provides significantly faster incremental builds:

```bash
ebuild build --backend ninja
# Or set in build.yaml:
# cmake:
#   generator: Ninja
```

---

# Part IV: Project Management

---

## Chapter 11: Project Scaffolding and Templates

### 11.1 Template System

ebuild provides 6 project templates:

| Template | Description | Board Examples |
|---|---|---|
| `bare-metal` | Minimal embedded project, no RTOS | STM32F4, RISC-V |
| `ble-sensor` | BLE sensor application | nRF52, ESP32 |
| `rtos-app` | FreeRTOS or Zephyr application | STM32H7, nRF52 |
| `linux-app` | Linux userspace application | RPi4, i.MX8M |
| `safety-critical` | IEC 61508 / ISO 26262 project | TMS570, STM32H7 |
| `secure-boot` | Secure boot enabled project | STM32F4, i.MX8M |

### 11.2 Scaffolding Command

```bash
ebuild new <project_name> --template <template> --board <board> [--output-dir <dir>]
```

### 11.3 Generated Project Structure (bare-metal)

```
my_sensor/
  src/
    main.c                    # Application entry point
  include/
    app.h                     # Application header
  build.yaml                  # Build configuration
  CMakeLists.txt              # CMake build file
  README.md                   # Project documentation
```

### 11.4 Generated Project Structure (rtos-app)

```
my_motor/
  src/
    main.c                    # FreeRTOS application
    tasks.c                   # Task definitions
  include/
    app.h
    tasks.h
  config/
    FreeRTOSConfig.h          # RTOS configuration
  build.yaml
  CMakeLists.txt
  README.md
```

### 11.5 Generated Project Structure (secure-boot)

```
my_secure/
  src/
    main.c
  include/
    app.h
  keys/
    README.md                 # Key generation instructions
  configs/
    boot.yaml                 # Secure boot config
  build.yaml
  CMakeLists.txt
  README.md
```

---

## Chapter 12: Package Management

### 12.1 Package Recipe System

ebuild uses a recipe-based package system:

```
recipes/
  freertos.yaml
  lwip.yaml
  mbedtls.yaml
  zlib.yaml
  littlefs.yaml
```

### 12.2 Recipe Format

```yaml
# recipes/freertos.yaml
package:
  name: freertos
  version: 10.5.1
  description: Real-time operating system kernel
  source:
    type: git
    url: https://github.com/FreeRTOS/FreeRTOS-Kernel.git
    tag: V10.5.1
  build:
    type: cmake
    options:
      FREERTOS_PORT: GCC_ARM_CM4F
  provides:
    - include/FreeRTOS.h
    - lib/libfreertos.a
```

### 12.3 Available Packages

| Package | Version | Description |
|---|---|---|
| FreeRTOS | 10.5.1 | Real-time kernel |
| lwIP | 2.2.0 | Lightweight TCP/IP stack |
| mbedTLS | 3.5.0 | TLS/crypto library |
| zlib | 1.3 | Compression library |
| LittleFS | 2.8.0 | Wear-leveling filesystem |

### 12.4 Package Commands

```bash
ebuild list-packages           # List available recipes
ebuild install                 # Fetch and build all dependencies
ebuild install freertos        # Install specific package
```

### 12.5 Package Resolution

The package resolver handles version constraints and dependency ordering:

```
Request: freertos >= 10.5, mbedtls ^3.0
    |
    v
+-------------------+
| Version Resolver  |  Find compatible versions
+-------------------+
    |
    v
+-------------------+
| Dependency Graph  |  Order by dependencies
+-------------------+
    |
    v
+-------------------+
| Cache Check       |  Skip if already built
+-------------------+
    |
    v
+-------------------+
| Fetch + Build     |  Download and compile
+-------------------+
```

---

## Chapter 13: SDK Generation

### 13.1 SDK Overview

ebuild can generate distributable SDKs containing pre-compiled libraries, headers, toolchain files, build scripts, examples, and documentation for target architectures.

### 13.2 SDK Commands

```bash
ebuild sdk generate --board stm32f4 --output sdk/
ebuild sdk package --format tar.gz
```

### 13.3 SDK Structure

```
sdk/
  include/                    # All public headers
  lib/                        # Pre-compiled libraries (.a)
  toolchains/                 # CMake toolchain files
  examples/                   # Example projects
  docs/                       # API documentation
  sdk_config.cmake            # SDK integration file
  README.md                   # Usage instructions
```

---

# Part V: Advanced Topics

---

## Chapter 14: ebuild and eBoot Integration

### 14.1 How They Work Together

```
ebuild = CONFIGURATION GENERATOR  (runs on your laptop at build time)
eBoot  = BOOTLOADER               (runs on the MCU at power-on)
```

### 14.2 Without ebuild (Manual)

```bash
# Write flash layout header by hand
vim eboot_flash_layout.h

# Build eBoot standalone
cd eBoot
cmake -B build -DEBLDR_BOARD=none && cmake --build build
```

Warning: Manual offset calculation, no validation, no linker script.

### 14.3 With ebuild (Automated)

```bash
# ebuild generates everything from your schematic
ebuild analyze --file board.kicad_sch --output-dir configs/

# Build eos + eBoot in one command
cd eos && ebuild build
```

Auto-calculated, validated, linker script + signing script included.

### 14.4 Comparison

| Aspect | WITHOUT ebuild | WITH ebuild |
|---|---|---|
| Config files | 1 (manual) | 9 (auto-generated) |
| Time to configure | ~5-10 minutes | ~260ms |
| Flash layout | Calculate by hand | Auto-calculated |
| Linker script | Write by hand | Auto-generated |
| Validation | None | Schema validated |
| Human errors | Likely | Eliminated |

---

## Chapter 15: CI/CD Integration

### 15.1 GitHub Actions Workflow

```yaml
name: CI
on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install ebuild
        run: pip install -e .
      - name: Build
        run: ebuild build
      - name: Test
        run: |
          ebuild build --test
          cd _build && ctest --output-on-failure
```

### 15.2 Multi-Board CI Matrix

```yaml
strategy:
  matrix:
    board: [stm32f4, nrf52, rpi4, esp32]

steps:
  - run: ebuild build --board ${{ matrix.board }}
```

### 15.3 Firmware Signing in CI

```bash
ebuild analyze --file board.kicad_sch --output-dir configs/
bash configs/pack_image.sh build/firmware.bin keys/private.pem
# Output: firmware.signed.bin
```

### 15.4 CI Workflow Matrix

| Workflow | Schedule | Coverage |
|---|---|---|
| CI | Every push/PR | Build + test |
| Nightly | Daily | Full regression |
| Release | Tag v*.*.* | Build + sign + publish |

---

## Chapter 16: LLM-Enhanced Configuration

### 16.1 LLM Prompt Generation

ebuild generates an optional `llm_prompt.txt` file that can be passed to an LLM for enhanced configuration suggestions:

- Pin muxing optimization
- DMA channel assignment
- Interrupt priority recommendations
- Power mode configuration

### 16.2 Using with Ollama

```bash
ebuild analyze --file board.kicad_sch --output-dir configs/
ollama run llama3 < configs/llm_prompt.txt
```

### 16.3 API Key Security

LLM API keys are loaded exclusively from environment variables (`OPENAI_API_KEY`, `EOS_LLM_API_KEY`). No keys are stored in source code or generated configs.

---

# Part VI: Reference

---

## Chapter 17: Complete CLI Reference

### 17.1 Command Summary

| Command | Description |
|---|---|
| `ebuild build` | Build project (auto-detects backend) |
| `ebuild info` | Show targets, deps, build order |
| `ebuild analyze --file <f>` | Hardware schematic to config files |
| `ebuild new <name> --template <t> --board <b>` | Scaffold new project |
| `ebuild list-packages` | List package recipes |
| `ebuild install` | Fetch and build packages |
| `ebuild clean` | Remove build directory |
| `ebuild configure` | Generate build files only |
| `ebuild firmware` | Build RTOS firmware |
| `ebuild system` | Build Linux system image |
| `ebuild setup` | Clone eos + eboot to cache |
| `ebuild repos` | Manage cached repos |
| `ebuild --version` | Show version |
| `ebuild --help` | Show help |

### 17.2 ebuild build

```
Usage: ebuild build [OPTIONS]

Options:
  --board TEXT        Target board name
  --backend TEXT      Build backend (cmake/ninja/make/meson/cargo)
  --test              Build and run tests
  --release           Release build (optimized)
  --verbose           Verbose output
  --jobs INT          Parallel jobs (default: nproc)
  --help              Show help
```

### 17.3 ebuild analyze

```
Usage: ebuild analyze [OPTIONS]

Options:
  --file PATH         Input file (required)
  --output-dir PATH   Output directory (required)
  --board TEXT         Override board name
  --verbose           Show analysis details
  --help              Show help
```

### 17.4 ebuild new

```
Usage: ebuild new NAME [OPTIONS]

Options:
  --template TEXT     Project template (required)
  --board TEXT        Target board (required)
  --output-dir PATH   Output directory
  --help              Show help

Templates: bare-metal, ble-sensor, rtos-app, linux-app,
           safety-critical, secure-boot
```

---

## Chapter 18: YAML Configuration Schema

### 18.1 board.yaml Schema

```yaml
board:
  name: string          # Board identifier
  mcu: string           # MCU part number
  arch: string          # Architecture (arm, riscv, xtensa, x86_64)
  core: string          # Core type (cortex-m4, cortex-a72, rv64gc)
  vendor: string        # Silicon vendor
  clock_hz: integer     # System clock frequency
  memory:
    flash: integer      # Flash size in bytes
    ram: integer        # RAM size in bytes
  peripherals:
    - name: string
      type: string      # i2c, spi, uart, can, gpio, etc.
      address: string   # I2C address (optional)
      interface: string # Communication interface (optional)
```

### 18.2 boot.yaml Schema

```yaml
boot:
  flash_base: string    # Flash base address (hex)
  flash_size: integer   # Total flash size
  layout:
    stage0:
      offset: string
      size: integer
    stage1:
      offset: string
      size: integer
    slot_a:
      offset: string
      size: integer
    slot_b:
      offset: string
      size: integer
  policy:
    max_boot_attempts: integer
    require_signature: boolean
    anti_rollback: boolean
```

---

## Chapter 19: MCU and Component Database

### 19.1 MCU Database (160+ entries)

| MCU | Arch | Core | Clock | Flash | RAM |
|---|---|---|---|---|---|
| STM32F407 | ARM | Cortex-M4 | 168 MHz | 1 MB | 192 KB |
| STM32H743 | ARM | Cortex-M7 | 480 MHz | 2 MB | 1 MB |
| nRF52840 | ARM | Cortex-M4F | 64 MHz | 1 MB | 256 KB |
| ATSAMD51 | ARM | Cortex-M4F | 120 MHz | 1 MB | 256 KB |
| ESP32 | Xtensa | LX6 | 240 MHz | 4 MB | 520 KB |
| ESP32-S3 | Xtensa | LX7 | 240 MHz | 8 MB | 512 KB |
| GD32VF103 | RISC-V | RV32IMAC | 108 MHz | 128 KB | 32 KB |
| BCM2711 | ARM | Cortex-A72 | 1.5 GHz | SD | 1-8 GB |
| i.MX8M Mini | ARM | Cortex-A53 | 1.8 GHz | eMMC | 1-4 GB |
| AM6442 | ARM | A53+R5F | 1 GHz | eMMC | 2 GB |
| FU740 | RISC-V | U74 | 1.2 GHz | SPI | 8-16 GB |
| TMS570 | ARM | Cortex-R4 | 300 MHz | 3 MB | 256 KB |

### 19.2 Sample Board Files

| File | Format | MCU | Peripherals |
|---|---|---|---|
| sample_stm32f4_sensor.kicad_sch | KiCad | STM32F407 | BME280, W25Q128, CAN, USB |
| sample_iot_gateway.yaml | YAML | STM32H743 | 18 peripherals |
| sample_ble_sensor.yaml | YAML | nRF52840 | BLE 5.0, NFC |
| sample_esp32s3_display.yaml | YAML | ESP32-S3 | WiFi, LCD, touch, camera |
| sample_riscv_industrial.yaml | YAML | GD32VF103 | RS485, CAN, 4-20mA |
| sample_rpi4_gateway.yaml | YAML | BCM2711 | Gigabit ETH, WiFi |

---

## Chapter 20: Troubleshooting

### 20.1 Common Issues

| Symptom | Cause | Solution |
|---|---|---|
| `ebuild: command not found` | Not installed or not in PATH | Run `./install.sh` or add `~/.local/bin` to PATH |
| `No CMakeLists.txt found` | Wrong directory | Run `ebuild info` to check project detection |
| `Unknown MCU` | MCU not in database | Use YAML input with explicit MCU field |
| `Build fails with missing header` | Dependencies not installed | Run `ebuild install` |
| `Cross-compiler not found` | Toolchain not installed | Install the target toolchain |
| `analyze produces empty config` | Input not recognized | Check file format matches parser expectations |
| `Flash layout overflow` | Firmware too large | Increase slot size or optimize code |

### 20.2 Debugging Build Issues

```bash
# Verbose build output
ebuild build --verbose

# Show detected configuration
ebuild info

# Check generated CMake cache
cat _build/CMakeCache.txt | grep EOS_

# Manual CMake build for debugging
cmake -B _build -DCMAKE_VERBOSE_MAKEFILE=ON
cmake --build _build -- VERBOSE=1
```

### 20.3 Verifying Generated Configs

```bash
ebuild analyze --file board.kicad_sch --output-dir /tmp/test

cat > /tmp/test/verify.c << 'EOF'
#include <stdio.h>
#include "eboot_flash_layout.h"
#include "eos_product_config.h"
int main(void) {
    printf("MCU: %s (%s)\n", EOS_MCU, EOS_CORE);
    printf("Flash: 0x%08X (%dKB)\n", EBOOT_FLASH_BASE, EBOOT_FLASH_SIZE/1024);
    return 0;
}
EOF
gcc -o /tmp/test/verify /tmp/test/verify.c -I/tmp/test && /tmp/test/verify
```

---

## Appendix A: Glossary

| Term | Definition |
|---|---|
| **Backend** | Build system engine (CMake, Ninja, Make, Meson, Cargo) |
| **BOM** | Bill of Materials |
| **BSP** | Board Support Package |
| **Cross-compilation** | Compiling for a different target architecture |
| **ebuild** | EmbeddedOS Build Tool (not Gentoo ebuilds) |
| **Flash layout** | Memory map of bootloader and firmware partitions |
| **KiCad** | Open-source PCB/schematic design tool |
| **Linker script** | File defining memory regions for the linker |
| **MCU** | Microcontroller Unit |
| **OTA** | Over-The-Air firmware update |
| **Recipe** | Package build definition (YAML) |
| **Scaffold** | Generate project structure from template |
| **SDK** | Software Development Kit |
| **Toolchain** | Set of tools for cross-compilation |

---

## Appendix B: Supported Boards and MCUs

ebuild supports 73+ architecture families and 160+ MCUs. See the MCU Database in Chapter 19 for a representative sample, and `ebuild/ebuild/eos_ai/mcu_database.py` for the complete list.

---

## Appendix C: Related Projects

| Project | Repository | Purpose |
|---|---|---|
| EoS | embeddedos-org/eos | Embedded OS |
| eBoot | embeddedos-org/eBoot | Secure bootloader |
| **ebuild** | embeddedos-org/ebuild | Build system (this project) |
| eIPC | embeddedos-org/eipc | IPC framework |
| eAI | embeddedos-org/eai | AI/ML runtime |
| eNI | embeddedos-org/eni | Neural interface |
| eApps | embeddedos-org/eApps | Cross-platform apps |
| EoSim | embeddedos-org/eosim | Simulator |
| EoStudio | embeddedos-org/EoStudio | Design suite |

---

## Security

ebuild handles security-sensitive operations including firmware signing and LLM API access:

- **Firmware signing**: `pack_image.sh` reads signing keys from file paths; keys never embedded
- **LLM integration**: API keys loaded from environment variables only
- **Supply chain**: Full SBOM via `sbom.json`; Dependabot and Scorecard enabled
- **Build outputs**: Generated files contain only public configuration constants

For vulnerability reports, email security@embeddedos.org.

---

## Standards Compliance

ebuild aligns with: ISO/IEC/IEEE 15288:2023, ISO/IEC 12207, ISO/IEC/IEEE 42010, ISO/IEC 25000, ISO/IEC 25010, ISO/IEC 27001.

---

*This book is part of the EmbeddedOS Documentation Series.*
*For the latest version, visit: https://github.com/embeddedos-org/ebuild*

---
Part of the [EmbeddedOS Organization](https://embeddedos-org.github.io).
