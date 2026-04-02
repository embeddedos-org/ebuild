# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Toolchain resolution for ebuild.

Maps toolchain names to compiler prefixes, architecture flags,
and sysroot paths for cross-compilation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ResolvedToolchain:
    """Resolved compiler toolchain with paths and flags."""

    cc: str = "gcc"
    cxx: str = "g++"
    ar: str = "ar"
    objcopy: str = "objcopy"
    prefix: str = ""
    arch: str = "x86_64"
    sysroot: Optional[str] = None
    cflags: List[str] = field(default_factory=list)
    ldflags: List[str] = field(default_factory=list)


PREDEFINED_TOOLCHAINS: Dict[str, Dict[str, str]] = {
    "host": {
        "prefix": "",
        "arch": "x86_64",
    },
    "arm-none-eabi": {
        "prefix": "arm-none-eabi-",
        "arch": "arm",
    },
    "aarch64-linux-gnu": {
        "prefix": "aarch64-linux-gnu-",
        "arch": "arm64",
    },
    "riscv64-linux-gnu": {
        "prefix": "riscv64-linux-gnu-",
        "arch": "riscv64",
    },
    "xtensa-esp32-elf": {
        "prefix": "xtensa-esp32-elf-",
        "arch": "xtensa",
    },
}


def resolve_toolchain(toolchain_config) -> ResolvedToolchain:
    """Resolve a ToolchainConfig into a ResolvedToolchain.

    Looks up predefined toolchains by compiler name, then applies
    any overrides from the config (prefix, sysroot, extra flags).

    Args:
        toolchain_config: A ToolchainConfig dataclass or None for host.

    Returns:
        A fully resolved ResolvedToolchain ready for Ninja generation.
    """
    if toolchain_config is None:
        return ResolvedToolchain()

    compiler = getattr(toolchain_config, "compiler", "gcc")
    arch = getattr(toolchain_config, "arch", "x86_64")
    prefix = getattr(toolchain_config, "prefix", None) or ""
    sysroot = getattr(toolchain_config, "sysroot", None)
    extra_cflags = getattr(toolchain_config, "extra_cflags", [])
    extra_ldflags = getattr(toolchain_config, "extra_ldflags", [])

    predef = PREDEFINED_TOOLCHAINS.get(compiler, {})
    if not prefix and predef.get("prefix"):
        prefix = predef["prefix"]
    if arch == "x86_64" and predef.get("arch"):
        arch = predef["arch"]

    return ResolvedToolchain(
        cc=f"{prefix}gcc",
        cxx=f"{prefix}g++",
        ar=f"{prefix}ar",
        objcopy=f"{prefix}objcopy",
        prefix=prefix,
        arch=arch,
        sysroot=sysroot,
        cflags=list(extra_cflags),
        ldflags=list(extra_ldflags),
    )
