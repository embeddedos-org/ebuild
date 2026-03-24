"""CMake build backend — generates and invokes CMake builds."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, List, Optional


class CMakeBackend:
    """Drives CMake-based builds."""

    def __init__(self, source_dir: Path, build_dir: Path) -> None:
        self.source_dir = source_dir
        self.build_dir = build_dir

    def configure(
        self,
        defines: Optional[Dict[str, str]] = None,
        generator: str = "Ninja",
        build_type: str = "Release",
        toolchain_file: Optional[Path] = None,
    ) -> None:
        cmd: List[str] = [
            "cmake", "-B", str(self.build_dir), "-S", str(self.source_dir),
            f"-G{generator}", f"-DCMAKE_BUILD_TYPE={build_type}",
        ]
        if toolchain_file:
            cmd.append(f"-DCMAKE_TOOLCHAIN_FILE={toolchain_file}")
        if defines:
            for k, v in defines.items():
                cmd.append(f"-D{k}={v}")

        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(f"CMake configure failed: {result.stderr.decode()}")

    def build(self, targets: Optional[List[str]] = None, jobs: int = 4) -> None:
        cmd = ["cmake", "--build", str(self.build_dir), f"-j{jobs}"]
        if targets:
            cmd.extend(["--target"] + targets)

        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(f"CMake build failed: {result.stderr.decode()}")

    def install(self, prefix: Optional[Path] = None) -> None:
        cmd = ["cmake", "--install", str(self.build_dir)]
        if prefix:
            cmd.extend(["--prefix", str(prefix)])

        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(f"CMake install failed: {result.stderr.decode()}")
