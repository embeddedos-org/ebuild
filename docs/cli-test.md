# `ebuild test`

Run the project's test suite as part of the ebuild golden path
(refs [#83](https://github.com/embeddedos-org/ebuild/issues/83)).
`ebuild monitor` is still missing — this command is the first half of
that issue.

## Runner auto-detection

`ebuild test` detects the runner from the project layout, in this order:

1. **ctest** — if `<build-dir>/CTestTestfile.cmake` exists (a configured
   CMake/CTest tree is the strongest signal)
2. **pytest** — if a pytest config marker exists (`pytest.ini`,
   `pyproject.toml`, `setup.cfg`, `tox.ini`) or a `tests/` / `test/`
   directory exists

With nothing detected the command exits `2` fail-closed rather than
pretending to test.

## Usage

```sh
ebuild test                          # auto-detect and run
ebuild test --runner ctest            # choose explicitly
ebuild test --build-dir build/host    # non-default CMake build dir
ebuild test -- -k network -x          # args after -- go to the runner
ebuild test --runner ctest -- --output-on-failure
```

## Exit codes

The runner's exit code is propagated unchanged; a non-zero run prints an
error and exits with the same code. Detection failure exits `2`.
