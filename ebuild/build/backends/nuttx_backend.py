"""NuttX build backend — Make-based NuttX builds."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional


class NuttXBackend:
    """Drives NuttX RTOS builds."""

    def __init__(self, source_dir: Path, build_dir: Path) -> None:
        self.source_dir = source_dir
        self.build_dir = build_dir

    def configure(self, board_config: str = "sim:nsh") -> None:
        cmd = [str(self.source_dir / "tools" / "configure.sh"), board_config]
        result = subprocess.run(cmd, capture_output=True, cwd=str(self.source_dir))
        if result.returncode != 0:
            raise RuntimeError(f"NuttX configure failed: {result.stderr.decode()}")

    def build(self, jobs: int = 4) -> Path:
        result = subprocess.run(
            ["make", "-C", str(self.source_dir), f"-j{jobs}"],
            capture_output=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"NuttX build failed: {result.stderr.decode()}")

        return self.source_dir / "nuttx.bin"
