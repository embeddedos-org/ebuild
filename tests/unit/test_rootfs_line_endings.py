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

import os
from pathlib import Path

import pytest

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


def test_tar_image_marks_target_executables_executable(tmp_path: Path) -> None:
    """The archive, not the build host's filesystem, decides the mode.

    Windows has no POSIX mode to copy, so a rootfs assembled there produced a
    tar whose /etc/init.d/rcS was 0644. BusyBox cannot run
    ``::sysinit:/etc/init.d/rcS`` without the execute bit, so the target did
    not boot. Raised by the Sourcery review of #223.
    """
    import tarfile

    from ebuild.system.image import ImageBuilder

    rootfs = RootfsBuilder(tmp_path / "build").assemble(init_system="busybox")
    # Simulate a host that cannot express the execute bit.
    (rootfs / "etc" / "init.d" / "rcS").chmod(0o644)

    out = ImageBuilder(tmp_path / "out").create(rootfs, image_format="tar")
    with tarfile.open(out) as tar:
        members = {m.name.lstrip("./"): m for m in tar.getmembers()}

    rcs = members["etc/init.d/rcS"]
    assert rcs.mode & 0o111, f"rcS is not executable in the archive: {rcs.mode:o}"
    assert rcs.mode == 0o755
    # Ownership describes the target, not whoever ran the build.
    assert (rcs.uid, rcs.gid, rcs.uname, rcs.gname) == (0, 0, "root", "root")
    # A plain config file stays non-executable.
    assert members["etc/inittab"].mode == 0o644
    assert members["etc"].mode == 0o755


def _tar_members(tmp_path: Path, rootfs: Path) -> dict:
    import tarfile

    from ebuild.system.image import ImageBuilder

    out = ImageBuilder(tmp_path / "out").create(rootfs, image_format="tar")
    with tarfile.open(out) as tar:
        return {m.name.lstrip("./"): m for m in tar.getmembers()}


@pytest.mark.skipif(os.name == "nt", reason="needs a host with POSIX modes")
def test_tar_image_keeps_posix_host_modes(tmp_path: Path) -> None:
    """A POSIX host's mode is the target's and must survive the archive.

    Forcing every file to 0644 stripped the execute bit from executables
    outside the listed directories, and dropped setuid, sticky and 0600.
    """
    rootfs = RootfsBuilder(tmp_path / "build").assemble(init_system="busybox")
    tool = rootfs / "opt" / "eos-sdk" / "bin" / "eos-tool"
    tool.parent.mkdir(parents=True)
    tool.write_text("#!/bin/sh\n")
    tool.chmod(0o755)
    (rootfs / "etc" / "shadow").chmod(0o600)
    (rootfs / "tmp").chmod(0o1777)

    members = _tar_members(tmp_path, rootfs)

    assert members["opt/eos-sdk/bin/eos-tool"].mode == 0o755
    assert members["etc/shadow"].mode == 0o600
    assert members["tmp"].mode == 0o1777


def test_tar_image_synthesises_modes_on_windows(tmp_path: Path, monkeypatch) -> None:
    """On Windows the host mode means nothing, so the layout decides it."""
    from ebuild.system import image

    monkeypatch.setattr(image, "IS_WINDOWS", True)
    rootfs = RootfsBuilder(tmp_path / "build").assemble(init_system="busybox")
    (rootfs / "etc" / "init.d" / "rcS").chmod(0o644)
    (rootfs / "etc" / "inittab").chmod(0o755)

    members = _tar_members(tmp_path, rootfs)

    assert members["etc/init.d/rcS"].mode == 0o755
    assert members["etc/inittab"].mode == 0o644
    assert members["etc"].mode == 0o755


def test_integration_rootfs_files_are_not_written_with_write_text(
    tmp_path: Path, monkeypatch
) -> None:
    """ebuild integration/qemu wrote its two files with Path.write_text.

    Same defect as the rootfs files this PR fixes, in the rootfs that
    ``ebuild integration`` builds: host line endings, and the script's
    box-drawing characters raised UnicodeEncodeError under a legacy Windows
    encoding. Raised by the Sourcery review of #223.

    A byte check cannot catch this on Linux, where ``Path.write_text``
    already emits LF in UTF-8 -- the bug only appears on Windows. So this
    asserts the thing that is actually wrong and is testable anywhere: these
    files no longer go through ``Path.write_text`` at all.
    """
    from ebuild.cli import integration
    from ebuild.cli.logger import Logger

    def _refuse(self, *args, **kwargs):  # noqa: ANN001 - test double
        raise AssertionError(
            f"{self} was written with Path.write_text; it must use "
            "write_target_text so the target gets LF and UTF-8"
        )

    monkeypatch.setattr(Path, "write_text", _refuse)
    rootfs = integration._build_rootfs(tmp_path, [], "unit-test", Logger())

    for rel in ("etc/eos-release", "etc/init.d/S99_qemu_test"):
        raw = (rootfs / rel).read_bytes()
        assert b"\r" not in raw, f"{rel} carries a carriage return"
    # The box-drawing characters survive as UTF-8, whatever the host encoding.
    assert "\u2550\u2550\u2550\u2550".encode("utf-8") in (
        rootfs / "etc/init.d/S99_qemu_test"
    ).read_bytes()
