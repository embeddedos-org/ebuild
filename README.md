# ⚙️ eBuild — EoS Embedded OS Build Tool

[![CI](https://github.com/embeddedos-org/ebuild/actions/workflows/ci.yml/badge.svg)](https://github.com/embeddedos-org/ebuild/actions/workflows/ci.yml)
[![Nightly](https://github.com/embeddedos-org/ebuild/actions/workflows/nightly.yml/badge.svg)](https://github.com/embeddedos-org/ebuild/actions/workflows/nightly.yml)
[![Release](https://github.com/embeddedos-org/ebuild/actions/workflows/release.yml/badge.svg)](https://github.com/embeddedos-org/ebuild/actions/workflows/release.yml)
[![Version](https://img.shields.io/github/v/tag/embeddedos-org/ebuild?label=version)](https://github.com/embeddedos-org/ebuild/releases/latest)

> **⚠️ Not Gentoo ebuilds.** This project is the **EmbeddedOS Build Tool** (`ebuild`) — a unified build system for the EoS embedded operating system. It is _not_ related to [Gentoo's ebuild format](https://wiki.gentoo.org/wiki/Ebuild) or the Portage package manager.

**Single monorepo for the entire EoS Embedded Operating System.**

One clone, one build command — from PCB hardware description to deployable firmware image. `ebuild` orchestrates cross-compilation across multiple backends (CMake, Make, Meson, Cargo, Kbuild), resolves package dependencies, analyzes hardware schematics, and generates deployable OS images for 14+ embedded targets.

## What This Does

| Capability | Description |
|---|---|
| **Build OS images** | Cross-compile a complete embedded OS (kernel, HAL, drivers, services) for ARM, AArch64, RISC-V, MIPS, x86_64 |
| **Generate SDKs** | Produce Yocto-style SDKs with toolchain files, sysroots, and environment scripts |
| **Analyze hardware** | Parse KiCad schematics, YAML board descriptions, BOMs → auto-detect MCU, peripherals, memory layout |
| **Manage packages** | Resolve, fetch, build, and cache external dependencies via YAML recipes |
| **Scaffold projects** | Generate complete project skeletons from 6 templates (bare-metal, RTOS, Linux, hybrid, safety-critical, secure-boot) |
| **Package deliverables** | Create versioned ZIP bundles with firmware, SDK, sources, and SBOM |

## Quick Start

```bash
# 1. Clone
git clone https://github.com/embeddedos-org/ebuild.git
cd ebuild

# 2. Install (editable mode for development)
pip install -e .

# 3. Build core only (EoS kernel + eBoot bootloader)
ebuild build --target raspi4

# 4. Build with optional layers (AI, neural interface, IPC)
ebuild build --target raspi4 --with eai,eni,eipc

# 5. Build everything
ebuild build --target raspi4 --with all
```

### Workflow Examples

**Create a new project from a template:**
```bash
# Scaffold a safety-critical RTOS project for the TMS570
ebuild new --board tms570 --template safety-critical --name my_safety_app

# This generates:
#   my_safety_app/
#   ├── build.yaml          # Build configuration
#   ├── eos.yaml            # EoS platform config
#   ├── src/main.c          # Application entry point
#   ├── linker/tms570_app.ld
#   └── README.md
```

**Build and generate an SDK:**
```bash
# Generate a cross-compilation SDK
ebuild sdk --target raspi4 --output build/

# Use the SDK in your own project
source build/eos-sdk-raspi4/environment-setup
cmake -B app-build -DCMAKE_TOOLCHAIN_FILE=$CMAKE_TOOLCHAIN_FILE
cmake --build app-build
```

**Analyze hardware from a schematic:**
```bash
# Analyze a KiCad schematic or YAML board description
ebuild analyze --input hardware/board/sample_iot_gateway.yaml

# Output: detected MCU (STM32H743), peripherals, memory map,
#         suggested build config, EoS enables
```

## Architecture

```
ebuild/
├── core/                          ALWAYS BUILT
│   ├── eos/                       Embedded OS (HAL, kernel, services, debug, drivers)
│   └── eboot/                     Bootloader (26 boards, A/B update, secure boot)
├── layers/                        OPTIONAL (--with flag)
│   ├── eai/                       AI layer (LLM models, Ebot server)
│   ├── eni/                       Neural interface (Neuralink adapter)
│   ├── eipc/                      Secure IPC (Go + C SDK)
│   └── eosuite/                   Dev tools (Ebot client, 20+ GUI apps)
├── sdk/                           SDK generator + header-only API
├── ebuild/                        Build system CLI (Python)
│   ├── cli/                       18 CLI commands
│   ├── build/                     Multi-backend build dispatch
│   ├── packages/                  Package recipe/registry/resolver pipeline
│   ├── eos_ai/                    Hardware analyzer + project generator
│   └── plugins/                   Plugin system (extensible hooks)
├── hardware/                      PCB/YAML hardware descriptions
├── recipes/                       Package recipes (zlib, mbedtls, freertos, ...)
├── templates/                     Project templates (6 types)
└── tests/                         Unified test suite
```

For a detailed architecture overview, see [docs/architecture.md](docs/architecture.md).

## Supported Hardware (14 targets)

| Target | Arch | CPU | Vendor | eBoot Board |
|---|---|---|---|---|
| `stm32f4` | ARM Cortex-M4 | cortex-m4 | ST STM32F407 | stm32f4 |
| `stm32h7` | ARM Cortex-M7 | cortex-m7 | ST STM32H743 | stm32h7 |
| `nrf52` | ARM Cortex-M4 | cortex-m4 | Nordic nRF52840 | nrf52 |
| `rp2040` | ARM Cortex-M0+ | cortex-m0+ | RPi RP2040 | samd51 |
| `tms570` | ARM Cortex-R5F | cortex-r5f | TI TMS570 | cortex_r5 |
| `raspi3` | AArch64 | cortex-a53 | Broadcom BCM2837 | qemu_arm64 |
| `raspi4` | AArch64 | cortex-a72 | Broadcom BCM2711 | rpi4 |
| `imx8m` | AArch64 | cortex-a53 | NXP i.MX8M | imx8m |
| `am64x` | AArch64 | cortex-a53 | TI AM6442 | am64x |
| `riscv_virt` | RISC-V | rv64gc | QEMU virt | riscv64_virt |
| `sifive_u` | RISC-V | u74 | SiFive FU740 | sifive_u |
| `malta` | MIPS | 24kf | MIPS Malta | mips |
| `x86_64` | x86_64 | generic | Generic PC | x86_64_efi |

For adding new board targets, see [docs/guides/adding_a_board.md](docs/guides/adding_a_board.md).

## Layers (optional components)

| Layer | Flag | Description |
|---|---|---|
| **EAI** | `--with eai` | AI inference — 12 curated LLM models (TinyLlama→Llama 3.2), agent loop, Ebot HTTP server |
| **ENI** | `--with eni` | Neural interface — Neuralink 1024-channel adapter, BCI framework, intent decoder |
| **EIPC** | `--with eipc` | Secure IPC — Go server + C SDK, HMAC-SHA256, replay protection |
| **eApps** | `--with eosuite` | Dev tools — Ebot AI client, 20+ GUI apps, cross-compiled for target |
| **All** | `--with all` | Build everything |

## Core Components (always built)

### EoS — Embedded Operating System

| Module | Description |
|---|---|
| HAL | 33 peripherals (GPIO, UART, SPI, I2C, CAN, PWM, ADC, DAC, Timer, DMA, USB, Ethernet...) |
| Kernel | Round-robin scheduler with priority, recursive mutex, counting semaphore, typed message queues |
| Crypto | SHA-256 (RFC 6234, NIST verified), AES-128/256, CRC32, RSA, ECC |
| OTA | A/B firmware update with SHA-256 verification + rollback |
| Sensor | Registry, calibration, 3 filters (average, median, lowpass) |
| Motor | PID controller with anti-windup, speed/position modes |
| Filesystem | RAM/Flash FS with POSIX-like API (open, read, write, seek, mkdir, readdir) |
| Logging | 6 levels (TRACE→FATAL), module filter, ring buffer (64 entries), multi-output |
| Debug | GDB remote stub (RSP protocol, 16 breakpoints) + core dump handler (CRC32) |
| Drivers | Loadable framework (19 device classes), probe/bind/unbind, suspend/resume |
| DeviceTree | .dtb FDT parser, node/property lookup by path/compatible/phandle |
| Services | Daemon lifecycle manager (start/stop/restart, watchdog, health checks, auto-restart) |

### eBoot — Bootloader

26 board ports, A/B firmware update, secure boot chain, crypto verification, recovery partition.

## CLI Commands (18)

| Command | Description |
|---|---|
| `ebuild build` | Build from build.yaml (core + selected layers) |
| `ebuild build --with eai,eni` | Build with optional layers |
| `ebuild sdk --target raspi4` | Generate Yocto-style SDK |
| `ebuild package --target raspi4` | Package deliverable ZIP (source + SDK + libs + image) |
| `ebuild models` | List LLM models for EAI layer |
| `ebuild analyze` | Analyze hardware (KiCad/YAML/text) |
| `ebuild firmware` | Build RTOS firmware |
| `ebuild system` | Build Linux system image |
| `ebuild integration` | Build + test all components |
| `ebuild qemu` | QEMU sanity boot test |
| `ebuild new` | Scaffold project from template |
| + 7 more | clean, configure, info, install, add, list-packages, generate-boot |

## SDK

```bash
# Generate SDK for any target
ebuild sdk --target raspi4 --output build/

# Use the SDK
source build/eos-sdk-raspi4/environment-setup
cmake -B app-build -DCMAKE_TOOLCHAIN_FILE=$CMAKE_TOOLCHAIN_FILE
cmake --build app-build
```

Or use the header-only SDK:

```c
#define EOS_SDK_ALL
#include "eos_sdk.h"
```

See `sdk/README.md` for full API reference.

## Build from Source

```bash
# Core only
cmake -B build -DEOS_BUILD_TESTS=ON
cmake --build build
cd build && ctest

# With all layers
cmake -B build -DEOS_WITH_ALL=ON -DEOS_BUILD_TESTS=ON
cmake --build build

# Cross-compile for Raspberry Pi 4
cmake -B build -DCMAKE_C_COMPILER=aarch64-linux-gnu-gcc \
  -DCMAKE_SYSTEM_NAME=Linux -DEOS_WITH_ALL=ON
cmake --build build
```

## Extending ebuild

ebuild supports a plugin system for extending its functionality. See:

- [Plugin Development](docs/guides/customization.md) — how to write plugins and customize builds
- [Adding a Board Target](docs/guides/adding_a_board.md) — step-by-step guide for new MCUs/SoCs
- [Architecture Overview](docs/architecture.md) — how the subsystems connect
- [Compatibility Matrix](docs/compatibility.md) — supported toolchain and host OS versions
- [Overlay System](docs/guides/overlays.md) — sharing board configs and layer presets

## Standards Compliance

This project is part of the EoS ecosystem and aligns with international standards including ISO/IEC/IEEE 15288:2023, ISO/IEC 12207, ISO/IEC/IEEE 42010, ISO/IEC 25000, ISO/IEC 25010, ISO/IEC 27001, ISO/IEC 15408, IEC 61508, ISO 26262, DO-178C, FIPS 140-3, POSIX (IEEE 1003), WCAG 2.1, and more. See the [EoS Compliance Documentation](https://github.com/embeddedos-org/.github/tree/master/docs/compliance) for full details including NTIA SBOM, SPDX, CycloneDX, and OpenChain compliance.

## License

MIT License — see [LICENSE](LICENSE) for details.
