# ebuild Test Suite

**156 tests** across **21 classes** in two test modules, validating the ebuild
build system and the full Cortex-R5 cross-compile pipeline spanning three repos
(ebuild, eos, eboot).

## Quick Start

```bash
# Run everything (from ebuild repo root)
python -m pytest

# Run a single module
python -m pytest tests/test_eos_ai.py
python -m pytest tests/test_cortex_r5_integration.py

# Run a single class
python -m pytest tests/test_cortex_r5_integration.py::TestEbootMPU

# Run a single test
python -m pytest tests/test_cortex_r5_integration.py::TestEbootMPU::test_cp15_drbar

# Standalone (no pytest required)
python tests/test_eos_ai.py
python tests/test_cortex_r5_integration.py
```

### Prerequisites

- Python ≥ 3.9
- `pytest` (for pytest runner — not needed for standalone mode)
- Sibling repos checked out for integration tests:
  ```
  parent/
  ├── ebuild/   ← you are here
  ├── eos/
  └── eboot/
  ```

No other dependencies are required. The test suite deliberately avoids
importing modules that depend on `pyyaml` or `click`, so tests run on a
bare Python install.

---

## Test Modules

### `test_eos_ai.py` — Unit Tests (23 tests)

Validates the ebuild EoS AI hardware analyzer, profile dataclass, and
analysis pipeline. Runs standalone with zero dependencies.

| Class | Tests | What it covers |
|-------|------:|----------------|
| `TestHardwareAnalyzer` | 16 | MCU detection (STM32, nRF52, ESP32, i.MX8M, RP2040), peripheral keyword matching, BOM parsing, flash/RAM/clock extraction, LLM prompt generation |
| `TestHardwareProfile` | 4 | `has_peripheral()`, `get_eos_enables()`, `to_dict()`, empty profile defaults |
| `TestEosAIIntegration` | 3 | End-to-end text→profile→enables for STM32H7, nRF52 BLE, unknown MCU |

### `test_cortex_r5_integration.py` — Integration Tests (133 tests)

Validates the complete Cortex-R5 first-class support across all three repos.
Requires `../eos` and `../eboot` checked out alongside `ebuild`.

#### Phase 1 — eboot (65 tests)

| Class | Tests | What it covers |
|-------|------:|----------------|
| `TestEbootToolchain` | 10 | `arm-none-eabi-r5.cmake` flags: `-mcpu=cortex-r5`, hard-float, no `-mthumb`, `nosys.specs`, `STATIC_LIBRARY` try-compile |
| `TestEbootBoardHeader` | 12 | `board_cortex_r5.h` memory map: ATCM/BTCM/Flash/RAM addresses and sizes, flash layout slots, SCI/RTI bases, `EOS_PLATFORM_ARM_R5F` |
| `TestEbootBoardPort` | 12 | `board_cortex_r5.c`: `cpsid if`/`cpsie if` (IRQ+FIQ), direct branch jump (no MSP), RTI watchdog key sequence, SCI UART registers, all 28 `eos_board_ops_t` fields |
| `TestEbootLinkerScripts` | 9 | Stage-0 (`ATCM`/`BTCM`, `.vectors` section), Stage-1 (`FLASH`/`RAM` origins), standard `.text`/`.data`/`.bss` sections |
| `TestEbootCMakeLists` | 6 | `cortex_r5` in board option string, `elseif` block, `eboot_add_board()` call, `FATAL_ERROR` listing |
| `TestEbootMPU` | 10 | CP15 coprocessor registers (RGNR `c6,c2,0`, DRBAR `c6,c1,0`, DRSR `c6,c1,2`, DRACR `c6,c1,4`, SCTLR `c1,c0,0`), ISB barriers, `__ARM_ARCH_7R__` guards in both `eos_mpu_apply` and `eos_mpu_disable` |
| `TestEbootReleaseCI` | 6 | `release.yml` matrix entry: `arm-cortex-r5` arch, toolchain path, packages, artifact suffix, release body table |

#### Phase 2 — eos (26 tests)

