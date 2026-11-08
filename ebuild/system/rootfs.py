# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Root filesystem assembly.

Creates a Linux-compatible root filesystem with FHS skeleton,
init system configuration, and user setup.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional


class RootfsError(Exception):
    """Raised when rootfs assembly fails."""


FHS_DIRS = [
    "bin", "sbin", "usr/bin", "usr/sbin", "usr/lib",
    "etc", "etc/init.d", "etc/network",
    "var/log", "var/run", "var/tmp",
    "tmp", "dev", "proc", "sys", "run",
    "home", "root", "opt", "mnt", "media",
    "lib", "lib/modules", "lib/firmware",
    "boot",
]


# Shadow password field for a locked account: no password can log in.
LOCKED_PASSWORD = "!"

# Characters that must never appear in a passwd/shadow field: the field
# separator, line breaks, and control characters (including NUL and DEL).
_FORBIDDEN_FIELD_CHARS = frozenset(":\n\r") | frozenset(
    chr(c) for c in range(0x20)
) | frozenset("\x7f")


def _validate_passwd_field(value: str, label: str) -> str:
    """Reject a value that would break /etc/passwd or /etc/shadow lines.

    A ``:`` or newline smuggled into a name, shell, or home would inject
    extra fields or whole lines into the account files, so anything
    containing one (or any control character) is refused outright.
    """
    if not isinstance(value, str):
        raise RootfsError(
            f"{label} must be a string, got {type(value).__name__}"
        )
    if value == "":
        raise RootfsError(f"{label} must not be empty")
    bad = sorted(set(value) & _FORBIDDEN_FIELD_CHARS)
    if bad:
        raise RootfsError(
            f"{label} contains forbidden character(s): {bad!r}"
        )
    return value


def _validate_username(name: str) -> str:
    """Validate a login name for use in passwd/shadow/group lines."""
    name = _validate_passwd_field(name, "user name")
    if name == "root":
        raise RootfsError("user name 'root' is reserved for UID 0")
    if name in (".", "..") or name.startswith("-"):
        raise RootfsError(f"invalid user name: {name!r}")
    if any(c in name for c in "/ \t"):
        raise RootfsError(
            f"user name {name!r} must not contain '/' or whitespace"
        )
    return name


def _validate_absolute_path(value: str, label: str) -> str:
    """Validate a shell or home path for use in a passwd line."""
    value = _validate_passwd_field(value, label)
    if not value.startswith("/"):
        raise RootfsError(f"{label} must be an absolute path: {value!r}")
    parts = [part for part in value.split("/") if part not in ("", ".")]
    if ".." in parts:
        raise RootfsError(f"{label} must not contain '..': {value!r}")
    return value


def _validate_password_hash(password_hash: str) -> str:
    """Validate a crypt(3) password hash for /etc/shadow.

    Accepts only the ``$id$salt$hash`` form. The lock markers ``!`` and
    ``*`` are not hashes and are refused here, so a caller cannot
    accidentally pass a lock value where a usable password was meant.
    """
    value = _validate_passwd_field(password_hash, "password hash")
    if not value.startswith("$") or value.count("$") < 2:
        raise RootfsError(
            "password hash must be a crypt(3) hash such as "
            "'$6$salt$hash'"
        )
    return value


