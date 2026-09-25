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


#: Compiler drivers `compiler:` may name, longest first so that `clang++`
#: is matched before `clang` and `g++` before `cc`.
_COMPILER_DRIVERS = ("clang++", "clang", "g++", "gcc", "c++", "cc")

#: The C++ driver that goes with each C driver.
_CXX_DRIVER = {"gcc": "g++", "clang": "clang++", "cc": "c++"}


def _split_driver(compiler: str) -> tuple:
    """Split a compiler name into (prefix, driver).

    ``arm-none-eabi-gcc`` -> ``("arm-none-eabi-", "gcc")``; ``clang`` ->
    ``("", "clang")``. A name that carries no recognised driver is used as
    the compiler verbatim, with no prefix inferred -- a custom driver then
    fails loudly at build time rather than silently becoming host gcc.
    """
    for driver in _COMPILER_DRIVERS:
        if compiler == driver:
            return "", driver
        if compiler.endswith("-" + driver):
            return compiler[: -len(driver)], driver
    return "", compiler


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

    predef = PREDEFINED_TOOLCHAINS.get(compiler)
    if predef is not None:
        # `compiler` named one of the toolchains above, which is a shorthand
        # for a prefix and an arch. Those toolchains are all GCC.
        if not prefix and predef.get("prefix"):
            prefix = predef["prefix"]
        if arch == "x86_64" and predef.get("arch"):
            arch = predef["arch"]
        driver = "gcc"
    else:
        # Otherwise `compiler` names the compiler binary, which is how the
        # documentation spells it (`compiler: gcc` with `prefix:` alongside,
        # docs/task_cortex_r5_example.md). It used to be read only as a key
        # into the table above: anything not in it -- `clang`, `cc`, or the
        # `arm-none-eabi-gcc` spelling -- fell through to a bare `gcc`, with
        # no warning, so a cross-compile config produced a host binary and
        # reported success.
        derived_prefix, driver = _split_driver(compiler)
        if not prefix:
            prefix = derived_prefix

    return ResolvedToolchain(
        cc=f"{prefix}{driver}",
        cxx=f"{prefix}{_CXX_DRIVER.get(driver, driver)}",
        ar=f"{prefix}ar",
        objcopy=f"{prefix}objcopy",
        prefix=prefix,
        arch=arch,
        sysroot=sysroot,
        cflags=list(extra_cflags),
        ldflags=list(extra_ldflags),
    )
