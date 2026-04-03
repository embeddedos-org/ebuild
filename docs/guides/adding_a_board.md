# Adding a New Board Target

Step-by-step guide for contributing a new MCU/SoC board target to ebuild.

## Overview

Adding a new board requires changes in up to 4 places:

1. **ebuild** — MCU database + CLI board map + toolchain (this repo)
2. **eboot** — Board port (header, source, linker scripts, CMake)
3. **eos** — Toolchain YAML/CMake + board YAML
4. **tests** — Validation tests

## Step 1: Add to MCU Database

Edit `ebuild/eos_ai/eos_hw_analyzer.py` and add your MCU to `MCU_DATABASE`:

```python
MCU_DATABASE = {
    # ... existing entries ...
    "my_mcu": {
        "arch": "arm",           # arm, arm64, riscv, xtensa, mips, x86_64
        "core": "cortex-m4",     # CPU core
        "vendor": "MyVendor",    # Chip vendor
        "family": "MY_MCU",      # MCU family name
    },
}
```

### MCU Database Fields

| Field | Description | Examples |
|-------|-------------|---------|
| `arch` | ISA architecture | `arm`, `arm64`, `riscv`, `xtensa`, `mips`, `x86_64` |
| `core` | CPU core model | `cortex-m0+`, `cortex-m4`, `cortex-m4f`, `cortex-m7`, `cortex-r5f`, `cortex-a53`, `cortex-a72`, `lx6`, `rv64gc` |
| `vendor` | Chip manufacturer | `ST`, `Nordic`, `Espressif`, `TI`, `NXP`, `Broadcom`, `SiFive`, `Renesas` |
| `family` | MCU family name | `STM32F4`, `STM32H7`, `NRF52`, `ESP32`, `TMS570`, `RP2040`, `IMX8M` |

## Step 2: Add CLI Board Map Entry

Edit `ebuild/cli/commands.py` and add to `board_map` in the `new` command:

```python
board_map = {
    # ... existing entries ...
    "my_board": {
        "arch": "arm",
        "core": "cortex-m4",
        "toolchain": "arm-none-eabi",
        "vendor": "myvendor",
    },
}
```

## Step 3: Add Toolchain (if new)

If your board uses a toolchain not already in `ebuild/build/toolchain.py`, add it to `PREDEFINED_TOOLCHAINS`:

```python
PREDEFINED_TOOLCHAINS = {
    # ... existing entries ...
    "my-toolchain": {
        "prefix": "my-toolchain-",
        "arch": "arm",
        "cc": "my-toolchain-gcc",
        "cxx": "my-toolchain-g++",
        "ar": "my-toolchain-ar",
        "objcopy": "my-toolchain-objcopy",
    },
}
```

Existing toolchains: `host`, `arm-none-eabi`, `aarch64-linux-gnu`, `riscv64-linux-gnu`, `xtensa-esp32-elf`.

## Step 4: Create eboot Board Port

Create a directory under `eboot/boards/my_board/` with:

### board_my_board.h

```c
#ifndef BOARD_MY_BOARD_H
#define BOARD_MY_BOARD_H

#include "eos_hal.h"

// Memory regions
#define MY_FLASH_BASE   0x08000000
#define MY_FLASH_SIZE   (512 * 1024)
#define MY_RAM_BASE     0x20000000
#define MY_RAM_SIZE     (128 * 1024)

// Flash layout
#define MY_STAGE0_ADDR  MY_FLASH_BASE
#define MY_STAGE1_ADDR  (MY_FLASH_BASE + 0x4000)
#define MY_SLOT_A_ADDR  (MY_FLASH_BASE + 0x10000)
#define MY_SLOT_B_ADDR  (MY_FLASH_BASE + 0x48000)

// Platform
#define EOS_PLATFORM     EOS_PLATFORM_ARM_M4

// Board API
void board_early_init(void);
const eos_board_ops_t *board_get_ops(void);

#endif
```

### board_my_board.c

Implement the `eos_board_ops_t` interface:

