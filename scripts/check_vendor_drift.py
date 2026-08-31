#!/usr/bin/env python3
"""Compare the vendored snapshots under core/ against their pinned upstreams.

core/eos/ and core/eboot/ are snapshots of other repositories in this
organisation, not original source. Fixes merged upstream do not reach them, so
they drift silently: a security fix landed in eos is simply absent here, and
nothing reports it.

ADR-019 in the eos repository records the decision to replace the snapshots with
real pinned dependencies. Until that lands, this check makes the drift visible.

Existing drift is grandfathered via ``baseline_drift`` in core/UPSTREAM.yaml so
the guard can be merged without blocking work already in flight. *New* drift
fails the build.

Usage:
    scripts/check_vendor_drift.py            # check, exit 1 on new drift
    scripts/check_vendor_drift.py --list     # also list every drifted file
"""

from __future__ import annotations

import argparse
import filecmp
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PIN_FILE = REPO_ROOT / "core" / "UPSTREAM.yaml"


class Pin:
    def __init__(self, path: str, repository: str, revision: str, baseline: int) -> None:
        self.path = path
        self.repository = repository
        self.revision = revision
        self.baseline = baseline


def read_pins(pin_file: Path) -> list[Pin]:
    """Parse core/UPSTREAM.yaml without requiring PyYAML.

    The file is a fixed shape — a list of entries with four scalar fields — so a
    line scan is enough and keeps this script dependency-free for CI.
    """
    if not pin_file.is_file():
        raise SystemExit(f"error: {pin_file} not found")

    text = pin_file.read_text(encoding="utf-8")
    fields = {
        "path": re.findall(r"^\s*- path:\s*(\S+)", text, re.M),
        "repository": re.findall(r"^\s*repository:\s*(\S+)", text, re.M),
        "revision": re.findall(r"^\s*revision:\s*(\S+)", text, re.M),
        "baseline_drift": re.findall(r"^\s*baseline_drift:\s*(\d+)", text, re.M),
    }
    counts = {k: len(v) for k, v in fields.items()}
    if len(set(counts.values())) != 1 or counts["path"] == 0:
        raise SystemExit(
            f"error: {pin_file} is malformed — every entry needs path, repository, "
            f"revision and baseline_drift (found {counts})"
        )

    return [
        Pin(p, r, rev, int(b))
        for p, r, rev, b in zip(
            fields["path"], fields["repository"], fields["revision"], fields["baseline_drift"]
        )
    ]


def fetch_upstream(repository: str, revision: str, dest: Path) -> None:
    """Check out one upstream revision into dest."""
    run = lambda *a: subprocess.run(a, cwd=dest, check=True, capture_output=True)
    subprocess.run(["git", "init", "-q", str(dest)], check=True, capture_output=True)
    run("git", "remote", "add", "origin", repository)
    try:
        run("git", "fetch", "-q", "--depth", "1", "origin", revision)
    except subprocess.CalledProcessError:
        # Some servers refuse single-commit fetches; fall back to full history.
        run("git", "fetch", "-q", "origin")
    run("git", "checkout", "-q", revision)


def compare(local_root: Path, upstream_root: Path) -> tuple[list[str], int, int]:
    """Return (drifted paths, files only here, files only upstream)."""
    drifted: list[str] = []
    only_here = 0

    for local_file in sorted(local_root.rglob("*")):
        if not local_file.is_file() or ".git" in local_file.parts:
            continue
        rel = local_file.relative_to(local_root).as_posix()
        upstream_file = upstream_root / rel
        if not upstream_file.is_file():
            only_here += 1
        elif not filecmp.cmp(local_file, upstream_file, shallow=False):
            drifted.append(rel)

    only_upstream = 0
    for upstream_file in upstream_root.rglob("*"):
        if not upstream_file.is_file() or ".git" in upstream_file.parts:
            continue
        rel = upstream_file.relative_to(upstream_root).as_posix()
        if not (local_root / rel).is_file():
            only_upstream += 1

    return drifted, only_here, only_upstream


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="list every drifted file")
    args = parser.parse_args()

    failed = False

    for pin in read_pins(PIN_FILE):
        local_root = REPO_ROOT / pin.path
        print(f"── {pin.path}  ←  {pin.repository} @ {pin.revision[:12]}")

        if not local_root.is_dir():
            print(f"   error: {pin.path} does not exist")
            failed = True
            continue

        with tempfile.TemporaryDirectory() as tmp:
            upstream_root = Path(tmp) / "upstream"
            upstream_root.mkdir()
            try:
                fetch_upstream(pin.repository, pin.revision, upstream_root)
            except subprocess.CalledProcessError as exc:
                stderr = (exc.stderr or b"").decode(errors="replace").strip()
                print(f"   error: could not fetch {pin.revision[:12]}: {stderr}")
                failed = True
                continue

            drifted, only_here, only_upstream = compare(local_root, upstream_root)

        if args.list:
            for rel in drifted:
                print(f"   drifted: {rel}")

        print(
            f"   drifted={len(drifted)}  baseline={pin.baseline}  "
            f"only-here={only_here}  only-upstream={only_upstream}"
        )

        if len(drifted) > pin.baseline:
            print(f"   FAIL: drift grew from {pin.baseline} to {len(drifted)}.")
            print(f"         Send the change upstream to {pin.repository}, or revert it here.")
            print("         Do not raise baseline_drift to make this pass.")
            failed = True
        elif len(drifted) < pin.baseline:
            print(
                f"   Drift reduced to {len(drifted)}. Lower baseline_drift in "
                "core/UPSTREAM.yaml to lock the gain in."
            )
        else:
            print("   OK: no new drift.")
        print()

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
