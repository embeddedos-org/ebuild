# 🚀 ebuild — Unified Embedded Build System

**One tool for all embedded builds: applications, firmware, and complete Linux systems**

ebuild wraps and orchestrates **any build system** — from raw Makefiles to CMake to full Buildroot — through a single YAML config and CLI.

---

## 📥 Installation

### Prerequisites

ebuild requires **Python 3.9+** and optionally the build tools for your backend.

| Requirement | Required? | Purpose |
| --- | --- | --- |
| Python 3.9+ | ✅ Required | ebuild runtime |
| pip | ✅ Required | Package installer |
| CMake 3.15+ | For cmake backend | Build system generator |
| Make (GNU Make) | For make backend | Low-level build tool |
| Ninja | For ninja backend | Fast incremental builds |
| Rust/Cargo | For cargo backend | Rust builds |
| Meson | For meson backend | Modern build generator |

### 🐧 Linux (Ubuntu / Debian)

```bash
# Install Python and build tools
sudo apt update
sudo apt install python3 python3-pip python3-venv cmake ninja-build make gcc g++

# Install ebuild
git clone https://github.com/embeddedos-org/ebuild.git
cd ebuild
pip install -e .

# Verify
ebuild --version
```

For cross-compilation (ARM, RISC-V):
```bash
sudo apt install gcc-arm-none-eabi gcc-aarch64-linux-gnu gcc-riscv64-linux-gnu
```

### 🐧 Linux (Fedora / RHEL / CentOS)

```bash
sudo dnf install python3 python3-pip cmake ninja-build make gcc gcc-c++
git clone https://github.com/embeddedos-org/ebuild.git
cd ebuild
pip install -e .
```

### 🐧 Linux (Arch Linux)

```bash
sudo pacman -S python python-pip cmake ninja make gcc
git clone https://github.com/embeddedos-org/ebuild.git
cd ebuild
pip install -e .
```

### 🪟 Windows

**Option A — With Python from python.org:**
```powershell
# Install Python from https://www.python.org/downloads/ (check "Add to PATH")
# Install CMake from https://cmake.org/download/ (check "Add to PATH")
# Install Visual Studio Build Tools from https://visualstudio.microsoft.com/downloads/

git clone https://github.com/embeddedos-org/ebuild.git
cd ebuild
pip install -e .
ebuild --version
```

**Option B — With winget (Windows Package Manager):**
```powershell
winget install Python.Python.3.12
winget install Kitware.CMake
winget install Ninja-build.Ninja

git clone https://github.com/embeddedos-org/ebuild.git
cd ebuild
pip install -e .
```

**Option C — With WSL (Windows Subsystem for Linux):**
```bash
# Inside WSL (Ubuntu):
sudo apt install python3 python3-pip cmake ninja-build make gcc g++
git clone https://github.com/embeddedos-org/ebuild.git
cd ebuild
pip install -e .
```

### 🍎 macOS

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install build tools
brew install python cmake ninja make

# Install ebuild
git clone https://github.com/embeddedos-org/ebuild.git
cd ebuild
pip3 install -e .
ebuild --version
```

For cross-compilation (ARM):
```bash
brew install --cask gcc-arm-embedded
```

### 🐳 Docker (Any Platform)

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    cmake ninja-build make gcc g++ \
    gcc-arm-none-eabi gcc-aarch64-linux-gnu \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/embeddedos-org/ebuild.git /opt/ebuild \
    && pip install -e /opt/ebuild

WORKDIR /workspace
ENTRYPOINT ["ebuild"]
```

```bash
docker build -t ebuild .
docker run -v $(pwd):/workspace ebuild build
```

### 📦 pip install (from PyPI — when published)

```bash
pip install ebuild
```

### Verify Installation

```bash
ebuild --version                     # should print version
ebuild --help                        # show all commands
```

---

## 🎯 Quick Start

```bash
# Build any project — ebuild auto-detects the build system
cd my-project/
ebuild build

# Or specify the backend explicitly
ebuild build --backend cmake
ebuild build --backend make
ebuild build --backend meson
ebuild build --backend cargo

# Build the EoS embedded OS (CMake project)
cd eos/
ebuild build

# Build eBootloader (CMake project)
cd eboot/
ebuild build

# Build a Linux system image
ebuild system --format tar

# Build RTOS firmware
ebuild firmware --rtos freertos --board stm32f4
```

