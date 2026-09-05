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

---

## Parallel Package Builds

`ebuild build` resolves declared packages into a dependency graph and builds
them in an order that satisfies every dependency. By default it walks that
order one package at a time.

A topological order is only *an* order, though — it says nothing about which
packages could have been built simultaneously. A project depending on `zlib`,
`mbedtls` and `lwip` builds all three back-to-back even though none of them
depends on the others.

`-j/--jobs` lifts that restriction:

```bash
ebuild build -j 4       # up to 4 packages building at once
ebuild build            # equivalent to -j 1: strictly sequential
```

### What the scheduler guarantees

- **Dependency order is never violated.** A package starts only once every
  package it depends on has finished *successfully*.
- **The schedule is dynamic, not level-by-level.** A package becomes eligible
  the moment its own dependencies complete, rather than waiting for every
  other package at the same depth. A slow package therefore delays only what
  actually depends on it.
- **Dispatch order is deterministic** for a given graph and job count, so logs
  stay comparable between runs.
- **A failure stops new work.** The first exception is re-raised unchanged;
  packages that never ran because a dependency failed are reported as skipped.
  Packages already in flight are allowed to finish rather than being abandoned
  part-way, which would leave half-written install trees in the cache.
- **`-j 1` is exactly the previous behaviour**, not a one-worker special case
  of the parallel path.

### Choosing a value

`-j` counts *packages*, not compiler processes. Each package's own build
already parallelises internally (`make -j`, `cmake --build --parallel`), so the
effective process count is roughly `jobs × per-package parallelism`. On a
machine with N cores, `-j 2` to `-j 4` is usually enough to overlap the long
poles without thrashing; going much higher mostly adds memory pressure.

Parallel builds also interleave package log lines. Output from each package is
written atomically, but the packages themselves are no longer contiguous —
use `-j 1` when reading a build log closely.

---

## Remote Package Index & Discovery

ebuild provides index-based package discovery and remote recipe synchronization, allowing embedded projects to discover, query, and install external libraries seamlessly.

### Discovering Packages (`ebuild search`)

Search across local project recipes (`./recipes/`), bundled system recipes, and cached remote repository indices:

```bash
ebuild search json                 # Search by keyword in name, description, or license
ebuild search --all                # List all available packages across all sources
ebuild search --json               # Output machine-readable JSON array
ebuild search --build-system cmake # Filter by build system (cmake, make, meson)
ebuild search --license MIT        # Filter by license type
```

Example output:

```
=== ebuild - Package Search ===
[info] Found 10 package(s):
   cjson v1.7.18 [cmake] (MIT) - Ultralightweight JSON parser in ANSI C
   freertos v11.1.0 [cmake] (MIT) - Real-time operating system kernel for embedded devices
   littlefs v2.9.3 [make] (BSD-3-Clause) - Little fail-safe filesystem designed for microcontrollers
   lvgl v9.2.2 [cmake] (MIT) - Light and Versatile Embedded Graphics Library
   lwip v2.2.0 [cmake] (BSD-3-Clause) - Lightweight TCP/IP stack for embedded systems
   mbedtls v3.6.0 [cmake] (Apache-2.0) - Lightweight TLS/SSL library for embedded systems
   nanopb v0.4.9.1 [cmake] (zlib) - Protocol Buffers with small code size for microcontrollers
   tinyusb v0.18.0 [cmake] (MIT) - Open-source cross-platform USB host/device stack for embedded system
   unity v2.6.1 [cmake] (MIT) - Simple Unit Testing for C
   zlib v1.3.1 [cmake] (Zlib) - General-purpose lossless data compression library
```

### Synchronizing Remote Index (`ebuild update-index`)

Refresh the local package index and cached recipe definitions from a remote repository mirror:

```bash
ebuild update-index --url https://example.com/recipes/index.json  # Remote repository URL (HTTPS required)
ebuild update-index --url https://example.com/recipes/index.json --force  # Bypass 24h cache TTL and re-download
ebuild update-index --offline                   # Use local cached index without network
```

