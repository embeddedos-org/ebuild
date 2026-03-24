"""Structured logging with colored output for build status."""

from __future__ import annotations

import sys
from enum import Enum
from typing import Optional


class Color(Enum):
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"


def _supports_color() -> bool:
    """Check if the terminal supports ANSI color codes."""
    if not hasattr(sys.stdout, "isatty"):
        return False
    return sys.stdout.isatty()


_COLOR_ENABLED = _supports_color()


def _fmt(text: str, color: Color) -> str:
    if not _COLOR_ENABLED:
        return text
    return f"{color.value}{text}{Color.RESET.value}"


def enable_color(enabled: bool = True) -> None:
    global _COLOR_ENABLED
    _COLOR_ENABLED = enabled


class Logger:
    """Build logger with colored, structured output."""

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose

    def info(self, msg: str) -> None:
        prefix = _fmt("[info]", Color.BLUE)
        print(f"{prefix} {msg}")

    def success(self, msg: str) -> None:
        prefix = _fmt("[ok]", Color.GREEN)
        print(f"{prefix} {msg}")

    def warning(self, msg: str) -> None:
        prefix = _fmt("[warn]", Color.YELLOW)
        print(f"{prefix} {msg}", file=sys.stderr)

    def error(self, msg: str) -> None:
        prefix = _fmt("[error]", Color.RED)
        print(f"{prefix} {msg}", file=sys.stderr)

    def debug(self, msg: str) -> None:
        if self.verbose:
            prefix = _fmt("[debug]", Color.GRAY)
            print(f"{prefix} {msg}")

    def step(self, msg: str) -> None:
        arrow = _fmt("→", Color.CYAN)
        print(f"  {arrow} {msg}")

    def header(self, msg: str) -> None:
        line = _fmt(f"═══ {msg} ═══", Color.BOLD)
        print(f"\n{line}")

    def build_status(self, target: str, status: str) -> None:
        tag = _fmt(f"[{status}]", Color.GREEN if status == "OK" else Color.RED)
        name = _fmt(target, Color.BOLD)
        print(f"  {tag} {name}")
