# ebuild — EoS Build System

**The tool.** Standalone build system for the EoS Embedded Operating System.

```bash
pip install ebuild
ebuild build --target raspi4 --source /path/to/eos-platform --with all
```

## Install

```bash
pip install ebuild
# or
pip install git+https://github.com/embeddedos-org/ebuild.git
```

## Commands (18)

| Command | Description |
|---|---|
| `ebuild build` | Build from build.yaml + optional layers |
| `ebuild build --with eai,eni` | Build with optional layers |
| `ebuild sdk --target raspi4` | Generate Yocto-style SDK |
| `ebuild package --target raspi4` | Package deliverable ZIP |
| `ebuild models` | List LLM models for EAI |
| `ebuild analyze` | Analyze hardware (KiCad/YAML) |
| `ebuild new` | Scaffold project from template |
| `ebuild firmware` | Build RTOS firmware |
| `ebuild system` | Build Linux system image |
| `ebuild qemu` | QEMU sanity boot test |
| `ebuild integration` | Build + test all components |
| + 7 more | clean, configure, info, install, add, list-packages, generate-boot |

## Supported Targets (14)

| Target | Arch | Vendor | Board |
|---|---|---|---|
| stm32f4 | ARM Cortex-M4 | ST | STM32F407 |
| stm32h7 | ARM Cortex-M7 | ST | STM32H743 |
| nrf52 | ARM Cortex-M4 | Nordic | nRF52840 |
| rp2040 | ARM Cortex-M0+ | RPi | RP2040 |
| raspi3 | AArch64 | Broadcom | BCM2837 |
| raspi4 | AArch64 | Broadcom | BCM2711 |
| imx8m | AArch64 | NXP | i.MX8M |
| am64x | AArch64 | TI | AM6442 |
| riscv_virt | RISC-V | QEMU | virt |
| sifive_u | RISC-V | SiFive | FU740 |
| malta | MIPS | MIPS | Malta |
| x86_64 | x86_64 | Generic | PC |

## SDK Generation

```bash
ebuild sdk --target raspi4 --output build/
source build/eos-sdk-raspi4/environment-setup
cmake -B app -DCMAKE_TOOLCHAIN_FILE=\
cmake --build app
```

## Deliverable Packaging

```bash
ebuild package --target raspi4 --version 0.1.0 --source /path/to/eos-platform
# -> dist/eos-raspi4-v0.1.0-deliverable.zip
#    Contains: source + SDK + libs + image + EoSuite + manifest
```

## License
MIT