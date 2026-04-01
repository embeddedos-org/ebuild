# Add Cortex-R5 Example Firmware Project

## Summary

Create a complete, buildable Cortex-R5 example firmware project that demonstrates
the TMS570 board port end-to-end. This is the missing "hello world" that proves a
developer can scaffold, build, and flash a Cortex-R5 target using the ebuild/eos/eboot
tooling.

Today a developer can run `ebuild new my-app --template bare-metal --board tms570`
and get a project scaffolded with the correct toolchain/arch/core, but the generated
`main.c` uses generic GPIO/UART calls that don't showcase R5-specific capabilities.
There is also no standalone example under `ebuild/examples/` for Cortex-R5, and no
matching `ebuild new` template that demonstrates safety-critical patterns.

---

## Deliverables

### 1. Example project: `ebuild/examples/cortex_r5_safety/`

A self-contained example (like `hello_world` or `rtos_firmware`) that can be
built with `ebuild build` or directly with CMake + the R5 cross-compiler.

#### `examples/cortex_r5_safety/build.yaml`

```yaml
name: cortex-r5-safety
version: "1.0.0"

toolchain:
  compiler: gcc
  arch: arm
  prefix: arm-none-eabi-

targets:
  - name: r5_safety_demo
    type: executable
    sources: ["src/*.c"]
    include_dirs: ["include"]
    cflags: ["-mcpu=cortex-r5", "-mfloat-abi=hard", "-mfpu=vfpv3-d16", "-Os"]
    ldflags: ["-T", "linker/tms570_app.ld", "-nostartfiles"]

firmware:
  board: tms570
  core: cortex-r5f
  tick_rate: 1000
  watchdog_ms: 100
```

#### `examples/cortex_r5_safety/linker/tms570_app.ld`

Minimal linker script for application firmware (runs from flash, data in RAM):
- `FLASH (rx)` at 0x00210000 (slot A region from board_cortex_r5.h)
- `RAM (rwx)` at 0x08000000 (256K SRAM)
- Standard `.text`, `.data (AT>FLASH)`, `.bss` sections
- `_estack` at top of RAM

#### `examples/cortex_r5_safety/include/app_config.h`

Project-level configuration header:
- Watchdog timeout, heartbeat interval, CAN node ID
- SCI baud rate (115200), RTI tick rate (1 kHz)
- Safety: ECC check enable, lockstep mode flag, ESM channel config

#### `examples/cortex_r5_safety/src/main.c`

Demonstrate R5-specific patterns (~120 lines):
- **RTI timer setup** — configure RTI Compare 0 for 1 ms tick (not SysTick)
- **SCI UART** — print boot banner via TMS570 SCI registers (not generic USART)
- **DWD watchdog** — enable RTI Digital Windowed Watchdog, feed in main loop
- **CAN transmit** — send a heartbeat CAN frame (DCAN module, TMS570-specific)
- **ESM** — check Error Signaling Module status on boot, clear flags
- **Interrupt control** — use `cpsid if` / `cpsie if` (both IRQ+FIQ)
- Main loop: feed watchdog → read SCI → transmit CAN heartbeat → toggle GPIO

#### `examples/cortex_r5_safety/src/r5_startup.c`

Minimal startup code (~60 lines):
- ARM exception vector table (reset, undef, SWI, prefetch abort, data abort, IRQ, FIQ)
- `_reset_handler`: zero BSS, copy `.data` from flash to RAM, branch to `main()`
- No MSP load (Cortex-R boots directly, unlike Cortex-M vector table)

#### `examples/cortex_r5_safety/README.md`

- What this example demonstrates (R5 safety MCU patterns)
- Hardware target (TMS570LC43x / RM57Lx)
- Build instructions (ebuild and CMake)
- Flash instructions (CCS UniFlash / OpenOCD + XDS110)
- Key differences from Cortex-M examples (no Thumb, no SysTick, no NVIC, DWD watchdog)
- Memory map reference (link to `eboot/boards/cortex_r5/board_cortex_r5.h`)

---

### 2. Template: `ebuild/templates/safety-critical/`

A new `ebuild new` template for safety-critical R5 projects, selectable via:
```bash
ebuild new my-safety-app --template safety-critical --board tms570
```

#### `templates/safety-critical/main.c.template`

Similar to the example `main.c` but with `{{PROJECT_NAME}}`, `{{BOARD_NAME}}`,
`{{TOOLCHAIN}}` placeholders. Should include:
- RTI watchdog init + feed
- SCI UART banner print
- ESM status check
- `cpsid if` / `cpsie if` interrupt guards
- Heartbeat loop with CAN transmit stub

#### `templates/safety-critical/build.yaml.template`

Following the `bare-metal` template pattern with R5-specific cflags:
```yaml
toolchain:
  target: {{TOOLCHAIN}}
targets:
  - name: {{PROJECT_NAME}}
    type: executable
    sources: [src/main.c]
    cflags: ["-mcpu=cortex-r5", "-mfloat-abi=hard", "-mfpu=vfpv3-d16"]
```

