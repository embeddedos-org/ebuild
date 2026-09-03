# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Shared pytest helpers for the ebuild test suite."""

import shutil
import subprocess


def gcc_is_missing() -> bool:
    """True when this host cannot run gcc.

    ``subprocess.run(['gcc', ...])`` raises ``FileNotFoundError`` on Windows
    when gcc is not installed. Evaluating that directly in ``skipif`` is not
    a skip: it aborts collection of the file and, with default pytest, the
    suite. Used by both ``tests/ebuild/test_build_dir_resolution.py`` and
    ``tests/unit/test_footprint.py`` -- previously each carried its own copy
    of this probe, one of them the version this existed to fix.
    """
    gcc = shutil.which("gcc")
    if gcc is None:
        return True
    try:
        return subprocess.run(
            [gcc, "--version"], capture_output=True
        ).returncode != 0
    except OSError:
        return True
