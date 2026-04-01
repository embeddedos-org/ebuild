# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.4.0] — 2026-03-28

### Added
- **`EOS_ERR_NOT_FOUND` error code** (`-12`) in `eos_types.h` — dedicated error for variable/item lookups instead of misusing `EOS_ERR_NO_IMAGE`
- **`eos_boot_log.h` full API** — populated the previously empty header with 8 functions: `eos_boot_log_init()`, `eos_boot_log_append()`, `eos_boot_log_read()`, `eos_boot_log_count()`, `eos_boot_log_clear()`, `eos_boot_log_flush()`, `eos_boot_log_get_latest()`, `eos_boot_log_event_name()`
- **Comprehensive README** — added complete API reference documentation for all 15 public headers covering HAL, boot control, image verification, slot manager, firmware update, firmware transport, firmware services, crypto, multicore, runtime services, boot log, board registry, and board configuration APIs
- **GitHub CLI integration guide** — added `gh release`, `gh workflow run`, `gh issue create`, and `gh pr list` examples to README

### Fixed
- **`eos_slot_manager.h`:** Fixed `eos_slot_id_t` → `eos_slot_t` type mismatch — all slot manager APIs now use the correct type from `eos_types.h`, resolving compilation errors across all platforms
- **`board_rpi4.c`:** Removed duplicate `bootctl_backup_addr`, `log_addr`, and `app_vector_offset` fields in `eos_board_ops_t` initializer — was causing build failures with `-Werror` on GCC/Clang
- **`board_cortex_r5.c`:** Fixed 5 function signature mismatches with `eos_board_ops_t`:
  - `r5_flash_read/write/erase`: `uint32_t len` → `size_t len`
  - `r5_watchdog_init`: `void` → `uint32_t timeout_ms`
  - `r5_get_reset_reason`: `uint32_t` → `eos_reset_reason_t`
  - `r5_uart_init`: `void` → `int (*)(uint32_t baud)`
  - `r5_uart_send`: `(const uint8_t*, uint32_t)` → `(const void*, size_t)`
  - `r5_uart_recv`: `(uint8_t*, uint32_t, uint32_t)` → `(void*, size_t, uint32_t)`
- **`boot_scan.c`:** Replaced non-portable `__builtin_memcpy` with standard `memcpy` and added missing `#include <string.h>` — fixes MSVC builds
- **`crypto_boot.c`:** Fixed unsafe direct pointer cast `(const uint8_t *)(uintptr_t)image_addr` in `eos_crypto_verify_image()` — now reads flash data via `eos_hal_flash_read()` in 256-byte chunks, preventing segfaults on host test builds and platforms where flash is not memory-mapped
- **`runtime_services.c`:** Changed `EOS_ERR_NO_IMAGE` to `EOS_ERR_NOT_FOUND` for variable lookup failures — semantically correct error code
- **`power_init.c`:** Wrapped `printf` calls in `eos_power_dump()` with `#if !defined(EOS_BARE_METAL)` guard — prevents linker errors on bare-metal targets without libc
- **`ecc_scrub.c`:** Wrapped `printf` calls in `eos_ecc_dump()` with `#if !defined(EOS_BARE_METAL)` guard
- **`bmc_handoff.c`:** Wrapped `printf` calls in `eos_bmc_handoff_dump()` with `#if !defined(EOS_BARE_METAL)` guard
- **`CONTRIBUTING.md`:** Removed duplicate sections (commit messages, PR checklist, board porting guide, reporting issues, and license appeared twice)
- **`CHANGELOG.md`:** Removed duplicate entries in v0.1.0 section

### Changed
- **Version bump** to 0.4.0 in `CMakeLists.txt`

---

## [0.3.0] — 2026-03-27

### Added
- **Cross-compilation toolchains:** CMake toolchain files for ARM Cortex-M (`arm-none-eabi`), AArch64 Linux (`aarch64-linux-gnu`), and RISC-V 64 (`riscv64-linux-gnu`)
- **Multi-arch release workflow:** Automated cross-compiled binary releases for 4 architectures (x86_64, ARM Cortex-M, AArch64, RISC-V)
- **`requirements.txt`** for Python dependencies (PyYAML)
- **CI/CD pipeline:** GitHub Actions workflows for CI (ubuntu, windows, macos) and release automation
- **`slot_manager.h`:** New public header for A/B slot management API
- **`boot_log.h`:** New public header for structured boot logging
- **`extern "C"` guards:** Added C++ compatibility guards to 11 public headers (`eos_hal.h`, `eos_bootctl.h`, `eos_image.h`, `eos_fwsvc.h`, `eos_fw_update.h`, `eos_fw_transport.h`, `eos_multicore.h`, `eos_board_config.h`, `eos_board_registry.h`, `eos_rtos_boot.h`, `eos_boot_menu.h`)
- **`printf` guards:** Wrapped all `printf`/`fprintf` calls with `#if !defined(EOS_BARE_METAL)` for bare-metal targets without libc

### Fixed
- **`eos_power.h`:** Removed duplicate `EOS_RESET_*` enum constants that collided with `eos_types.h` — was blocking all builds on every platform
- **`eos_board_config.h`:** Renamed `eos_clock_config_t` to `eos_board_clock_config_t` to avoid typedef collision with `eos_clock.h`
- **`boot_menu.c`:** Fixed UART return value check (`rc == 1` → `rc == EOS_OK`) — boot menu was always timing out
- **`os_adapter.c`:** Added MSVC `_ReadWriteBarrier()` fallback for memory barrier — multicore sync was broken on Windows
- **`rtos_params.c`:** Fixed macOS Mach-O `__attribute__((section))` format — was failing on macOS builds
- **`eos_hal.h` / `eos_hal_set_msp()`:** Fixed Cortex-M MSP (Main Stack Pointer) inline assembly — was using wrong constraint for `__MSR` on ARMv6-M/ARMv7-M
- **`power_init.c`:** Fixed `eos_power_state_t` enum ordering to match hardware register bit layout — power sequencing was wrong on cold boot
- **`board_rpi4.c`:** Corrected RPi4 peripheral base address (`0xFE000000`) and VideoCore mailbox address (`0xFE00B880`) — GPIO and mailbox were inaccessible

## [0.1.0] — 2026-03-26

### Added
- Multi-stage bootloader architecture (Stage-0 → Stage-1)
- A/B slot management with automatic rollback
- Secure boot with SHA-256 image verification
- 23 board support packages (STM32F4, STM32H7, nRF52, RPi4, RISC-V, ESP32, x86_64 EFI, i.MX8M, AM64x, SAMD51, and more)
- Boot control block with CRC-32 integrity
- RTOS boot support with parameter passing
- Interactive UART boot menu
- Firmware update over UART transport
- Recovery mode with factory reset
- Declarative board configuration (pins, memory, clocks, interrupts, peripherals)
- Runtime board registry with auto-registration
- Multicore boot management
- Config generation script (`generate_config.py`) for flash layout and linker scripts
