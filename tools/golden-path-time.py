#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Measure the golden path, leg by leg (see docs/golden-path.md).

Runs the documented legs and prints one line per leg: status, seconds,
and detail. Legs that cannot run in the current environment are
recorded as BLOCKED with the reason — never as a fabricated time, and
never as a failure of the script itself. The script therefore always
exits 0 on a completed measurement (even with blocked legs); it exits
2 only on a usage error.

Legs:
  1. ebuild --version (install sanity)
  2. ebuild init gp-blink --template rtos --target stm32f4 (scaffold)
  3. ebuild build in <ebuild-checkout>/examples/hello_world (host build)
  4. ebuild platforms list (EoSim registry read)
  5. ebuild sim --timeout 5 in the scaffolded project (QEMU stand-in)

Usage:
  python3 tools/golden-path-time.py [--ebuild-checkout PATH] [--log FILE]

--ebuild-checkout defaults to the current directory when it looks like
an ebuild checkout (contains ebuild/cli/golden_path.py); otherwise leg 3
is recorded BLOCKED with the reason. The scaffold goes into a temporary
directory that is removed afterwards.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def run(cmd, cwd):
    """Run cmd, return (returncode, elapsed_seconds, tail_of_output)."""
    start = time.monotonic()
    proc = subprocess.run(cmd, check=False, cwd=cwd, capture_output=True, text=True)
    elapsed = time.monotonic() - start
    out = (proc.stdout + proc.stderr).strip().splitlines()
    tail = "\n".join(out[-3:]) if out else ""
    return proc.returncode, elapsed, tail


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ebuild-checkout",
        default=None,
        help="Path to an ebuild checkout (for leg 3).",
    )
    parser.add_argument(
        "--log", default=None, help="Also write the JSON summary to FILE."
    )
    args = parser.parse_args()

    checkout = Path(args.ebuild_checkout) if args.ebuild_checkout else Path.cwd()
    has_checkout = (checkout / "ebuild" / "cli" / "golden_path.py").is_file()

    rows = []
    with tempfile.TemporaryDirectory(prefix="gp-time-") as tmp:
        tmp_path = Path(tmp)
        # Leg 1: install sanity.
        rc, secs, tail = run(["ebuild", "--version"], cwd=tmp_path)
        rows.append(
            {
                "leg": "ebuild --version",
                "status": "OK" if rc == 0 else "BLOCKED",
                "seconds": round(secs, 3),
                "detail": tail,
            }
        )
        # Leg 2: scaffold.
        rc, secs, tail = run(
            ["ebuild", "init", "gp-blink", "--template", "rtos", "--target", "stm32f4"],
            cwd=tmp_path,
        )
        rows.append(
            {
                "leg": "ebuild init (rtos/stm32f4)",
                "status": "OK" if rc == 0 else "BLOCKED",
                "seconds": round(secs, 3),
                "detail": tail,
            }
        )
        # Leg 3: host build (needs a checkout).
        if has_checkout:
            rc, secs, tail = run(
                ["ebuild", "build"], cwd=checkout / "examples" / "hello_world"
            )
            rows.append(
                {
                    "leg": "ebuild build (examples/hello_world)",
                    "status": "OK" if rc == 0 else "BLOCKED",
                    "seconds": round(secs, 3),
                    "detail": tail,
                }
            )
        else:
            rows.append(
                {
                    "leg": "ebuild build (examples/hello_world)",
                    "status": "BLOCKED",
                    "seconds": 0.0,
                    "detail": "no ebuild checkout given (pass --ebuild-checkout PATH)",
                }
            )
        # Leg 4: platforms list (needs the eosim package).
        rc, secs, tail = run(["ebuild", "platforms", "list"], cwd=tmp_path)
        rows.append(
            {
                "leg": "ebuild platforms list",
                "status": "OK" if rc == 0 else "BLOCKED",
                "seconds": round(secs, 3),
                "detail": tail,
            }
        )
        # Leg 5: sim in the scaffolded project (needs eos checkout +
        # arm-none-eabi-gcc + qemu-system-arm; records its clean error
        # when a prerequisite is missing).
        proj = tmp_path / "gp-blink"
        if proj.is_dir():
            rc, secs, tail = run(["ebuild", "sim", "--timeout", "5"], cwd=proj)
            rows.append(
                {
                    "leg": "ebuild sim (scaffolded project)",
                    "status": "OK" if rc == 0 else "BLOCKED",
                    "seconds": round(secs, 3),
                    "detail": tail,
                }
            )
        else:
            rows.append(
                {
                    "leg": "ebuild sim (scaffolded project)",
                    "status": "BLOCKED",
                    "seconds": 0.0,
                    "detail": "leg 2 did not produce a project dir",
                }
            )

    total = round(sum(r["seconds"] for r in rows), 3)
    print(f"{'leg':<42} {'status':<8} {'seconds':>8}  detail")
    for r in rows:
        print(
            f"{r['leg']:<42} {r['status']:<8} {r['seconds']:>8}  "
            f"{r['detail'].splitlines()[-1] if r['detail'] else ''}"
        )
    print(
        f"\nTotal measured time (sum of legs): {total}s. "
        f"Blocked legs are NOT a time claim: the full chain is "
        f"unmeasured until every leg reports OK."
    )
    if args.log:
        Path(args.log).write_text(
            json.dumps({"legs": rows, "total_seconds": total}, indent=2) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
