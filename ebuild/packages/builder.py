"""Package builder — compiles external packages using their declared build system.

Supports cmake, autoconf, make, and meson build systems.
Passes cross-compilation flags and dependency install paths automatically.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from ebuild.packages.cache import PackageCache
from ebuild.packages.recipe import PackageRecipe


class BuildError(Exception):
    """Raised when a package build fails."""


class PackageBuilder:
    """Builds packages from source using their declared build system.

    Supports cmake, autoconf, make, and meson strategies.
    Cross-compilation flags are forwarded from the project toolchain.
    """

    def __init__(
        self,
        cache: PackageCache,
        toolchain_env: Optional[Dict[str, str]] = None,
        jobs: int = 0,
        verbose: bool = False,
    ) -> None:
        self.cache = cache
        self.toolchain_env = toolchain_env or {}
        self.jobs = jobs or os.cpu_count() or 4
        self.verbose = verbose

    def build(
        self,
        recipe: PackageRecipe,
        dep_install_dirs: Optional[List[Path]] = None,
    ) -> Path:
        """Build a package and return its install directory.

        Skips the build if the package is already cached.

        Args:
            recipe: The package recipe to build.
            dep_install_dirs: Install prefixes of dependency packages
                              (used for CMAKE_PREFIX_PATH, PKG_CONFIG_PATH, etc.)

        Returns:
            Path to the install directory (with include/ and lib/).

        Raises:
            BuildError: If the build fails.
        """
        if self.cache.is_built(recipe):
            return self.cache.install_dir(recipe)

        self.cache.ensure_dirs(recipe)

        src_dir = self._find_source_root(recipe)
        build_dir = self.cache.build_dir(recipe)
        install_dir = self.cache.install_dir(recipe)

        env = self._build_env(dep_install_dirs)
        log_path = self.cache.log_file(recipe)

        strategy = self._get_strategy(recipe.build_system)
        strategy(recipe, src_dir, build_dir, install_dir, env, log_path)

        self.cache.mark_built(recipe)
        return install_dir

    def _find_source_root(self, recipe: PackageRecipe) -> Path:
        """Find the actual source root inside the extracted archive.

        Many tarballs extract into a subdirectory like `zlib-1.2.13/`.
        """
        src_dir = self.cache.src_dir(recipe)
        entries = [e for e in src_dir.iterdir() if e.is_dir()]
        if len(entries) == 1:
            return entries[0]
        return src_dir

    def _build_env(self, dep_install_dirs: Optional[List[Path]] = None) -> Dict[str, str]:
        """Construct environment variables for the build."""
        env = dict(os.environ)
        env.update(self.toolchain_env)

        if dep_install_dirs:
            prefix_paths = [str(d) for d in dep_install_dirs]
            existing = env.get("CMAKE_PREFIX_PATH", "")
            sep = ";" if os.name == "nt" else ":"
            env["CMAKE_PREFIX_PATH"] = sep.join(filter(None, prefix_paths + [existing]))

            pkg_dirs = [str(d / "lib" / "pkgconfig") for d in dep_install_dirs]
            existing_pkg = env.get("PKG_CONFIG_PATH", "")
            env["PKG_CONFIG_PATH"] = sep.join(filter(None, pkg_dirs + [existing_pkg]))

            cflags_extra = " ".join(f"-I{d / 'include'}" for d in dep_install_dirs)
            ldflags_extra = " ".join(f"-L{d / 'lib'}" for d in dep_install_dirs)
            env["CFLAGS"] = f"{env.get('CFLAGS', '')} {cflags_extra}".strip()
            env["LDFLAGS"] = f"{env.get('LDFLAGS', '')} {ldflags_extra}".strip()

        return env

    def _get_strategy(self, build_system: str):
        """Return the build function for the given build system."""
        strategies = {
            "cmake": self._build_cmake,
            "autoconf": self._build_autoconf,
            "make": self._build_make,
            "meson": self._build_meson,
        }
        strategy = strategies.get(build_system)
        if not strategy:
            raise BuildError(f"Unsupported build system: {build_system}")
        return strategy

    def _run(
        self,
        cmd: List[str],
        cwd: Path,
        env: Dict[str, str],
        log_path: Path,
        step_name: str,
    ) -> None:
        """Execute a build command, logging output."""
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(f"\n{'='*60}\n{step_name}\n{'='*60}\n")
            log.write(f"$ {' '.join(cmd)}\n\n")

            result = subprocess.run(
                cmd,
                cwd=str(cwd),
                env=env,
                stdout=log if not self.verbose else None,
                stderr=subprocess.STDOUT if not self.verbose else None,
            )

        if result.returncode != 0:
            raise BuildError(
                f"Package build failed at step '{step_name}'.\n"
                f"Command: {' '.join(cmd)}\n"
                f"Exit code: {result.returncode}\n"
                f"See log: {log_path}"
            )

    def _build_cmake(
        self,
        recipe: PackageRecipe,
        src_dir: Path,
        build_dir: Path,
        install_dir: Path,
        env: Dict[str, str],
        log_path: Path,
    ) -> None:
        configure_cmd = [
            "cmake",
            "-S", str(src_dir),
            "-B", str(build_dir),
            f"-DCMAKE_INSTALL_PREFIX={install_dir}",
            "-DCMAKE_BUILD_TYPE=Release",
        ] + recipe.configure_args

        build_cmd = [
            "cmake",
            "--build", str(build_dir),
            "--parallel", str(self.jobs),
        ] + recipe.build_args

        install_cmd = [
            "cmake",
            "--install", str(build_dir),
        ] + recipe.install_args

        self._run(configure_cmd, build_dir, env, log_path, "cmake configure")
        self._run(build_cmd, build_dir, env, log_path, "cmake build")
        self._run(install_cmd, build_dir, env, log_path, "cmake install")

    def _build_autoconf(
        self,
        recipe: PackageRecipe,
        src_dir: Path,
        build_dir: Path,
        install_dir: Path,
        env: Dict[str, str],
        log_path: Path,
    ) -> None:
        configure_script = src_dir / "configure"
        if not configure_script.exists():
            autogen = src_dir / "autogen.sh"
            if autogen.exists():
                self._run(["sh", "autogen.sh"], src_dir, env, log_path, "autogen")

        configure_cmd = [
            str(configure_script),
            f"--prefix={install_dir}",
        ] + recipe.configure_args

        make_cmd = ["make", f"-j{self.jobs}"] + recipe.build_args
        install_cmd = ["make", "install"] + recipe.install_args

        self._run(configure_cmd, build_dir, env, log_path, "configure")
        self._run(make_cmd, build_dir, env, log_path, "make")
        self._run(install_cmd, build_dir, env, log_path, "make install")

    def _build_make(
        self,
        recipe: PackageRecipe,
        src_dir: Path,
        build_dir: Path,
        install_dir: Path,
        env: Dict[str, str],
        log_path: Path,
    ) -> None:
        make_cmd = [
            "make",
            f"-j{self.jobs}",
            f"PREFIX={install_dir}",
        ] + recipe.build_args

        install_cmd = [
            "make",
            "install",
            f"PREFIX={install_dir}",
        ] + recipe.install_args

        self._run(make_cmd, src_dir, env, log_path, "make")
        self._run(install_cmd, src_dir, env, log_path, "make install")

    def _build_meson(
        self,
        recipe: PackageRecipe,
        src_dir: Path,
        build_dir: Path,
        install_dir: Path,
        env: Dict[str, str],
        log_path: Path,
    ) -> None:
        setup_cmd = [
            "meson",
            "setup",
            str(build_dir),
            str(src_dir),
            f"--prefix={install_dir}",
            "--buildtype=release",
        ] + recipe.configure_args

        compile_cmd = [
            "meson",
            "compile",
            "-C", str(build_dir),
            f"-j{self.jobs}",
        ] + recipe.build_args

        install_cmd = [
            "meson",
            "install",
            "-C", str(build_dir),
        ] + recipe.install_args

        self._run(setup_cmd, build_dir, env, log_path, "meson setup")
        self._run(compile_cmd, build_dir, env, log_path, "meson compile")
        self._run(install_cmd, build_dir, env, log_path, "meson install")
