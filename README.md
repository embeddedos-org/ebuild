# ebuild — Unified Embedded Build System

[![CI](https://github.com/embeddedos-org/ebuild/actions/workflows/ci.yml/badge.svg)](https://github.com/embeddedos-org/ebuild/actions/workflows/ci.yml)
[![CodeQL](https://github.com/embeddedos-org/ebuild/actions/workflows/codeql.yml/badge.svg)](https://github.com/embeddedos-org/ebuild/actions/workflows/codeql.yml)
[![Scorecard](https://github.com/embeddedos-org/ebuild/actions/workflows/scorecard.yml/badge.svg)](https://github.com/embeddedos-org/ebuild/actions/workflows/scorecard.yml)
[![Release](https://github.com/embeddedos-org/ebuild/actions/workflows/release.yml/badge.svg)](https://github.com/embeddedos-org/ebuild/actions/workflows/release.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

ebuild is a unified embedded build system written in Python. You describe a
project in a single `build.yaml`; ebuild resolves the dependency and toolchain
graph and drives an underlying build backend, then extends into firmware and
system-image workflows for embedded targets. It is part of the
[EmbeddedOS (EoS)](https://github.com/embeddedos-org) ecosystem. (`ebuild` here
is the EoS build tool and is unrelated to Gentoo's ebuild format.)

## ⚡ Quick Demo

New here? See **[demo.md](demo.md)** — a 5-minute, self-contained walkthrough
that lists the prerequisites (Python, `gcc`, and the `ninja` **pip** package),
then builds and runs a tiny "thermostat" C program end-to-end via `ebuild
build`. A troubleshooting appendix covers no-root / PEP 668 environments and
building without a system compiler.

## Features

Observed in the source tree:

- **Backend dispatch** — auto-detects the project's build system and dispatches
  to CMake, Make, Meson, Cargo, or Kbuild, or generates a Ninja build
  (`ebuild/build/dispatch.py`, `ebuild/build/ninja_backend.py`). Per the package
  metadata, its target scope also includes Buildroot, Zephyr, FreeRTOS, and
  NuttX.
- **Package graph** — install and list project packages
  (`ebuild add`, `ebuild list-packages`).
- **Firmware & flashing** — build RTOS firmware and flash images to targets
  (`ebuild firmware`, `ebuild flash`; `ebuild/firmware/`).
- **System images** — root filesystem, kernel, and disk-image assembly
  (`ebuild system`; `ebuild/system/`).
- **Project scaffolding** — generate projects and boards from templates
  (`ebuild new`, `ebuild generate-project`, `ebuild generate-board`,
  `ebuild generate-boot`).
- **Layers & recipes** — reusable board/OS composition under `layers/` and
  `recipes/`.

## What's inside

| Path | Contents |
|------|----------|
| `ebuild/` | The Python package: `cli/`, `build/`, `core/`, `system/`, `firmware/`, `deps/`, `packages/`, `plugins/`, `eos_ai/` |
| `core/` | Native support components (e.g. `eboot/`) |
| `examples/` | `hello_world`, `linux_image`, `multi_target`, `rtos_firmware`, `cortex_r5_safety`, `eradar360`, `with_packages` |
| `templates/` | Project/board templates used by the generators |
| `recipes/`, `layers/` | Reusable build recipes and board/OS layers |
| `hardware/` | Board/hardware definitions |
| `sdk/` | SDK generation support |
| `tools/` | Helper scripts |
| `docs/` | Documentation (published with MkDocs) |

## Install

Requires Python 3.8+.

```bash
pip install -e .        # from the repo root
# or:
./install.sh            # puts the 'ebuild' command on your PATH
./install.sh --check    # verify the installation
```

Runtime dependencies (`click`, `pyyaml`, `ninja`) are installed automatically.
Note the `ninja` **pip package** is required — a system `ninja` binary alone is
not enough, because ebuild invokes `python -m ninja`.

## Usage

```bash
ebuild info             # show what ebuild parsed from build.yaml
ebuild build            # resolve and build (auto-detects the backend)
ebuild test             # run the project's tests
ebuild build -j 4       # build independent packages concurrently
ebuild clean            # remove build artifacts
ebuild --version
```

`-j/--jobs` controls how many **packages** are built at once. Dependency order
is always honoured — a package starts only once everything it depends on has
finished — so `-j` only overlaps packages that are genuinely independent of one
another. It defaults to `1`, which builds strictly in dependency order. Note
that each package's own build may already run parallel compile jobs, so a large
`-j` can oversubscribe the machine. See
[docs/dependency-management.md](docs/dependency-management.md#parallel-package-builds).

Additional commands: `configure`, `install`, `add`, `list-packages`,
`search`, `update-index`, `pipeline`, `system`, `firmware`, `flash`, `new`,
`generate-project`, `generate-board`, `generate-boot`, `analyze`, `setup`,
and the `repos` group (`status`, `update`, `set-url`, `set-branch`, `link`,
`unlink`). Run `ebuild --help` for the full list.


`ebuild test` reports the counts the underlying runner printed, and reports none
when it printed nothing recognisable — a number inferred from a zero exit status
is a guess presented as a measurement.

It also treats a run that executed **no tests** as a failure. `ctest` exits `0`
when it finds nothing to run, and a `CMakeLists.txt` with `enable_testing()` and
no `add_test()` still produces a `CTestTestfile.cmake` — so the runner is found,
ctest prints `No tests were found!!!`, and trusting the exit status would report
a green suite for a project with no tests at all.

## Test

```bash
pip install -e ".[dev]"
pytest                  # configuration in pytest.ini
```

## Documentation

Docs live under `docs/` and are published with MkDocs (`mkdocs.yml`):
<https://embeddedos-org.github.io/ebuild/>.

## License

MIT — see [LICENSE](LICENSE).

Part of [embeddedos-org](https://github.com/embeddedos-org).
