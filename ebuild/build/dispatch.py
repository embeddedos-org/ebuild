# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Build backend dispatcher for ebuild.

Auto-detects and dispatches to external build systems:
CMake, Make, Meson, Cargo, Kbuild.
"""

from __future__ import annotations

import logging
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

TIER_1 = {"make", "kbuild"}

TIER_2 = {"cmake", "meson"}

TIER_3 = {"cargo"}

ALL_BACKENDS = {"cmake", "make", "meson", "cargo", "kbuild", "ninja"}

#: Backends this dispatcher actually drives. "ninja" is ebuild's own backend --
#: the CLI invokes NinjaBackend directly and never routes it through here.
DISPATCHED_BACKENDS = {"cmake", "make", "meson", "cargo", "kbuild"}


class UnknownBackendError(ValueError, RuntimeError):
    """Raised when a backend reaches the dispatcher that it cannot drive.

    Subclasses both ValueError and RuntimeError: callers treat an unrecognized
    backend name as a bad argument, while the CLI treats a backend it failed to
    route (notably "ninja") as a routing failure. Silently doing nothing here is
    what made `ebuild build` report "Build completed successfully" without ever
    running a compiler.
    """


def _unknown_backend(backend: str, step: str) -> UnknownBackendError:
    return UnknownBackendError(
        f"Unknown build backend '{backend}'. "
        f"Supported backends: {', '.join(sorted(DISPATCHED_BACKENDS))}. "
        "ebuild's own 'ninja' backend is invoked directly by the CLI and is "
        f"not dispatched here, so it cannot be {step} through BackendDispatcher."
    )


def detect_backend(source_dir: Path) -> str:
    """Auto-detect the build system from project files.

    Returns:
        One of: cmake, make, meson, cargo, kbuild, ninja
    """
    if (source_dir / "CMakeLists.txt").exists():
        return "cmake"
    if (source_dir / "meson.build").exists():
        return "meson"
    if (source_dir / "Cargo.toml").exists():
        return "cargo"
    if (source_dir / "Kconfig").exists() or (source_dir / "Kbuild").exists():
        return "kbuild"
    if (source_dir / "Makefile").exists() or (source_dir / "makefile").exists():
        return "make"
    return "ninja"


def _run_or_log(
    cmd: List[str],
    dry_run: bool,
    *,
    check: bool = True,
    cwd: Optional[str] = None,
) -> Optional[subprocess.CompletedProcess]:
    """Run a command or log it in dry-run mode.

    Args:
        cmd: Command and arguments to execute.
        dry_run: If True, log the command instead of executing it.
        check: If True, raise on non-zero exit (passed to subprocess.run).
        cwd: Working directory for the command.

    Returns:
        The CompletedProcess result, or None in dry-run mode.
    """
    if dry_run:
        cmd_str = " ".join(cmd)
        if cwd:
            logger.info("[dry-run] cd %s && %s", cwd, cmd_str)
        else:
            logger.info("[dry-run] %s", cmd_str)
        return None
    return subprocess.run(cmd, check=check, cwd=cwd)


class BackendDispatcher:
    """Dispatch configure/build/clean to external build systems.

    Args:
        source_dir: Project source directory.
        build_dir: Build output directory.
    """

    def __init__(self, source_dir: Path, build_dir: Path) -> None:
        self.source_dir = source_dir
        self.build_dir = build_dir

    def configure(
        self,
        backend: str,
        config: Optional[Dict[str, Any]] = None,
        *,
        dry_run: bool = False,
    ) -> None:
        """Run the configure step for the given backend.

        Args:
            backend: Build backend name (cmake, meson, cargo, etc.).
            config: Optional backend-specific configuration dict.
            dry_run: If True, log commands instead of executing them.

        Raises:
            UnknownBackendError: If the backend is not one this dispatcher drives.
        """
        config = config or {}
        self.build_dir.mkdir(parents=True, exist_ok=True)

        if backend == "cmake":
            cmd = ["cmake", "-B", str(self.build_dir), "-S", str(self.source_dir)]
            generator = config.get("generator")
            if generator:
                cmd.extend(["-G", generator])
            for key, val in config.get("defines", {}).items():
                cmd.append(f"-D{key}={val}")
            _run_or_log(cmd, dry_run)

        elif backend == "meson":
            cmd = ["meson", "setup", str(self.build_dir), str(self.source_dir)]
            _run_or_log(cmd, dry_run)

        elif backend == "cargo":
            pass  # Cargo does not have a separate configure step

        elif backend in ("make", "kbuild"):
            pass  # No separate configure step

        else:
            raise _unknown_backend(backend, "configured")

    def build(
        self,
        backend: str,
        config: Optional[Dict[str, Any]] = None,
        *,
        dry_run: bool = False,
    ) -> None:
        """Run the build step for the given backend.

        Args:
            backend: Build backend name (cmake, make, meson, cargo, kbuild).
            config: Optional backend-specific configuration dict.
            dry_run: If True, log commands instead of executing them.

        Raises:
            UnknownBackendError: If the backend is not one this dispatcher drives.
        """
        config = config or {}

        if backend == "cmake":
            cmd = ["cmake", "--build", str(self.build_dir)]
            jobs = config.get("jobs")
            if jobs:
                cmd.extend(["-j", str(jobs)])
            _run_or_log(cmd, dry_run)

        elif backend == "make":
            make_cmd = "nmake" if sys.platform == "win32" else "make"
            cmd = [make_cmd, "-C", str(self.source_dir)]
            _run_or_log(cmd, dry_run)

        elif backend == "meson":
            cmd = ["meson", "compile", "-C", str(self.build_dir)]
            _run_or_log(cmd, dry_run)

        elif backend == "cargo":
            cmd = ["cargo", "build"]
            if config.get("release"):
                cmd.append("--release")
            _run_or_log(cmd, dry_run, cwd=str(self.source_dir))

        elif backend == "kbuild":
            cmd = ["make", "-C", str(self.source_dir)]
            _run_or_log(cmd, dry_run)

        else:
            raise _unknown_backend(backend, "built")

    def clean(
        self,
        backend: str,
        *,
        dry_run: bool = False,
    ) -> None:
        """Run the clean step for the given backend.

        Args:
            backend: Build backend name.
            dry_run: If True, log commands instead of executing them.

        Raises:
            UnknownBackendError: If the backend is not one this dispatcher drives.
        """
        if backend == "cmake":
            _run_or_log(
                ["cmake", "--build", str(self.build_dir), "--target", "clean"],
                dry_run,
                check=False,
            )
        elif backend in ("make", "kbuild"):
            _run_or_log(
                ["make", "-C", str(self.source_dir), "clean"],
                dry_run,
                check=False,
            )
        elif backend == "meson":
            _run_or_log(
                ["meson", "compile", "-C", str(self.build_dir), "--clean"],
                dry_run,
                check=False,
            )
        elif backend == "cargo":
            _run_or_log(
                ["cargo", "clean"],
                dry_run,
                check=False,
                cwd=str(self.source_dir),
            )
        elif backend == "ninja":
            _run_or_log(
                [sys.executable, "-m", "ninja", "-C", str(self.build_dir), "-t", "clean"],
                dry_run,
                check=False,
            )
        else:
            raise _unknown_backend(backend, "cleaned")


    def test(
        self,
        backend: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> "TestOutcome":
        """Run the backend's test step and report what its runner printed.

        Counts come from parsing the runner's own summary, never from the exit
        status. A command that reported "N passed" because the process happened
        to exit 0 would go green for a suite that never ran a single test, which
        is the failure mode this whole command exists to prevent. When no
        summary can be parsed the counts stay None and only ok/ran are
        meaningful — reported honestly as unknown rather than filled in.
        """
        config = config or {}

        if backend == "cmake":
            cmd = ["ctest", "--test-dir", str(self.build_dir), "--output-on-failure"]
        elif backend == "meson":
            cmd = ["meson", "test", "-C", str(self.build_dir)]
        elif backend == "cargo":
            cmd = ["cargo", "test"]
        elif backend in ("make", "kbuild"):
            make_cmd = "nmake" if sys.platform == "win32" else "make"
            cmd = [make_cmd, "-C", str(self.source_dir), "test"]
        else:
            return TestOutcome(ok=False, ran=False, output="",
                               reason="no test runner for the '%s' backend" % backend)

        cwd = str(self.source_dir) if backend == "cargo" else None
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
        except FileNotFoundError:
            return TestOutcome(
                ok=False, ran=False, output="",
                reason="%s is not installed or not on PATH" % cmd[0])

        output = (proc.stdout or "") + (proc.stderr or "")
        passed, failed = _parse_test_counts(backend, output)
        found_none = _found_no_tests(backend, output, passed, failed)

        # ctest exits 0 when it finds nothing to run, and prints "No tests were
        # found!!!". Taken at face value that is a green test command for a
        # project with no tests at all — the single most misleading result this
        # command could produce, and the reason it treats an empty run as a
        # failure rather than a pass.
        return TestOutcome(
            ok=proc.returncode == 0 and not found_none,
            ran=True,
            passed=passed,
            failed=failed,
            output=output,
            returncode=proc.returncode,
            found_none=found_none,
        )
