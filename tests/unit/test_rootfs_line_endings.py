# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Rootfs files must use Unix line endings on every build host.

The rootfs is for a Linux target, but its files were written with
``Path.write_text``, which translates ``\\n`` to the host's line separator.
Assembled on Windows, ``/etc/init.d/rcS`` began ``#!/bin/sh\\r`` (no such
interpreter), and every ``/etc/passwd`` entry named ``/bin/sh\\r`` as the
login shell. Reading the files back as text hides this, so these tests read
raw bytes.
"""

from pathlib import Path

from ebuild.system.rootfs import RootfsBuilder


def test_assembled_rootfs_files_have_no_carriage_returns(tmp_path: Path) -> None:
    rootfs = RootfsBuilder(tmp_path).assemble(
        hostname="eos-test",
        users=[{"name": "dev"}],
    )

    written = sorted(p for p in rootfs.rglob("*") if p.is_file() and p.stat().st_size)
    names = {p.relative_to(rootfs).as_posix() for p in written}
    assert {"etc/inittab", "etc/init.d/rcS", "etc/passwd", "etc/group",
            "etc/shadow", "etc/hostname", "etc/hosts",
            "etc/resolv.conf"} <= names

    with_cr = [p.relative_to(rootfs).as_posix() for p in written
               if b"\r" in p.read_bytes()]
    assert with_cr == []


def test_rcs_shebang_and_passwd_shell_are_exact(tmp_path: Path) -> None:
    rootfs = RootfsBuilder(tmp_path).assemble()

    rcs = (rootfs / "etc" / "init.d" / "rcS").read_bytes()
    assert rcs.startswith(b"#!/bin/sh\n")

    passwd = (rootfs / "etc" / "passwd").read_bytes()
    assert passwd == b"root:x:0:0:root:/root:/bin/sh\n"
