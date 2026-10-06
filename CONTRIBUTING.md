# Contributing to EoS

## Requirements

1. **DCO Sign-off**: Every commit must carry a `Signed-off-by` line (use `git commit -s`).
   This is the Developer Certificate of Origin: it certifies you have the right to submit the code under the MIT license.
2. **License Headers**: Every new source file must have an SPDX header.
3. **Tests**: New behavior requires a test. CI runs `python -m pytest tests/`; there is no coverage threshold yet (`--cov-fail-under=0` in `.github/workflows/ci.yml`), so reviewers enforce this.
4. **Conventional Commits**: Commit messages must follow the `<type>(<scope>): <message>` format.

## Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
   (**Keep it up to date** to prevent "evil merges" (accidentally dropping other people's code during conflict resolution))
3. (Optional) Configure the commit template: `git config commit.template .gitmessage`
4. Write code with SPDX headers on all new files
5. Add tests for new functionality
6. Run what CI runs: `ruff check .` and `python -m pytest tests/`; for the C/CMake side, `cmake -B build -DEOS_BUILD_TESTS=ON && cmake --build build && cd build && ctest`
7. Commit with DCO sign-off: `git commit -s`
8. Push and create Pull Request

**Windows contributors:** `.gitattributes` pins `*.yml` and `*.yaml` to LF so
yamllint sees the same bytes on every platform. The attribute governs future
checkouts, not files already sitting in a working tree, and `git add
--renormalize .` rewrites only the index, never the files. After pulling that
change, from a clean tree run `git rm --cached -r . && git reset --hard HEAD`
once (or re-clone) so the YAML files are checked out again as LF; otherwise
yamllint will still see CRLF locally.

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