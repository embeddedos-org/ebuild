<!-- generated: eos-ai-scaffold -->
# Tasks

Working ledger for `ebuild`. The planner writes entries; each owning role
updates its own row. Roles are in [AGENTS.md](./AGENTS.md), the workflow in
[ORCHESTRATION.md](./ORCHESTRATION.md), the gate in [VERIFY.md](./VERIFY.md).

Status is one of: `todo`, `in-progress`, `blocked`, `review`, `done`.

## Active

### T-119 — Preserve toolchain linker settings for shared libraries

Owner: backend / testing
Mode: Verification
Status: review
Depends on: none

Goal: shared-library link commands honor the same toolchain settings as executables.

Acceptance criteria:
- Shared-library link flags include toolchain ldflags and sysroot before target ldflags and package library paths.
- Generating multiple shared libraries does not mutate or leak flags between targets or into the toolchain.
- A real Linux shared-library build honors toolchain `-Wl,--no-undefined`: a resolved source builds successfully and an unresolved source fails to link.

Design: reuse the already-computed `_get_toolchain_ldflags()` result with list
concatenation, matching executable handling. No API or dependency changes.
Files in scope: `ebuild/build/ninja_backend.py`,
`tests/unit/test_shared_library_toolchain.py`, `CHANGELOG.md`, `TASKS.md`.
Other shared-library features and unrelated defects are out of scope.
Risk: previously ignored linker options may now correctly reject invalid builds.
Verification: new tests before/after the fix, full pytest suite, Ruff, mypy,
Python package build, and the repository's CMake/CTest check.

Handoff (planning/architecture -> implementation/testing): discovery found the
shared-library branch initializes flags from the target alone. The executable
branch already includes toolchain flags. Acceptance criteria are the three
bullets above; all checks are NOT RUN. Next: write failing regressions, then fix.

Verification results (Linux, Python 3.12):
- PASS: all three new regression cases failed against the original backend,
  then passed with the fix (`pytest tests/unit/test_shared_library_toolchain.py -q`).
- PASS: independent reviewer repeated the focused tests (3 passed), found no
  blocking issues, and confirmed all three acceptance criteria.
- PASS: Ruff on both changed Python files; mypy on `ninja_backend.py`;
  `python -m build --no-isolation` (sdist and wheel); `git diff --check`;
  `yamllint .` (no YAML changes).
- FAIL (pre-existing): full suite: `9 failed, 672 passed, 3 skipped in 51.88s`.
  All nine failures are in `tests/unit/test_index_sync.py`:
  `AttributeError: 'PackageRecipe' object has no attribute 'to_dict'`.
  Reproduced the same nine failures in a detached baseline worktree at
  `8b623d5` (9 failed, 13 passed in that module).
- FAIL (pre-existing): repository-wide mypy reports the same missing
  `PackageRecipe.to_dict` at `ebuild/packages/index_sync.py:354`.
- FAIL (pre-existing): repository-wide Ruff reports F811 in
  `tests/ebuild/test_build_dir_resolution.py`, W292 in
  `tests/ebuild/test_package_recipe.py`, and two E402 findings in
  `tests/unit/test_ci_gate.py`. These files are unchanged.
- NOT RUN: CMake/CTest; `cmake: command not found` in this environment.
- NOT RUN: real Windows/macOS linker execution and cross-compilation with an SDK.
  Portable manifest tests cover sysroot emission; the compiler regression is
  explicitly Linux/GCC-only.

Handoff (verification -> maintainer): focused change independently reviewed;
submission is for review, not a release. Remaining work: maintainer review/CI,
with the unrelated baseline failures above tracked here for separate fixes.

| ID | Task | Owner | Mode | Status | Depends on |
|----|------|-------|------|--------|------------|
| T-002 | Fix Windows Ninja test-target path parsing | backend | Maintenance | review | none |
| T-003 | `ebuild package` looks for the unsuffixed binary on Windows (`_build/app` rather than `_build/app.exe`) | backend | Maintenance | review | none |
| T-004 | `_report_footprint` (the flash/RAM report `ebuild build` prints) looks for the unsuffixed binary on Windows, and fails silently rather than logging why | backend | Maintenance | review | none |
| T-005 | Move `executable_output_path()` out of the Ninja-specific backend into a backend-neutral module (`ebuild/build/layout.py`), re-exported from `ninja_backend` for compatibility | backend | Maintenance | todo | none |

### Evidence (self-reported by implementer; pending independent review per `.ai/reviewer.md` — "if you implemented it, you do not approve it")

