# eboot Installation & Usage Guide

## Installation

eboot is a C project built with CMake. No package manager needed — just clone, configure, and build.

### Prerequisites

| Tool | Required? | Purpose |
|---|---|---|
| CMake 3.15+ | ✅ Required | Build system generator |
| GCC / Clang / MSVC | ✅ Required | C compiler (any) |
| ARM GCC | For ARM boards | `arm-none-eabi-gcc` |
| RISC-V GCC | For RISC-V boards | `riscv64-unknown-elf-gcc` |
| Python 3.9+ | For host tools | image packing, signing |

### 🐧 Linux

```bash
# Install build tools
sudo apt install cmake gcc g++ make python3

# Clone and build
git clone https://github.com/embeddedos-org/eboot.git
cd eboot
cmake -B build -DEBLDR_BUILD_TESTS=ON
cmake --build build

# Run tests
ctest --test-dir build --output-on-failure

# Install cross-compilers for target boards
sudo apt install gcc-arm-none-eabi   # ARM Cortex-M/R
sudo apt install gcc-aarch64-linux-gnu  # ARM64 Linux
```

### 🪟 Windows

```powershell
# Option A: Visual Studio
# Install "Desktop development with C++" workload from Visual Studio Installer
# Install CMake from https://cmake.org/download/

git clone https://github.com/embeddedos-org/eboot.git
cd eboot
cmake -B build -DEBLDR_BUILD_TESTS=ON
cmake --build build --config Release

# Option B: MinGW / MSYS2
pacman -S cmake gcc make
cmake -B build -G "MinGW Makefiles" -DEBLDR_BUILD_TESTS=ON
cmake --build build
```

### 🍎 macOS

```bash
brew install cmake
xcode-select --install  # Clang compiler

git clone https://github.com/embeddedos-org/eboot.git
cd eboot
cmake -B build -DEBLDR_BUILD_TESTS=ON
cmake --build build
ctest --test-dir build
```

### Via ebuild (recommended)

```bash
# If you have ebuild installed, it builds eboot automatically
cd eboot
ebuild build
```

---

## Usage — How to Use eboot in Your Project

### Step 1: Choose your board

```bash
# See available boards
ls boards/
# stm32f4  stm32h7  nrf52  samd51  rpi4  imx8m  am64x
# riscv64_virt  sifive_u  esp32  x86_64_efi

# Build for STM32F4 (requires arm-none-eabi-gcc)
cmake -B build -DEBLDR_BOARD=stm32f4 \
  -DCMAKE_TOOLCHAIN_FILE=toolchains/arm-none-eabi.cmake
cmake --build build
```

### Step 2: Configure boot policy

Create a `boot.yaml` (or use ebuild's EoS AI to generate one):

```yaml
boot:
  board: stm32f4
  arch: arm
  flash_base: "0x08000000"
  flash_size: 1048576    # 1MB
  layout:
    stage0:
      offset: "0x0"
      size: 16384          # 16KB
    stage1:
      offset: "0x4000"
      size: 65536          # 64KB
    bootctl_primary:
      offset: "0x14000"
      size: 4096
    bootctl_backup:
      offset: "0x15000"
      size: 4096
    slot_a:
      offset: "0x16000"
      size: 479232
    slot_b:
      offset: "0x8B000"
      size: 479232
  policy:
    max_boot_attempts: 3
    watchdog_timeout_ms: 5000
    require_signature: true
```

### Step 3: Generate C headers from config

```bash
# Generate flash layout header + linker script
python scripts/generate_config.py boot.yaml generated/

# Output:
#   generated/eboot_generated_layout.h   — #define constants
#   generated/eboot_generated_memory.ld  — MEMORY regions
```

### Step 4: Build your firmware application

```c
// Your app (runs after eboot hands off)
#include <stdint.h>

void main(void) {
    // eboot already initialized hardware, verified image, jumped here
    // Your application starts running
    while (1) {
        // application logic
    }
}
```

### Step 5: Pack and sign firmware image

```bash
# Pack firmware with eboot image header
python tools/imgpack.py firmware.bin --output firmware.packed.bin

# Sign the image
python tools/sign_image.py firmware.packed.bin --key signing_key.pem

# Flash to board
python tools/uart_recovery.py --port /dev/ttyUSB0 firmware.packed.bin
```

### Step 6: Confirm boot (in your app)

```c
#include "eos_bootctl.h"

void app_init(void) {
    eos_bootctl_t bctl;
    eos_bootctl_load(&bctl);

    // Tell eboot this boot succeeded — don't rollback
    eos_bootctl_confirm(&bctl);
}
```

---

## Boot Flow

```
Power On
  │
  ▼
Stage-0 (≤16KB, immutable)
  ├── Minimal HW init (clocks, watchdog)
  ├── Check recovery pin
  └── Jump to Stage-1
        │
        ▼
Stage-1 (≤64KB)
  ├── Load boot control block
  ├── Select boot slot (A or B)
  ├── Verify image (SHA-256 + signature)
  ├── Check boot attempt counter
  ├── If max attempts exceeded → rollback to other slot
  └── Jump to application
        │
        ▼
Application (your firmware / RTOS / Linux)
  └── Call eos_bootctl_confirm() to mark boot successful
```

---

## API Quick Reference

| Header | Purpose | Key Functions |
|---|---|---|
| `eos_bootctl.h` | Boot control block | `load`, `save`, `confirm`, `set_pending`, `request_recovery` |
| `eos_image.h` | Image verification | `verify_header`, `verify_hash`, `verify_signature` |
| `eos_fwsvc.h` | Firmware services | `get_version`, `get_slot`, `mark_valid` |
| `eos_fw_update.h` | OTA update | `begin`, `write`, `finalize`, `progress` |
| `eos_rtos_boot.h` | RTOS boot | `detect`, `boot`, MPU config |
| `eos_multicore.h` | Multicore | `start_smp`, `start_amp`, `boot_all` |
| `eos_board_config.h` | HW config | Pin/memory/clock/IRQ macros |
| `eos_boot_menu.h` | Boot menu | UART-based interactive menu |
| `eos_device_table.h` | Device table | UEFI-style resource table |
| `eos_runtime_svc.h` | Runtime services | Get/set variables, reset, time |
