# Overlay System Guide

Overlays allow sharing and reusing board configurations, layer presets, and package recipes across projects and teams.

## What is an Overlay?

An overlay is a directory containing reusable ebuild configurations that can be layered on top of the default project settings. Overlays can provide:

- **Board definitions** — preconfigured `board.yaml` files for custom hardware
- **Layer presets** — layer configurations for specific use cases
- **Package recipes** — additional package recipes not in the main repository
- **Build profiles** — predefined build profiles (minimal, full, custom)

## Directory Structure

```
overlays/
└── my-overlay/
    ├── overlay.yaml          # Overlay metadata (required)
    ├── boards/               # Board YAML files
    │   ├── custom_board_1.yaml
    │   └── custom_board_2.yaml
    ├── layers/               # Layer definitions
    │   └── my_custom_layer/
    │       ├── CMakeLists.txt
    │       ├── include/
    │       └── src/
    ├── recipes/              # Package recipes
    │   ├── my_lib.yaml
    │   └── my_driver.yaml
    └── profiles/             # Build profiles
        ├── industrial.yaml
        └── automotive.yaml
```

## Overlay Metadata

Every overlay must have an `overlay.yaml` file:

```yaml
name: my-overlay
version: "1.0.0"
description: "Custom board configs for MyCompany products"
author: "MyCompany Engineering"
license: MIT
compatibility:
  ebuild: ">=0.1.0"
  python: ">=3.9"
```

### Metadata Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Unique overlay name (lowercase, hyphens allowed) |
| `version` | Yes | Semantic version string |
| `description` | Yes | Human-readable description |
| `author` | No | Author or organization name |
| `license` | No | SPDX license identifier |
| `compatibility.ebuild` | No | Minimum ebuild version required |
| `compatibility.python` | No | Minimum Python version required |

## Using Overlays

### Register an Overlay

```bash
# Add a local overlay directory
ebuild overlay add ./path/to/my-overlay

# Add from a Git repository
ebuild overlay add https://github.com/mycompany/ebuild-overlay.git
```

### List Registered Overlays

```bash
ebuild overlay list
```

### Build with Overlay Boards

Once registered, overlay boards become available:

```bash
# Use a board from an overlay
ebuild new --board custom_board_1 --template rtos-app --name my_project

# Build with overlay recipes
ebuild build --target custom_board_1 --overlay my-overlay
```

## Creating an Overlay

### 1. Initialize the Overlay

```bash
mkdir -p my-overlay/{boards,layers,recipes,profiles}
```

### 2. Create the Metadata

```yaml
# my-overlay/overlay.yaml
name: acme-boards
version: "0.1.0"
description: "Board support for ACME Corp custom hardware"
author: "ACME Engineering"
compatibility:
  ebuild: ">=0.1.0"
```

### 3. Add Board Definitions

```yaml
# my-overlay/boards/acme_sensor_v2.yaml
board:
  name: "ACME Sensor v2"
  vendor: "ACME Corp"
  mcu: STM32H743
  arch: arm
  core: cortex-m7
  clock_mhz: 480
  memory:
    flash:
      size_kb: 2048
      base: 0x08000000
    ram:
      size_kb: 1024
      base: 0x24000000
  peripherals:
    - type: uart
      count: 2
    - type: spi
      count: 3
    - type: i2c
      count: 2
    - type: adc
      count: 1
    - type: can
      count: 1
    - type: ble
      count: 1
  boot:
    secure: true
    slots: 2
```

### 4. Add Package Recipes

```yaml
# my-overlay/recipes/acme_driver.yaml
package: acme-driver
version: "2.1.0"
description: "ACME proprietary sensor driver"
url: https://internal.acme.com/releases/acme-driver-2.1.0.tar.gz
checksum: sha256:abc123...
build: cmake
configure_args:
  - -DACME_PLATFORM=eos
  - -DACME_SENSOR_TYPE=imu
dependencies:
  - zlib
```

### 5. Add Build Profiles

```yaml
# my-overlay/profiles/industrial.yaml
profile: industrial
description: "Industrial IoT configuration with safety features"
packages:
  - core
  - hal
  - drivers
  - crypto
  - ota
  - can
  - modbus
  - acme-driver
exclude:
  - ai
  - graphics
  - bluetooth
```

## Sharing Overlays

### Via Git

The recommended way to share overlays:

```bash
# Create a Git repo for your overlay
cd my-overlay
git init
git add .
git commit -m "Initial overlay release"
git remote add origin https://github.com/mycompany/ebuild-overlay.git
git push -u origin main
```

Others can then add it:

```bash
ebuild overlay add https://github.com/mycompany/ebuild-overlay.git
```

### Via Archive

Package as a tarball:

```bash
tar czf acme-boards-0.1.0.tar.gz -C overlays acme-boards/
```

## Overlay Resolution Order

When multiple overlays define the same board or recipe, ebuild resolves them in registration order (first registered wins). To override:

```bash
# Set overlay priority (higher = preferred)
ebuild overlay priority acme-boards 100
ebuild overlay priority community-boards 50
```
