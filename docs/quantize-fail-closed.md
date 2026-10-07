# `ebuild quantize`: fail-closed design invariant

**Status:** design invariant (2026-10-07), pre-implementation. This document
records a property the `ebuild quantize` step MUST have before it ships; it
constrains the implementation, it is not the implementation.

## The invariant

`ebuild quantize` MUST **fail closed** when calibration data is absent:

- Exit non-zero.
- Emit nothing — no output model file, no stub, no placeholder.
- Never write a placeholder or garbage model and call it quantized.

A quantize step that "succeeds" by writing zeros has corrupted the build
artifact silently. That failure mode must be unreachable, not merely unlikely.

## Post-step validation contract

Before the step completes, it MUST validate the quantized output (the exact
mechanism is an implementation detail; the contract is not):

1. **Hash-compare** the output against the source checkpoint, OR
2. **Accuracy smoke-test** the output on a calibration sample,

and refuse to emit the output if the check fails. In particular: if the
output weights are all-zeros or placeholder-shaped, delete the partial
output and exit non-zero — the build must fail loudly at the quantize step,
not silently at deploy time.

## Defect-class evidence

This invariant exists because the failure class is real, in this org, this
week: eNI#40 — `tools/quantize_model.py` writes a **zero-weight
placeholder**, ignores its input, and exits 0. That incident is exactly what
this invariant prevents: input is ignored → output is placeholder → build
"passes". If `ebuild quantize` ships without this invariant, it will
reproduce that bug as a feature.

## API shape (future, when implemented)

- `ebuild quantize --validate=<hash|smoke>`: select the validation contract.
- Validation is **always on by default**.
- `--no-validate` is an **error, not a flag**. There is no supported way to
  turn validation off; a user who wants to skip it is asking for a different
  tool.
