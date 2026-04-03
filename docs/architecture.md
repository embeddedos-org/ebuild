# Architecture Overview

> **Naming context:** The tool is called `ebuild` (short for "EoS Build Tool"). It is **not** related to [Gentoo's ebuild format](https://wiki.gentoo.org/wiki/Ebuild). When referring to this tool in documentation, prefer "EoS ebuild" or "EmbeddedOS Build Tool" to avoid confusion.

## System Diagram

```mermaid
graph TD
    subgraph CLI["ebuild CLI (Python)"]
        CMD[cli/commands.py<br>18 commands]
    end

    subgraph BUILD["Build Orchestrator"]
        ORCH[build/orchestrator.py]
        NINJA[build/ninja_backend.py]
        TC[build/toolchain.py<br>5 predefined toolchains]
    end

    subgraph PACKAGES["Package Pipeline"]
        RECIPE[packages/recipe.py]
        REG[packages/registry.py]
        RESOLVE[packages/resolver.py]
        FETCH[packages/fetcher.py]
        BUILDER[packages/builder.py]
        CACHE[packages/cache.py]
        LOCK[packages/lockfile.py]
        REPO[packages/repository.py<br>Remote index]
        PROFILES[packages/profiles.py<br>Build profiles]
    end

    subgraph HWAI["Hardware AI"]
        ANALYZER[eos_ai/eos_hw_analyzer.py<br>MCU database + peripheral detection]
        PROJGEN[eos_ai/eos_project_generator.py<br>Manifest + project scaffolding]
    end

    subgraph CORE["Core Components (always built)"]
        EOS[core/eos/<br>HAL, Kernel, Crypto, OTA, Drivers]
        EBOOT[core/eboot/<br>Bootloader, 26 board ports]
    end

    subgraph LAYERS["Optional Layers (--with flag)"]
        EAI[layers/eai/<br>AI inference + LLM models]
        ENI[layers/eni/<br>Neural interface]
        EIPC[layers/eipc/<br>Secure IPC (Go + C)]
        EOSUITE[layers/eosuite/<br>Dev tools + GUI apps]
    end

    subgraph HW["Hardware Intake"]
        BOARD[hardware/board/<br>KiCad, Eagle, YAML, BOM]
        SOC[hardware/soc/<br>Datasheets, TRMs]
        BOOT[hardware/boot/<br>Image layout, boot flow]
        SW[hardware/software/<br>Device trees, linker scripts]
    end

    subgraph SDK_OUT["SDK Output"]
        SDKGEN[sdk_generator.py]
        SDKAPI[sdk/include/<br>Header-only API]
    end

    subgraph TEMPLATES["Project Templates"]
        T1[bare-metal]
        T2[rtos-app]
        T3[linux-app]
        T4[safety-critical]
        T5[secure-boot]
        T6[ble-sensor]
    end

    CMD --> ORCH
    CMD --> SDKGEN
    CMD --> ANALYZER
    CMD --> PROJGEN

    ORCH --> NINJA
    ORCH --> TC
    ORCH --> CORE
    ORCH --> LAYERS

    ORCH --> RECIPE
    RECIPE --> REG
    REG --> RESOLVE
    RESOLVE --> FETCH
    FETCH --> BUILDER
    BUILDER --> CACHE
    RESOLVE --> LOCK
    REG --> REPO

    HW --> ANALYZER
    ANALYZER --> PROJGEN
    PROJGEN --> TEMPLATES
    PROJGEN --> CORE
    PROJGEN --> EBOOT

    TC -->|cmake| CORE
    TC -->|cmake| LAYERS
```

## Subsystem Details

### CLI (`ebuild/cli/`)

The entry point for all user interaction. 18 commands implemented in `commands.py` using [Click](https://click.palletsprojects.com/). Key commands:

- `ebuild build` — orchestrate a full build from `build.yaml`
- `ebuild new` — scaffold a project from a template
- `ebuild analyze` — run the hardware analyzer on schematics
- `ebuild sdk` — generate a cross-compilation SDK
- `ebuild package` — create a versioned deliverable ZIP

At startup, the CLI loads any installed [plugins](guides/customization.md) via Python entry points (`ebuild.plugins`).

### Build Orchestrator (`ebuild/build/`)

Dispatches builds to the appropriate backend based on the project's build system:

| Backend | Used For |
|---------|----------|
| CMake | Core EoS, eBoot, EAI, ENI |
| Make | EIPC (Go components) |
| Meson | Optional modules |
| Cargo | Rust components |
| Kbuild | Linux kernel builds |
| Ninja | Custom ebuild backend |

The **toolchain manager** (`toolchain.py`) maintains 5 predefined cross-compilation toolchains:

- `host` — native x86_64
- `arm-none-eabi` — ARM bare-metal (Cortex-M/R)
- `aarch64-linux-gnu` — ARM64 Linux
- `riscv64-linux-gnu` — RISC-V 64
- `xtensa-esp32-elf` — ESP32

### Package Pipeline (`ebuild/packages/`)

A full dependency management system:

```
recipe.yaml → Registry → Resolver → Fetcher → Builder → Cache
                                        ↓
                                    Lockfile
```

1. **Recipe** (`recipe.py`) — YAML schema defining package name, version, URL, checksum, build system, dependencies
2. **Registry** (`registry.py`) — scans recipe directories and indexes available packages
3. **Repository** (`repository.py`) — remote package index for discovery and search
4. **Resolver** (`resolver.py`) — dependency resolution with version constraint solving
5. **Fetcher** (`fetcher.py`) — downloads and verifies source archives
6. **Builder** (`builder.py`) — builds packages using the specified build system
7. **Cache** (`cache.py`) — caches built artifacts to avoid rebuilding
8. **Lockfile** (`lockfile.py`) — records exact resolved versions for reproducibility
9. **Profiles** (`profiles.py`) — composable build profiles (minimal, standard, full, custom)

### Hardware AI (`ebuild/eos_ai/`)

The hardware analyzer parses schematic inputs (KiCad, Eagle, YAML, BOM CSV, plain text) and produces a `HardwareProfile`:

- MCU detection via `MCU_DATABASE` (15+ MCU families)
- 24+ peripheral types detected
- Flash/RAM size and clock frequency extraction
- Generates: `board.yaml`, `boot.yaml`, `build.yaml`, `eos_product_config.h`, `eboot_flash_layout.h`, linker scripts

The **project generator** maps hardware profiles to eboot board ports, eos toolchains, and platform configurations.

### Layer System

Layers are optional components activated via `--with`:

| Layer | Directory | Build System | Notes |
|-------|-----------|--------------|-------|
| EAI | `layers/eai/` | CMake | 12 LLM models, agent loop, Ebot server |
| ENI | `layers/eni/` | CMake | Neuralink adapter, BCI framework |
| EIPC | `layers/eipc/` | Make (Go) + CMake (C SDK) | Go server + C client SDK |
| eOSuite | `layers/eosuite/` | CMake | Excluded on Windows |

### Templates

6 project templates in `templates/` use `{{PLACEHOLDER}}` variable substitution:

- `bare-metal` — minimal embedded application
- `rtos-app` — FreeRTOS/EoS RTOS application
- `linux-app` — Linux user-space application
- `safety-critical` — IEC 61508/ISO 26262 compliant (Cortex-R targets)
- `secure-boot` — secure boot chain with crypto verification
- `ble-sensor` — BLE sensor device (Nordic nRF52)
