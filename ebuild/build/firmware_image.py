# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Assemble an eFirmware `.efw` image from a built artifact.

§29's development-to-device flow ends:

    eBuild -> {EoS, eBoot, application} -> eFirmware artifact -> {EoSim, hardware}

Every piece of that existed except the arrow into eFirmware. The
`embeddedos-org/eFirmware` repository implements the image format and ships
`efwtool` to pack, inspect and verify one; nothing in ebuild referenced it, so
a developer had to know the tool existed, build it themselves, and run it by
hand.

This drives `efwtool` rather than re-implementing the header in Python. The
header is a packed C struct with a magic, a version, a size and a SHA-256, and
a second implementation of it in another language is a second thing to keep in
step — the exact failure this repository has been repairing all week. If the
format changes, the tool changes with it and this keeps working.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

#: Where `ebuild setup` caches the sibling repositories.
_EFW_REPO = "efirmware"

#: Built once and reused, inside the clone, so `ebuild setup` stays the only
#: thing that owns ~/.ebuild/repos.
_BUILD_DIRNAME = "_ebuild"


class FirmwareImageError(RuntimeError):
    """Raised when an image cannot be assembled."""


def find_efwtool(repos_dir: Path) -> Optional[Path]:
    """Locate `efwtool`, building the cached eFirmware checkout if needed.

    Returns None when the checkout is absent or cannot be built, so the caller
    can say what to run rather than failing with a stack trace.
    """
    on_path = shutil.which("efwtool")
    if on_path:
        return Path(on_path)

    root = Path(repos_dir) / _EFW_REPO
    if not (root / "CMakeLists.txt").is_file():
        return None

    build_dir = root / _BUILD_DIRNAME
    existing = _first_efwtool(build_dir)
    if existing:
        return existing

    if shutil.which("cmake") is None:
        return None
    try:
        subprocess.run(["cmake", "-S", str(root), "-B", str(build_dir)],
                       check=True, capture_output=True, timeout=600)
        subprocess.run(["cmake", "--build", str(build_dir), "-j",
                        str(os.cpu_count() or 1)],
                       check=True, capture_output=True, timeout=1800)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return None
    return _first_efwtool(build_dir)


def _first_efwtool(build_dir: Path) -> Optional[Path]:
    if not build_dir.is_dir():
        return None
    # Windows toolchains link the tool as efwtool.exe.
    for name in ("efwtool", "efwtool.exe"):
        for candidate in sorted(build_dir.rglob(name)):
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return candidate
    return None


def pack(efwtool: Path, payload: Path, output: Path, *,
         version: str = "0.0.0",
         load_addr: Optional[str] = None,
         entry_addr: Optional[str] = None) -> None:
    """Wrap ``payload`` in an eFirmware header, writing ``output``."""
    if not payload.is_file():
        raise FirmwareImageError(f"no artifact to package at {payload}")

    argv: List[str] = [str(efwtool), "pack", str(payload), str(output),
                       "--version", version]
    if load_addr:
        argv += ["--load", load_addr]
    if entry_addr:
        argv += ["--entry", entry_addr]

    proc = _run(argv, f"packing {payload.name}")
    if not output.is_file():
        raise FirmwareImageError(
            f"efwtool reported success but wrote no image at {output}: "
            f"{proc.stdout.strip()[:200]}"
        )


def verify(efwtool: Path, image: Path) -> str:
    """Re-read the image through efwtool. Returns its verdict line.

    Packing and verifying with the same tool does not prove the format is
    right, but it does prove the file on disk parses — which catches a
    truncated write, a wrong path, and a payload that never got copied.
    """
    return _run([str(efwtool), "verify", str(image)],
                f"verifying {image.name}").stdout.strip()


def inspect(efwtool: Path, image: Path) -> str:
    return _run([str(efwtool), "inspect", str(image)],
                f"inspecting {image.name}").stdout.strip()


def _run(argv: List[str], what: str) -> subprocess.CompletedProcess:
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise FirmwareImageError(f"{what} failed: {exc}") from exc
    if proc.returncode != 0:
        raise FirmwareImageError(
            f"{what} failed: {(proc.stderr or proc.stdout).strip()[:300]}"
        )
    return proc


def missing_tool_message(repos_dir: Path) -> str:
    """What to tell a developer who has no efwtool."""
    root = Path(repos_dir) / _EFW_REPO
    if not root.is_dir():
        return (
            "eFirmware is not in the local cache, so no .efw image can be "
            "assembled.\n"
            "  Run 'ebuild setup' to fetch it, or put efwtool on PATH."
        )
    return (
        f"eFirmware is cached at {root} but efwtool could not be built.\n"
        "  Build it by hand with:\n"
        f"    cmake -S {root} -B {root / _BUILD_DIRNAME} && "
        f"cmake --build {root / _BUILD_DIRNAME}"
    )
