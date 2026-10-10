# `ebuild test`

Run the project's test suite as part of the ebuild golden path (step six;
refs [#83](https://github.com/embeddedos-org/ebuild/issues/83)).
`ebuild monitor` is still missing — this command is the first half of
that issue.

## What it does

1. If the project has a `build.yaml` with native `test` targets, those are
   built and run first (scaffolded projects with no external test setup).
2. Otherwise `ebuild test` drives the project's own runner — auto-detected
   from the project layout, in this order:
   1. **ctest** — if `<build-dir>/CTestTestfile.cmake` exists (a configured
      CMake/CTest tree is the strongest signal)
   2. **pytest** — if a `tests/` or `test/` directory exists, or a pytest
      config marker (`pytest.ini`, `pyproject.toml`, `setup.cfg`, `tox.ini`)
   3. **cargo test** — if `Cargo.toml` exists
   4. **meson test** — if `<build-dir>/meson-info/` exists
   5. **make test** — if a Makefile declares a `test:` target

No `build.yaml` is required: in a plain project directory the command
falls back to layout detection, so `ebuild test` works anywhere.

With nothing detected the command exits `1` fail-closed rather than
pretending to test. A runner that exits 0 having run zero tests is also
treated as a failure — a pass must mean something ran.

## Usage

```sh
ebuild test                          # auto-detect and run
ebuild test --runner ctest            # choose explicitly
ebuild test --build-dir build/host    # non-default CMake build dir
ebuild test --filter net              # only tests matching "net"
ebuild test -- -k network -x          # args after -- go to the runner
ebuild test --runner ctest -- --output-on-failure
```

## Exit codes

The runner's exit code is propagated unchanged; a non-zero run prints an
error and exits with the same code. Detection failure exits `1`.