> [!WARNING]
> **Index Authenticity & Provenance Notice (Unauthenticated Index)**:
> Remote package index synchronization validates transport encryption (HTTPS only) and verifies individual package archive bytes against stated SHA-256 checksums. However, the index document itself is currently **unauthenticated** (detached cryptographic signature verification and package provenance proof are not yet implemented).
>
> In accordance with reproducible build guarantees (§9.2), recipe discovery enforces a strict 3-tier source-ranked precedence hierarchy:
> 1. **Project-Local Recipes** (`./recipes/`): Absolute highest priority; project pins always override upstream.
> 2. **Shipped Catalog Recipes** (`<ebuild>/recipes/`): Built-in verified recipes shipped with ebuild.
> 3. **Cached Remote Index** (`~/.ebuild/index/recipes/`): Definitions synchronized from remote repositories.
>
> An index update will never override pinned URLs, build systems, or checksums defined in your project repository.
>
> Furthermore, `ebuild update-index` automatically prunes stale cached `.yaml` and `.yml` recipes from `~/.ebuild/index/recipes/` that are absent from the updated remote index, preventing retired packages from lingering in the local cache.
>
> To support integrity verification, the SHA-256 digest of the downloaded index is recorded in `~/.ebuild/index/packages.json.sha256`.

### Component Contract (§10.1) Field Coverage

eBuild recipes currently carry a subset of the Master Design §10.1 component contract:
- **Identity**: Package name, version, and optional description.
- **Dependencies**: List of external library package dependencies.
- **Compliance**: Package open-source license identifier.
- **Integrity**: Transport SHA-256 checksum pin for downloaded tarballs.

*Deferred Contract Fields*: Compatibility constraints (EmbeddedOS ABI/API version, architecture, and SoC targets) and Resource constraints (`flash_max`, `ram_max`) are not yet evaluated by the registry layer and must be validated at project build configuration time.

### Shipped Embedded Library Catalog

ebuild includes a curated suite of pre-packaged recipes under `recipes/`:

| Package | Version | Build System | License | Description |
|:---|:---|:---|:---|:---|
| **`cjson`** | 1.7.18 | CMake | MIT | Ultralightweight JSON parser in ANSI C |
| **`freertos`** | 11.1.0 | CMake | MIT | Real-time operating system kernel for embedded devices |
| **`littlefs`** | 2.9.3 | Make | BSD-3-Clause | Fail-safe power-resilient filesystem for microcontrollers |
| **`lvgl`** | 9.2.2 | CMake | MIT | Light and Versatile Embedded Graphics Library |
| **`lwip`** | 2.2.0 | CMake | BSD-3-Clause | Lightweight TCP/IP stack for embedded targets |
| **`mbedtls`** | 3.6.0 | CMake | Apache-2.0 | Cryptographic primitives, TLS/SSL stack |
| **`nanopb`** | 0.4.9.1 | CMake | zlib | Memory-efficient Protocol Buffers implementation |
| **`tinyusb`** | 0.18.0 | CMake | MIT | Cross-platform USB host/device stack |
| **`unity`** | 2.6.1 | CMake | MIT | Standard embedded C unit testing framework |
| **`zlib`** | 1.3.1 | CMake | Zlib | General-purpose lossless data compression |

### Offline & Air-Gapped Operation

For isolated CI/CD pipelines and field deployments:
- Set environment variable `EBUILD_OFFLINE=1` or pass `--offline` to `ebuild update-index` to use cached remote indices without attempting network synchronization.
- Note: Package archive source fetching (`ebuild build`) currently verifies archive integrity against pinned SHA-256 checksums but is not yet gated by the `--offline` flag.
- ebuild automatically searches local directories first and gracefully falls back to cached indices in `~/.ebuild/index/` if the network is unreachable.
- All downloads are validated against SHA-256 integrity pins before extraction.


