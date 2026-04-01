# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Root filesystem assembly.

Creates a Linux-compatible root filesystem with FHS skeleton,
init system configuration, and user setup.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional


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
        users: Optional[List[Dict[str, str]]] = None,
    ) -> None:
        """Create /etc/passwd, /etc/group, /etc/shadow."""
        passwd_lines = ["root:x:0:0:root:/root:/bin/sh\n"]
        group_lines = ["root:x:0:\n"]
        shadow_lines = ["root::0:0:99999:7:::\n"]

        if users:
            uid = 1000
            for user in users:
                name = user.get("name", "user")
                shell = user.get("shell", "/bin/sh")
                home = user.get("home", f"/home/{name}")
                passwd_lines.append(f"{name}:x:{uid}:{uid}:{name}:{home}:{shell}\n")
                group_lines.append(f"{name}:x:{uid}:\n")
                shadow_lines.append(f"{name}::0:0:99999:7:::\n")
                (self.rootfs_dir / home.lstrip("/")).mkdir(parents=True, exist_ok=True)
                uid += 1

        (self.rootfs_dir / "etc" / "passwd").write_text("".join(passwd_lines))
        (self.rootfs_dir / "etc" / "group").write_text("".join(group_lines))
        (self.rootfs_dir / "etc" / "shadow").write_text("".join(shadow_lines))

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
        users: Optional[List[Dict[str, str]]] = None,
    ) -> Path:
        """Full rootfs assembly pipeline."""
        self.create_skeleton()
        self.install_init(init_system)
        self.configure_users(users)
        self.configure_network(hostname)
        return self.rootfs_dir
