# Contributing to eboot

Thank you for your interest in contributing to eBootloader!

## Getting Started

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes
4. Run the build and tests locally
5. Submit a pull request

## Prerequisites

| Tool | Minimum Version | Purpose |
|---|---|---|
| **CMake** | 3.16+ | Build system |
| **GCC / Clang / MSVC** | GCC 10+, Clang 12+, MSVC 2019+ | C11 compiler |
| **Python** | 3.8+ | Config generation scripts |
| **PyYAML** | 6.0+ | `pip install -r requirements.txt` |
| **arm-none-eabi-gcc** | 10+ | *(optional)* ARM Cortex-M cross-compilation |
| **aarch64-linux-gnu-gcc** | 10+ | *(optional)* AArch64 cross-compilation |
| **riscv64-linux-gnu-gcc** | 10+ | *(optional)* RISC-V 64 cross-compilation |

## Development Setup

### Native Build (Host)

```bash
git clone https://github.com/embeddedos-org/eboot.git
cd eboot
cmake -B build -DEBLDR_BUILD_TESTS=ON
cmake --build build
ctest --test-dir build --output-on-failure
```

### Cross-Compilation

```bash
# ARM Cortex-M (bare-metal)
cmake -B build-arm -DEBLDR_BOARD=stm32f4 \
  -DCMAKE_TOOLCHAIN_FILE=toolchains/arm-none-eabi.cmake
cmake --build build-arm

# AArch64 Linux (e.g. RPi4)
cmake -B build-aarch64 -DEBLDR_BOARD=rpi4 \
  -DCMAKE_TOOLCHAIN_FILE=toolchains/aarch64-linux-gnu.cmake
cmake --build build-aarch64

# RISC-V 64
cmake -B build-riscv -DEBLDR_BOARD=riscv64_virt \
  -DCMAKE_TOOLCHAIN_FILE=toolchains/riscv64-linux-gnu.cmake
cmake --build build-riscv
```

### Config Generation Testing

```bash
pip install -r requirements.txt
python scripts/generate_config.py configs/example_boot.yaml /tmp/generated/
```

## Test Suites

eboot includes 7 unit test suites that run natively on the host:

| Test | Covers |
|---|---|
| `test_bootctl` | Boot control block save/load, CRC, rollback |
| `test_crypto` | SHA-256 against known vectors |
| `test_device_table` | Device table create, add, validate |
| `test_runtime_svc` | Runtime variable get/set/delete |
| `test_board_config` | Pin/memory/IRQ config lookup |
| `test_multicore` | Core state management, SMP/AMP init |
| `test_board_registry` | Board register, find, activate |

Run all tests:

```bash
cmake -B build -DEBLDR_BUILD_TESTS=ON
cmake --build build --config Release
ctest --test-dir build --output-on-failure -C Release
```

## CI Requirements

All pull requests must pass the following CI checks before merging:

### Required Status Checks

| Check | Platform | What It Validates |
|---|---|---|
| **Build (ubuntu-latest)** | Linux | GCC build + all 7 unit tests |
| **Build (windows-latest)** | Windows | MSVC build + all 7 unit tests |
| **Build (macos-latest)** | macOS | Clang build + all 7 unit tests |
| **Config Generation** | Linux | `generate_config.py` produces valid headers and linker scripts |

### How to Verify Locally

Before submitting a PR, ensure all checks pass:

```bash
# 1. Build + test on your host
cmake -B build -DEBLDR_BUILD_TESTS=ON
cmake --build build --config Release
ctest --test-dir build --output-on-failure -C Release

# 2. Config generation
pip install -r requirements.txt
python scripts/generate_config.py configs/example_boot.yaml /tmp/out/
test -f /tmp/out/eboot_generated_layout.h
test -f /tmp/out/eboot_generated_memory.ld
```

### Nightly Regression (Informational)

The nightly workflow runs additional cross-compilation checks that are not required for PRs but are monitored for regressions:

- Cross-compile for AArch64 Linux (`aarch64-linux-gnu-gcc`)
- Cross-compile for RISC-V 64 (`riscv64-linux-gnu-gcc`)
- Cross-compile for ARM Cortex-M (`arm-none-eabi-gcc`)

## Code Guidelines

### C Style

- **Standard:** C11 (`-std=c11`)
- **Warnings:** `-Wall -Wextra` must compile clean (zero warnings)
- **Platform guards:** All platform-specific code must be guarded:
  - `#if defined(__APPLE__)` for macOS
  - `#if defined(_MSC_VER)` for MSVC/Windows
  - `#if defined(__GNUC__) || defined(__clang__)` for GCC/Clang
  - `#if defined(__ARM_ARCH)` for ARM-specific code
- **No `printf` in production paths** — use `eos_hal_uart_send()` for output
- **Include guards:** Use `#ifndef HEADER_NAME_H` / `#define` / `#endif`
- **Types:** Use `<stdint.h>` types (`uint32_t`, `int8_t`, etc.)
- **C++ compatibility:** All public headers must have `extern "C"` guards

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add SPI transport for firmware update
fix: bootctl CRC calculation on big-endian targets
docs: update board porting guide
ci: add ARM Cortex-M cross-compilation to nightly
chore: bump version to 0.4.0
```

### Pull Request Checklist

- [ ] Code compiles with zero warnings on GCC, Clang, and MSVC
- [ ] All existing tests pass
- [ ] New features include unit tests in `tests/unit/`
- [ ] Platform-specific code has `#ifdef` guards for all 3 OS targets
- [ ] No hardcoded paths (use platform abstractions)
- [ ] Commit messages follow conventional commits format

## Adding a New Board Port

1. Create `boards/<name>/board_<name>.c` implementing `eos_board_ops_t`
2. Create `boards/<name>/board_<name>.h` with memory map constants
3. Add the board to `CMakeLists.txt` via `eboot_add_board()`
4. Optionally add linker scripts (`<name>_stage0.ld`, `<name>_stage1.ld`)
5. Add the board name to the help text in `CMakeLists.txt`

## Reporting Issues

- Use GitHub Issues with the appropriate label (`bug`, `enhancement`, `question`)
- Include: OS, compiler version, board target, and full error output
- For build failures: attach the full CMake configure + build log

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