| Class | Tests | What it covers |
|-------|------:|----------------|
| `TestEosToolchainYAML` | 7 | `arm-none-eabi-r5.yaml`: name, target, cflags (`-mcpu=cortex-r5`, no `-mthumb`), ldflags |
| `TestEosToolchainCMake` | 2 | `arm-none-eabi-r5.cmake` exists, `CMAKE_C_FLAGS_INIT` matches eboot's toolchain |
| `TestEosBoardYAML` | 9 | `tms570.yaml`: `cortex-r5f` core, `arm` arch, TI vendor, TMS570 family, TCM memory, safety/MPU features, toolchain reference |
| `TestEosToolchainC` | 4 | `toolchain.c` `arch_from_target()`: `arm-none-eabi` → `EOS_ARCH_ARM_CORTEX_M`, detection order before `EOS_ARCH_HOST` fallthrough |
| `TestEosHalRTOS` | 4 | `hal_rtos.c` comments: "Cortex-M and Cortex-R", "RTI timer ISR (Cortex-R)" |

#### Phase 3 — ebuild (20 tests)

| Class | Tests | What it covers |
|-------|------:|----------------|
| `TestEbuildMCUDatabase` | 7 | `MCU_DATABASE` entries: tms570/tms570lc/rm57 (`cortex-r5f`), rm46/rz_t1 (`cortex-r4f`), text detection roundtrip |
| `TestEbuildCLIBoardMap` | 6 | `commands.py` `board_map`: tms570 with `arm`/`cortex-r5f`/`arm-none-eabi`/`ti`, am64x hybrid |
| `TestEbuildPredefinedToolchains` | 3 | `toolchain.py` `PREDEFINED_TOOLCHAINS`: `arm-none-eabi` entry with correct prefix and arch |
| `TestEbuildProjectGenerator` | 4 | `eos_project_generator.py`: `MCU_TO_EBOOT_BOARD` (tms570/rm57/rm46 → `cortex_r5`), `ARCH_TO_TOOLCHAIN` (`arm-cortex-r` → `arm-none-eabi-r5.yaml`) |

#### End-to-End (10 tests)

| Class | Tests | What it covers |
|-------|------:|----------------|
| `TestEndToEndPipeline` | 10 | Full cross-repo roundtrips: text→profile→manifest, memory map consistency (header↔linker scripts), Cortex-M vs R5 toolchain flag differentiation, ebuild→eboot board dir existence, eos board YAML→toolchain file resolution, CI matrix coverage |

#### Phase 5 — Example + Template (12 tests)

| Class | Tests | What it covers |
|-------|------:|----------------|
| `TestCortexR5Example` | 12 | Example project: build.yaml, main.c R5 patterns, linker script addresses, startup vectors, config header, README; Template: all 4 files exist, placeholders, R5 patterns; CLI `safety-critical` choice registered |

---

## Configuration

### `pytest.ini`

```ini
[pytest]
testpaths = tests
pythonpath = .          # import ebuild without pip install
addopts = -v --tb=short --strict-markers --no-header
```

Key settings:
- **`pythonpath = .`** — makes `import ebuild` work without `pip install -e .`
- **`testpaths = tests`** — discovers tests only in `tests/` (excludes root-level `test_full_pipeline.py`)
- **`--strict-markers`** — catches marker typos at collection time

The snippet above shows key settings only; the full file also declares `python_files`,
`python_classes`, `python_functions`, and the `markers` block.

### `conftest.py`

Provides:
- **`EBUILD_ROOT`**, **`EOS_ROOT`**, **`EBOOT_ROOT`** path constants and matching fixtures
- **`pytest_collection_modifyitems`** hook — auto-skips tests marked `@pytest.mark.needs_yaml` when `pyyaml` is not installed

### Markers

```bash
# Run only eboot tests
python -m pytest -m eboot

# Run only integration tests
python -m pytest -m integration

# Skip tests that need pyyaml
python -m pytest -m "not needs_yaml"
```

| Marker | Purpose |
|--------|---------|
| `eboot` | Tests that validate eboot repo artifacts |
| `eos` | Tests that validate eos repo artifacts |
| `ebuild` | Tests that validate ebuild repo artifacts |
| `integration` | End-to-end tests spanning multiple repos |
| `needs_yaml` | Tests that import modules requiring `pyyaml` |

---

## CI Workflow

The GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every push to
`master` and on every pull request targeting `master`.

### Jobs

```
┌─────────────────────────────────────────────────────────────┐
│                        CI Pipeline                          │
├──────────┬───────────────────┬──────────────┬───────────────┤
│   unit   │   integration     │  full-suite  │   ci-pass     │
│          │                   │              │               │
│ 3 OS     │ 3 OS              │ Ubuntu       │ Gate job      │
│ × 2 Py   │ × 2 Py            │ × 2 Py       │               │
│          │                   │              │ Required:     │
│ ebuild   │ ebuild + eos      │ All tests    │  unit ✓       │
│ only     │ + eboot           │ + coverage   │  full-suite ✓ │
│          │                   │ + pipeline   │               │
│ 23 tests │ 133 tests         │ 156 tests    │ Best-effort:  │
│          │                   │              │  integration  │
└──────────┴───────────────────┴──────────────┴───────────────┘
```