```c
#include "board_my_board.h"

static int my_flash_read(uint32_t addr, void *buf, uint32_t len) { /* ... */ }
static int my_flash_write(uint32_t addr, const void *buf, uint32_t len) { /* ... */ }
static int my_flash_erase(uint32_t addr, uint32_t len) { /* ... */ }
static void my_watchdog_init(uint32_t timeout_ms) { /* ... */ }
static void my_watchdog_feed(void) { /* ... */ }
// ... implement all board ops ...

static const eos_board_ops_t board_ops = {
    .flash_base = MY_FLASH_BASE,
    .flash_size = MY_FLASH_SIZE,
    .slot_a_addr = MY_SLOT_A_ADDR,
    // ... all fields ...
    .flash_read = my_flash_read,
    .flash_write = my_flash_write,
    .flash_erase = my_flash_erase,
    .watchdog_init = my_watchdog_init,
    .watchdog_feed = my_watchdog_feed,
    // ... all function pointers ...
};

void board_early_init(void) {
    // Clock init, GPIO setup, etc.
}

const eos_board_ops_t *board_get_ops(void) {
    return &board_ops;
}
```

### Linker Scripts

Create `my_board_stage0.ld` and `my_board_stage1.ld`:

```ld
/* my_board_stage0.ld */
MEMORY {
    FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 16K
    RAM   (rwx) : ORIGIN = 0x20000000, LENGTH = 128K
}

SECTIONS {
    .vectors : { KEEP(*(.vectors)) } > FLASH
    .text    : { *(.text*) }          > FLASH
    .rodata  : { *(.rodata*) }       > FLASH
    .data    : { *(.data*) }          > RAM AT> FLASH
    .bss     : { *(.bss*) }          > RAM
}
```

## Step 5: Register in eboot CMakeLists.txt

Add your board to `eboot/CMakeLists.txt`:

```cmake
elseif(EBLDR_BOARD STREQUAL "my_board")
    eboot_add_board(my_board
        boards/my_board/board_my_board.c
        boards/my_board/board_my_board.h
    )
```

Add `my_board` to the `FATAL_ERROR` message listing valid boards.

## Step 6: Create Hardware YAML (optional)

Add a sample board description to `hardware/board/`:

```yaml
# hardware/board/my_board.yaml
board:
  name: "My Custom Board"
  vendor: "MyVendor"
  mcu: MY_MCU_MODEL
  arch: arm
  core: cortex-m4
  clock_mhz: 168
  memory:
    flash:
      size_kb: 512
      base: 0x08000000
    ram:
      size_kb: 128
      base: 0x20000000
  peripherals:
    - type: uart
      count: 3
    - type: spi
      count: 2
    - type: i2c
      count: 2
    - type: gpio
      count: 5
```

## Step 7: Add Project Generator Mapping

Edit `ebuild/eos_ai/eos_project_generator.py`:

```python
MCU_TO_EBOOT_BOARD = {
    # ... existing ...
    "my_mcu": "my_board",
}
```

## Step 8: Write Tests

Add test cases in `tests/ebuild/`:

```python
class TestMyBoardIntegration:
    """Validates my_board target across repos."""

    def test_mcu_in_database(self):
        from ebuild.eos_ai.eos_hw_analyzer import EosHardwareAnalyzer
        assert "my_mcu" in EosHardwareAnalyzer.MCU_DATABASE

    def test_board_in_cli_map(self):
        src = Path("ebuild/cli/commands.py").read_text()
        assert '"my_board"' in src

    def test_eboot_board_dir_exists(self):
        assert (EBOOT_ROOT / "boards" / "my_board").is_dir()
```

## Step 9: Add QEMU Test (if applicable)

If your board can be tested with QEMU, add a test in `tests/test_qemu_targets.py`:

```python
@pytest.mark.qemu
def test_my_board_qemu_boot():
    """Verify my_board boots in QEMU."""
    result = subprocess.run(
        ["qemu-system-arm", "-M", "my_machine", "-kernel", "build/my_board.elf",
         "-nographic", "-serial", "mon:stdio"],
        capture_output=True, text=True, timeout=10
    )
    assert "EoS boot" in result.stdout
```

## Checklist

- [ ] MCU added to `MCU_DATABASE` in `eos_hw_analyzer.py`
- [ ] Board entry added to `board_map` in `commands.py`
- [ ] Toolchain exists in `PREDEFINED_TOOLCHAINS` (or added)
- [ ] eboot board port created (`board_*.h`, `board_*.c`)
- [ ] Linker scripts created (stage0, stage1)
- [ ] Board registered in eboot `CMakeLists.txt`
- [ ] Hardware YAML created in `hardware/board/`
- [ ] Project generator mapping added
- [ ] Tests written and passing
- [ ] QEMU test added (if applicable)
