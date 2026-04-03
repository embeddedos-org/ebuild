# 🔧 eBootloader

[![CI](https://github.com/embeddedos-org/eboot/actions/workflows/ci.yml/badge.svg)](https://github.com/embeddedos-org/eboot/actions/workflows/ci.yml)
[![Nightly](https://github.com/embeddedos-org/eboot/actions/workflows/nightly.yml/badge.svg)](https://github.com/embeddedos-org/eboot/actions/workflows/nightly.yml)
[![Release](https://github.com/embeddedos-org/eboot/actions/workflows/release.yml/badge.svg)](https://github.com/embeddedos-org/eboot/actions/workflows/release.yml)
[![Version](https://img.shields.io/github/v/tag/embeddedos-org/eboot?label=version)](https://github.com/embeddedos-org/eboot/releases/latest)

**Multi-platform modular bootloader with multicore, secure boot, and firmware update support**

eBootloader is a production-grade boot platform for embedded systems — supporting **24 board ports** across **10 architectures**, with clean separation between boot logic, hardware abstraction, and firmware management.

→ **New to eboot?** See the [Quickstart Guide](docs/quickstart.md) — build and flash in 3 commands.

→ **Using with eos?** See the [Integration Guide](../eos/docs/integration-guide.md) — how eos + eboot + ebuild work together.

---

## ✨ Key Features

| Category | Features |
| --- | --- |
| **Boot Management** | Staged boot (stage-0 + stage-1), A/B slots with automatic rollback, boot policy engine |
| **Secure Boot** | Self-contained SHA-256, CRC-32, Ed25519 signature stubs, anti-rollback |
| **Firmware Update** | Stream-based pipeline (256B chunks), XMODEM/YMODEM/raw transports, pluggable custom transports |
| **Multicore** | SMP, AMP, lockstep boot; ARM PSCI, RISC-V SBI HSM, x86 SIPI, mailbox support |
| **Hardware Config** | Declarative pin muxing, memory regions, interrupt priorities, clock trees via macros |
| **RTOS Boot** | Auto-detect FreeRTOS/Zephyr/NuttX, MPU config, structured boot parameter handoff |
| **UEFI-like** | Device table, runtime services (variables, reset, time), interactive boot menu |
| **Board Registry** | Runtime multi-board selection, GCC constructor auto-registration |
| **Recovery** | UART-based recovery protocol, hardware pin trigger, factory reset |
| **Platforms** | ARM Cortex-M/A, RISC-V 32/64, Xtensa, x86_64, PowerPC, SPARC, SuperH, M68K — 24 board ports |

---

## 🏗 Architecture

```text
┌─────────────────────────────────────────────────────────┐
│                    Boot Flow                             │
│  ROM → Stage-0 → Stage-1 → App (Linux / RTOS)           │
├─────────────────────────────────────────────────────────┤
│              Core Libraries (platform-agnostic)          │
│                                                          │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │ Boot    │ │ Firmware │ │ Multicore│ │ Board      │  │
│  │ Control │ │ Update   │ │ Boot     │ │ Config     │  │
│  │ & Slots │ │ Pipeline │ │ SMP/AMP  │ │ Pins/Mem   │  │
│  └────┬────┘ └────┬─────┘ └────┬─────┘ └──────┬─────┘  │
│       │           │            │               │         │
│  ┌────┴───┐  ┌────┴────┐ ┌────┴─────┐  ┌─────┴──────┐  │
│  │ Crypto │  │Transport│ │ RTOS     │  │ Device     │  │
│  │ SHA-256│  │ XMODEM  │ │ Detect & │  │ Table &    │  │
│  │ CRC-32 │  │ YMODEM  │ │ Boot     │  │ Runtime Svc│  │
│  └────────┘  └─────────┘ └──────────┘  └────────────┘  │
├─────────────────────────────────────────────────────────┤
│              HAL + Board Registry                        │
│  eos_board_ops_t vtable → dispatches to active board     │
├──────┬───────┬───────┬───────┬───────┬───────┬──────────┤
│ STM32│ nRF52 │ RPi4  │ i.MX8 │RISC-V │ ESP32 │ x86_64  │
│  F4  │       │       │   M   │  virt │       │  EFI    │
│  H7  │ SAMD51│       │ AM64x │SiFive │       │         │
└──────┴───────┴───────┴───────┴───────┴───────┴──────────┘
```

---

## 📂 Repository Structure

```text
eboot/
├── include/                  # Public headers
│   ├── eos_types.h           #   Return codes, slot types, flags
│   ├── eos_hal.h             #   Board HAL vtable + platform enum
│   ├── eos_bootctl.h         #   Boot control block
│   ├── eos_image.h           #   Image header + verification
│   ├── eos_fwsvc.h           #   Firmware services API
│   ├── eos_fw_update.h       #   Stream-based firmware update
│   ├── eos_fw_transport.h    #   Pluggable transport layer
│   ├── eos_multicore.h       #   Multicore/multiprocessor boot
│   ├── eos_board_config.h    #   Declarative hardware config
│   ├── eos_board_registry.h  #   Runtime board selection
│   ├── eos_rtos_boot.h       #   RTOS detection + boot
│   ├── eos_boot_menu.h       #   Interactive boot menu
│   ├── eos_device_table.h    #   UEFI-style device table
│   ├── eos_runtime_svc.h     #   Runtime services
│   ├── eos_crypto_boot.h     #   SHA-256 + signature verify
│   ├── eos_dram.h            #   DDR/LPDDR init + training
│   ├── eos_pci.h             #   PCI/PCIe bus enumeration
│   ├── eos_storage.h         #   Unified storage (NOR/NAND/eMMC/SD/NVMe)
│   ├── eos_power.h           #   Power management, PMIC, reset cause
│   ├── eos_clock.h           #   Clock tree init (PLL, dividers)
│   └── eos_mpu_boot.h        #   MPU config before OS handoff
├── core/                     # Core logic (platform-agnostic C)
├── hal/                      # HAL dispatch + board registry
├── stage0/                   # Minimal first-stage bootloader
├── stage1/                   # Stage-1 boot manager
├── boards/                   # Board ports (24 platforms)
│   ├── stm32f4/              #   ARM Cortex-M4 (reference)
│   ├── stm32h7/              #   ARM Cortex-M7
│   ├── nrf52/                #   ARM Cortex-M4F (BLE)
│   ├── samd51/               #   ARM Cortex-M4F (Microchip)
│   ├── rpi4/                 #   ARM64 Cortex-A72
│   ├── imx8m/                #   ARM64 Cortex-A53 (NXP)
│   ├── am64x/                #   ARM Cortex-A53+R5F (TI)
│   ├── riscv64_virt/         #   RISC-V 64 (QEMU)
│   ├── sifive_u/             #   RISC-V U74 (SiFive)
│   ├── esp32/                #   Xtensa LX6 (Espressif)
│   ├── x86_64_efi/           #   x86_64 UEFI
│   ├── powerpc/              #   PowerPC
│   ├── sparc/                #   SPARC LEON
│   ├── m68k/                 #   Motorola 68K
│   ├── sh4/                  #   SuperH SH-4
│   └── ...                   #   + 8 more architectures
├── tests/                    # Unit tests (native host)
├── tools/                    # Host tools (imgpack, signing)
└── docs/                     # Documentation
```

---

## 🔨 Building

```bash
# Native build — core libraries + unit tests (no board ports)
cmake -B build -DEBLDR_BUILD_TESTS=ON
cmake --build build
ctest --test-dir build

# Cross-compile for a specific board
cmake -B build -DEBLDR_BOARD=stm32f4 \
  -DCMAKE_TOOLCHAIN_FILE=toolchains/arm-none-eabi.cmake
cmake --build build
```

The build system separates **core libraries** (compile on any host) from **board ports** (require matching cross-compiler). Native builds produce `eboot_hal.lib`, `eboot_core.lib`, `eboot_stage1.lib` — sufficient for unit tests and host-side tools.

---

## 🖥 Multicore / Multiprocessor Boot

eboot manages secondary cores across three modes:

| Mode | Description | Example |
| --- | --- | --- |
| **SMP** | Same firmware, shared memory | RPi4 (4× A72), ESP32 (2× Xtensa) |
| **AMP** | Different firmware per core | TI AM64x (R5F + A53) |
| **Lockstep** | Identical code, safety-critical | STM32H7 dual-core |

Start methods are platform-aware:

| Method | Platform | Mechanism |
| --- | --- | --- |
| `EOS_START_PSCI` | ARM Cortex-A | PSCI CPU_ON SMC |
| `EOS_START_SBI_HSM` | RISC-V | SBI Hart State Management |
| `EOS_START_SIPI` | x86_64 | Startup IPI |
| `EOS_START_REG` | ESP32 | RTC register release |
| `EOS_START_MAILBOX` | Custom | Shared-memory handshake |

```c
#include "eos_multicore.h"

// SMP — start core 1 with same firmware
eos_multicore_start_smp(1, 0x08020000, 0x20010000);

// AMP — boot Cortex-R5F from Slot A, Cortex-A53 from Slot B
eos_multicore_start_amp(0, EOS_SLOT_A, EOS_ARCH_ARM_R5);
eos_multicore_start_amp(1, EOS_SLOT_B, EOS_ARCH_ARM_A53);

// Boot all configured cores
eos_multicore_boot_all(core_configs, num_cores);

// Wait for core 1 to reach running state
eos_multicore_wait_state(1, EOS_CORE_STATE_RUNNING, 5000);
```

---

## 🔧 Easy Hardware Configuration

Configure memory, pins, interrupts, and clocks with **declarative macros** — no register-level C code needed:

```c
#include "eos_board_config.h"

// Pins — one macro per pin
static const eos_pin_config_t pins[] = {
    EOS_PIN_UART_TX(0, 'A', 2, 7),      // USART2 TX → PA2, AF7
    EOS_PIN_UART_RX(0, 'A', 3, 7),      // USART2 RX → PA3, AF7
    EOS_PIN_I2C_SCL(0, 'B', 6, 4),      // I2C1 SCL → PB6, AF4
    EOS_PIN_I2C_SDA(0, 'B', 7, 4),      // I2C1 SDA → PB7, AF4
    EOS_PIN_LED('C', 13, true),          // LED on PC13, active-low
    EOS_PIN_RECOVERY_BTN('C', 0),        // Recovery button PC0
};

// Memory — named regions with MPU attributes
static const eos_mem_config_t memory[] = {
    EOS_MEM_FLASH(0x08000000, 1024 * 1024),
    EOS_MEM_RAM(0x20000000, 128 * 1024),
    EOS_MEM_PERIPH(0x40000000, 0x20000000),
    EOS_MEM_SHARED(0x38000000, 4096),    // multicore shared region
};

// Clocks — full PLL tree
static const eos_clock_config_t clocks = {
    .source = EOS_CLK_SRC_PLL, .sysclk_hz = 168000000,
    .hclk_hz = 168000000, .pclk1_hz = 42000000, .pclk2_hz = 84000000,
    .hse_hz = 8000000, .use_pll = true,
    .pll_m = 8, .pll_n = 336, .pll_p = 2, .pll_q = 7,
};

// Interrupts
static const eos_irq_config_t irqs[] = {
    EOS_IRQ(38, 3, true),   // USART2, priority 3
    EOS_IRQ(15, 0, true),   // SysTick, priority 0
};

// Apply everything in one call
static const eos_board_config_t config = {
    .name = "my-board", .mcu = "STM32F407VG",
    .pins = pins, .pin_count = 6,
    .memory = memory, .mem_count = 4,
    .clocks = &clocks,
    .irqs = irqs, .irq_count = 2,
};
eos_board_config_apply(&config);

// Runtime queries
uint32_t ram = eos_board_config_total_ram();
const eos_pin_config_t *tx = eos_board_config_find_pin(EOS_PIN_FUNC_UART_TX, 0);
```

---

## 📦 Firmware Update Pipeline

Stream-based — never holds the full image in RAM:

```c
#include "eos_fw_update.h"

eos_fw_update_ctx_t ctx;
eos_fw_update_begin(&ctx, EOS_SLOT_B);       // erase target slot

while (data_available()) {
    eos_fw_update_write(&ctx, chunk, len);    // stream to flash
    printf("%d%%\n", eos_fw_update_progress(&ctx));
}

eos_fw_update_finalize(&ctx, EOS_UPGRADE_TEST);  // verify + mark for boot
```

Built-in transports — XMODEM, YMODEM, raw:

```c
#include "eos_fw_transport.h"

eos_fw_transport_t tp = {
    .ops = eos_fw_transport_uart_xmodem(),
    .baudrate = 115200, .timeout_ms = 60000,
};
eos_fw_transport_update(&tp, EOS_SLOT_B, EOS_UPGRADE_TEST);
```

---

## 🤖 RTOS-Aware Boot

```c
#include "eos_rtos_boot.h"

eos_rtos_type_t type = eos_rtos_detect(slot_addr);  // FreeRTOS? Zephyr? NuttX?

eos_rtos_boot_config_t cfg = {
    .type = type, .entry_addr = 0x08020000,
    .stack_addr = 0x20020000, .mpu_mode = EOS_MPU_PROTECTED,
    .tick_rate_hz = 1000, .num_priorities = 8,
};
eos_rtos_boot(&cfg);  // configure MPU, pass boot params, jump
```

---

## 🎯 Supported Boards

| Board | Architecture | MCU / SoC | Industry Use |
| --- | --- | --- | --- |
| STM32F4 | ARM Cortex-M4 | STM32F407 | Motor control, sensors |
| STM32H7 | ARM Cortex-M7 | STM32H743 | DSP, graphics |
| nRF52 | ARM Cortex-M4F | nRF52840 | BLE wearables |
| SAMD51 | ARM Cortex-M4F | ATSAMD51 | Arduino/Adafruit IoT |
| Raspberry Pi 4 | ARM64 Cortex-A72 | BCM2711 | Edge gateways |
| NXP i.MX 8M | ARM64 Cortex-A53 | i.MX8M Mini | Industrial HMI |
| TI AM64x | ARM A53+R5F | AM6442 Sitara | PLCs, factory |
| RISC-V 64 virt | RISC-V 64 | QEMU virt | Development |
| SiFive HiFive | RISC-V U74 | FU740 | Linux eval |
| ESP32 | Xtensa LX6 | ESP32 | Wi-Fi/BLE IoT |
| x86_64 EFI | x86_64 | UEFI PCs | Edge appliances |

### Adding a new board

1. Create `boards/<name>/board_<name>.h` — memory map, constants
2. Create `boards/<name>/board_<name>.c` — implement `eos_board_ops_t`
3. Add `eboot_add_board()` in `CMakeLists.txt`
4. Optionally add linker scripts for firmware executables

---

## 🧪 Unit Tests

Tests run natively on the host using a simulated flash backend:

```bash
cmake -B build -DEBLDR_BUILD_TESTS=ON
cmake --build build
ctest --test-dir build --output-on-failure
```

Test suites:

| Test | Covers |
| --- | --- |
| `test_bootctl` | Boot control block save/load, CRC, rollback |
| `test_crypto` | SHA-256 against known vectors |
| `test_device_table` | Device table create, add, validate |
| `test_runtime_svc` | Runtime variable get/set/delete |
| `test_board_config` | Pin/memory/IRQ config lookup |
| `test_multicore` | Core state management, SMP/AMP init |
| `test_board_registry` | Board register, find, activate |

---

## 🛡 22 Core Boot Services

| # | Service | Header | Implementation |
|---|---|---|---|
| 1 | Boot control (A/B slots) | `eos_bootctl.h` | `bootctl.c` |
| 2 | Image verification | `eos_image.h` | `image_verify.c` |
| 3 | Crypto (SHA-256, CRC-32) | `eos_crypto_boot.h` | `crypto_boot.c` |
| 4 | Firmware update (stream) | `eos_fw_update.h` | `fw_update.c` |
| 5 | Transport (XMODEM/YMODEM) | `eos_fw_transport.h` | `fw_transport_uart.c` |
| 6 | Firmware services API | `eos_fwsvc.h` | `fw_services.c` |
| 7 | Multicore boot | `eos_multicore.h` | `multicore.c` |
| 8 | RTOS-aware boot | `eos_rtos_boot.h` | `rtos_boot.c` + `rtos_params.c` |
| 9 | Boot menu (UART) | `eos_boot_menu.h` | `boot_menu.c` |
| 10 | Device table (UEFI-style) | `eos_device_table.h` | `device_table.c` |
| 11 | Runtime services | `eos_runtime_svc.h` | `runtime_services.c` |
| 12 | Board config macros | `eos_board_config.h` | `board_config.c` |
| 13 | Board registry | `eos_board_registry.h` | `board_registry.c` |
| 14 | Boot policy engine | — | `boot_policy.c` |
| 15 | Slot manager | — | `slot_manager.c` |
| 16 | Recovery | — | `recovery.c` |
| 17 | DDR/DRAM init + training | `eos_dram.h` | `dram_init.c` |
| 18 | PCI/PCIe enumeration | `eos_pci.h` | `pci_enum.c` |
| 19 | Unified storage | `eos_storage.h` | `storage.c` |
| 20 | Power management | `eos_power.h` | `power_init.c` |
| 21 | Clock tree init | `eos_clock.h` | `clock_init.c` |
| 22 | MPU config | `eos_mpu_boot.h` | `mpu_boot.c` |

---

## 🔄 OTA Update Flow (eos + eboot)

Complete A/B firmware update with automatic rollback — **no external OTA framework needed**:

```
eos OTA Agent                    eboot Bootloader
──────────────                   ─────────────────
1. Download firmware
2. SHA-256 + signature verify
3. Write to Slot B (inactive)
4. eos_bootctl_set_pending(B)
5. Reboot
                                 6. Load bootctl → pending=B
                                 7. Verify Slot B image (SHA-256 + sig)
                                 8. Increment boot_attempts
                                 9. Jump to Slot B

New firmware runs
10. Self-test passes
11. eos_bootctl_confirm()
    → confirmed_slot = B
    → boot_attempts = 0
    ✅ OTA complete

If crash before confirm:
    Watchdog resets →
                                 boot_attempts > max (3)?
                                 YES → rollback to Slot A
                                 ✅ Device is SAFE
```

---

## 📋 Boot Config Schemas (for ebuild integration)

The `configs/` directory defines the boot configuration contract that ebuild generates:

| Schema | Purpose |
|---|---|
| `boot.schema.yaml` | Flash layout, boot policy, image format, RTOS params |
| `flash_layout.schema.yaml` | Partitioning constraints + 3 typical layouts (256K/1M/2M) |
| `image.schema.yaml` | 128-byte image header format + signing specs |

```bash
# Generate C headers from boot.yaml (eboot-side, deterministic)
python scripts/generate_config.py boot.yaml generated/
# → generated/eboot_generated_layout.h
# → generated/eboot_generated_memory.ld
```

---

## 🚀 CI/CD

GitHub Actions runs on every push/PR to `master`:

- **Build matrix**: Linux × Windows × macOS
- **Board sanity**: 6 boards built in parallel
- **Config generation**: `generate_config.py` test with sample boot.yaml
- **Tests**: `ctest` runs all 7 test suites
- **Releases**: Tag `v*.*.*` → auto-changelog → GitHub Release

```bash
git tag v0.3.0
git push origin v0.3.0
```

---

## 🎯 Use Cases

### Who uses eboot and why

| Customer | Use Case | Board | Key Features Used |
|---|---|---|---|
| **IoT device maker** | WiFi sensor with OTA updates | nRF52 / ESP32 | A/B slots, OTA, secure boot, recovery |
| **Automotive supplier** | ECU with dual-core fail-safe boot | AM64x (A53+R5F) | Multicore AMP, watchdog, rollback |
| **Medical device OEM** | Patient monitor with signed firmware | STM32H7 | Crypto (SHA-256), signature verify, audit |
| **Drone manufacturer** | Flight controller with field updates | STM32F4 | OTA via UART, recovery pin, anti-rollback |
| **Industrial PLC vendor** | Factory controller — can't brick | RISC-V | A/B slots, max boot attempts, auto-rollback |
| **Consumer electronics** | Smart speaker with Linux | RPi4 / i.MX8M | DRAM init, device table, RTOS+Linux boot |
| **Telecom vendor** | 5G radio unit bootloader | x86_64 EFI | PCIe enum, UEFI runtime services, multicore SMP |
| **Wearable maker** | Smartwatch with BLE updates | nRF52 / SAMD51 | Tiny stage-0 (8KB), BLE transport, power mgmt |
| **Satellite company** | Spacecraft boot — must never fail | Custom RISC-V | Triple redundancy, watchdog, CRC+signature |
| **EV manufacturer** | Battery management controller | STM32H7 | CAN boot, motor safe-state, MPU isolation |

### eboot standalone (without eos or ebuild)

```bash
# Customer uses plain CMake — no eos, no ebuild needed
cmake -B build -DEBLDR_BOARD=stm32f4 \
  -DCMAKE_TOOLCHAIN_FILE=toolchains/arm-none-eabi.cmake
cmake --build build
# → ebldr_stage0.bin + eboot_firmware.bin ready to flash
```

### eboot with any build system

| Build System | Integration |
|---|---|
| **CMake** | Native — `cmake -B build -DEBLDR_BOARD=stm32f4` |
| **Make / Makefile** | Compile `core/*.c` + `stage0/*.c` + `stage1/*.c` + `boards/*.c` |
| **Yocto** | `.bb` recipe, `inherit cmake`, set `EBLDR_BOARD` |
| **Buildroot** | `eboot.mk` with `$(eval $(cmake-package))` |
| **ebuild** | `ebuild build` (auto-detect CMake) |
| **Vendor SDK** | Drop source + headers into vendor project |

---

## ⚠️ Related Projects

| Project | Repository | Purpose |
| --- | --- | --- |
| **eos** | [embeddedos-org/eos](https://github.com/embeddedos-org/eos) | Embedded OS — HAL, RTOS kernel, drivers, services |
| **ebuild** | [embeddedos-org/ebuild](https://github.com/embeddedos-org/ebuild) | Build system — YAML config, Ninja backend, packages |
| **eipc** | [embeddedos-org/eipc](https://github.com/embeddedos-org/eipc) | Inter-process communication — RPC, shared memory, message passing |
| **eai** | [embeddedos-org/eai](https://github.com/embeddedos-org/eai) | AI/ML inference runtime — on-device models, TinyML |
| **eni** | [embeddedos-org/eni](https://github.com/embeddedos-org/eni) | Network interface — TCP/IP stack, BLE, Wi-Fi, mesh networking |
| **eos-sdk** | [embeddedos-org/eos-sdk](https://github.com/embeddedos-org/eos-sdk) | SDK — unified development kit, templates, CLI tools |

---

## 📖 Complete API Reference

### Return Codes (`eos_types.h`)

| Code | Value | Description |
|---|---|---|
| `EOS_OK` | `0` | Success |
| `EOS_ERR_GENERIC` | `-1` | Unspecified error |
| `EOS_ERR_INVALID` | `-2` | Invalid parameter |
| `EOS_ERR_CRC` | `-3` | CRC/integrity check failed |
| `EOS_ERR_SIGNATURE` | `-4` | Digital signature verification failed |
| `EOS_ERR_NO_IMAGE` | `-5` | No valid firmware image in slot |
| `EOS_ERR_FLASH` | `-6` | Flash read/write/erase failure |
| `EOS_ERR_TIMEOUT` | `-7` | Operation timed out |
| `EOS_ERR_BUSY` | `-8` | Resource busy |
| `EOS_ERR_AUTH` | `-9` | Authentication failure |
| `EOS_ERR_VERSION` | `-10` | Version check failed (anti-rollback) |
| `EOS_ERR_FULL` | `-11` | Storage full |
| `EOS_ERR_NOT_FOUND` | `-12` | Item not found |

### Slot Identifiers & Version Encoding

```c
// Slots
EOS_SLOT_A, EOS_SLOT_B, EOS_SLOT_RECOVERY, EOS_SLOT_NONE

// Version encoding: major.minor.patch → uint32_t
uint32_t v = EOS_VERSION_MAKE(1, 2, 3);  // 0x01020003
EOS_VERSION_MAJOR(v)  // 1
EOS_VERSION_MINOR(v)  // 2
EOS_VERSION_PATCH(v)  // 3
```

### HAL API (`eos_hal.h`)

```c
// Initialization
void eos_hal_init(const eos_board_ops_t *ops);
const eos_board_ops_t *eos_hal_get_ops(void);

// Flash
int  eos_hal_flash_read(uint32_t addr, void *buf, size_t len);
int  eos_hal_flash_write(uint32_t addr, const void *buf, size_t len);
int  eos_hal_flash_erase(uint32_t addr, size_t len);

// Watchdog
void eos_hal_watchdog_init(uint32_t timeout_ms);
void eos_hal_watchdog_feed(void);

// System
eos_reset_reason_t eos_hal_get_reset_reason(void);
void eos_hal_system_reset(void);
bool eos_hal_recovery_pin_asserted(void);
void eos_hal_jump(uint32_t vector_addr);

// UART
int  eos_hal_uart_init(uint32_t baud);
int  eos_hal_uart_send(const void *buf, size_t len);
int  eos_hal_uart_recv(void *buf, size_t len, uint32_t timeout_ms);

// Timing & Interrupts
uint32_t eos_hal_get_tick_ms(void);
void eos_hal_disable_interrupts(void);
void eos_hal_enable_interrupts(void);
void eos_hal_deinit_peripherals(void);

// Slot helpers
uint32_t eos_hal_slot_addr(eos_slot_t slot);
uint32_t eos_hal_slot_size(eos_slot_t slot);
```

### Boot Control API (`eos_bootctl.h`)

```c
int  eos_bootctl_load(eos_bootctl_t *bctl);          // Load from flash (primary + backup fallback)
int  eos_bootctl_save(eos_bootctl_t *bctl);          // Save to flash (both copies, CRC)
void eos_bootctl_init_defaults(eos_bootctl_t *bctl); // Factory defaults
bool eos_bootctl_validate(const eos_bootctl_t *bctl);// Validate CRC
int  eos_bootctl_increment_attempts(eos_bootctl_t *bctl); // Increment + save
int  eos_bootctl_reset_attempts(eos_bootctl_t *bctl);     // Reset to 0 + save
int  eos_bootctl_set_pending(eos_bootctl_t *bctl, eos_slot_t slot); // Set test boot slot
int  eos_bootctl_clear_pending(eos_bootctl_t *bctl);       // Clear pending test boot
int  eos_bootctl_confirm(eos_bootctl_t *bctl);             // Confirm active as good
eos_slot_t eos_bootctl_other_slot(eos_slot_t slot);        // A→B, B→A
int  eos_bootctl_request_recovery(eos_bootctl_t *bctl);    // Force recovery on next boot
int  eos_bootctl_request_factory_reset(eos_bootctl_t *bctl); // Erase + reset
```

### Image Verification API (`eos_image.h`)

```c
int  eos_image_parse_header(uint32_t addr, eos_image_header_t *out);
int  eos_image_verify_integrity(const eos_image_header_t *hdr, uint32_t addr);
int  eos_image_verify_signature(const eos_image_header_t *hdr);
int  eos_image_check_version(uint32_t candidate_version, uint32_t min_version);
uint32_t eos_crc32(uint32_t addr, size_t len);
```

### Slot Manager API (`eos_slot_manager.h`)

```c
int  eos_slot_scan_all(void);                              // Scan all slots
bool eos_slot_is_valid(eos_slot_t slot);                   // Valid image?
uint32_t eos_slot_get_version(eos_slot_t slot);            // Image version
int  eos_slot_get_header(eos_slot_t slot, eos_image_header_t *out);
eos_slot_state_t eos_slot_get_state(eos_slot_t slot);      // EMPTY/VALID/INVALID/TESTING/CONFIRMED
int  eos_slot_erase(eos_slot_t slot);                      // Erase slot
```

### Firmware Update API (`eos_fw_update.h`)

```c
int  eos_fw_update_begin(eos_fw_update_ctx_t *ctx, eos_slot_t slot);     // Erase + init
int  eos_fw_update_write(eos_fw_update_ctx_t *ctx, const uint8_t *data, size_t len); // Stream
int  eos_fw_update_finalize(eos_fw_update_ctx_t *ctx, eos_upgrade_mode_t mode); // Verify + mark
void eos_fw_update_abort(eos_fw_update_ctx_t *ctx);        // Abort + cleanup
uint8_t eos_fw_update_progress(const eos_fw_update_ctx_t *ctx);   // 0-100%
eos_fw_update_state_t eos_fw_update_get_state(const eos_fw_update_ctx_t *ctx);
```

### Firmware Transport API (`eos_fw_transport.h`)

```c
int eos_fw_transport_update(eos_fw_transport_t *tp, eos_slot_t slot, eos_upgrade_mode_t mode);
const eos_fw_transport_ops_t *eos_fw_transport_uart_raw(void);
const eos_fw_transport_ops_t *eos_fw_transport_uart_xmodem(void);
const eos_fw_transport_ops_t *eos_fw_transport_uart_ymodem(void);
```

### Firmware Services API (`eos_fwsvc.h`)

```c
int  eos_fw_get_status(eos_fw_status_t *out);       // Complete boot status
bool eos_fw_is_test_boot(void);                     // Are we in test mode?
uint32_t eos_fw_remaining_attempts(void);           // Attempts left before rollback
int  eos_fw_confirm_running_image(void);            // MUST call after successful test boot
int  eos_fw_request_upgrade(eos_slot_t slot, eos_upgrade_mode_t mode);
int  eos_fw_get_slot_version(eos_slot_t slot, uint32_t *version);
int  eos_fw_request_recovery(void);                 // Enter recovery on next boot
int  eos_fw_factory_reset(void);                    // Erase both slots + reset bootctl
int  eos_fw_read_boot_log(void *buf, size_t len);   // Read boot event log
```

### Crypto API (`eos_crypto_boot.h`)

```c
// Streaming SHA-256
void eos_sha256_init(eos_sha256_ctx_t *ctx);
void eos_sha256_update(eos_sha256_ctx_t *ctx, const uint8_t *data, size_t len);
void eos_sha256_final(eos_sha256_ctx_t *ctx, uint8_t digest[32]);

// One-shot
int eos_crypto_hash(const uint8_t *data, size_t len, uint8_t digest[32]);

// Image verification (reads via HAL flash_read, safe for all platforms)
int eos_crypto_verify_image(uint32_t image_addr, uint32_t image_size,
                             const uint8_t expected_hash[32]);

// Digital signature (Ed25519/ECDSA stub)
int eos_crypto_verify_signature(const uint8_t *data, size_t data_len,
                                 const uint8_t *sig, size_t sig_len,
                                 const uint8_t *pubkey, size_t key_len);
```

### Multicore API (`eos_multicore.h`)

```c
int  eos_multicore_init(const eos_multicore_ops_t *ops);
uint8_t eos_multicore_count(void);
uint8_t eos_multicore_current(void);
int  eos_multicore_start(const eos_core_config_t *cfg);
int  eos_multicore_stop(uint8_t core_id);
int  eos_multicore_reset(uint8_t core_id);
eos_core_state_t eos_multicore_get_state(uint8_t core_id);
int  eos_multicore_send_ipi(uint8_t core_id, uint32_t message);
int  eos_multicore_boot_all(const eos_core_config_t *configs, uint8_t count);
int  eos_multicore_wait_state(uint8_t core_id, eos_core_state_t target, uint32_t timeout_ms);
int  eos_multicore_start_smp(uint8_t core_id, uint32_t entry_addr, uint32_t stack_addr);
int  eos_multicore_start_amp(uint8_t core_id, eos_slot_t slot, eos_core_arch_t arch);
```

### Runtime Services API (`eos_runtime_svc.h`)

```c
int  eos_rtsvc_init(void);
int  eos_rtsvc_get_variable(const char *name, void *data, uint32_t *size);
int  eos_rtsvc_set_variable(const char *name, const void *data, uint32_t size);
int  eos_rtsvc_delete_variable(const char *name);
void eos_rtsvc_reset_system(eos_reset_type_t type); // EOS_RESET_COLD/WARM/HALT
uint32_t eos_rtsvc_get_time(void);
eos_slot_t eos_rtsvc_get_next_boot(void);
int  eos_rtsvc_set_next_boot(eos_slot_t slot);
```

### Boot Log API (`eos_boot_log.h`)

```c
int  eos_boot_log_init(void);                    // Init log subsystem
void eos_boot_log_append(uint32_t event, uint32_t slot, uint32_t detail);  // Add entry
int  eos_boot_log_read(eos_boot_log_entry_t *entries, uint32_t max_count); // Read all
uint32_t eos_boot_log_count(void);               // Entry count
int  eos_boot_log_clear(void);                   // Erase all entries
int  eos_boot_log_flush(void);                   // Flush to flash
int  eos_boot_log_get_latest(eos_boot_log_entry_t *entry); // Most recent
const char *eos_boot_log_event_name(uint32_t event);       // Event code → string
```

### Board Registry API (`eos_board_registry.h`)

```c
int  eos_board_register(const eos_board_info_t *info);
const eos_board_info_t *eos_board_find(const char *name);
const eos_board_info_t *eos_board_detect(void);    // Auto-detect
uint32_t eos_board_count(void);
const eos_board_info_t *eos_board_get(uint32_t index);
int  eos_board_activate(const char *name);         // Find + HAL init
int  eos_board_activate_auto(void);                // Detect + HAL init

// Self-registration macro (GCC/Clang constructor, file scope)
EBOOT_REGISTER_BOARD("stm32f4", EOS_PLATFORM_ARM_CM4, 0x0413,
                      board_get_ops, board_detect);
```

### Board Configuration API (`eos_board_config.h`)

```c
int  eos_board_config_apply(const eos_board_config_t *cfg);
const eos_board_config_t *eos_board_config_get(void);
const eos_pin_config_t *eos_board_config_find_pin(eos_pin_function_t func, uint8_t idx);
const eos_mem_config_t *eos_board_config_find_memory(eos_mem_cfg_type_t type);
const eos_periph_config_t *eos_board_config_find_periph(eos_periph_cfg_type_t type, uint8_t idx);
uint32_t eos_board_config_total_ram(void);
uint32_t eos_board_config_total_flash(void);
void eos_board_config_dump(void);
void eos_board_config_set_ops(const eos_board_config_ops_t *ops);
```

### GitHub CLI Integration

```bash
# Create a tagged release with binaries
gh release create v0.4.0 \
  --title "E-Boot v0.4.0" \
  --notes-file CHANGELOG.md \
  build-arm/ebldr_stage0.bin build-arm/eboot_firmware.bin

# Trigger CI workflow
gh workflow run ci.yml

# View workflow runs
gh run list --workflow=ci.yml

# Download release artifacts
gh release download v0.4.0 --pattern '*.bin'

# Create an issue for a bug
gh issue create --title "Build failure on MSVC" --label bug

# View open PRs
gh pr list --state open
```

---

## 📜 License

MIT License
