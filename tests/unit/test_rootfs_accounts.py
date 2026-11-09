# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Rootfs account safety (foundation PR-EB-1).

Generated images must never ship passwordless accounts by default: root
and every user are locked unless a crypt(3) password hash is supplied or
passwordless login is explicitly opted into. Names, shells, homes, and
hashes are validated before any passwd/shadow line is written, so a
``:``, newline, or control character can never inject extra fields or
lines into the account files.
"""

from pathlib import Path

import pytest

from ebuild.system.rootfs import RootfsBuilder, RootfsError


def _builder(tmp_path: Path) -> RootfsBuilder:
    builder = RootfsBuilder(tmp_path)
    builder.create_skeleton()
    return builder


def _read(builder: RootfsBuilder, name: str) -> str:
    return (builder.rootfs_dir / "etc" / name).read_text()


def _shadow_field(shadow: str, user: str) -> str:
    for line in shadow.splitlines():
        fields = line.split(":")
        if fields[0] == user:
            return fields[1]
    raise AssertionError(f"no shadow entry for {user!r}")


def test_root_locked_by_default(tmp_path: Path) -> None:
    builder = _builder(tmp_path)
    builder.configure_users()
    assert _shadow_field(_read(builder, "shadow"), "root") == "!"
    assert _read(builder, "passwd") == "root:x:0:0:root:/root:/bin/sh\n"


def test_user_locked_by_default(tmp_path: Path) -> None:
    builder = _builder(tmp_path)
    builder.configure_users(users=[{"name": "eos", "shell": "/bin/sh"}])
    shadow = _read(builder, "shadow")
    assert _shadow_field(shadow, "eos") == "!"
    assert "eos:x:1000:1000:eos:/home/eos:/bin/sh\n" in _read(builder, "passwd")
    assert (builder.rootfs_dir / "home" / "eos").is_dir()


def test_user_password_hash_is_used(tmp_path: Path) -> None:
    builder = _builder(tmp_path)
    digest = "$6$salt$hashvalue"
    builder.configure_users(
        users=[{"name": "eos", "password_hash": digest}]
    )
    assert _shadow_field(_read(builder, "shadow"), "eos") == digest


def test_user_passwordless_opt_in(tmp_path: Path) -> None:
    builder = _builder(tmp_path)
    builder.configure_users(
        users=[{"name": "eos", "allow_passwordless": True}]
    )
    assert _shadow_field(_read(builder, "shadow"), "eos") == ""


def test_root_password_hash_and_opt_in(tmp_path: Path) -> None:
    digest = "$y$j9T$saltsaltsaltsalt$hashvalue"
    builder = _builder(tmp_path)
    builder.configure_users(root_password_hash=digest)
    assert _shadow_field(_read(builder, "shadow"), "root") == digest

    builder = _builder(tmp_path)
    builder.configure_users(allow_passwordless_root=True)
    assert _shadow_field(_read(builder, "shadow"), "root") == ""


def test_mutually_exclusive_options_rejected(tmp_path: Path) -> None:
    builder = _builder(tmp_path)
    with pytest.raises(RootfsError):
        builder.configure_users(
            root_password_hash="$6$s$h", allow_passwordless_root=True
        )
    with pytest.raises(RootfsError):
        builder.configure_users(
            users=[{
                "name": "eos",
                "password_hash": "$6$s$h",
                "allow_passwordless": True,
            }]
        )


@pytest.mark.parametrize(
    "user",
    [
        {"name": "bad:name"},
        {"name": "bad\nname"},
        {"name": "bad\x00name"},
        {"name": "bad/name"},
        {"name": "bad name"},
        {"name": "root"},
        {"name": "-eos"},
        {"name": "eos", "shell": "/bin/sh:evil"},
        {"name": "eos", "shell": "bin/sh"},
        {"name": "eos", "shell": "/bin/sh\n/root:x:0:0::/root:/bin/sh"},
        {"name": "eos", "home": "/home/eos:evil"},
        {"name": "eos", "home": "/home/eos\nroot:x:0:0::/root:/bin/sh"},
        {"name": "eos", "home": "home/eos"},
        {"name": "eos", "home": "/home/../../etc"},
        {"name": "eos", "password_hash": "*"},
        {"name": "eos", "password_hash": "!"},
        {"name": "eos", "password_hash": "plaintext"},
        {"name": "eos", "password_hash": "$6$salt:hash"},
        {"name": "eos", "password_hash": "$6$salt\nhash"},
    ],
)
def test_injection_cases_rejected(tmp_path: Path, user: dict) -> None:
    builder = _builder(tmp_path)
    with pytest.raises(RootfsError):
        builder.configure_users(users=[user])


def test_rejected_user_writes_nothing(tmp_path: Path) -> None:
    builder = _builder(tmp_path)
    with pytest.raises(RootfsError):
        builder.configure_users(users=[{"name": "bad:name"}])
    for name in ("passwd", "group", "shadow"):
        assert not (builder.rootfs_dir / "etc" / name).exists()


def test_duplicate_user_names_rejected(tmp_path: Path) -> None:
    builder = _builder(tmp_path)
    with pytest.raises(RootfsError):
        builder.configure_users(
            users=[{"name": "eos"}, {"name": "eos"}]
        )


def test_assemble_threads_account_options(tmp_path: Path) -> None:
    builder = RootfsBuilder(tmp_path)
    builder.assemble(root_password_hash="$6$s$h")
    assert _shadow_field(_read(builder, "shadow"), "root") == "$6$s$h"

    builder = RootfsBuilder(tmp_path / "second")
    builder.assemble()
    assert _shadow_field(_read(builder, "shadow"), "root") == "!"
