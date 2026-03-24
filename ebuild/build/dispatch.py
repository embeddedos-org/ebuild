"""Build backend dispatcher — auto-selects the right build tool.

Routes builds to the appropriate backend based on config:

Tier 1 — Low-level build tools (direct execution):
  - make: Reads Makefile, executes build commands directly
  - ninja: Reads build.ninja, fast incremental builds

Tier 2 — Build system generators (generate + execute):
  - cmake: Generates Makefiles/Ninja files, then builds
  - meson: Generates Ninja files, then builds
  - kbuild: Linux kernel build system (make + Kconfig)
  - cargo: Rust build system

Tier 3 — Full build frameworks (entire system):
  - buildroot: Complete Linux system (toolchain + kernel + rootfs)
  - yocto: Layer-based Linux distribution builder
  - zephyr: RTOS build via west
  - freertos: RTOS build via CMake
  - nuttx: RTOS build via Make + Kconfig

Usage:
  dispatcher = BackendDispatcher(source_dir, build_dir)
  dispatcher.build(backend="cmake", config={"generator": "Ninja"})
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ebuild.build.backends.cmake_backend import CMakeBackend
from ebuild.build.backends.make_backend import MakeBackend
from ebuild.build.backends.meson_backend import MesonBackend
from ebuild.build.backends.kbuild_backend import KbuildBackend
from ebuild.build.backends.cargo_backend import CargoBackend
from ebuild.build.backends.zephyr_backend import ZephyrBackend
from ebuild.build.backends.freertos_backend import FreeRTOSBackend
from ebuild.build.backends.nuttx_backend import NuttXBackend


TIER_1 = {"make", "ninja"}
TIER_2 = {"cmake", "meson", "kbuild", "cargo"}
TIER_3 = {"buildroot", "yocto", "zephyr", "freertos", "nuttx"}

ALL_BACKENDS = TIER_1 | TIER_2 | TIER_3


def detect_backend(source_dir: Path) -> str:
    """Auto-detect the build system from project files."""
    if (source_dir / "CMakeLists.txt").exists():
        return "cmake"
    if (source_dir / "meson.build").exists():
        return "meson"
    if (source_dir / "Cargo.toml").exists():
        return "cargo"
    if (source_dir / "Kconfig").exists():
        return "kbuild"
    if (source_dir / "Makefile").exists() or (source_dir / "makefile").exists():
        return "make"
    if (source_dir / "build.ninja").exists():
        return "ninja"
    if (source_dir / "west.yml").exists():
        return "zephyr"
    if (source_dir / "Config.in").exists() and (source_dir / "Makefile").exists():
        return "buildroot"
    return "ninja"


class BackendDispatcher:
    """Routes builds to the correct backend based on type."""

    def __init__(self, source_dir: Path, build_dir: Path) -> None:
        self.source_dir = source_dir
        self.build_dir = build_dir
        self.build_dir.mkdir(parents=True, exist_ok=True)

    def get_tier(self, backend: str) -> int:
        if backend in TIER_1:
            return 1
        elif backend in TIER_2:
            return 2
        elif backend in TIER_3:
            return 3
        return 0

    def configure(
        self,
        backend: str = "auto",
        config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Configure the build system (Tier 2+3 only). Returns resolved backend name."""
        if backend == "auto":
            backend = detect_backend(self.source_dir)

        if config is None:
            config = {}

        if backend == "cmake":
            b = CMakeBackend(self.source_dir, self.build_dir)
            b.configure(
                defines=config.get("defines"),
                generator=config.get("generator", "Ninja"),
                build_type=config.get("build_type", "Release"),
                toolchain_file=config.get("toolchain_file"),
            )
        elif backend == "meson":
            b = MesonBackend(self.source_dir, self.build_dir)
            b.configure(
                options=config.get("options"),
                build_type=config.get("build_type", "release"),
                cross_file=config.get("cross_file"),
            )
        elif backend == "kbuild":
            b = KbuildBackend(self.source_dir, self.build_dir)
            b.configure(
                defconfig=config.get("defconfig", "defconfig"),
                arch=config.get("arch", "arm64"),
                cross_compile=config.get("cross_compile", ""),
            )
        elif backend == "freertos":
            b = FreeRTOSBackend(self.source_dir, self.build_dir)
            b.configure(
                board=config.get("board", "generic"),
                toolchain=config.get("toolchain", "arm-none-eabi-"),
            )

        return backend

    def build(
        self,
        backend: str = "auto",
        config: Optional[Dict[str, Any]] = None,
        jobs: int = 4,
        targets: Optional[List[str]] = None,
    ) -> Path:
        """Run the build using the specified backend."""
        if backend == "auto":
            backend = detect_backend(self.source_dir)

        if config is None:
            config = {}

        if backend == "cmake":
            b = CMakeBackend(self.source_dir, self.build_dir)
            b.build(targets=targets, jobs=jobs)

        elif backend == "make":
            b = MakeBackend(self.source_dir, self.build_dir)
            b.build(
                targets=targets,
                variables=config.get("variables"),
                jobs=jobs,
            )

        elif backend == "meson":
            b = MesonBackend(self.source_dir, self.build_dir)
            b.build(targets=targets, jobs=jobs)

        elif backend == "kbuild":
            b = KbuildBackend(self.source_dir, self.build_dir)
            b.build(
                arch=config.get("arch", "arm64"),
                cross_compile=config.get("cross_compile", ""),
                jobs=jobs,
                target=targets[0] if targets else None,
            )

        elif backend == "cargo":
            b = CargoBackend(self.source_dir)
            b.build(
                release=config.get("release", True),
                target=config.get("target"),
                features=config.get("features"),
            )

        elif backend == "zephyr":
            b = ZephyrBackend(self.source_dir, self.build_dir)
            return b.build(
                board=config.get("board", "qemu_cortex_m3"),
                extra_args=config.get("extra_args"),
            )

        elif backend == "freertos":
            b = FreeRTOSBackend(self.source_dir, self.build_dir)
            return b.build(jobs=jobs)

        elif backend == "nuttx":
            b = NuttXBackend(self.source_dir, self.build_dir)
            return b.build(jobs=jobs)

        elif backend == "ninja":
            import subprocess
            cmd = ["ninja", "-C", str(self.build_dir), f"-j{jobs}"]
            if targets:
                cmd.extend(targets)
            subprocess.run(cmd, check=True)

        else:
            raise ValueError(f"Unknown backend: {backend}. Available: {sorted(ALL_BACKENDS)}")

        return self.build_dir

    def clean(self, backend: str = "auto") -> None:
        """Clean build artifacts."""
        if backend == "auto":
            backend = detect_backend(self.source_dir)

        if backend == "make":
            b = MakeBackend(self.source_dir, self.build_dir)
            b.clean()
        elif backend in ("cmake", "meson", "ninja"):
            import shutil
            if self.build_dir.exists():
                shutil.rmtree(self.build_dir)
        elif backend == "cargo":
            import subprocess
            subprocess.run(["cargo", "clean"], cwd=str(self.source_dir), capture_output=True)
