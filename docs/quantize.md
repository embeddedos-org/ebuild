# `ebuild quantize` — model quantization for on-device targets

Track 1 (tightly-coupled AI) build-pipeline entry point: quantize and convert
a model for an accelerator backend, with an optional bit-exactness check.
The CLI contract below is stable; backend kernels land incrementally.

## CLI contract

```
ebuild quantize --model <path.onnx|tflite> --format int8|int16
                --calibration <data/dir> --target cmsis-nn|esp-nn|aie
                [--validate] [-o <output>]
```

| Flag | Meaning |
|---|---|
| `--model` | `.onnx` or `.tflite` file (must exist). |
| `--format` | `int8` (default) or `int16`. |
| `--calibration` | Calibration data file or directory (must exist). |
| `--target` | Backend: `cmsis-nn` / `esp-nn` (tiny HAL tier) or `aie` (large tier). |
| `--validate` | Run the bit-exactness harness after conversion. |
| `-o/--output` | Output path; default `<stem>.quantized.<fmt><ext>`. |

## Targets

- `cmsis-nn`, `esp-nn` — tiny-tier backends (int8 kernels, arena SRAM; see
  `docs/track1/accelerator-hal-profiles.md` in `embeddedos-org/eos`).
- `aie` — large-tier (Versal AIE class). Accepted by the CLI but not
  implemented yet; the command points at the HAL design doc and exits 2.

## Calibration data

A directory of representative input samples (raw tensors, one file per
sample) or a single manifest file listing them. The format is intentionally
loose in the skeleton: backends define the exact sample layout when they
land. What is fixed now: the path must exist, and `--validate` compares the
quantized model's outputs against the float model's on this data.

## Honesty contract

Backend kernels are not implemented yet. Until they are, the command
validates arguments, prints the quantization plan, and exits 2 — it never
writes a fake artifact and never silently no-ops. `--validate` without a
backend exits 2 with the harness hook noted.

## Registry (planned)

Quantized artifacts will be registered next to the package registry with
their content hash, target, format, and calibration-data hash, so a build
can pin `model@sha256:…` the way it pins packages. Not implemented yet.

## See also

- `embeddedos-org/eos` `docs/track1/accelerator-hal-profiles.md` — tiered
  profiles and the `eos_accel_backend_t` interface this feeds.
- `eAI` `docs/track1/runtime-api.md` — the inference-service API that
  consumes quantized models on device.