---

## 🔗 Integration with eos and eboot

ebuild builds both **eos** and **eboot** out of the box. Each project includes a `build.yaml`:

```bash
# Build eos (Embedded OS)
cd eos/
ebuild build          # auto-detects CMakeLists.txt → cmake backend
                      # configures with EOS_BUILD_TESTS=ON, builds all libraries

# Build eboot (Bootloader)
cd eboot/
ebuild build          # auto-detects CMakeLists.txt → cmake backend
                      # configures with EBLDR_BUILD_TESTS=ON, builds core + tests
```

**eos/build.yaml:**
```yaml
name: eos
version: "0.3.0"
backend: cmake
cmake:
  build_type: Release
  defines:
    EOS_BUILD_TESTS: "ON"
    EOS_PLATFORM: "linux"
```

**eboot/build.yaml:**
```yaml
name: eboot
version: "0.3.0"
backend: cmake
cmake:
  build_type: Release
  defines:
    EBLDR_BUILD_TESTS: "ON"
```

ebuild works with **any project** — not just eos and eboot. Drop a `build.yaml` in any CMake, Make, Meson, or Cargo project and `ebuild build` just works.

---

## ⚙️ Backend Auto-Detection

ebuild detects the build system from project files:

| File Found | Backend Selected | Tier |
| --- | --- | --- |
| `CMakeLists.txt` | cmake | 2 — Generator |
| `meson.build` | meson | 2 — Generator |
| `Cargo.toml` | cargo | 2 — Generator |
| `Kconfig` | kbuild | 2 — Generator |
| `Makefile` / `makefile` | make | 1 — Low-level |
| `build.ninja` | ninja | 1 — Low-level |
| `west.yml` | zephyr | 3 — Framework |
| `Config.in` + `Makefile` | buildroot | 3 — Framework |

Override with `--backend <name>` or set `backend:` in `build.yaml`.

---

## 📂 Project Structure

```text
ebuild/
├── ebuild/
│   ├── cli/                    # CLI interface (Click)
│   │   ├── commands.py         #   All commands: build, system, firmware, clean, info
│   │   └── logger.py           #   Colored output
│   ├── core/                   # Core engine
│   │   ├── config.py           #   YAML config parser
│   │   └── graph.py            #   Dependency graph
│   ├── build/                  # Build backends
│   │   ├── dispatch.py         #   Backend auto-detection + routing
│   │   ├── ninja_backend.py    #   Ninja file generator (ebuild's own)
│   │   ├── compiler.py         #   Compiler abstraction
│   │   ├── toolchain.py        #   Toolchain resolution
│   │   └── backends/           #   External build system wrappers
│   │       ├── cmake_backend.py    # Tier 2: CMake
│   │       ├── make_backend.py     # Tier 1: GNU Make
│   │       ├── meson_backend.py    # Tier 2: Meson
│   │       ├── kbuild_backend.py   # Tier 2: Linux Kbuild
│   │       ├── cargo_backend.py    # Tier 2: Rust Cargo
│   │       ├── zephyr_backend.py   # Tier 3: Zephyr RTOS
│   │       ├── freertos_backend.py # Tier 3: FreeRTOS
│   │       └── nuttx_backend.py    # Tier 3: NuttX RTOS
│   ├── packages/               # Package manager
│   │   ├── recipe.py, registry.py, resolver.py
│   │   ├── fetcher.py, builder.py, cache.py
│   │   └── lockfile.py
│   ├── system/                 # Version 2: OS image builder
│   │   ├── rootfs.py           #   FHS skeleton, init, users
│   │   ├── image.py            #   raw, qcow2, tar, ext4, squashfs
│   │   └── kernel.py           #   Kernel build orchestration
│   └── firmware/               # Version 2: RTOS firmware builder
│       ├── firmware.py         #   RTOS build dispatch
│       └── flash.py            #   Flash tools (openocd, pyocd, nrfjprog)
├── examples/
│   ├── hello_world/            # Tier 1: simple Makefile project
│   ├── multi_target/           # Tier 2: CMake multi-target
│   ├── with_packages/          # Tier 2: with package deps
│   ├── rtos_firmware/          # Tier 3: FreeRTOS firmware
│   └── linux_image/            # Tier 3: Linux system image
├── recipes/                    # Package recipes (YAML)
└── pyproject.toml
```

