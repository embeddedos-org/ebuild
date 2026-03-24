"""Cargo build backend — drives Rust Cargo builds."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Optional


class CargoBackend:
    """Drives Cargo (Rust) builds."""

    def __init__(self, source_dir: Path) -> None:
        self.source_dir = source_dir

    def build(
        self,
        release: bool = True,
        target: Optional[str] = None,
        features: Optional[List[str]] = None,
    ) -> None:
        cmd = ["cargo", "build"]
        if release:
            cmd.append("--release")
        if target:
            cmd.extend(["--target", target])
        if features:
            cmd.extend(["--features", ",".join(features)])

        result = subprocess.run(cmd, capture_output=True, cwd=str(self.source_dir))
        if result.returncode != 0:
            raise RuntimeError(f"Cargo build failed: {result.stderr.decode()}")

    def test(self) -> None:
        result = subprocess.run(
            ["cargo", "test"], capture_output=True, cwd=str(self.source_dir)
        )
        if result.returncode != 0:
            raise RuntimeError(f"Cargo test failed: {result.stderr.decode()}")
