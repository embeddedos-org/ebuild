# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Backend-neutral paths for generated build outputs."""

from __future__ import annotations

import sys
from pathlib import Path


def _exe_suffix() -> str:
    """Return the executable suffix used by the host platform."""
    return ".exe" if sys.platform == "win32" else ""


def executable_output_path(build_dir: Path, target_name: str) -> Path:
    """Return the linked binary path for an executable or test target.

    Args:
        build_dir: Directory containing the generated build files and outputs.
        target_name: Name of the executable or test target.

    Returns:
        The target path, including ``.exe`` on Windows.

    Example:
        >>> from pathlib import Path
        >>> executable_output_path(Path("_build"), "hello").name in (
        ...     "hello", "hello.exe")
        True
    """
    return Path(build_dir) / (target_name + _exe_suffix())