---

## 🔧 Supported Build Systems

### Tier 1 — Low-level Build Tools

| Backend | What it does | When to use |
| --- | --- | --- |
| **make** | Reads `Makefile`, runs `gcc`/`g++` directly | Simple projects, legacy code |
| **ninja** | Reads `build.ninja`, fast incremental | Performance-critical builds |

### Tier 2 — Build System Generators

| Backend | What it does | When to use |
| --- | --- | --- |
| **cmake** | `CMakeLists.txt` → Makefiles/Ninja → build | Most C/C++ projects |
| **meson** | `meson.build` → Ninja → build | Modern C/C++ projects |
| **kbuild** | `Kconfig` + `make` → Linux kernel builds | Kernel, kernel modules |
| **cargo** | `Cargo.toml` → Rust builds | Rust projects |

### Tier 3 — Full Build Frameworks

| Backend | What it does | When to use |
| --- | --- | --- |
| **buildroot** | Toolchain + kernel + rootfs → complete Linux | Embedded Linux systems |
| **zephyr** | `west build` → RTOS firmware | Zephyr RTOS projects |
| **freertos** | CMake → FreeRTOS firmware | FreeRTOS projects |
| **nuttx** | `make` + Kconfig → NuttX firmware | NuttX RTOS projects |
| **system** | ebuild's rootfs + kernel + image pipeline | Custom embedded Linux |

---

## 📦 Package Management

```bash
ebuild add zlib                       # add to build.yaml
ebuild add libpng --version 1.6.40
ebuild install                        # fetch + build all packages
ebuild list-packages                  # show available recipes
```

Packages are defined as YAML recipes, resolved with topological sort, built and cached locally, pinned in `ebuild.lock` for reproducibility.

---

## 🤖 RTOS Firmware

```bash
ebuild firmware --rtos zephyr --board nrf52840dk_nrf52840
ebuild firmware --rtos freertos --board stm32f4
ebuild firmware --rtos nuttx --board sim:nsh
```

---

## 🐧 Linux System Images

```bash
ebuild system --format tar            # rootfs tar archive
ebuild system --format raw --size 512 # raw disk image (512MB)
ebuild system --format qcow2 --size 1024  # QEMU qcow2 image
ebuild system --format ext4 --size 256    # ext4 filesystem image
ebuild system --format squashfs       # read-only squashfs
```

---

## 🧠 EoS AI — Hardware Design Analyzer

The `eos_ai/` module analyzes hardware designs and generates all configs needed for eos + eboot. **No server needed. No API key. Offline rule engine.**

```bash
# Analyze from text prompt
ebuild analyze "STM32H7 with 2MB flash, 1MB RAM, UART SPI I2C CAN WiFi BLE PWM ADC"

# Analyze from hardware design file
ebuild analyze --file hardware/board/schematic.kicad_sch

# Generate eboot C headers from boot.yaml
ebuild generate-boot boot.yaml --output-dir _generated/
```

### What it generates

| Output | Used By |
|---|---|
| `board.yaml` | eos board definition |
| `boot.yaml` | eboot flash layout + boot policy |
| `build.yaml` | ebuild project config |
| `eos_product_config.h` | C header with `EOS_ENABLE_*` flags |
| `eboot_flash_layout.h` | C header with flash addresses/sizes |
| `eboot_memory.ld` | Linker script memory regions |
| `eboot_config.cmake` | CMake definitions for eboot |

### Supported MCUs (built-in rule engine)

| MCU | Architecture | Core | Vendor |
|---|---|---|---|
| STM32F4 | ARM | Cortex-M4 | ST |
| STM32H7 | ARM | Cortex-M7 | ST |
| nRF52 | ARM | Cortex-M4F | Nordic |
| ESP32 | Xtensa | LX6 | Espressif |
| RP2040 | ARM | Cortex-M0+ | Raspberry Pi |
| i.MX8M | ARM64 | Cortex-A53 | NXP |

