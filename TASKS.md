<!-- generated: eos-ai-scaffold -->
# Tasks

Working ledger for `ebuild`. The planner writes entries; each owning role
updates its own row. Roles are in [AGENTS.md](./AGENTS.md), the workflow in
[ORCHESTRATION.md](./ORCHESTRATION.md), the gate in [VERIFY.md](./VERIFY.md).

Status is one of: `todo`, `in-progress`, `blocked`, `review`, `done`.

## Active

| ID | Task | Owner | Mode | Status | Depends on |
|----|------|-------|------|--------|------------|
| T-002 | Fix Windows Ninja test-target path parsing | backend | Maintenance | review | none |

## Completed

| ID | Task | Owner | Verified by | Evidence |
|----|------|-------|-------------|----------|
| T-001 | Make initramfs creation portable and self-contained | backend | independent reviewer | Focused archive tests: **5 passed, 1 skipped** (symlink creation unavailable on this Windows host). Independent `bsdtar` extraction validated hard-link identity and payload. Full Python suite: **288 passed, 2 skipped, 1 unrelated failure** in the pre-existing Windows Ninja path assertion, recorded as T-002. QEMU boot was not run on Windows. |
| T-003 | `ebuild package` looks for the unsuffixed binary on Windows (`_build/app` rather than `_build/app.exe`) | backend | self (see PR #110 review, finding 2) | Was deferred out of T-002 for reviewability, then folded back in once `executable_output_path()` existed: `ebuild/cli/commands.py` now calls it at the `package` artifact lookup instead of `Path(build_dir) / name`. Covered by `tests/unit/test_package_efw.py::TestCommandPacks::test_it_finds_the_windows_suffixed_artifact`, which forces `_exe_suffix()` to `.exe` so it exercises the Windows path on any host, and also caught the fix's ripple effect on the suite's own real-Windows host: existing `test_package_efw.py` fixtures wrote an unsuffixed stand-in binary, which the fixed lookup could no longer find natively (`_exe_suffix()` returns `.exe` there unforced), so those fixtures now build the artifact through `executable_output_path()` too. Full suite run on this Windows host: **559 passed, 6 skipped, 0 failed**. |
| T-004 | `_report_footprint` (the flash/RAM report `ebuild build` prints) looks for the unsuffixed binary on Windows, and fails silently rather than logging why | backend | self (see PR #110 review, finding 1) | Third of three `build_dir / name` call sites, and the only one with no diagnostic on the early-return path. `ebuild/cli/commands.py:516` now uses `executable_output_path()`, and the bare `return` on a missing artifact now logs at debug level, matching the function's other two early exits. Covered by `tests/unit/test_footprint.py::TestCLIFootprintReport::test_looks_up_the_windows_suffixed_artifact`, which forces `_exe_suffix()` to `.exe`; confirmed to fail against the pre-fix lookup (no report emitted) and pass against the fix. Full suite on this Windows host: **560 passed, 6 skipped, 0 failed**. |

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