class RootfsBuilder:
    """Assembles a root filesystem from packages and configuration."""

    def __init__(self, build_dir: Path) -> None:
        self.build_dir = build_dir
        self.rootfs_dir = build_dir / "rootfs"

    def create_skeleton(self) -> Path:
        """Create the FHS directory skeleton."""
        for d in FHS_DIRS:
            (self.rootfs_dir / d).mkdir(parents=True, exist_ok=True)

        # Create essential device nodes (as regular files for non-root)
        (self.rootfs_dir / "dev" / ".keep").touch()

        return self.rootfs_dir

    def install_init(self, init_system: str = "busybox") -> None:
        """Install the init system configuration."""
        inittab = self.rootfs_dir / "etc" / "inittab"

        if init_system == "busybox":
            inittab.write_text(
                "::sysinit:/etc/init.d/rcS\n"
                "::respawn:/sbin/getty -L 115200 ttyS0 vt100\n"
                "::ctrlaltdel:/sbin/reboot\n"
                "::shutdown:/bin/umount -a -r\n"
            )
        elif init_system == "systemd":
            (self.rootfs_dir / "etc" / "systemd").mkdir(parents=True, exist_ok=True)

        # Create rcS init script
        rcs = self.rootfs_dir / "etc" / "init.d" / "rcS"
        rcs.write_text(
            "#!/bin/sh\n"
            "mount -t proc proc /proc\n"
            "mount -t sysfs sysfs /sys\n"
            "mount -t devtmpfs devtmpfs /dev\n"
            "hostname eos\n"
            "echo 'EoS booted successfully'\n"
        )
        if os.name != "nt":
            rcs.chmod(0o755)

    def configure_users(
        self,
        users: Optional[List[Dict[str, Any]]] = None,
        root_password_hash: Optional[str] = None,
        allow_passwordless_root: bool = False,
    ) -> None:
        """Create /etc/passwd, /etc/group, /etc/shadow.

        Accounts are locked by default: root and every user get ``!`` in
        the shadow password field, so no password can log in. A usable
        password comes only from an explicit ``password_hash`` (a crypt(3)
        hash) on that account, or from the explicit opt-in
        ``allow_passwordless=True`` on a user dict /
        ``allow_passwordless_root=True`` for root. Passwordless accounts
        are never the default.

        Every name, shell, home, and hash is validated before anything is
        written, so a ``:``, newline, or control character can never
        inject extra fields or lines into the account files.
        """
        if root_password_hash is not None and allow_passwordless_root:
            raise RootfsError(
                "root_password_hash and allow_passwordless_root are "
                "mutually exclusive"
            )
        if root_password_hash is not None:
            root_shadow_pw = _validate_password_hash(root_password_hash)
        elif allow_passwordless_root:
            root_shadow_pw = ""
        else:
            root_shadow_pw = LOCKED_PASSWORD

        passwd_lines = ["root:x:0:0:root:/root:/bin/sh\n"]
        group_lines = ["root:x:0:\n"]
        shadow_lines = [f"root:{root_shadow_pw}:0:0:99999:7:::\n"]

        home_dirs: List[Path] = []
        seen_names = {"root"}
        if users:
            uid = 1000
            for user in users:
                name = _validate_username(user.get("name", "user"))
                if name in seen_names:
                    raise RootfsError(f"duplicate user name: {name!r}")
                seen_names.add(name)
                shell = _validate_absolute_path(
                    user.get("shell", "/bin/sh"), "shell"
                )
                home = _validate_absolute_path(
                    user.get("home", f"/home/{name}"), "home"
                )
                password_hash = user.get("password_hash")
                allow_passwordless = user.get("allow_passwordless", False)
                if password_hash is not None and allow_passwordless:
                    raise RootfsError(
                        f"user {name!r}: password_hash and "
                        "allow_passwordless are mutually exclusive"
                    )
                if password_hash is not None:
                    shadow_pw = _validate_password_hash(password_hash)
                elif allow_passwordless:
                    shadow_pw = ""
                else:
                    shadow_pw = LOCKED_PASSWORD
                passwd_lines.append(
                    f"{name}:x:{uid}:{uid}:{name}:{home}:{shell}\n"
                )
                group_lines.append(f"{name}:x:{uid}:\n")
                shadow_lines.append(
                    f"{name}:{shadow_pw}:0:0:99999:7:::\n"
                )
                safe_home = os.path.normpath(home.lstrip("/"))
                home_dirs.append(self.rootfs_dir / safe_home)
                uid += 1

        # All validation passed; only now touch the filesystem, so a bad
        # account can never leave a half-written passwd/shadow behind.
        (self.rootfs_dir / "etc" / "passwd").write_text("".join(passwd_lines))
        (self.rootfs_dir / "etc" / "group").write_text("".join(group_lines))
        (self.rootfs_dir / "etc" / "shadow").write_text("".join(shadow_lines))
        for home_dir in home_dirs:
            home_dir.mkdir(parents=True, exist_ok=True)

    def configure_network(self, hostname: str = "eos") -> None:
        """Create basic network configuration."""
        (self.rootfs_dir / "etc" / "hostname").write_text(f"{hostname}\n")
        (self.rootfs_dir / "etc" / "hosts").write_text(
            f"127.0.0.1\tlocalhost\n"
            f"127.0.1.1\t{hostname}\n"
        )
        (self.rootfs_dir / "etc" / "resolv.conf").write_text("nameserver 8.8.8.8\n")

    def install_packages(self, package_dirs: List[Path]) -> None:
        """Install built packages into the rootfs."""
        for pkg_dir in package_dirs:
            if not pkg_dir.exists():
                continue
            # Copy package contents into rootfs
            for item in pkg_dir.rglob("*"):
                if item.is_file():
                    rel = item.relative_to(pkg_dir)
                    dest = self.rootfs_dir / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(item.read_bytes())

    def assemble(
        self,
        init_system: str = "busybox",
        hostname: str = "eos",
        users: Optional[List[Dict[str, Any]]] = None,
        root_password_hash: Optional[str] = None,
        allow_passwordless_root: bool = False,
    ) -> Path:
        """Full rootfs assembly pipeline."""
        self.create_skeleton()
        self.install_init(init_system)
        self.configure_users(
            users,
            root_password_hash=root_password_hash,
            allow_passwordless_root=allow_passwordless_root,
        )
        self.configure_network(hostname)
        return self.rootfs_dir
