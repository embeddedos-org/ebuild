"""Make build backend — drives GNU Make builds."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, List, Optional


class MakeBackend:
    """Drives Make-based builds."""

    def __init__(self, source_dir: Path, build_dir: Path) -> None:
        self.source_dir = source_dir
        self.build_dir = build_dir

    def build(
        self,
        targets: Optional[List[str]] = None,
        variables: Optional[Dict[str, str]] = None,
        jobs: int = 4,
    ) -> None:
        cmd = ["make", "-C", str(self.source_dir), f"-j{jobs}"]
        if self.build_dir != self.source_dir:
            cmd.append(f"O={self.build_dir}")
        if variables:
            for k, v in variables.items():
                cmd.append(f"{k}={v}")
        if targets:
            cmd.extend(targets)

        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(f"Make build failed: {result.stderr.decode()}")

    def clean(self) -> None:
        cmd = ["make", "-C", str(self.source_dir), "clean"]
        subprocess.run(cmd, capture_output=True)
