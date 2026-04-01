# Contributing to EoS

## Developer Certificate of Origin (DCO)

All contributions require a DCO sign-off. Add to your commit message:

    Signed-off-by: Your Name <your.email@example.com>

Use: git commit -s -m "your message"

This certifies you have the right to submit the code under the MIT license.

## Process

1. Fork the repository
2. Create a feature branch: git checkout -b feat/my-feature
3. Write code with SPDX headers on all new files
4. Add tests for new functionality
5. Run: cmake -B build -DEOS_BUILD_TESTS=ON && cmake --build build && cd build && ctest
6. Commit with DCO sign-off: git commit -s
7. Push and create Pull Request

## Coding Standards

### C (ISO C11)
- snake_case for functions and variables
- UPPER_CASE for macros and constants
- Doxygen comments on all public APIs
- SPDX-License-Identifier on every file
- No dynamic allocation in kernel/HAL code
- All functions return error codes (0 = success)

### Python (PEP 8)
- black formatter, flake8 linter
- Type hints on public functions
- SPDX-License-Identifier on every file

### Go
- gofmt, golangci-lint
- SPDX-License-Identifier on every file

## Commit Convention

    type(scope): description

Types: feat, fix, docs, test, build, refactor, perf, ci
Scopes: eos, eboot, eai, eni, eipc, eosuite, sdk, ebuild