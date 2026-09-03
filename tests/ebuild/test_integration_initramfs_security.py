"""Regression tests for portable, injection-safe initramfs creation.

_create_initramfs() used to build a single shell string
(``cd {rootfs} && find . | cpio ... > {initramfs}``) and execute it with
``subprocess.run(cmd, shell=True, ...)``. Both ``rootfs`` and ``build_dir``
flow in from the ``--build-dir`` CLI option (an unrestricted click.Path()),
so a directory name containing shell metacharacters was executed as shell
syntax rather than treated as a literal path. The implementation no longer
starts subprocesses at all: it serializes ``newc`` with the standard library.

Note on the injection check: a directory name can never contain "/" (that's
a filesystem-level restriction on any POSIX path component, not just a
Python one), so a marker command like ``touch /abs/path/marker`` can't be
embedded as a literal directory name for a mkdir-based PoC. Instead these
tests rely on a more direct and fully deterministic signal: with the old
``shell=True`` code, the final ``> {initramfs}`` redirect target itself
would be corrupted by shell metacharacters injected via ``build_dir``,
so the initramfs would fail to land at the exact literal path we asked
for. The fix must produce a valid initramfs at exactly that path, with no
shell ever getting a chance to reinterpret it.
"""

import gzip
import os
import shutil
import stat

import pytest

from ebuild.cli.integration import _create_initramfs

# _create_initramfs() drives find(1) and cpio(1) directly. Neither exists on a
# stock Windows runner, so these fail with WinError 2 before reaching anything
# they mean to test. Building a Linux initramfs is not a Windows operation;
# skipping is the honest outcome, matching how test_ninja_backend.py skips when
# no host C compiler is present.
requires_cpio = pytest.mark.skipif(
    shutil.which("cpio") is None or shutil.which("find") is None,
    reason="find(1)/cpio(1) not available on this host",
)


@requires_cpio
def _newc_members(data):
    """Parse enough of ``newc`` to validate names, metadata, and contents."""
    members = {}
    offset = 0
    while True:
        header = data[offset:offset + 110]
        assert len(header) == 110
        assert header[:6] == b"070701"
        fields = [int(header[i:i + 8], 16) for i in range(6, 110, 8)]
        inode = fields[0]
        mode = fields[1]
        link_count = fields[4]
        file_size = fields[6]
        name_size = fields[11]

        offset += 110
        encoded_name = data[offset:offset + name_size]
        assert encoded_name.endswith(b"\0")
        name = os.fsdecode(encoded_name[:-1])
        offset += name_size
        offset += -offset % 4

        contents = data[offset:offset + file_size]
        assert len(contents) == file_size
        offset += file_size
        offset += -offset % 4
        members[name] = {
            "inode": inode,
            "mode": mode,
            "link_count": link_count,
            "contents": contents,
        }

        if name == "TRAILER!!!":
            return members



def test_create_initramfs_produces_valid_gzip_with_expected_content(tmp_path):
    """Functional regression: the pipeline must still work correctly."""
    rootfs = tmp_path / "rootfs"
    rootfs.mkdir()
    (rootfs / "hello.txt").write_text("hi from rootfs\n")

    build_dir = tmp_path / "build"
    build_dir.mkdir()

    initramfs = _create_initramfs(rootfs, build_dir)

    assert initramfs == build_dir / "initramfs.cpio.gz"
    assert initramfs.exists()
    assert initramfs.stat().st_size > 0

    # Valid gzip stream.
    with gzip.open(initramfs, "rb") as f:
        cpio_data = f.read()
    assert cpio_data.startswith(b"07070")  # newc cpio magic

    members = _newc_members(cpio_data)
    assert "." in members
    assert members["./hello.txt"]["contents"] == (
        rootfs / "hello.txt"
    ).read_bytes()
    assert "TRAILER!!!" in members


