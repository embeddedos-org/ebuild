<!-- generated: eos-ai-scaffold -->
# Memory

Durable context for `ebuild` — decisions and constraints that outlive one
session and are not recoverable from the code or the git history.

Write here when a future reader would otherwise repeat an argument that was
already settled, or repeat a mistake that was already made.

## What belongs here

- Decisions and the reason behind them, especially the options rejected.
- Constraints that are not visible in the code — a deadline, a compatibility
  promise, a hardware limitation, an external dependency's behaviour.
- Traps: things that look wrong but are deliberate, and things that look safe
  but break.

## What does not

- Anything derivable by reading the code.
- Anything in the git log.
- Task status — that is [TASKS.md](./TASKS.md).
- Standards — those are [QUALITY.md](./QUALITY.md),
  [TESTING.md](./TESTING.md) and [SECURITY-STANDARDS.md](./SECURITY-STANDARDS.md).

## Decisions

Format: what was chosen, why, and what was rejected. The rejected option is the
valuable half — without it the decision gets re-argued every time someone new
notices the obvious-looking alternative.

| Date | Decision | Reason | Rejected alternative |
|------|----------|--------|----------------------|
| 2026-09-13 | LLM endpoints accept `http` and `https`; package-index fetch stays HTTPS-only | Ollama's default listener is `http://localhost:11434`. Requiring HTTPS would break the documented local path. `file://` and other urllib schemes are rejected. | Reuse the index-sync `https://` allowlist for LLM URLs — rejected because it would disable stock Ollama. |

<!-- Example of the level of detail worth recording:
| 2026-03-14 | Queue writes in-process rather than via Redis | Deploy target has no
network sidecar; measured throughput was sufficient at 4x expected peak |
Redis Streams — rejected on operational cost, not on capability. Revisit if
peak exceeds 8x. |
-->

## Constraints

| Constraint | Source | Consequence if broken |
|------------|--------|-----------------------|
| —          | —      | —                     |

## Traps

Things that look wrong but are deliberate, and things that look safe but break.
Add an entry the first time something here costs someone an hour — that is the
threshold, and it is deliberately low.

None recorded yet.

---

Rules for this file:

- Absolute dates. Never "last week" or "recently".
- One entry per fact. A paragraph covering three decisions gets skimmed.
- Delete an entry when it becomes false. A stale note is worse than a missing
  one, because it is trusted.
- If an entry is derivable from the code or the git log, it does not belong
  here.
