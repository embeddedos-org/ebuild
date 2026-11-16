# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""The booted hostname must be the one the rootfs was assembled with.

``assemble(hostname=...)`` writes the name to /etc/hostname and /etc/hosts,
but rcS ran a literal ``hostname eos`` at boot. A board image assembled as
``eos-rpi4`` therefore came up calling itself ``eos`` -- a name /etc/hosts
does not resolve -- while every config file said otherwise.
"""

from pathlib import Path

from ebuild.system.rootfs import RootfsBuilder


def _rcs(rootfs: Path) -> str:
    return (rootfs / "etc" / "init.d" / "rcS").read_text()


def test_rcs_sets_the_hostname_from_etc_hostname(tmp_path: Path) -> None:
    rootfs = RootfsBuilder(tmp_path).assemble(hostname="eos-rpi4")

    assert (rootfs / "etc" / "hostname").read_text() == "eos-rpi4\n"
    rcs_lines = _rcs(rootfs).splitlines()
    assert "hostname eos" not in rcs_lines
    assert any("hostname -F /etc/hostname" in line for line in rcs_lines)


def test_rcs_keeps_eos_as_the_fallback_without_etc_hostname(tmp_path: Path) -> None:
    # install_init() alone writes no /etc/hostname; boot must still name the
    # system rather than leave the kernel default.
    builder = RootfsBuilder(tmp_path)
    builder.create_skeleton()
    builder.install_init()

    assert any(
        "/etc/hostname" in line and line.rstrip().endswith("hostname eos")
        for line in _rcs(builder.rootfs_dir).splitlines()
    )
