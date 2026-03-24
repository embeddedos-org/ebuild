"""Zephyr RTOS build backend — uses west build system."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, Optional


class ZephyrBackend:
    """Drives Zephyr RTOS builds via west."""

    def __init__(self, source_dir: Path, build_dir: Path) -> None:
        self.source_dir = source_dir
        self.build_dir = build_dir

    def build(
        self,
        board: str = "qemu_cortex_m3",
        extra_args: Optional[Dict[str, str]] = None,
    ) -> Path:
        cmd = ["west", "build", "-b", board, str(self.source_dir),
               "-d", str(self.build_dir)]
        if extra_args:
            for k, v in extra_args.items():
                cmd.extend([f"-D{k}={v}"])

        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(f"Zephyr build failed: {result.stderr.decode()}")

        return self.build_dir / "zephyr" / "zephyr.bin"

    def flash(self) -> None:
        result = subprocess.run(
            ["west", "flash", "-d", str(self.build_dir)], capture_output=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"Zephyr flash failed: {result.stderr.decode()}")
