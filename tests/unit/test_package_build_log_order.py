# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""The package build log must put each step's banner before its output.

``PackageBuilder._run`` writes a banner through a buffered Python file
object, then hands the same file to the subprocess, which writes straight
to the descriptor. Unless the banner is flushed first, it lands *after* the
step's output, so every section of ``build.log`` is headed by the name of
the previous step's banner and a failing step's output appears under the
wrong heading.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from ebuild.packages.builder import PackageBuilder
from ebuild.packages.cache import PackageCache


def _emit(text: str) -> list:
    # Split the literal so the echoed "$ command" line in the log does not
    # itself contain the marker the assertions look for.
    head, tail = text[:3], text[3:]
    return [sys.executable, "-c", f"print({head!r} + {tail!r})"]


def test_step_banner_precedes_step_output(tmp_path: Path) -> None:
    builder = PackageBuilder(PackageCache(tmp_path / "cache"), jobs=1)
    log_path = tmp_path / "build.log"

    builder._run(_emit("OUTPUT-OF-CONFIGURE"), tmp_path, dict(os.environ), log_path, "configure")
    builder._run(_emit("OUTPUT-OF-BUILD"), tmp_path, dict(os.environ), log_path, "build")

    log = log_path.read_text(encoding="utf-8")
    configure_banner = log.index("\nconfigure\n")
    build_banner = log.index("\nbuild\n")
    configure_output = log.index("OUTPUT-OF-CONFIGURE")
    build_output = log.index("OUTPUT-OF-BUILD")

    assert configure_banner < configure_output < build_banner < build_output, log
