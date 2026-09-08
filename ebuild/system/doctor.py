# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Environment diagnosis — one command that says why the build will fail.

The MLP list asks for "one-command environment diagnosis". Without it, a
missing cross toolchain surfaces as a compiler-not-found error partway through
a build, a missing repo cache surfaces as `eos/hal.h: No such file`, and a
missing `size` silently drops the footprint report. Each of those is a
different-looking symptom of the same class of problem, and none of them names
the fix.

Every check is read-only: this reports on the environment, it does not repair
it. `ebuild setup` fetches the repos; installing a toolchain is the
developer's package manager's job, and guessing which one they use is how a
diagnostic tool starts doing damage.
"""

from __future__ import annotations

import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

OK, MISSING, WARN = "ok", "missing", "warn"

#: Cross toolchains, and the boards that need them. Named so the report can
#: say what a missing one costs rather than just that it is absent.
_CROSS_TOOLCHAINS = {
    "arm-none-eabi": ["stm32f4", "stm32h7", "nrf52", "nrf52840", "rp2040", "tms570"],
    "aarch64-linux-gnu": ["rpi4", "am64x"],
    "xtensa-esp32-elf": ["esp32"],
}

_VERSION = re.compile(r"(\d+\.\d+(?:\.\d+)?)")


@dataclass
class Check:
    name: str
    status: str
    detail: str = ""
    fix: str = ""

    @property
    def ok(self) -> bool:
        return self.status == OK


def _version_of(exe: str, *args: str) -> str:
    """First version-looking string in the tool's own output, or ''."""
    try:
        proc = subprocess.run([exe, *(args or ("--version",))],
                              capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    m = _VERSION.search((proc.stdout or "") + (proc.stderr or ""))
    return m.group(1) if m else ""


def _tool_check(name: str, exe: str, fix: str, required: bool = True,
                version_args: tuple = ()) -> Check:
    path = shutil.which(exe)
    if not path:
        return Check(name, MISSING if required else WARN, f"{exe} not on PATH", fix)
    version = _version_of(path, *version_args)
    return Check(name, OK, f"{version} ({path})" if version else path)


def host_checks() -> List[Check]:
    """Everything needed to build for the host."""
    return [
        Check("python", OK,
              f"{platform.python_version()} ({sys.executable})"),
        _tool_check("ninja", "ninja",
                    "install ninja-build, or `pip install ninja`"),
        _tool_check("cmake", "cmake",
                    "install cmake (only needed for CMake-backed projects)",
                    required=False),
        _tool_check("host compiler", "cc",
                    "install a C compiler (build-essential, base-devel, Xcode CLT)"),
        _tool_check("size", "size",
                    "install binutils — without it builds work but report no "
                    "flash/RAM footprint",
                    required=False),
        _tool_check("git", "git",
                    "install git — `ebuild setup` clones the eos and eboot repos"),
    ]


def toolchain_checks() -> List[Check]:
    """Cross toolchains, reported as optional.

    A developer targeting only the host is not missing anything, so these are
    warnings. What the report adds is which boards each one unlocks.
    """
    out = []
    for prefix, boards in sorted(_CROSS_TOOLCHAINS.items()):
        exe = f"{prefix}-gcc"
        path = shutil.which(exe)
        targets = ", ".join(boards)
        if path:
            out.append(Check(prefix, OK,
                             f"{_version_of(path)} ({path})".strip()))
        else:
            out.append(Check(prefix, WARN, f"not installed — no {targets} builds",
                             f"install the {prefix} toolchain to target {targets}"))
    return out


def repo_checks() -> List[Check]:
    """The cached eos and eboot checkouts `uses: [eos]` resolves against."""
    from ebuild.deps import EBUILD_REPOS_DIR

    out = []
    for name in ("eos", "eboot"):
        root = Path(EBUILD_REPOS_DIR) / name
        if not root.is_dir():
            out.append(Check(f"{name} repo", MISSING,
                             f"not cloned at {root}", "run `ebuild setup`"))
            continue
        if not (root / ".git").exists():
            out.append(Check(f"{name} repo", WARN,
                             f"{root} exists but is not a git checkout",
                             "remove it and run `ebuild setup`"))
            continue
        branch = ""
        try:
            proc = subprocess.run(["git", "-C", str(root), "rev-parse",
                                   "--abbrev-ref", "HEAD"],
                                  capture_output=True, text=True, timeout=15)
            branch = proc.stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            pass
        out.append(Check(f"{name} repo", OK,
                         f"{root}" + (f" ({branch})" if branch else "")))
    return out


def run_all() -> List[Check]:
    return host_checks() + toolchain_checks() + repo_checks()


def format_report(checks: List[Check]) -> str:
    """The report body, one line per check, widest name setting the column."""
    marks = {OK: "OK  ", MISSING: "MISS", WARN: "warn"}
    width = max((len(c.name) for c in checks), default=0)
    lines = [f"  {marks[c.status]}  {c.name.ljust(width)}  {c.detail}".rstrip()
             for c in checks]

    problems = [c for c in checks if c.status == MISSING]
    advisories = [c for c in checks if c.status == WARN and c.fix]

    lines.append("")
    if problems:
        lines.append(f"{len(problems)} problem(s) will stop a build:")
        for c in problems:
            lines.append(f"  - {c.name}: {c.fix}")
    else:
        lines.append("No problems. The host build path is ready.")

    if advisories:
        lines.append("")
        lines.append("Optional, for other targets:")
        for c in advisories:
            lines.append(f"  - {c.fix}")
    return "\n".join(lines)


def exit_code(checks: List[Check]) -> int:
    """Non-zero only for things that actually stop a build.

    A warning must not fail CI: a host-only machine legitimately has no cross
    toolchain, and a doctor that always exits 1 stops being consulted.
    """
    return 1 if any(c.status == MISSING for c in checks) else 0
