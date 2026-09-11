# Development

## Contribution source of truth

[CONTRIBUTING](https://github.com/embeddedos-org/ebuild/blob/master/CONTRIBUTING.md)

Before proposing a change, also review the [README](https://github.com/embeddedos-org/ebuild/blob/master/README.md). Keep changes scoped, add tests appropriate to the affected behavior, and follow the repository's current automation and review requirements.

## Build and dependency inputs found

`CMakeLists.txt`, `Dockerfile`, `core/eboot/CMakeLists.txt`, `core/eboot/requirements.txt`, `core/eboot/tests/CMakeLists.txt`, `core/eos/CMakeLists.txt`, `core/eos/backends/CMakeLists.txt`, `core/eos/cmd/eos/CMakeLists.txt`, `core/eos/core/CMakeLists.txt`, `core/eos/debug/CMakeLists.txt`, `core/eos/drivers/devicetree/CMakeLists.txt`, `core/eos/examples/ble-sensor/CMakeLists.txt`, and 55 more.

## Tests found in the default-branch tree

`core/eboot/tests/CMakeLists.txt`, `core/eboot/tests/unit/test_board_config.c`, `core/eboot/tests/unit/test_board_registry.c`, `core/eboot/tests/unit/test_bootctl.c`, `core/eboot/tests/unit/test_crypto.c`, `core/eboot/tests/unit/test_device_table.c`, `core/eboot/tests/unit/test_multicore.c`, `core/eboot/tests/unit/test_runtime_svc.c`, `core/eos/tests/CMakeLists.txt`, `core/eos/tests/mocks/lvgl.h`, `core/eos/tests/test_config.c`, `core/eos/tests/test_crypto.c`, and 132 more.

## Documented test commands

These commands are reproduced from the inspected root README or contributing guide:

```bash
pytest                  # configuration in pytest.ini
```

## Verification baseline

This inventory comes from `master` at [`8b623d5786b5`](https://github.com/embeddedos-org/ebuild/commit/8b623d5786b5f841823f92a5506269f1e155a0f1) and found 144 test-related paths among 1210 files. Re-check the source tree when that commit is no longer current.
