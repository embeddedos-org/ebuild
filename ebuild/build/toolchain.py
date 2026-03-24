"""Cross-compilation toolchain configuration.

Provides predefined profiles for common architectures (ARM, x86_64, RISC-V)
and supports custom toolchain paths and prefixes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ebuild.build.compiler import Compiler
from ebuild.core.config import ToolchainConfig


PREDEFINED_TOOLCHAINS: Dict[str, Dict[str, str]] = {
    "x86_64": {
        "prefix": "",
        "arch": "x86_64",
    },
    "arm": {
        "prefix": "arm-linux-gnueabihf-",
        "arch": "arm",
    },
    "aarch64": {
        "prefix": "aarch64-linux-gnu-",
        "arch": "aarch64",
    },
    "riscv64": {
        "prefix": "riscv64-linux-gnu-",
        "arch": "riscv64",
    },
    "riscv32": {
        "prefix": "riscv32-unknown-elf-",
        "arch": "riscv32",
    },
}


def resolve_toolchain(config: Optional[ToolchainConfig]) -> Compiler:
    """Create a Compiler instance from a ToolchainConfig.

    If no config is provided, returns a default native GCC compiler.
    Supports predefined architecture profiles and custom prefixes.
    """
    if config is None:
        return Compiler.from_name("gcc")

    prefix = config.prefix or ""
    if not prefix and config.arch in PREDEFINED_TOOLCHAINS:
        prefix = PREDEFINED_TOOLCHAINS[config.arch]["prefix"]

    return Compiler.from_name(
        name=config.compiler,
        prefix=prefix,
        sysroot=config.sysroot,
    )


def list_predefined_toolchains() -> List[str]:
    """Return names of all predefined toolchain profiles."""
    return sorted(PREDEFINED_TOOLCHAINS.keys())
