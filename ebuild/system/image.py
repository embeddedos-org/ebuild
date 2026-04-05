# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""OS image builder module.

Handles disk image creation (raw, qcow2, tar) for embedded Linux systems.
Cross-platform: uses Python stdlib where possible, shell tools as fallback.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Optional

from ebuild.cli.logger import Logger

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"


class ImageError(Exception):
    """Raised when image creation fails."""


def _has_command(name: str) -> bool:
    """Check if a shell command is available on this platform."""
    try:
        subprocess.run(
            ["where" if IS_WINDOWS else "which", name],
            capture_output=True, check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


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
        """Create tar.gz archive using Python tarfile (cross-platform)."""
        output = self.output_dir / f"{label}.tar.gz"
        if self.log:
            self.log.step(f"Creating tar image: {output}")

        with tarfile.open(str(output), "w:gz") as tar:
            tar.add(str(rootfs_dir), arcname=".")

        return output

    def _create_empty_image(self, output: Path, size_mb: int) -> None:
        """Create an empty image file (cross-platform)."""
        if IS_WINDOWS:
            # Use fsutil on Windows, or Python fallback
            try:
                size_bytes = size_mb * 1024 * 1024
                subprocess.run(
                    ["fsutil", "file", "createnew", str(output), str(size_bytes)],
                    capture_output=True, check=True,
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Python fallback — works everywhere
                with open(str(output), "wb") as f:
                    f.seek(size_mb * 1024 * 1024 - 1)
                    f.write(b"\0")
        else:
            # Unix: try dd, fall back to Python
            try:
                subprocess.run(
                    ["dd", "if=/dev/zero", f"of={output}",
                     "bs=1M", f"count={size_mb}"],
                    capture_output=True, check=True,
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                with open(str(output), "wb") as f:
                    f.seek(size_mb * 1024 * 1024 - 1)
                    f.write(b"\0")

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

        self._create_empty_image(output, size_mb)
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

        if not _has_command("qemu-img"):
            raise ImageError(
                "qemu-img not found. Install QEMU tools:\n"
                "  Linux:   sudo apt install qemu-utils\n"
                "  macOS:   brew install qemu\n"
                "  Windows: choco install qemu"
            )

        cmd = ["qemu-img", "create", "-f", "qcow2", str(output), f"{size_mb}M"]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise ImageError(f"qemu-img failed: {result.stderr.decode()}")

        return output

    def _create_ext4(self, rootfs_dir: Path, size_mb: int, label: str) -> Path:
        output = self.output_dir / f"{label}.ext4"
        if self.log:
            self.log.step(f"Creating ext4 image: {output}")

        if IS_WINDOWS:
            raise ImageError(
                "ext4 image creation is not supported on Windows.\n"
                "Use WSL or a Linux VM, or choose 'tar' or 'raw' format instead."
            )

        self._create_empty_image(output, size_mb)

        if _has_command("mkfs.ext4"):
            subprocess.run(
                ["mkfs.ext4", "-L", label, "-d", str(rootfs_dir), str(output)],
                capture_output=True,
            )
        else:
            raise ImageError(
                "mkfs.ext4 not found. Install e2fsprogs:\n"
                "  Linux: sudo apt install e2fsprogs\n"
                "  macOS: brew install e2fsprogs"
            )

        return output

    def _create_squashfs(self, rootfs_dir: Path, label: str) -> Path:
        output = self.output_dir / f"{label}.squashfs"
        if self.log:
            self.log.step(f"Creating squashfs image: {output}")

        if IS_WINDOWS:
            raise ImageError(
                "SquashFS image creation is not supported on Windows.\n"
                "Use WSL or a Linux VM, or choose 'tar' format instead."
            )

        if not _has_command("mksquashfs"):
            raise ImageError(
                "mksquashfs not found. Install squashfs-tools:\n"
                "  Linux: sudo apt install squashfs-tools\n"
                "  macOS: brew install squashfs"
            )

        cmd = ["mksquashfs", str(rootfs_dir), str(output),
               "-noappend", "-comp", "zstd"]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise ImageError(f"mksquashfs failed: {result.stderr.decode()}")

        return output
