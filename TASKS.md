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
| T-003 | `ebuild package` looks for the unsuffixed binary on Windows (`_build/app` rather than `_build/app.exe`) | backend | Maintenance | review | none |
| T-004 | `_report_footprint` (the flash/RAM report `ebuild build` prints) looks for the unsuffixed binary on Windows, and fails silently rather than logging why | backend | Maintenance | review | none |
| T-005 | Move `executable_output_path()` out of the Ninja-specific backend into a backend-neutral module (`ebuild/build/layout.py`), re-exported from `ninja_backend` for compatibility | backend | Maintenance | todo | none |
| T-006 | Make optional LLM analysis honest: probe configured Ollama URL, join OpenAI `/v1` once, reject non-HTTP(S), do not report `--llm` success on a failed call | backend | Maintenance | review | none |
| T-007 | Flash/RAM size regex requires `[mk]b` immediately before `flash`/`ram`, so `"2MB SPI flash"` yields `flash_size=0` and `generate_boot_yaml` silently defaults to 1 MB | backend | Maintenance | todo | none |
| T-008 | `IndexSyncManager.sync` calls `PackageRecipe.to_dict()`, which does not exist; `tests/unit/test_index_sync.py` currently fails 9 tests on that AttributeError. Unrelated to T-006. | backend | Maintenance | todo | none |

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
- **T-006**: `LLMClient.is_available()` probes `self.base_url` rather than
  hardcoded localhost; `_openai_chat_url()` joins `/v1` once; non-HTTP(S)
  schemes never reach `urlopen`; a failed `analyze_with_llm` appends
  `llm_failed:<provider>` and `ebuild analyze --llm` warns instead of
  printing success. Covered by `tests/ebuild/test_llm_integration.py`
  (**33 passed**). The `/v1` join test was confirmed to fail against the
  pre-fix `f"{base}/v1/chat/completions"` (3 parametrized cases produced
  `/v1/v1/chat/completions`) and pass against the fix. `llm_integration.py`
  coverage **99.46%** on that file. Full `tests/ebuild` + `tests/unit`:
  **699 passed, 3 skipped, 9 failed** — the 9 are pre-existing
  `PackageRecipe.to_dict` errors in `index_sync.py`, recorded as T-008.


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
