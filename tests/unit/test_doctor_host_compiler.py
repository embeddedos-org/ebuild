# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""`ebuild doctor` must check the host compiler the build actually runs.

A host build resolves its compiler to ``gcc`` (ResolvedToolchain.cc,
ToolchainConfig.compiler) and cross toolchains are checked as
``<prefix>-gcc``, but the host check looked for ``cc``. A machine with gcc
and no ``cc`` was told its host compiler was missing, and a machine with
only ``cc`` was told it was ready for a build that would then fail to find
gcc.
"""

from ebuild.build.toolchain import resolve_toolchain
from ebuild.system import doctor as doc


def _host_compiler(monkeypatch, present):
    monkeypatch.setattr(
        doc.shutil, "which",
        lambda name: f"/usr/bin/{name}" if name in present else None,
    )
    return next(c for c in doc.host_checks() if c.name == "host compiler")


def test_host_compiler_check_uses_the_compiler_the_build_invokes(monkeypatch):
    built_with = resolve_toolchain(None).cc
    check = _host_compiler(monkeypatch, {built_with})

    assert check.status == doc.OK, check.detail


def test_cc_alone_does_not_pass_for_a_gcc_build(monkeypatch):
    check = _host_compiler(monkeypatch, {"cc"})

    assert check.status == doc.MISSING
