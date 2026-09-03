# Compatibility Matrix

Supported versions of toolchains, host operating systems, and dependencies for ebuild.

## Host OS Support

| OS | Status | Notes |
|----|--------|-------|
| Ubuntu 22.04+ | ✅ Full support | Primary development platform |
| Ubuntu 20.04 | ✅ Supported | Minimum supported version |
| Debian 11+ | ✅ Supported | |
| Fedora 38+ | ✅ Supported | |
| macOS 13+ (Ventura) | ✅ Supported | Apple Silicon and Intel |
| macOS 12 (Monterey) | ⚠️ Limited | Some QEMU features unavailable |
| Windows 11 | ✅ Supported | eOSuite layer excluded (`EOS_WITH_EOSUITE` disabled) |
| Windows 10 | ⚠️ Limited | WSL2 recommended for full functionality |

## Python

| Version | Status |
|---------|--------|
| Python 3.12 | ✅ Recommended |
| Python 3.11 | ✅ Supported |
| Python 3.10 | ✅ Supported |
| Python 3.9 | ✅ Minimum supported |
| Python 3.8 | ❌ Not supported |

## Build Tools

| Tool | Minimum Version | Recommended | Notes |
|------|----------------|-------------|-------|
| CMake | 3.20 | 3.28+ | Required for core builds |
| Make | 4.0 | 4.4+ | Required for EIPC layer |
| Ninja | 1.11 | 1.12+ | Optional, faster builds |
| Meson | 0.60 | 1.3+ | Optional, for Meson-based modules |
| Cargo | 1.70 | 1.80+ | Optional, for Rust components |

## Cross-Compilation Toolchains

| Toolchain | Tested Version | Targets |
|-----------|---------------|---------|
| `arm-none-eabi-gcc` | 12.3, 13.2, 14.1 | Cortex-M0+, M4, M4F, M7, R4F, R5F |
| `aarch64-linux-gnu-gcc` | 12.3, 13.2 | Cortex-A53, A72 (RPi, i.MX8M, AM64x) |
| `riscv64-linux-gnu-gcc` | 12.3, 13.2 | RV64GC (SiFive, QEMU virt) |
| `xtensa-esp32-elf-gcc` | 12.2 (ESP-IDF 5.x) | ESP32 LX6 |
| `mips-linux-gnu-gcc` | 12.3 | MIPS Malta |

### Installing Toolchains

**Ubuntu/Debian:**
```bash
# ARM bare-metal
sudo apt install gcc-arm-none-eabi

# ARM64 Linux
sudo apt install gcc-aarch64-linux-gnu

# RISC-V
sudo apt install gcc-riscv64-linux-gnu
```

**macOS (Homebrew):**
```bash
brew install --cask gcc-arm-embedded
brew install aarch64-elf-gcc
```

**Windows:**
Download from [ARM Developer](https://developer.arm.com/downloads/-/gnu-rm) and add to PATH.

## QEMU (for testing)

| Version | Status | Notes |
|---------|--------|-------|
| QEMU 8.0+ | ✅ Recommended | Full ARM/AArch64/RISC-V/MIPS support |
| QEMU 7.0+ | ✅ Supported | |
| QEMU 6.0+ | ⚠️ Limited | Some machine types may be missing |

### Supported QEMU Machines

| Machine | QEMU Binary | Board Target |
|---------|-------------|-------------|
| `lm3s6965evb` | `qemu-system-arm` | stm32f4 (Cortex-M testing) |
| `mps2-an385` | `qemu-system-arm` | nrf52 (Cortex-M testing) |
| `raspi3b` | `qemu-system-aarch64` | raspi3 |
| `raspi4b` | `qemu-system-aarch64` | raspi4 |
| `virt` | `qemu-system-aarch64` | imx8m, am64x |
| `virt` | `qemu-system-riscv64` | riscv_virt, sifive_u |
| `malta` | `qemu-system-mips` | malta |

## Python Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `click` | ≥8.0 | CLI framework |
| `pyyaml` | ≥6.0 | YAML parsing (recipes, board configs) |
| `ninja` | ≥1.11 | Ninja build backend (Python bindings) |
| `pytest` | ≥7.0 | Testing (dev dependency) |
| `pytest-cov` | ≥4.0 | Coverage reporting (dev dependency) |

## Known Limitations

| Limitation | Affected | Workaround |
|-----------|----------|------------|
| eOSuite excluded on Windows | `--with eosuite` | Use WSL2 or Linux VM |
| `ebuild package` looks for `_build/<name>` rather than `_build/<name>.exe` | Windows | Tracked as T-003 |
| EIPC Go build separate from CMake | `layers/eipc/` | Build EIPC separately with `make` |
| ESP32 requires ESP-IDF | `--target esp32` | Install ESP-IDF v5.x first |
| MIPS toolchain not in most distros | `--target malta` | Build from source or use Docker |
