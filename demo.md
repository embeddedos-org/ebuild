# Quick Demo

A 5-minute, self-contained walkthrough that builds and runs a tiny "thermostat"-style
C program end-to-end via `ebuild build`.

## Prerequisites

- Python 3.8+
- A system C compiler (`gcc` or `clang`)
- A `ninja` binary on PATH, or the `ninja` pip package as fallback —
  `ebuild` prefers the binary and uses `python -m ninja` only if none is present.

## 1. Set up a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 2. Install ebuild

```bash
pip install -e '.[dev]'   # falls back to: pip install -e .
```

If this fails with an error like:

```
ERROR: File "setup.py" or "setup.cfg" not found. Directory cannot be installed
in editable mode: ...
(A "pyproject.toml" file was found, but editable mode currently requires a
setuptools-based build.)
```

your virtualenv's `pip` is too old to support `pyproject.toml`-only editable
installs (PEP 660). Upgrade it first, then retry:

```bash
python3 -m pip install --upgrade pip
pip install -e '.[dev]'
```

## 3. Run the test suite (optional, but confirms your install is healthy)

```bash
pytest
```

You should see all tests pass.

## 4. Build and run the example

```bash
cd examples/hello_world
cat build.yaml   # see how the project is described
ebuild build
```

Expected output ends with:

```
[info] Auto-detected backend: ninja
   Resolving dependency graph...
   Resolving toolchain...
   Generating build.ninja in _build/...
[ok] Generated _build/build.ninja
[ok] Generated _build/compile_commands.json
   Invoking ninja...
[ok] Build completed successfully.
```

Run the built binary:

```bash
./_build/hello
```

```
Hello from EoS Build System!
```

## Troubleshooting

### No-root / PEP 668 environments

Using a virtualenv (step 1) avoids Python's PEP 668 "externally managed
environment" errors entirely, since you're not installing into the system
Python. If you still hit editable-install errors inside the venv, see the
pip-upgrade note in step 2 above — that resolves the case actually
encountered while writing this guide.

### Building without a system compiler

**Not yet verified.** This guide's build step was tested with a system `gcc`
available. Behavior when no system compiler is present (e.g. cross-compile-only
environments) has not been confirmed and needs a maintainer with the
appropriate toolchain setup to document. If you hit this, please open an issue
with the exact error output.
