"""FreeRTOS build backend — CMake-based FreeRTOS builds."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional


class FreeRTOSBackend:
    """Drives FreeRTOS builds via CMake."""

    def __init__(self, source_dir: Path, build_dir: Path) -> None:
        self.source_dir = source_dir
        self.build_dir = build_dir

    def configure(
        self, board: str = "generic", toolchain: str = "arm-none-eabi-",
        freertos_dir: Optional[Path] = None,
    ) -> None:
        cmd = ["cmake", "-B", str(self.build_dir), "-S", str(self.source_dir),
               f"-DCMAKE_C_COMPILER={toolchain}gcc",
               f"-DBOARD={board}"]
        if freertos_dir:
            cmd.append(f"-DFREERTOS_KERNEL_PATH={freertos_dir}")

        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(f"FreeRTOS configure failed: {result.stderr.decode()}")

    def build(self, jobs: int = 4) -> Path:
        result = subprocess.run(
            ["cmake", "--build", str(self.build_dir), f"-j{jobs}"],
            capture_output=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"FreeRTOS build failed: {result.stderr.decode()}")

        return self.build_dir
