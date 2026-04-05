# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Build backend dispatcher for ebuild.

Auto-detects and dispatches to external build systems:
CMake, Make, Meson, Cargo, Kbuild.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

TIER_1 = {"make", "kbuild"}

TIER_2 = {"cmake", "meson"}

TIER_3 = {"cargo"}


def detect_backend(source_dir: Path) -> str:
    """Auto-detect the build system from project files.

    Returns:
        One of: cmake, make, meson, cargo, kbuild, ninja
    """
    if (source_dir / "CMakeLists.txt").exists():
        return "cmake"
    if (source_dir / "meson.build").exists():
        return "meson"
    if (source_dir / "Cargo.toml").exists():
        return "cargo"
    if (source_dir / "Kconfig").exists() or (source_dir / "Kbuild").exists():
        return "kbuild"
    if (source_dir / "Makefile").exists() or (source_dir / "makefile").exists():
        return "make"
    return "ninja"


class BackendDispatcher:
    """Dispatch configure/build/clean to external build systems.

    Args:
        source_dir: Project source directory.
        build_dir: Build output directory.
    """

    def __init__(self, source_dir: Path, build_dir: Path) -> None:
        self.source_dir = source_dir
        self.build_dir = build_dir

    def configure(
        self,
        backend: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Run the configure step for the given backend."""
        config = config or {}
        self.build_dir.mkdir(parents=True, exist_ok=True)

        if backend == "cmake":
            cmd = ["cmake", "-B", str(self.build_dir), "-S", str(self.source_dir)]
            generator = config.get("generator")
            if generator:
                cmd.extend(["-G", generator])
            for key, val in config.get("defines", {}).items():
                cmd.append(f"-D{key}={val}")
            subprocess.run(cmd, check=True)

        elif backend == "meson":
            cmd = ["meson", "setup", str(self.build_dir), str(self.source_dir)]
            subprocess.run(cmd, check=True)

        elif backend == "cargo":
            pass

    def build(
        self,
        backend: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Run the build step for the given backend."""
        config = config or {}

        if backend == "cmake":
            cmd = ["cmake", "--build", str(self.build_dir)]
            jobs = config.get("jobs")
            if jobs:
                cmd.extend(["-j", str(jobs)])
            subprocess.run(cmd, check=True)

        elif backend == "make":
            make_cmd = "nmake" if sys.platform == "win32" else "make"
            cmd = [make_cmd, "-C", str(self.source_dir)]
            subprocess.run(cmd, check=True)

        elif backend == "meson":
            cmd = ["meson", "compile", "-C", str(self.build_dir)]
            subprocess.run(cmd, check=True)

        elif backend == "cargo":
            cmd = ["cargo", "build"]
            if config.get("release"):
                cmd.append("--release")
            subprocess.run(cmd, check=True, cwd=str(self.source_dir))

        elif backend == "kbuild":
            cmd = ["make", "-C", str(self.source_dir)]
            subprocess.run(cmd, check=True)

    def clean(self, backend: str) -> None:
        """Run the clean step for the given backend."""
        if backend == "cmake":
            subprocess.run(
                ["cmake", "--build", str(self.build_dir), "--target", "clean"],
                check=False,
            )
        elif backend in ("make", "kbuild"):
            subprocess.run(
                ["make", "-C", str(self.source_dir), "clean"],
                check=False,
            )
        elif backend == "cargo":
            subprocess.run(
                ["cargo", "clean"],
                check=False,
                cwd=str(self.source_dir),
            )
