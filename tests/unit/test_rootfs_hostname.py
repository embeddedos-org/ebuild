# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""The booted hostname must be the one the rootfs was assembled with.

``assemble(hostname=...)`` writes the name to /etc/hostname and /etc/hosts,
but rcS ran a literal ``hostname eos`` at boot. A board image assembled as
``eos-rpi4`` therefore came up calling itself ``eos`` -- a name /etc/hosts
does not resolve -- while every config file said otherwise.

These tests do not grep rcS for command text: a typo such as
``echo hostname -F /etc/hostname`` would satisfy a substring check while
never setting the hostname. They *run* the generated rcS under /bin/sh with
a stub ``hostname`` and assert the name the stub was actually asked to set.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from ebuild.system.rootfs import RootfsBuilder

SH = shutil.which("sh")

pytestmark = pytest.mark.skipif(
    os.name == "nt" or SH is None,
    reason="rcS is a POSIX shell script; needs /bin/sh",
)


def _rcs(rootfs: Path) -> str:
    return (rootfs / "etc" / "init.d" / "rcS").read_text()


def _boot(rootfs: Path, tmp_path: Path) -> str:
    """Run the generated rcS and return the hostname it actually set.

    The script is run against *rootfs* as if it were ``/``: the only
    rewriting is the absolute ``/etc/`` prefix, so the command, its
    arguments and the branch structure are exactly what ships. ``mount``
    and ``hostname`` are stubbed; the ``hostname`` stub resolves ``-F
    FILE`` the way BusyBox does, so what it records is the effective name.
    """
    stub_dir = tmp_path / "stub-bin"
    stub_dir.mkdir(exist_ok=True)
    log = tmp_path / "hostname.log"

    (stub_dir / "mount").write_text("#!/bin/sh\nexit 0\n")
    # PATH below is the stub dir alone, so that nothing can fall through to
    # a real `hostname`/`mount`. The stub therefore uses only builtins.
    (stub_dir / "hostname").write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "-F" ]; then\n'
        '  read name < "$2"\n'
        f'  echo "$name" >> "{log}"\n'
        "else\n"
        f'  echo "$1" >> "{log}"\n'
        "fi\n"
    )
    for stub in ("mount", "hostname"):
        (stub_dir / stub).chmod(0o755)

    script = tmp_path / "rcS.under-test"
    # Treat `rootfs` as the filesystem root. Nothing else is altered.
    script.write_text(_rcs(rootfs).replace("/etc/", f"{rootfs}/etc/"))

    result = subprocess.run(
        [SH, str(script)],
        env={**os.environ, "PATH": str(stub_dir)},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"rcS failed: {result.stderr}"
    return log.read_text().strip() if log.exists() else ""


def test_rcs_boots_with_the_assembled_hostname(tmp_path: Path) -> None:
    rootfs = RootfsBuilder(tmp_path / "r").assemble(hostname="eos-rpi4")

    assert (rootfs / "etc" / "hostname").read_text() == "eos-rpi4\n"
    # The literal that caused the bug must not be what boot applies.
    assert _boot(rootfs, tmp_path) == "eos-rpi4"


def test_rcs_keeps_eos_as_the_fallback_without_etc_hostname(tmp_path: Path) -> None:
    # install_init() alone writes no /etc/hostname; boot must still name the
    # system rather than leave the kernel default.
    builder = RootfsBuilder(tmp_path / "r")
    builder.create_skeleton()
    builder.install_init()

    assert not (builder.rootfs_dir / "etc" / "hostname").exists()
    assert _boot(builder.rootfs_dir, tmp_path) == "eos"


def test_rcs_does_not_mask_a_failed_hostname_load(tmp_path: Path) -> None:
    """A present /etc/hostname that fails to load must not fall back to eos.

    The original fix used `... && hostname -F ... || hostname eos`, which
    silently booted as `eos` when the load failed (QUALITY.md: never fail
    silently). Here the stub `hostname` always fails; rcS must surface that
    rather than quietly applying the wrong name.
    """
    rootfs = RootfsBuilder(tmp_path / "r").assemble(hostname="eos-rpi4")

    stub_dir = tmp_path / "stub-bin"
    stub_dir.mkdir(exist_ok=True)
    (stub_dir / "mount").write_text("#!/bin/sh\nexit 0\n")
    log = tmp_path / "calls.log"
    (stub_dir / "hostname").write_text(
        f'#!/bin/sh\necho "$@" >> "{log}"\nexit 1\n'
    )
    for stub in ("mount", "hostname"):
        (stub_dir / stub).chmod(0o755)

    script = tmp_path / "rcS.under-test"
    script.write_text(_rcs(rootfs).replace("/etc/", f"{rootfs}/etc/"))
    subprocess.run(
        [SH, str(script)],
        env={**os.environ, "PATH": str(stub_dir)},
        capture_output=True,
        text=True,
        timeout=30,
    )

    calls = log.read_text().split("\n") if log.exists() else []
    # Exactly one attempt: the -F load. No second, masking `hostname eos`.
    assert [c for c in calls if c.strip()] == [f"-F {rootfs}/etc/hostname"]