#### `templates/safety-critical/eos.yaml.template`

```yaml
system:
  kind: baremetal
  board: {{BOARD_NAME}}
  entry: src/main.c
  output: {{PROJECT_NAME}}.bin
```

#### `templates/safety-critical/README.md.template`

With `{{PROJECT_NAME}}` and `{{BOARD_NAME}}` placeholders.

---

### 3. Register the template in `ebuild/cli/commands.py`

Add `"safety-critical"` to the `--template` choice list in the `new` command
(line 946):

```python
type=click.Choice(["bare-metal", "ble-sensor", "rtos-app", "linux-app",
                    "secure-boot", "safety-critical"]),
```

No other code changes needed — the `new` command already handles template
variable substitution and the `board_map` already has the `tms570` entry.

---

### 4. Tests: `tests/test_cortex_r5_integration.py`

Add a new test class `TestCortexR5Example` with:

```python
class TestCortexR5Example:
    EXAMPLE = _EBUILD_ROOT / "examples" / "cortex_r5_safety"
    TEMPLATE = _EBUILD_ROOT / "templates" / "safety-critical"

    def test_example_directory_exists(self):
        assert self.EXAMPLE.is_dir()

    def test_example_build_yaml(self):
        content = (self.EXAMPLE / "build.yaml").read_text()
        assert "cortex-r5" in content
        assert "tms570" in content

    def test_example_main_has_r5_patterns(self):
        content = (self.EXAMPLE / "src" / "main.c").read_text()
        assert "cpsid if" in content or "RTI" in content
        assert "SCI" in content or "DWD" in content

    def test_example_has_linker_script(self):
        assert (self.EXAMPLE / "linker" / "tms570_app.ld").exists()

    def test_example_has_startup(self):
        assert (self.EXAMPLE / "src" / "r5_startup.c").exists()

    def test_template_directory_exists(self):
        assert self.TEMPLATE.is_dir()

    def test_template_has_all_files(self):
        for f in ["main.c.template", "build.yaml.template",
                   "eos.yaml.template", "README.md.template"]:
            assert (self.TEMPLATE / f).exists(), f"Missing {f}"

    def test_template_uses_placeholders(self):
        content = (self.TEMPLATE / "main.c.template").read_text()
        assert "{{PROJECT_NAME}}" in content
        assert "{{BOARD_NAME}}" in content

    def test_safety_critical_in_cli_choices(self):
        src = (_EBUILD_ROOT / "ebuild" / "cli" / "commands.py").read_text()
        assert "safety-critical" in src
```

---

## Files Created / Modified

| File | Action |
|------|--------|
| `examples/cortex_r5_safety/build.yaml` | **Create** |
| `examples/cortex_r5_safety/linker/tms570_app.ld` | **Create** |
| `examples/cortex_r5_safety/include/app_config.h` | **Create** |
| `examples/cortex_r5_safety/src/main.c` | **Create** |
| `examples/cortex_r5_safety/src/r5_startup.c` | **Create** |
| `examples/cortex_r5_safety/README.md` | **Create** |
| `templates/safety-critical/main.c.template` | **Create** |
| `templates/safety-critical/build.yaml.template` | **Create** |
| `templates/safety-critical/eos.yaml.template` | **Create** |
| `templates/safety-critical/README.md.template` | **Create** |
| `ebuild/cli/commands.py` | **Modify** — add `safety-critical` to template choices |
| `tests/test_cortex_r5_integration.py` | **Modify** — add `TestCortexR5Example` class |

## Acceptance Criteria

1. `ebuild new test-app --template safety-critical --board tms570` scaffolds a
   project with R5-specific cflags and SCI/RTI/DWD patterns in `main.c`
2. `examples/cortex_r5_safety/` contains a buildable project (compiles with
   `arm-none-eabi-gcc -mcpu=cortex-r5` without errors when cross-compiler is present)
3. All existing tests pass (`python -m pytest tests/ -q` → 144+ passed)
4. New `TestCortexR5Example` tests pass (~9 tests)
5. `main.c` in both example and template demonstrates at least: RTI watchdog,
   SCI UART, interrupt control via `cpsid if`/`cpsie if`, and one
   safety-specific pattern (ESM check or ECC status)

## References

- Board port: `eboot/boards/cortex_r5/board_cortex_r5.c` (SCI, RTI, DWD register patterns)
- Board header: `eboot/boards/cortex_r5/board_cortex_r5.h` (memory map, register bases)
- Board YAML: `eos/boards/tms570.yaml` (core, features, peripherals)
- Existing template pattern: `ebuild/templates/bare-metal/` (4-file structure)
- Existing example pattern: `ebuild/examples/rtos_firmware/` (build.yaml with firmware section)
- CLI board_map: `ebuild/cli/commands.py` line 1006 (tms570 already registered)