- **T-002**: `ebuild/cli/commands.py:2624` and `:2633` (the Ninja target-list
  argv and the binary that gets executed in `_run_native_tests`) both use
  `executable_output_path()` instead of rebuilding the path themselves.
  Covered by
  `tests/unit/test_golden_path_commands.py::TestTestTargetType::test_native_runner_asks_ninja_for_the_linked_binary`,
  which forces `_exe_suffix()` to `.exe`; confirmed to fail against the
  pre-fix argv construction and pass against the fix.
- **T-003**: Was deferred out of T-002 for reviewability, then folded back in
  once `executable_output_path()` existed: `ebuild/cli/commands.py` now calls
  it at the `package` artifact lookup instead of `Path(build_dir) / name`.
  Covered by
  `tests/unit/test_package_efw.py::TestCommandPacks::test_it_finds_the_windows_suffixed_artifact`,
  which forces `_exe_suffix()` to `.exe` so it exercises the Windows path on
  any host, and also caught the fix's ripple effect on the suite's own
  real-Windows host: existing `test_package_efw.py` fixtures wrote an
  unsuffixed stand-in binary, which the fixed lookup could no longer find
  natively (`_exe_suffix()` returns `.exe` there unforced), so those
  fixtures now build the artifact through `executable_output_path()` too.
- **T-004**: Third of three `build_dir / name` call sites, and the only one
  with no diagnostic on the early-return path. `ebuild/cli/commands.py:516`
  now uses `executable_output_path()`, and the bare `return` on a missing
  artifact now logs at debug level, matching the function's other two early
  exits. Covered by
  `tests/unit/test_footprint.py::TestCLIFootprintReport::test_looks_up_the_windows_suffixed_artifact`,
  which forces `_exe_suffix()` to `.exe` and chdirs into `tmp_path` so the
  process cwd's own `eos.yaml`/`board.yaml`, if any, cannot change what it
  measures; confirmed to fail against the pre-fix lookup (no report
  emitted) and pass against the fix.
- **Suite result** (single run, both changes present, this Windows host):
  **560 passed, 6 skipped, exit code 0**. Supersedes any other count quoted
  for T-003 or T-004 elsewhere in this repo or in PR #110's description.

## Completed

| ID | Task | Owner | Verified by | Evidence |
|----|------|-------|-------------|----------|
| T-001 | Make initramfs creation portable and self-contained | backend | independent reviewer | Focused archive tests: **5 passed, 1 skipped** (symlink creation unavailable on this Windows host). Independent `bsdtar` extraction validated hard-link identity and payload. Full Python suite: **288 passed, 2 skipped, 1 unrelated failure** in the pre-existing Windows Ninja path assertion, recorded as T-002. QEMU boot was not run on Windows. |
| T-003 | Address PR #111 review findings 1, 2, 3, 6, 7, 8 | backend | reviewer | Unit tests in `tests/unit/test_index_sync.py` (22 passed) verify keep-set filename matching, empty index floor and fallback status, .yml preservation and pruning, lack-of-URL recipe preservation, CLI prune reporting, and trailing newline in `CHANGELOG.md`. Static analysis with `ruff` on all PR-touched files reports 0 errors; `mypy` on modified packages reports 0 errors without suppressions. Full test suite passes 605 tests on Linux. |

---

## Task template

```markdown
### T-000 — <short title>

Owner: <role>
Mode: <see MODES.md>
Status: todo
Depends on: <task ids, or none>

Goal
: <one sentence: what is true afterwards that is not true now>

Acceptance criteria
: - <observable, checkable statement>
  - <observable, checkable statement>

Files in scope
: <paths the owner is expected to touch>

Out of scope
: <what this task deliberately does not change>

Risks
: <what could break, and what would reveal it>

Verification
: | Check | Command | Result |
  |-------|---------|--------|
  | <name> | `<command>` | `NOT RUN` |
```

## Verification commands for this repository

These commands were derived from the manifests at the repository root. Confirm one works before relying on it; a listed script may still be a stub.

| Check | Command | Default state |
|-------|---------|---------------|
| Unit tests | `pytest` | `NOT RUN` |
| Build | `cmake --build build -j` | `NOT RUN` |

## Rules

- One task per unit of work that can be verified on its own.
- Acceptance criteria are written before work starts and are not edited to match
  what was built. If they were wrong, say so and rewrite them explicitly.
- A task reaches `done` only when the definition of done in
  [ORCHESTRATION.md](./ORCHESTRATION.md) is met and the verification commands
  were actually run.
- `blocked` requires a note naming what it is blocked on and who can unblock it.
