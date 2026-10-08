# `ebuild quantize`: the MCU-class target decision

**Status:** architecture decision (2026-10-08), pre-implementation. This
document records *which* quantization formats `ebuild quantize` targets for
microcontroller-class devices. It constrains the implementation; it is not
the implementation. The fail-closed invariant is recorded separately in
[quantize-fail-closed.md](quantize-fail-closed.md) and applies to every
format below.

## Decision

| Tier | Format | Status | Rationale |
|---|---|---|---|
| Default MCU target | **int8** (LiteRT-compatible) | Planned | The portable, toolchain-supported path: CMSIS-NN / ESP-NN kernels exist, debuggers understand it, every MCU vendor's ML SDK speaks it. |
| Experimental | **BitNet-1.58 ternary** (`--format bitnet-1.58`) | Planned, experimental | 1.58-bit weights in {-1, 0, +1} eliminate FP MACs entirely. Flagged experimental until a second independent reproduction lands. |

## Evidence

The ternary tier stopped being speculative in September 2026: seven $4
ESP32-S3 chips run a **0.4B-parameter LLM in an SPI daisy-chain** ($28
total) with 1.58-bit weights — no floating-point multiply-accumulates
anywhere in the matmul path.

- https://byteiota.com/esp32-bitnet-llm-cluster/
- https://ai-beat.github.io/news/2026/09/esp32s3-bitnet-microcluster/

That demo is the existence proof the accelerator-HAL ternary tier (see
eAI's `docs/track1/accelerator-hal-ternary-tier.md`) is designed around,
and it is why `ebuild quantize` needs a ternary output format at all:
without a build step that produces BitNet-1.58 artifacts, the tier is a
doc without a pipeline.

## Proposed CLI shape

```
ebuild quantize --target esp32s3 --format {int8,bitnet-1.58} \
    --calibration <data> --output model.q
```

- `--format` defaults to `int8`.
- `--format bitnet-1.58` is accepted but prints an "experimental" notice
  and requires `--experimental` until the format graduates.
- `--calibration` is required: with no calibration data the step fails
  closed per [quantize-fail-closed.md](quantize-fail-closed.md) -- it must
  never emit a zero-weight placeholder (the eNI#40 defect class).

## Tensor-memory notes (MCU tier)

The formats imply placement, and the build step should validate it:

- **Embeddings:** flash-resident (they are read-only and large).
- **KV caches:** PSRAM where present (ESP32-S3 class); the step should
  refuse a configuration whose KV cache exceeds the target's PSRAM, rather
  than emitting a model that OOMs at runtime.
- **Scale-out:** the SPI daisy-chain pattern from the BitNet demo is the
  reference for multi-MCU inference; the format must record the partition
  map so the runtime can route shards.

## Metric

Adopt **tokens-per-watt** as the cross-format comparison metric (from the
eAI track-1 work): an int8 and a ternary build of the same model are
compared on tokens-per-watt on the target board, not just on size or
perplexity. A format that is smaller but hungrier is not a win on
battery-powered hardware.

## Cross-references

- [quantize-fail-closed.md](quantize-fail-closed.md) -- the fail-closed invariant.
- [quantize.md](quantize.md) -- the quantize step design.
- eAI `docs/track1/accelerator-hal-ternary-tier.md` -- the runtime tier this feeds.
- `eosllm/docs/quant_schemes.md` -- the inference-side scheme catalog.