@requires_cpio
def test_create_initramfs_build_dir_with_shell_metacharacters_is_not_interpreted(tmp_path):
    """A build_dir name containing shell syntax must be treated as a plain
    literal path component, never parsed as shell syntax. Pre-fix, a name
    like ``build; touch pwned #`` would corrupt the shell's ``>`` redirect
    target, so the initramfs would NOT land at the exact literal path
    requested."""
    rootfs = tmp_path / "rootfs"
    rootfs.mkdir()
    (rootfs / "f.txt").write_text("data\n")

    evil_build_dir = tmp_path / "build; touch pwned_marker #"
    evil_build_dir.mkdir()

    initramfs = _create_initramfs(rootfs, evil_build_dir)

    expected = evil_build_dir / "initramfs.cpio.gz"
    assert initramfs == expected
    assert expected.exists(), "initramfs did not land at the exact literal path -- shell reinterpreted it"
    assert expected.stat().st_size > 0

    with gzip.open(expected, "rb") as f:
        assert f.read().startswith(b"07070")

    # No stray file from an injected `touch` anywhere near the test area.
    assert not (tmp_path / "pwned_marker").exists()
    assert not (rootfs / "pwned_marker").exists()


@requires_cpio
def test_create_initramfs_rootfs_with_shell_metacharacters_is_not_interpreted(tmp_path):
    """Same check for the ``rootfs`` argument (the ``cd {rootfs}`` half of
    the old shell string)."""
    evil_rootfs = tmp_path / "rootfs; touch pwned_marker2 #"
    evil_rootfs.mkdir()
    (evil_rootfs / "f.txt").write_text("data\n")

    build_dir = tmp_path / "build2"
    build_dir.mkdir()

    initramfs = _create_initramfs(evil_rootfs, build_dir)

    assert initramfs == build_dir / "initramfs.cpio.gz"
    assert initramfs.exists()
    assert initramfs.stat().st_size > 0

    with gzip.open(initramfs, "rb") as f:
        cpio_data = f.read()
    assert cpio_data.startswith(b"07070")

    # The literal rootfs path must have supplied the archived content.
    assert _newc_members(cpio_data)["./f.txt"]["contents"] == (
        evil_rootfs / "f.txt"
    ).read_bytes()

    assert not (tmp_path / "pwned_marker2").exists()
    assert not (build_dir / "pwned_marker2").exists()


def test_create_initramfs_marks_shebang_scripts_executable(tmp_path):
    rootfs = tmp_path / "rootfs"
    bin_dir = rootfs / "bin"
    bin_dir.mkdir(parents=True)
    executable = bin_dir / "app"
    executable.write_bytes(b"#!/bin/sh\nexit 0\n")
    executable.chmod(0o755)

    build_dir = tmp_path / "build"
    build_dir.mkdir()
    initramfs = _create_initramfs(rootfs, build_dir)

    with gzip.open(initramfs, "rb") as archive:
        members = _newc_members(archive.read())

    assert stat.S_ISDIR(members["./bin"]["mode"])
    assert stat.S_ISREG(members["./bin/app"]["mode"])
    assert members["./bin/app"]["mode"] & 0o111 == 0o111


@pytest.mark.skipif(
    os.name == "nt", reason="Windows cannot reliably create symlinks"
)
def test_create_initramfs_preserves_symlink_target(tmp_path):
    rootfs = tmp_path / "rootfs"
    bin_dir = rootfs / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "app-link").symlink_to("app")

    build_dir = tmp_path / "build"
    build_dir.mkdir()
    initramfs = _create_initramfs(rootfs, build_dir)

    with gzip.open(initramfs, "rb") as archive:
        members = _newc_members(archive.read())

    assert stat.S_ISLNK(members["./bin/app-link"]["mode"])
    assert members["./bin/app-link"]["contents"] == b"app"


def test_create_initramfs_preserves_hard_links_without_duplicate_data(tmp_path):
    rootfs = tmp_path / "rootfs"
    rootfs.mkdir()
    first = rootfs / "first"
    second = rootfs / "second"
    payload = b"shared contents" * 64
    first.write_bytes(payload)
    os.link(first, second)

    build_dir = tmp_path / "build"
    build_dir.mkdir()
    initramfs = _create_initramfs(rootfs, build_dir)

    with gzip.open(initramfs, "rb") as archive:
        members = _newc_members(archive.read())

    first_record = members["./first"]
    second_record = members["./second"]
    assert first_record["inode"] == second_record["inode"]
    assert first_record["link_count"] == second_record["link_count"] == 2
    assert {first_record["contents"], second_record["contents"]} == {
        b"",
        payload,
    }
