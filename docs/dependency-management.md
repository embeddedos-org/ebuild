# Dependency Management

ebuild manages EoS and eBoot source repositories automatically so you no longer need embedded copies inside `core/`.

## Why This Changed

Previously, ebuild shipped **full copies** of EoS and eBoot inside `core/eos/` and `core/eboot/`. This created three copies of the same source (standalone repo, ebuild's `core/`, and workspace sibling), and `core/` would go stale whenever eos or eboot was updated.

Now ebuild **clones repos on demand** into a shared cache at `~/.ebuild/repos/` and resolves them dynamically at build time.

## Quick Start

```bash
# 1. Install ebuild
pip install -e .

# 2. Clone eos + eboot to the shared cache
ebuild setup

# 3. Build as usual
ebuild build --target raspi4
```

That's it. The `ebuild setup` command replaces the need for embedded `core/` directories.

## How Repo Resolution Works

When ebuild needs to find the eos or eboot source, it checks these locations **in order**:

| Priority | Source | Example |
|----------|--------|---------|
| 1 | CLI flag | `--eos-repo /path/to/eos` |
| 2 | Environment variable | `EBUILD_EOS_PATH=/path/to/eos` |
| 3 | Config path override | `~/.ebuild/config.yaml` → `repos.eos.path` |
| 4 | Cached clone | `~/.ebuild/repos/eos/` |
| 5 | Sibling directory | `../eos/` (workspace layout) |
| 6 | Embedded `core/` | `core/eos/` (deprecated, prints warning) |

The first match wins.

## `ebuild setup`

Clones both repos with default settings:

```bash
ebuild setup
```

### Custom fork URL

```bash
ebuild setup --eos-url https://github.com/myfork/eos.git
```

### Pin to a version tag

```bash
ebuild setup --eboot-branch v0.2.0
```

### Link to a local repo (no clone)

```bash
ebuild setup --eos-path /home/user/my-eos-checkout
```

## `ebuild repos` — Manage Cached Repos

### Show status

```bash
ebuild repos status
```

Output:

```
eos
  URL:    https://github.com/spatchava/eos.git
  Branch: main
  Cached: /home/user/.ebuild/repos/eos
  Git:    main @ a1b2c3d

eboot
  URL:    https://github.com/spatchava/eboot.git
  Branch: main
  Cached: /home/user/.ebuild/repos/eboot
  Git:    main @ e4f5g6h
```

### Update repos (git pull)

```bash
ebuild repos update          # Pull all repos
ebuild repos update eos      # Pull specific repo
```

### Change URL or branch

```bash
ebuild repos set-url eos https://github.com/myfork/eos.git
ebuild repos set-branch eboot v0.3.0
```

### Link / unlink local repos

```bash
ebuild repos link eos /path/to/local/eos       # Use local checkout
ebuild repos unlink eos                         # Revert to cached clone
```

## `ebuild generate-board` — Board Config Generation

Generate board/boot/build YAML configs from hardware inputs:

### From MCU name (no files needed)

```bash
ebuild generate-board --mcu stm32f407 --output ./config/
```

### From KiCad schematic

```bash
ebuild generate-board --from-kicad design.kicad_sch --output ./config/
```

### From Eagle schematic

```bash
ebuild generate-board --from-eagle design.sch --output ./config/
```

### From BOM CSV

```bash
ebuild generate-board --from-bom parts.csv --output ./config/
```

### From text description

```bash
ebuild generate-board --describe "STM32H743 with CAN, SPI flash W25Q128, IMU MPU6050" --output ./config/
```

### With product profile

```bash
ebuild generate-board --mcu nrf52840 --product ble-sensor --output ./config/
```

### Generated files

| File | Description |
|------|-------------|
| `board.yaml` | EoS board definition |
| `boot.yaml` | eBoot flash layout (auto-calculated partitions) |
| `build.yaml` | ebuild project config |
| `eos_product_config.h` | C header with `EOS_ENABLE_*` flags |
| `eboot_flash_layout.h` | eBoot C header |
| `eboot_memory.ld` | Linker script |
| `eboot_config.cmake` | CMake variables for eBoot |

## CMake Integration

The root `CMakeLists.txt` now auto-resolves repo paths. You can also override at configure time:

```bash
# Use cached repos (default after `ebuild setup`)
cmake -B build

# Override eos source
cmake -B build -DEOS_SOURCE_DIR=/path/to/eos

# Override eboot source
cmake -B build -DEBOOT_SOURCE_DIR=/path/to/eboot
```

## Configuration File

`~/.ebuild/config.yaml` stores persistent settings:

```yaml
repos:
  eos:
    url: "https://github.com/spatchava/eos.git"
    branch: "main"
    path: null          # null = use cache, or absolute path to local repo
  eboot:
    url: "https://github.com/spatchava/eboot.git"
    branch: "main"
    path: null
cache_dir: "~/.ebuild/repos"
```

Edit this file directly or use `ebuild repos set-url` / `ebuild repos set-branch` / `ebuild repos link`.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `EBUILD_EOS_PATH` | Override eos repo path (priority 2) |
| `EBUILD_EBOOT_PATH` | Override eboot repo path (priority 2) |
| `EBUILD_REPOS_DIR` | Override cache directory (default `~/.ebuild/repos`) |

## Migration from `core/` Layout

If you were using the old embedded `core/eos/` and `core/eboot/` directories:

1. Run `ebuild setup` to clone repos to the shared cache
2. The `core/` directories still work as a **fallback** but print a deprecation warning
3. You can safely delete `core/eos/` and `core/eboot/` after confirming `ebuild setup` works
4. CI pipelines should add `ebuild setup` as a first step

```bash
# Verify setup works
ebuild setup
ebuild repos status

# Confirm build works from cache
ebuild build --target raspi4

# Safe to remove embedded copies
rm -rf core/eos core/eboot
```
