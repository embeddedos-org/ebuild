"""Kbuild backend — drives Linux kernel-style Kbuild system."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional


class KbuildBackend:
    """Drives Kbuild (Linux kernel Makefile) builds."""

    def __init__(self, source_dir: Path, build_dir: Path) -> None:
        self.source_dir = source_dir
        self.build_dir = build_dir

    def configure(
        self, defconfig: str = "defconfig", arch: str = "arm64", cross_compile: str = ""
    ) -> None:
        cmd = ["make", "-C", str(self.source_dir), f"O={self.build_dir}",
               f"ARCH={arch}", defconfig]
        if cross_compile:
            cmd.append(f"CROSS_COMPILE={cross_compile}")

        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(f"Kbuild configure failed: {result.stderr.decode()}")

    def build(
        self, arch: str = "arm64", cross_compile: str = "", jobs: int = 4,
        target: Optional[str] = None,
    ) -> None:
        cmd = ["make", "-C", str(self.source_dir), f"O={self.build_dir}",
               f"ARCH={arch}", f"-j{jobs}"]
        if cross_compile:
            cmd.append(f"CROSS_COMPILE={cross_compile}")
        if target:
            cmd.append(target)

        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(f"Kbuild build failed: {result.stderr.decode()}")
