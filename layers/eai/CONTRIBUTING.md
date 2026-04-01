# Contributing to EAI

Thank you for your interest in contributing to the AI Layer!

## Getting Started

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes
4. Run the build and tests locally
5. Submit a pull request

## Development Setup

```bash
git clone https://github.com/embeddedos-org/eai.git
cd eai
cmake -B build -DEAI_BUILD_TESTS=ON
cmake --build build
ctest --test-dir build --output-on-failure
```

To build a specific profile:
```bash
cmake -B build -DEAI_PROFILE=smart-camera
cmake --build build
```

## CI Requirements

All pull requests must pass the following CI checks before merging:

### Required Status Checks

| Check | Platform | What It Validates |
|---|---|---|
| **Build (ubuntu-latest)** | Linux | GCC build with all libraries and tests |
| **Build (windows-latest)** | Windows | MSVC build — verifies cross-platform portability |
| **Build (macos-latest)** | macOS | Clang build — verifies Apple platform support |
| **Profile (smart-camera)** | Linux | Smart camera profile compiles cleanly |
| **Profile (industrial-gateway)** | Linux | Industrial gateway profile compiles cleanly |
| **Profile (robot-controller)** | Linux | Robot controller profile compiles cleanly |
| **Profile (mobile-edge)** | Linux | Mobile edge profile compiles cleanly |

### How to Verify Locally

Before submitting a PR, ensure all checks pass:

```bash
# 1. Full build with tests
cmake -B build -DEAI_BUILD_TESTS=ON
cmake --build build --config Release
ctest --test-dir build --output-on-failure -C Release

# 2. Profile builds (test at least one)
cmake -B build-camera -DEAI_PROFILE=smart-camera && cmake --build build-camera
cmake -B build-gateway -DEAI_PROFILE=industrial-gateway && cmake --build build-gateway
```

### Nightly Regression (Informational)

The nightly workflow runs additional checks not required for PRs but monitored for regressions:

- Full test suite with `EAI_BUILD_TESTS=ON` on all 3 OS platforms
- All 4 profile builds
- Cross-compilation for AArch64, ARM hard-float, and RISC-V 64

## Code Guidelines

### C Style

- **Standard:** C11 (`-std=c11`)
- **Warnings:** `-Wall -Wextra` must compile clean (zero warnings)
- **Platform guards:** All platform-specific code must be guarded:
  - `#ifdef _WIN32` for Windows-specific code
  - `#ifdef __APPLE__` for macOS-specific code
  - `#ifdef _MSC_VER` for MSVC compiler intrinsics
  - `#if defined(__GNUC__) || defined(__clang__)` for GCC/Clang builtins
- **Portability rules:**
  - No `__builtin_*` without MSVC fallback
  - No hardcoded Unix paths (`/tmp/`) — use `getenv("TEMP")` on Windows
  - Always `#include <stddef.h>` when using `size_t`
  - Always `#include <stdlib.h>` when using `getenv()`, `malloc()`, etc.
- **Include guards:** Use `#ifndef HEADER_NAME_H` / `#define` / `#endif`
- **Types:** Use `<stdint.h>` types (`uint32_t`, `int8_t`, etc.)

### Adding a Connector

When adding a new industrial connector (e.g., MQTT, OPC-UA, Modbus, CAN):

1. Create `framework/src/connector_<name>.c` implementing `eai_fw_connector_ops_t`
2. Create the corresponding header in `framework/include/eai_fw/`
3. Register in the connector manager initialization
4. Add unit tests in `tests/`

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add OPC-UA connector for industrial gateways
fix: memory_lite LRU eviction on full store
docs: add runtime integration guide
ci: add smart-camera profile to CI matrix
chore: bump version to 0.2.0
```

### Pull Request Checklist

- [ ] Code compiles with zero warnings on GCC, Clang, and MSVC
- [ ] All existing tests pass
- [ ] New features include unit tests in `tests/`
- [ ] Platform-specific code has `#ifdef` guards for all 3 OS targets
- [ ] No hardcoded filesystem paths
- [ ] Commit messages follow conventional commits format

## Reporting Issues

- Use GitHub Issues with the appropriate label (`bug`, `enhancement`, `question`)
- Include: OS, compiler version, profile, and full error output
- For build failures: attach the full CMake configure + build log

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
