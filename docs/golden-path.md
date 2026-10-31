# The golden path: from "I want to build a device" to a first run

This page documents the path as it actually exists in ebuild today —
not the path as the product story describes it. Where the two differ,
the difference is stated, not smoothed over. Times are measured, not
asserted: see "Measured, 2026-10-31" below, and run
`tools/golden-path-time.py` to re-measure on your machine.

The plan's golden path is: one `ebuild` install → one scaffold →
EoSim target by default → blinking in under 15 minutes → the same
project recompiled to a real board profile, unchanged. The honest
status of that path today is: **the first three legs exist as ebuild
commands, but the simulation leg runs on a QEMU stand-in, not on
EoSim, and the scaffolded app is not a blink.** Read the divergences
section before quoting any time.

## The chain, leg by leg

### 1. Install ebuild

```bash
pip install -e .        # from the repo root
# or:
./install.sh            # puts the 'ebuild' command on your PATH
```

Requires Python 3.8+ (README), a system C compiler (`gcc` or `clang`)
and a `ninja` binary on PATH (or the `ninja` pip package as fallback).
Version at the time of writing: ebuild 3.0.1.

### 2. Scaffold: `ebuild init`

```bash
ebuild init my-blink --template rtos --target stm32f4
cd my-blink
```

`init` is `new` under the getting-started guide's spelling
(`ebuild/cli/golden_path.py`, registered in `ebuild/cli/__init__.py`).
Guide template names map to `ebuild new` templates: `rtos` →
`rtos-app`, `bare-metal` → `bare-metal`, `ble-sensor` →
`ble-sensor`, `linux` → `linux-app`, `secure-boot` →
`secure-boot`, `safety-critical` → `safety-critical`. The scaffold
contains `README.md`, `build.yaml`, `eos.yaml` (`board: stm32f4`,
`target: arm-none-eabi`), `src/main.c`, and `tests/test_main.c`.
On success `init` prints the next step itself:
`then: cd my-blink && ebuild sim`.

**What the scaffold is not:** the `rtos-app` template's `main.c` is
a producer/consumer RTOS demo (mutex + message queue, the consumer
prints `[consumer] id=… value=…` lines). It is not an LED blink.
"my-blink" is the guide's project name, not a description of what
the code does. A true blink template is follow-on work (see below).

### 3. Host build (the documented hello-world)

```bash
cd examples/hello_world && ebuild build
```

`demo.md` walks a tiny thermostat-style C program end to end via
`ebuild build`; `examples/hello_world` builds a host binary
(`./_build/hello`). This leg proves the build backend works. It is
a host binary, not firmware, and not a blink.

### 4. Simulate: `ebuild sim` (QEMU stand-in, not EoSim)

```bash
cd my-blink && ebuild sim
```

Prerequisites, all three required: an eos checkout (`ebuild setup`,
or `EBUILD_EOS_PATH` pointing at one), `arm-none-eabi-gcc`, and
`qemu-system-arm`. `sim` compiles eos plus the project's first
executable target for a QEMU machine and runs it there. Arm
Cortex-M boards (`stm32f4`, `stm32h7`, `stm32l4`, `nrf52`,
`nrf52840`, `rp2040`, `raspi-pico`) run on QEMU's Cortex-M3 machine
(`lm3s6965evb`) as a **stand-in, not a model of the board**: it
proves kernel and application logic, not the board's peripherals
or timing. `sim` returns success only if the guest produced output
(or `--expect <regex>` matched); an image that prints nothing has
not been shown to run. Missing prerequisites fail with a clean,
actionable error (e.g. `no eos checkout found. Run ebuild setup…`),
not a traceback.

### 5. Platforms: `ebuild platforms list` (the ebuild↔EoSim bridge that exists)

```bash
ebuild platforms list
```

This reads **EoSim's platform registry** (it needs the `eosim`
package installed) and marks with `*` the platforms runnable with
`ebuild sim`. That registry read is the bridge between ebuild and
EoSim that exists today. What does not exist yet is the other
direction: running a scaffolded ebuild project *on EoSim*
(`eosim run <platform>` today loads a stock platform with no user
firmware — see EoSim's `getting-started.md`).

## Divergences from the plan's golden path (stated, not hidden)

1. **EoSim target by default ≠ what `sim` does.** `sim` targets a
   QEMU Cortex-M3 stand-in. An EoSim-executed first run of a
   scaffolded project does not exist yet.
2. **"Blinking" ≠ what the scaffold does.** The scaffold prints;
   it does not toggle an LED. First guest output is the honest
   milestone for this leg, not a blink.
3. **One install ≠ the real prerequisites.** The full chain needs
   ebuild + an eos checkout + an Arm toolchain + QEMU — four
   pieces, each with its own clean failure message, but four
   pieces all the same.
4. **Python floor drift (minor).** ebuild says Python 3.8+; EoSim
   says 3.9+ (3.11/3.12 recommended). One adopter following both
   docs hits two floors.
5. **Install-URL case (checked, not a finding).** EoSim's README
   install line uses the lowercase `eosim` repo path while the
   repo is `EoSim`; GitHub resolves the name case-insensitively
   (verified: the API returns the EoSim repo for the lowercase
   name), so the line works as written.

## Measured, 2026-10-31 (sandbox run; re-measure with the script)

Environment: clean venv, ebuild installed from a fresh clone of
master (`bfd9eb4c`, version 3.0.1), system `gcc` present, no
`arm-none-eabi-gcc`, no `qemu-system-arm`, no eos checkout, no
`eosim` package.

| Leg | Result | Time |
|-----|--------|------|
| venv + pip upgrade + `pip install -e .` | OK, `ebuild --version` → 3.0.1 | ~16 s wall |
| `ebuild init my-blink --template rtos --target stm32f4` | OK, all scaffold files created, sim hint printed | <1 s |
| `ebuild build` in `examples/hello_world` | OK (Flash 1.9 KB, RAM 608 B) | <1 s |
| `ebuild platforms list` | BLOCKED — `EoSim is not installed` (clean error with the install hint) | <1 s to the error |
| `ebuild sim` in the scaffolded project | BLOCKED — `no eos checkout found. Run ebuild setup…` (clean error) | <1 s to the error |

**No under-15-minutes claim is made.** The full chain was not run
end to end in this sandbox, so Saturday's golden-path line is
**partially measured** (install, scaffold, and host build timed;
the simulation leg blocked on prerequisites). A week where the
full chain is unmeasured is reported as unmeasured — this page
does not fill that gap with an assertion.

## Follow-ons (not done here)

- **Blink template + EoSim target (the real G1).** A scaffold
  template whose app actually blinks (or a documented LED-less
  equivalent), plus an EoSim-executed run of a scaffolded project
  — the cross-repo slice that turns this page's chain into the
  plan's golden path, with a timed clean-room run.
- **Timing in CI.** `tools/golden-path-time.py` is committed for
  repeatability; wiring it into CI is a separate decision (the
  EoSim install and toolchain legs may be too heavy for the
  default CI job — measure there before promising it).
