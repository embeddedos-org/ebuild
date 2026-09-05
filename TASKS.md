<!-- generated: eos-ai-scaffold -->
# Tasks

Working ledger for `ebuild`. The planner writes entries; each owning role
updates its own row. Roles are in [AGENTS.md](./AGENTS.md), the workflow in
[ORCHESTRATION.md](./ORCHESTRATION.md), the gate in [VERIFY.md](./VERIFY.md).

Status is one of: `todo`, `in-progress`, `blocked`, `review`, `done`.

## Active

| ID | Task | Owner | Mode | Status | Depends on |
|----|------|-------|------|--------|------------|
| T-002 | Fix Windows Ninja test-target path parsing | backend | Maintenance | todo | none |

## Completed

| ID | Task | Owner | Verified by | Evidence |
|----|------|-------|-------------|----------|
| T-001 | Make initramfs creation portable and self-contained | backend | independent reviewer | Focused archive tests: **5 passed, 1 skipped** (symlink creation unavailable on this Windows host). Independent `bsdtar` extraction validated hard-link identity and payload. Full Python suite: **288 passed, 2 skipped, 1 unrelated failure** in the pre-existing Windows Ninja path assertion, recorded as T-002. QEMU boot was not run on Windows. |
| T-003 | Address PR #111 findings 1, 2, 3, 4, 6, 7, 8 | backend | reviewer | Unit tests in `tests/unit/test_index_sync.py` verify keep-set filename matching, `.yml` pruning, lack-of-URL recipe preservation, CLI prune reporting, and trailing newline in `CHANGELOG.md`. |

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