| Job | Matrix | Repos | Tests | Artifacts |
|-----|--------|-------|-------|-----------|
| **`unit`** | 3 OS × 2 Python | ebuild | `test_eos_ai.py` (23) | `results-unit.xml` |
| **`integration`** | 3 OS × 2 Python | ebuild + eos + eboot | `test_cortex_r5_integration.py` (133) | `results-integration.xml` |
| **`full-suite`** | Ubuntu × 2 Python | ebuild + eos + eboot | All tests (156) + `test_full_pipeline.py` | `results-full.xml`, `coverage.xml` |
| **`ci-pass`** | Ubuntu | — | — | — |

### Sibling Repo Checkout

Integration and full-suite jobs check out all three repos side-by-side:

```
$GITHUB_WORKSPACE/
├── ebuild/    ← actions/checkout (this repo)
├── eos/       ← actions/checkout (sibling, continue-on-error)
└── eboot/     ← actions/checkout (sibling, continue-on-error)
```

This matches the local development layout that `test_cortex_r5_integration.py`
expects (`_EBOOT_ROOT = _EBUILD_ROOT.parent / "eboot"`).

When sibling repos are inaccessible (e.g., fork PRs), integration tests are
skipped gracefully — the `ci-pass` gate job treats integration as best-effort.

### Branch Protection

Add **`CI Pass`** as the required status check in branch protection rules.
This single job gates on `unit` + `full-suite` (required), waits for
`integration` (warns on failure without blocking merges).

### Test Results

All pytest runs emit JUnit XML (`--junitxml`), which GitHub Actions renders
as a test summary on the workflow run page. The full-suite job also produces
a `coverage.xml` for coverage tracking.

---

## Adding Tests

### Unit test (ebuild-only)

Add to `tests/test_eos_ai.py` or create a new `tests/test_<module>.py`:

```python
class TestMyFeature:
    def test_something(self):
        from ebuild.eos_ai.eos_hw_analyzer import EosHardwareAnalyzer
        analyzer = EosHardwareAnalyzer()
        profile = analyzer.interpret_text("my hardware description")
        assert profile.mcu == "EXPECTED"
```

### Integration test (cross-repo)

Add to `tests/test_cortex_r5_integration.py` or create a new module.
Use file-based checks to avoid importing modules with heavy dependencies:

```python
from pathlib import Path

_EBOOT_ROOT = Path(__file__).resolve().parent.parent.parent / "eboot"

class TestMyBoardPort:
    SOURCE = _EBOOT_ROOT / "boards" / "my_board" / "board_my_board.c"

    def test_file_exists(self):
        assert self.SOURCE.exists()

    def test_has_required_ops(self):
        content = self.SOURCE.read_text()
        assert ".flash_read" in content
```

### Avoiding dependency issues

Tests must run without `pyyaml`, `click`, or any other runtime dependency.
Follow these patterns:

| Need | Do | Don't |
|------|----|-------|
| Check a Python source file | Read it as text with `Path.read_text()` | `from ebuild.build.toolchain import X` (transitive yaml import) |
| Check a data structure | Import from modules without heavy deps | Import from modules that import `yaml` |
| Mark a test that needs yaml | `@pytest.mark.needs_yaml` | Let it crash at collection time |

---

## Standalone Mode

Both test files include a `__main__` block so they run without pytest:

```bash
python tests/test_eos_ai.py
python tests/test_cortex_r5_integration.py
```

`test_eos_ai.py` output:
```
  PASS: TestHardwareAnalyzer.test_detect_stm32h7
  ...
==================================================
Results: 23/23 passed, 0 failed
==================================================
```

`test_cortex_r5_integration.py` output:
```
  PASS: TestEbootToolchain.test_toolchain_file_exists
  ...
============================================================
Cortex-R5 Integration Tests: 133/133 passed, 0 failed
============================================================
```

There is also a root-level `test_full_pipeline.py` that exercises the
hardware-analysis→config-generation pipeline end-to-end without any imports
from ebuild (it inlines the core classes). This is run by the `full-suite`
CI job and the `nightly.yml` workflow.