### Full pipeline test

```bash
# Run the end-to-end pipeline test (zero dependencies)
python test_full_pipeline.py

# Test with custom prompt
python test_full_pipeline.py --text "nRF52 with BLE, SPI, I2C, 512KB flash"
```

---

## 📁 Hardware Design Intake

The `hardware/` folder is where hardware teams place design documents for analysis:

```text
hardware/
├── soc/         # SoC datasheets, reference manuals, errata
├── board/       # Schematics, BOMs, pin maps
├── storage/     # Flash, eMMC, DDR datasheets
├── boot/        # Boot flow, image layout, secure boot docs
└── software/    # Device tree, linker scripts, board configs
```

See `hardware/README.md` for the full intake spec.

---

## 🚀 CI/CD

GitHub Actions runs on every push/PR to `master`:

- **Lint**: flake8, black, isort
- **Test matrix**: Linux × Windows × macOS × Python 3.9/3.11/3.12 (9 jobs)
- **Build sanity**: EoS AI pipeline test + verify generated files
- **Releases**: Tag `v*.*.*` → auto-changelog → GitHub Release → PyPI publish

```bash
git tag v1.0.0
git push origin v1.0.0
```

---

## 🧪 Unit Tests

```bash
# Run EoS AI tests (23 tests, zero external dependencies)
python tests/test_eos_ai.py

# Run full pipeline test
python test_full_pipeline.py
```

| Test Suite | Tests | Coverage |
|---|---|---|
| `TestHardwareAnalyzer` | 16 | MCU detection (6 families), peripherals, memory, clock, BOM |
| `TestHardwareProfile` | 4 | has_peripheral, get_eos_enables, to_dict, empty |
| `TestEosAIIntegration` | 3 | Full STM32H7 pipeline, nRF52, unknown MCU |

---

## 🎯 Use Cases

### Who uses ebuild and why

| Customer | Use Case | Backend | Key Features Used |
|---|---|---|---|
| **Embedded startup** | Build firmware for STM32 + flash | cmake | Auto-detect, cross-compile, `ebuild firmware` |
| **IoT product team** | Build Linux image for gateway | buildroot + system | `ebuild system --format tar`, rootfs assembly |
| **Automotive developer** | Build RTOS firmware for ECU | cmake + freertos | `ebuild firmware --rtos freertos --board stm32f4` |
| **Hardware team** | Analyze schematic → generate configs | eos_ai | `ebuild analyze --file schematic.kicad_sch` |
| **DevOps engineer** | CI/CD pipeline for firmware releases | cmake + ninja | `ebuild build && ebuild system`, lockfile |
| **Rust embedded dev** | Cross-compile Rust for Cortex-M | cargo | `ebuild build --backend cargo` |
| **Linux kernel dev** | Build kernel + modules | kbuild | `ebuild build --backend kbuild` |
| **Zephyr RTOS dev** | Build Zephyr app for nRF52 | zephyr | `ebuild firmware --rtos zephyr --board nrf52840dk` |
| **Legacy project** | Build old Makefile project | make | `ebuild build --backend make` |
| **Multi-repo team** | Build eos + eboot + app together | cmake | `ebuild build` in each repo |

### ebuild standalone (without eos or eboot)

```bash
# Build any CMake project — ebuild auto-detects CMakeLists.txt
cd my-project/
ebuild build

# Build any Makefile project
cd legacy-project/
ebuild build --backend make

# Build any Rust project
cd my-rust-firmware/
ebuild build --backend cargo
```

### ebuild with Yocto / Buildroot

```bash
# Use ebuild as a host tool inside Yocto/Buildroot build
# Just pip install in the build container
pip install ebuild
ebuild firmware --rtos freertos --board stm32f4
```

---

## ⚠️ Related Projects

| Project | Purpose |
| --- | --- |
| **eos** | Embedded OS — HAL, RTOS kernel, drivers, services |
| **eboot** | Bootloader — multicore, secure boot, firmware update |

ebuild builds **eos** and **eboot** projects, plus any CMake/Make/Meson/Cargo project.

---

## 📜 License

MIT License
