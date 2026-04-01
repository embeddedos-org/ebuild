# Contributing to ENI

Thank you for your interest in contributing to the Neural Interface Adapter!

## Getting Started

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes
4. Run the build and tests locally
5. Submit a pull request

## Prerequisites

- **CMake** ≥ 3.16
- **GCC** ≥ 11, **Clang** ≥ 14, or **MSVC** ≥ 2022
- **Git** for version control
- **Doxygen** (optional, for API docs)

## Development Setup

```bash
git clone https://github.com/embeddedos-org/eni.git
cd eni
cmake -B build -DENI_BUILD_TESTS=ON
cmake --build build
ctest --test-dir build --output-on-failure
```

To build a specific profile:
```bash
cmake -B build -DENI_PROFILE=assistive-device
cmake --build build
```

## How to Verify Locally

Before submitting a PR, ensure all checks pass:

```bash
# 1. Full build with tests
cmake -B build -DENI_BUILD_TESTS=ON
cmake --build build --config Release
ctest --test-dir build --output-on-failure -C Release

# 2. Profile builds (test at least one)
cmake -B build-assistive -DENI_PROFILE=assistive-device && cmake --build build-assistive
cmake -B build-industrial -DENI_PROFILE=industrial-gateway && cmake --build build-industrial
```

## Adding a Provider

When adding a new input provider (e.g., BCI SDK, sensor adapter):

1. Create `providers/src/provider_<name>.c` implementing `eni_provider_ops_t`
2. Create the corresponding header in `providers/include/eni_providers/`
3. Register in the provider manager initialization
4. Add unit tests in `tests/`
5. Document the provider in `docs/`

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

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add EEG simulator provider
fix: trim_whitespace off-by-one in config parser
docs: add provider integration guide
ci: add assistive-device profile to CI matrix
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
