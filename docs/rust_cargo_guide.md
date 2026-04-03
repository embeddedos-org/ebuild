# Rust / Cargo Backend Guide

ebuild fully supports **Rust projects** through the Cargo backend.

## Prerequisites

Install Rust toolchain:

```bash
# Any platform — rustup installs Rust + Cargo
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Verify
rustc --version
cargo --version

# For embedded targets, add cross-compilation support
rustup target add thumbv7em-none-eabihf    # ARM Cortex-M4/M7
rustup target add riscv32imc-unknown-none-elf  # RISC-V 32
rustup target add aarch64-unknown-linux-gnu    # ARM64 Linux
```

## Quick Start

```bash
# Create a Rust project
cargo init my-firmware
cd my-firmware

# Build with ebuild (auto-detects Cargo.toml)
ebuild build

# Or explicitly select cargo backend
ebuild build --backend cargo
```

## build.yaml for Rust Projects

```yaml
project:
  name: my-firmware
  version: "0.1.0"

backend: cargo

cargo:
  release: true
  target: thumbv7em-none-eabihf    # cross-compile for Cortex-M
  features:
    - hal-stm32h7
    - rtos
```

## Cross-Compilation for Embedded

```bash
# Build for ARM Cortex-M7 (STM32H7)
ebuild build --backend cargo
# Equivalent to: cargo build --release --target thumbv7em-none-eabihf

# Build for RISC-V 32
# Set target in build.yaml: riscv32imc-unknown-none-elf
ebuild build --backend cargo
```

## Rust + EoS Integration

A Rust project can use EoS services via FFI bindings:

```rust
// src/main.rs
#![no_std]
#![no_main]

use core::panic::PanicInfo;

extern "C" {
    fn eos_gpio_write(port: u32, pin: u32, value: u32) -> i32;
    fn eos_uart_send(port: u32, data: *const u8, len: u32) -> i32;
}

#[no_mangle]
pub extern "C" fn main() -> ! {
    unsafe {
        eos_gpio_write(0, 13, 1);  // LED on
        let msg = b"Hello from Rust on EoS\n";
        eos_uart_send(0, msg.as_ptr(), msg.len() as u32);
    }
    loop {}
}

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! { loop {} }
```

## Rust + eboot Integration

Rust firmware can be signed and booted by eboot:

```bash
# Build Rust firmware
cargo build --release --target thumbv7em-none-eabihf

# Convert to binary
arm-none-eabi-objcopy -O binary \
  target/thumbv7em-none-eabihf/release/my-firmware firmware.bin

# Sign for eboot
bash _generated/pack_image.sh firmware.bin signing_key.pem

# Flash to slot A
python eboot/tools/uart_recovery.py --port /dev/ttyUSB0 firmware.signed.bin
```

## Cargo Backend API

The `CargoBackend` class in `ebuild/build/backends/cargo_backend.py`:

```python
from ebuild.build.backends.cargo_backend import CargoBackend

backend = CargoBackend(source_dir=Path("my-firmware"))

# Build in release mode
backend.build(release=True)

# Cross-compile
backend.build(release=True, target="thumbv7em-none-eabihf")

# Build with specific features
backend.build(release=True, features=["hal-stm32h7", "rtos"])

# Run tests
backend.test()
```

## Supported Rust Targets

| Target Triple | Architecture | Use Case |
|---|---|---|
| `thumbv7em-none-eabihf` | ARM Cortex-M4/M7 | STM32, nRF52 |
| `thumbv7m-none-eabi` | ARM Cortex-M3 | STM32F1/F2 |
| `thumbv6m-none-eabi` | ARM Cortex-M0/M0+ | RP2040, STM32F0 |
| `riscv32imc-unknown-none-elf` | RISC-V 32 | ESP32-C3, GD32V |
| `aarch64-unknown-linux-gnu` | ARM64 Linux | RPi4, i.MX8 |
| `x86_64-unknown-linux-gnu` | x86_64 Linux | Servers, QEMU |
