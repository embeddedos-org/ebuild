"""Meson build backend — generates and invokes Meson builds."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, List, Optional


class MesonBackend:
    """Drives Meson-based builds."""

    def __init__(self, source_dir: Path, build_dir: Path) -> None:
        self.source_dir = source_dir
        self.build_dir = build_dir

    def configure(
        self,
        options: Optional[Dict[str, str]] = None,
        build_type: str = "release",
        cross_file: Optional[Path] = None,
    ) -> None:
        cmd = ["meson", "setup", str(self.build_dir), str(self.source_dir),
               f"--buildtype={build_type}"]
        if cross_file:
            cmd.append(f"--cross-file={cross_file}")
        if options:
            for k, v in options.items():
                cmd.append(f"-D{k}={v}")

        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(f"Meson configure failed: {result.stderr.decode()}")

    def build(self, targets: Optional[List[str]] = None, jobs: int = 4) -> None:
        cmd = ["meson", "compile", "-C", str(self.build_dir), f"-j{jobs}"]
        if targets:
            cmd.extend(targets)

        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(f"Meson build failed: {result.stderr.decode()}")
