# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""OS image builder module.

Handles disk image creation (raw, qcow2, tar) for embedded Linux systems.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from ebuild.cli.logger import Logger


class ImageError(Exception):
    """Raised when image creation fails."""


class ImageBuilder:
    """Creates bootable disk images from assembled rootfs and kernel."""

    SUPPORTED_FORMATS = ("raw", "qcow2", "tar", "ext4", "squashfs")

    def __init__(self, build_dir: Path, log: Optional[Logger] = None) -> None:
        self.build_dir = build_dir
        self.output_dir = build_dir / "images"
        self.log = log

    def create(
        self,
        rootfs_dir: Path,
        kernel_image: Optional[Path] = None,
        image_format: str = "raw",
        image_size_mb: int = 256,
        label: str = "eos-rootfs",
    ) -> Path:
        """Create a disk image from a rootfs directory.

        Args:
            rootfs_dir: Path to the assembled root filesystem.
            kernel_image: Optional kernel image to include.
            image_format: Output format (raw, qcow2, tar, ext4, squashfs).
            image_size_mb: Image size in megabytes (for raw/ext4).
            label: Filesystem label.

        Returns:
            Path to the created image file.
        """
        if image_format not in self.SUPPORTED_FORMATS:
            raise ImageError(
                f"Unsupported format '{image_format}'. "
                f"Supported: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        self.output_dir.mkdir(parents=True, exist_ok=True)

        if image_format == "tar":
            return self._create_tar(rootfs_dir, label)
        elif image_format == "raw":
            return self._create_raw(rootfs_dir, kernel_image, image_size_mb, label)
        elif image_format == "qcow2":
            return self._create_qcow2(rootfs_dir, kernel_image, image_size_mb, label)
        elif image_format == "ext4":
            return self._create_ext4(rootfs_dir, image_size_mb, label)
        elif image_format == "squashfs":
            return self._create_squashfs(rootfs_dir, label)
        else:
            raise ImageError(f"Format '{image_format}' not implemented")

    def _create_tar(self, rootfs_dir: Path, label: str) -> Path:
        output = self.output_dir / f"{label}.tar.gz"
        if self.log:
            self.log.step(f"Creating tar image: {output}")

        cmd = ["tar", "-czf", str(output), "-C", str(rootfs_dir), "."]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise ImageError(f"tar failed: {result.stderr.decode()}")

        return output

    def _create_raw(
        self,
        rootfs_dir: Path,
        kernel_image: Optional[Path],
        size_mb: int,
        label: str,
    ) -> Path:
        output = self.output_dir / f"{label}.img"
        if self.log:
            self.log.step(f"Creating raw image: {output} ({size_mb}MB)")

        # Create empty image
        subprocess.run(
            ["dd", "if=/dev/zero", f"of={output}", "bs=1M", f"count={size_mb}"],
            capture_output=True,
        )

        return output

    def _create_qcow2(
        self,
        rootfs_dir: Path,
        kernel_image: Optional[Path],
        size_mb: int,
        label: str,
    ) -> Path:
        output = self.output_dir / f"{label}.qcow2"
        if self.log:
            self.log.step(f"Creating qcow2 image: {output}")

        cmd = ["qemu-img", "create", "-f", "qcow2", str(output), f"{size_mb}M"]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise ImageError(f"qemu-img failed: {result.stderr.decode()}")

        return output

    def _create_ext4(self, rootfs_dir: Path, size_mb: int, label: str) -> Path:
        output = self.output_dir / f"{label}.ext4"
        if self.log:
            self.log.step(f"Creating ext4 image: {output}")

        subprocess.run(
            ["dd", "if=/dev/zero", f"of={output}", "bs=1M", f"count={size_mb}"],
            capture_output=True,
        )
        subprocess.run(
            ["mkfs.ext4", "-L", label, "-d", str(rootfs_dir), str(output)],
            capture_output=True,
        )

        return output

    def _create_squashfs(self, rootfs_dir: Path, label: str) -> Path:
        output = self.output_dir / f"{label}.squashfs"
        if self.log:
            self.log.step(f"Creating squashfs image: {output}")

        cmd = ["mksquashfs", str(rootfs_dir), str(output), "-noappend", "-comp", "zstd"]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise ImageError(f"mksquashfs failed: {result.stderr.decode()}")

        return output
