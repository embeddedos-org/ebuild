# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Firmware build pipeline.

Dispatches to RTOS-specific build systems (Zephyr, FreeRTOS, NuttX)
to produce firmware binaries for embedded targets.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, Optional

from ebuild.cli.logger import Logger


class FirmwareError(Exception):
    """Raised when firmware build fails."""


class FirmwareBuilder:
    """Builds RTOS firmware images."""

    SUPPORTED_RTOS = ("zephyr", "freertos", "nuttx", "generic")

    def __init__(self, build_dir: Path, log: Optional[Logger] = None) -> None:
        self.build_dir = build_dir
        self.firmware_dir = build_dir / "firmware"
        self.firmware_dir.mkdir(parents=True, exist_ok=True)
        self.log = log

    def build(
        self,
        source_dir: Path,
        rtos: str = "generic",
        board: str = "generic",
        toolchain: str = "arm-none-eabi-",
        extra_args: Optional[Dict[str, str]] = None,
    ) -> Path:
        """Build firmware for the specified RTOS and board."""
        if rtos not in self.SUPPORTED_RTOS:
            raise FirmwareError(
                f"Unsupported RTOS '{rtos}'. "
                f"Supported: {', '.join(self.SUPPORTED_RTOS)}"
            )

        if self.log:
            self.log.step(f"Building firmware: rtos={rtos}, board={board}")

        if rtos == "zephyr":
            return self._build_zephyr(source_dir, board, extra_args)
        elif rtos == "freertos":
            return self._build_freertos(source_dir, board, toolchain)
        elif rtos == "nuttx":
            return self._build_nuttx(source_dir, board, toolchain)
        else:
            return self._build_generic(source_dir, toolchain)

    def _build_zephyr(
        self,
        source_dir: Path,
        board: str,
        extra_args: Optional[Dict[str, str]] = None,
    ) -> Path:
        output_dir = self.firmware_dir / "zephyr"
        output_dir.mkdir(parents=True, exist_ok=True)

        cmd = ["west", "build", "-b", board, str(source_dir), "-d", str(output_dir)]
        if extra_args:
            for key, val in extra_args.items():
                cmd.extend([f"-D{key}={val}"])

        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise FirmwareError(f"Zephyr build failed: {result.stderr.decode()}")

        return output_dir / "zephyr" / "zephyr.bin"

    def _build_freertos(
        self, source_dir: Path, board: str, toolchain: str
    ) -> Path:
        output_dir = self.firmware_dir / "freertos"
        output_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "cmake", "-B", str(output_dir), "-S", str(source_dir),
            f"-DCMAKE_C_COMPILER={toolchain}gcc",
            f"-DBOARD={board}",
        ]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise FirmwareError(f"FreeRTOS cmake failed: {result.stderr.decode()}")

        result = subprocess.run(
            ["cmake", "--build", str(output_dir)], capture_output=True
        )
        if result.returncode != 0:
            raise FirmwareError(f"FreeRTOS build failed: {result.stderr.decode()}")

        return output_dir

    def _build_nuttx(
        self, source_dir: Path, board: str, toolchain: str
    ) -> Path:
        output_dir = self.firmware_dir / "nuttx"
        output_dir.mkdir(parents=True, exist_ok=True)

        cmd = ["make", "-C", str(source_dir), f"BOARD={board}",
               f"CROSSDEV={toolchain}", f"O={output_dir}"]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise FirmwareError(f"NuttX build failed: {result.stderr.decode()}")

        return output_dir / "nuttx.bin"

    def _build_generic(self, source_dir: Path, toolchain: str) -> Path:
        output_dir = self.firmware_dir / "generic"
        output_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "cmake", "-B", str(output_dir), "-S", str(source_dir),
            f"-DCMAKE_C_COMPILER={toolchain}gcc",
            "-DCMAKE_BUILD_TYPE=Release",
        ]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise FirmwareError(f"Generic cmake failed: {result.stderr.decode()}")

        result = subprocess.run(
            ["cmake", "--build", str(output_dir)], capture_output=True
        )
        if result.returncode != 0:
            raise FirmwareError(f"Generic build failed: {result.stderr.decode()}")

        return output_dir
