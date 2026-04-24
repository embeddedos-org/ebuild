# ⚙️ ebuild — EoS Embedded Build System

[![CI](https://github.com/embeddedos-org/ebuild/actions/workflows/ci.yml/badge.svg)](https://github.com/embeddedos-org/ebuild/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Version](https://img.shields.io/github/v/tag/embeddedos-org/ebuild?label=version)](https://github.com/embeddedos-org/ebuild/releases/latest)

> **⚠️ Not Gentoo ebuilds.** This is the **EmbeddedOS Build Tool** — a unified build system for the [EoS embedded OS](https://github.com/embeddedos-org/eos). Not related to [Gentoo's ebuild format](https://wiki.gentoo.org/wiki/Ebuild).

**One command — from hardware schematic to deployable firmware.**

`ebuild` reads your KiCad/Eagle schematics or board descriptions, auto-generates all build configs, and compiles firmware for 73+ embedded targets.

---

## Quick Start

```bash
# Linux / macOS
git clone https://github.com/embeddedos-org/ebuild.git
cd ebuild
./install.sh         # or: pip install -e .
ebuild --version     # ebuild, version 0.1.0

# Windows
git clone https://github.com/embeddedos-org/ebuild.git
cd ebuild
install.bat
```

---

## Hands-On Examples

### 1. Build Hello World
```bash
cd examples/hello_world
ebuild info && ebuild build && ./_build/hello
# → "Hello from EoS Build System!"
```

### 2. Build Multi-Target (Library + Executable)
```bash
cd examples/multi_target
ebuild build && ./_build/myapp
# → add=17, subtract=7, multiply=60, factorial=120
```

### 3. Analyze Hardware → Generate 9 Config Files
```bash
# KiCad schematic (real S-expression parser)
ebuild analyze --file hardware/board/sample_stm32f4_sensor.kicad_sch --output-dir /tmp/configs

# YAML board description
ebuild analyze --file hardware/board/sample_iot_gateway.yaml --output-dir /tmp/iot

# CSV BOM
echo "Reference,Value
U1,STM32F407VGT6
U2,BME280" > /tmp/bom.csv
ebuild analyze --file /tmp/bom.csv --output-dir /tmp/bom_out

# Plain text
echo "STM32H743 at 480MHz with SPI flash, I2C sensors, CAN bus" > /tmp/desc.txt
ebuild analyze --file /tmp/desc.txt --output-dir /tmp/txt_out
```

### 4. Scaffold a New Project
```bash
ebuild new my_sensor --template bare-metal --board stm32f4
ebuild new my_ble    --template ble-sensor  --board nrf52
ebuild new my_motor  --template rtos-app    --board stm32h7
ebuild new my_gw     --template linux-app   --board rpi4
```

### 5. Build EoS + eBoot (Single-Phase)
```bash
git clone https://github.com/embeddedos-org/eos.git && cd eos
ebuild build    # Builds 25 libraries (3 eBoot + 22 EoS) in ~5 seconds
```

---

## Supported Input Formats

| Input | Format | Parser |
|---|---|---|
| `.kicad_sch` | KiCad 6/7/8 schematic | S-expression parser — components, nets, wires, MCU, pins |
| `.sch` (XML) | Eagle schematic | XML parser — components, nets, peripherals |
| `.csv` | BOM export | BOM parser + ComponentDB (200+ ICs with I2C addrs) |
| `.yaml` | Board description | Keyword extraction + MCU DB (160+ MCUs) |
| `.txt` / `.md` | Any text | Keyword extraction for MCU names, peripherals |

---

## Generated Files — Detailed Explanation

Each `ebuild analyze` produces **9 files** in ~260ms:

### 1. `board.yaml` — Hardware Board Description

**Used by:** EoS build system, device drivers, board support packages.

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
  - name: BME280       # Detected from KiCad component
    type: i2c
  - name: W25Q128
    type: spi
  - name: SN65HVD230
    type: can
  - name: UART
    type: uart
```

### 2. `boot.yaml` — Bootloader Flash Layout

**Used by:** eBoot bootloader, OTA update system.

```yaml
boot:
  flash_base: '0x08000000'
  flash_size: 1048576
  layout:
    stage0:              # First-stage bootloader
      offset: '0x0'
      size: 16384        # 16KB
    stage1:              # Boot manager
      offset: '0x4000'
      size: 65536        # 64KB
    slot_a:              # Firmware slot A
      offset: '0x16000'
      size: 479232       # ~468KB
    slot_b:              # Firmware slot B (OTA target)
      offset: '0x8b000'
      size: 479232
  policy:
    max_boot_attempts: 3
    require_signature: true    # Ed25519
    anti_rollback: true
```

### 3. `build.yaml` — Build Configuration

**Used by:** `ebuild build`, CI/CD.

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

### 4. `eos_product_config.h` — C Feature Header

**Used by:** Firmware source code (`#include "eos_product_config.h"`).

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

### 5. `eboot_flash_layout.h` — Bootloader Flash Constants

**Used by:** eBoot C code (`#include "eboot_flash_layout.h"`).

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

### 6. `eboot_memory.ld` — Linker Script

**Used by:** GCC linker (`-T eboot_memory.ld`). Places bootloader code at correct flash addresses.

### 7. `eboot_config.cmake` — CMake Definitions

**Used by:** CMake when building eBoot. Sets `EBLDR_BOARD`, flash sizes, security flags.

### 8. `pack_image.sh` — Firmware Signing Script

**Used by:** CI pipeline. Computes SHA-256, prepends eBoot header → `firmware.signed.bin`.

### 9. `llm_prompt.txt` — Optional LLM Enhancement

**Used by:** Optionally pass to Ollama/OpenAI for pin muxing, DMA, interrupt suggestions.

### File Flow Diagram

```
Hardware (.kicad_sch / .yaml / .csv)
         │
  ebuild analyze
         │
    ┌────┼────┐
    ▼    ▼    ▼
 board  boot  build     ← YAML configs
 .yaml  .yaml .yaml
    │    │    │
    ▼    ▼    ▼
 eos_   eboot_ eboot_   ← C headers + linker + cmake
 config flash  memory
 .h     .h     .ld
         │
    ebuild build
         │
         ▼
  firmware.signed.bin 🚀
```

---

## How ebuild and eBoot Work Together

```
ebuild = CONFIGURATION GENERATOR  (runs on your laptop at build time)
eBoot  = BOOTLOADER               (runs on the MCU at power-on)
```

### Flow 1: eBoot WITHOUT ebuild (manual)

```bash
# Write flash layout header by hand (calculate offsets from datasheet)
vim eboot_flash_layout.h

# Build eBoot standalone
cd ~/EoS/eBoot
cmake -B build -DEBLDR_BOARD=none && cmake --build build
```

⚠️ Manual offset calculation, no validation, no linker script.

### Flow 2: ebuild + eBoot TOGETHER (automated)

```bash
# ebuild generates everything from your schematic
ebuild analyze --file board.kicad_sch --output-dir configs/

# Build eos + eBoot in one command
cd ~/EoS/eos && ebuild build
```

✅ Auto-calculated, validated, linker script + signing script included.

### Comparison

| | WITHOUT ebuild | WITH ebuild |
|---|---|---|
| Config files | 1 (manual) | 9 (auto-generated) |
| Time to configure | ~5-10 minutes | ~260ms |
| Flash layout | Calculate by hand | Auto-calculated |
| Linker script | Write by hand | Auto-generated |
| Validation | None | Schema validated |
| Human errors | Likely | Eliminated |

---

## Sample Board Files

| File | Format | MCU | Peripherals |
|------|--------|-----|-------------|
| `sample_stm32f4_sensor.kicad_sch` | **KiCad** | STM32F407 | BME280, W25Q128, CAN, USB |
| `sample_iot_gateway.yaml` | YAML | STM32H743 | 18 — CAN, WiFi, BLE, ETH, GPS |
| `sample_ble_sensor.yaml` | YAML | nRF52840 | BLE 5.0, NFC, coin cell |
| `sample_esp32s3_display.yaml` | YAML | ESP32-S3 | WiFi, LCD, touch, camera |
| `sample_riscv_industrial.yaml` | YAML | GD32VF103 | RS485, CAN, 4-20mA |
| `sample_rpi4_gateway.yaml` | YAML | BCM2711 | Gigabit ETH, WiFi, 4GB |

---

## Manual Testing Guide

### Step 1: Verify Installation
```bash
source ~/.bashrc
export PATH="$HOME/.local/bin:$PATH"
ebuild --version && cmake --version | head -1 && gcc --version | head -1
```

### Step 2: Analyze All Input Formats
```bash
cd ~/EoS/ebuild
ebuild analyze --file hardware/board/sample_stm32f4_sensor.kicad_sch --output-dir /tmp/t1
ebuild analyze --file hardware/board/sample_iot_gateway.yaml --output-dir /tmp/t2
ebuild analyze --file hardware/board/sample_ble_sensor.yaml --output-dir /tmp/t3
echo "STM32H743 with SPI, I2C, CAN" > /tmp/desc.txt
ebuild analyze --file /tmp/desc.txt --output-dir /tmp/t4
cat /tmp/t1/board.yaml
```

### Step 3: Build Examples
```bash
cd ~/EoS/ebuild/examples/hello_world && rm -rf _build && ebuild build && ./_build/hello
cd ~/EoS/ebuild/examples/multi_target && rm -rf _build && ebuild build && ./_build/myapp
```

### Step 4: Scaffold All Templates
```bash
cd /tmp && rm -rf stest
ebuild new a --template bare-metal      --board stm32f4 --output-dir /tmp/stest
ebuild new b --template ble-sensor       --board nrf52   --output-dir /tmp/stest
ebuild new c --template rtos-app         --board stm32h7 --output-dir /tmp/stest
ebuild new d --template linux-app        --board rpi4    --output-dir /tmp/stest
ebuild new e --template safety-critical  --board tms570  --output-dir /tmp/stest
ebuild new f --template secure-boot      --board stm32f4 --output-dir /tmp/stest
ls /tmp/stest/*/
```

### Step 5: eBoot Standalone
```bash
cd ~/EoS/eBoot && rm -rf build
cmake -B build -DEBLDR_BOARD=none && cmake --build build -j$(nproc)
ls build/*.a
```

### Step 6: Auto-Generated Config → Compile Test
```bash
cd ~/EoS/ebuild
ebuild analyze --file hardware/board/sample_stm32f4_sensor.kicad_sch --output-dir /tmp/auto
cat > /tmp/auto/test.c << 'EOF'
#include <stdio.h>
#include "eboot_flash_layout.h"
#include "eos_product_config.h"
int main(void) {
    printf("Product: %s (%s)\n", EOS_PRODUCT_NAME, EOS_CORE);
    printf("Flash: 0x%08X (%dKB)\n", EBOOT_FLASH_BASE, EBOOT_FLASH_SIZE/1024);
    printf("Peripherals:");
    #if EOS_ENABLE_UART
    printf(" UART");
    #endif
    #if EOS_ENABLE_SPI
    printf(" SPI");
    #endif
    #if EOS_ENABLE_I2C
    printf(" I2C");
    #endif
    #if EOS_ENABLE_CAN
    printf(" CAN");
    #endif
    printf("\nPASS\n");
    return 0;
}
EOF
gcc -o /tmp/auto/test /tmp/auto/test.c -I/tmp/auto && /tmp/auto/test
```

### Step 7: Full eos + eBoot Build
```bash
cd ~/EoS/eos && rm -rf _build
cmake -B _build -DEOS_BUILD_TESTS=ON -DEOS_FETCH_DEPS=OFF
cmake --build _build -j$(nproc)
cd _build && ctest --output-on-failure
```

### Step 8: Same via ebuild CLI
```bash
cd ~/EoS/eos && rm -rf _build && ebuild build
```

---

## CLI Reference

| Command | Description |
|---------|-------------|
| `ebuild build` | Build project (auto-detects backend) |
| `ebuild info` | Show targets, deps, build order |
| `ebuild analyze --file <f>` | Hardware → config files |
| `ebuild new <name> --template <t> --board <b>` | Scaffold project |
| `ebuild list-packages` | List package recipes |
| `ebuild install` | Fetch and build packages |
| `ebuild clean` | Remove build directory |
| `ebuild configure` | Generate build files only |
| `ebuild firmware` | Build RTOS firmware |
| `ebuild system` | Build Linux system image |
| `ebuild setup` | Clone eos + eboot to cache |
| `ebuild repos` | Manage cached repos |

---

## Performance

| Operation | Time |
|-----------|------|
| Hardware analyze → 9 files | **261 ms** |
| Build hello_world (ninja) | **748 ms** |
| Build multi_target (ninja) | **794 ms** |
| Scaffold project | **242 ms** |
| Full eos+eboot build (100 .c) | **4.4 sec** |
| Full eos+eboot+tests | **26.6 sec** |

---

## Architecture

```
ebuild/
├── ebuild/              Python CLI + build system
│   ├── cli/             Click commands
│   ├── build/           Multi-backend dispatch (cmake/ninja/make/meson/cargo)
│   ├── packages/        Recipe registry, resolver, cache, fetcher
│   ├── eos_ai/          Hardware analyzer + config generator
│   └── plugins/         Extensible plugin system
├── hardware/board/      Sample board files (5 YAML + 1 KiCad)
├── recipes/             Package recipes (freertos, lwip, mbedtls, zlib, littlefs)
├── templates/           Project templates (6 types)
├── examples/            Working build examples
├── layers/              Optional: EAI, ENI, EIPC, eOSuite
├── sdk/                 SDK generator
├── install.sh           Linux/macOS installer
└── install.bat          Windows installer
```

---

## Security

ebuild handles security-sensitive operations including firmware signing and LLM API access:

- **Firmware signing** — `pack_image.sh` reads signing keys from file paths passed as arguments; private keys are never embedded in generated scripts
- **LLM integration** — API keys are loaded exclusively from environment variables (`OPENAI_API_KEY`, `EOS_LLM_API_KEY`); no keys are stored in source code or generated configs
- **Supply chain** — `sbom.json` provides a full Software Bill of Materials; Dependabot and Scorecard workflows run automatically
- **Build outputs** — generated headers and linker scripts contain only public configuration constants; no secrets are written to build artifacts
- **CI/CD** — CodeQL analysis, nightly and weekly security scans, and OpenSSF Scorecard are enabled

### Reporting Vulnerabilities

If you discover a security vulnerability, please **do not** open a public issue. Instead, email **security@embeddedos.org** with:

1. Description of the vulnerability
2. Steps to reproduce
3. Affected versions

We aim to acknowledge reports within 48 hours and provide a fix within 7 days for critical issues.

See [SECURITY.md](SECURITY.md) for the full security policy.

---

## Related Repos

| Repo | Description |
|------|-------------|
| [eos](https://github.com/embeddedos-org/eos) | Embedded OS — HAL, kernel, drivers, services |
| [eBoot](https://github.com/embeddedos-org/eBoot) | Secure bootloader — 83 boards, A/B update, chain of trust |
| **ebuild** (this repo) | Build system, hardware analyzer, SDK generator |

Clone just `eos` and it auto-fetches `eBoot` at build time. Use `ebuild` for the full CLI tooling.

## License

MIT — see [LICENSE](LICENSE).
