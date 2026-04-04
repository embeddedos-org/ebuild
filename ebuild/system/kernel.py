# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Kernel build orchestration.

Coordinates kernel source download, configuration, and compilation
for the target architecture.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import List, Optional


class KernelError(Exception):
    """Raised when kernel build fails."""


class KernelBuilder:
    """Orchestrates Linux kernel builds."""

    def __init__(self, build_dir: Path) -> None:
        self.build_dir = build_dir
        self.kernel_dir = build_dir / "kernel"
        self.kernel_dir.mkdir(parents=True, exist_ok=True)

    def configure(
        self,
        source_dir: Path,
        defconfig: str = "defconfig",
        arch: str = "arm64",
        cross_compile: str = "",
    ) -> None:
        """Run kernel configuration (make defconfig)."""
        env = {"ARCH": arch}
        if cross_compile:
            env["CROSS_COMPILE"] = cross_compile

        cmd = ["make", "-C", str(source_dir), f"O={self.kernel_dir}", defconfig]
        result = subprocess.run(cmd, capture_output=True, env={**dict(os.environ), **env})
        if result.returncode != 0:
            raise KernelError(f"Kernel configure failed: {result.stderr.decode()}")

    def build(
        self,
        source_dir: Path,
        arch: str = "arm64",
        cross_compile: str = "",
        jobs: int = 4,
        targets: Optional[List[str]] = None,
    ) -> Path:
        """Build the kernel image."""
        if targets is None:
            targets = ["Image"]

        env = {"ARCH": arch}
        if cross_compile:
            env["CROSS_COMPILE"] = cross_compile

        cmd = [
            "make", "-C", str(source_dir),
            f"O={self.kernel_dir}",
            f"-j{jobs}",
        ] + targets

        result = subprocess.run(cmd, capture_output=True, env={**dict(os.environ), **env})
        if result.returncode != 0:
            raise KernelError(f"Kernel build failed: {result.stderr.decode()}")

        return self.kernel_dir

    def build_modules(
        self,
        source_dir: Path,
        install_dir: Path,
        arch: str = "arm64",
        cross_compile: str = "",
        jobs: int = 4,
    ) -> None:
        """Build and install kernel modules."""
        env = {"ARCH": arch}
        if cross_compile:
            env["CROSS_COMPILE"] = cross_compile

        cmd = [
            "make", "-C", str(source_dir),
            f"O={self.kernel_dir}",
            f"-j{jobs}",
            "modules",
        ]
        result = subprocess.run(cmd, capture_output=True, env={**dict(os.environ), **env})
        if result.returncode != 0:
            raise KernelError(f"Module build failed: {result.stderr.decode()}")

        cmd = [
            "make", "-C", str(source_dir),
            f"O={self.kernel_dir}",
            f"INSTALL_MOD_PATH={install_dir}",
            "modules_install",
        ]
        result = subprocess.run(cmd, capture_output=True, env={**dict(os.environ), **env})
        if result.returncode != 0:
            raise KernelError(f"Module install failed: {result.stderr.decode()}")

    def get_image_path(self, arch: str = "arm64") -> Path:
        """Get path to the built kernel image."""
        arch_map = {
            "arm64": "arch/arm64/boot/Image",
            "arm": "arch/arm/boot/zImage",
            "x86_64": "arch/x86/boot/bzImage",
            "riscv": "arch/riscv/boot/Image",
        }
        rel_path = arch_map.get(arch, "vmlinux")
        return self.kernel_dir / rel_path
