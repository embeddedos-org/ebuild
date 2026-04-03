# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Package cache — tracks built packages and their install locations.

Manages the cache directory layout:
  _build/packages/<name>-<version>/
    ├── src/       — extracted source
    ├── build/     — build directory
    ├── install/   — install prefix (headers + libs)
    └── .built     — marker indicating successful build
"""

from __future__ import annotations

import json
from pathlib import Path

from ebuild.packages.recipe import PackageRecipe


class PackageCache:
    """Manages the package build cache directory.

    Each package gets its own subdirectory with src/, build/, and install/
    subdirectories. A `.built` marker file tracks successful builds.
    """

    def __init__(self, cache_root: str | Path) -> None:
        self.cache_root = Path(cache_root)

    def package_dir(self, recipe: PackageRecipe) -> Path:
        """Root directory for a specific package version."""
        return self.cache_root / recipe.slug

    def src_dir(self, recipe: PackageRecipe) -> Path:
        """Source directory for a package (where sources are extracted)."""
        return self.package_dir(recipe) / "src"

    def build_dir(self, recipe: PackageRecipe) -> Path:
        """Build directory for a package (out-of-tree build)."""
        return self.package_dir(recipe) / "build"

    def install_dir(self, recipe: PackageRecipe) -> Path:
        """Install prefix for a package (headers + libs go here)."""
        return self.package_dir(recipe) / "install"

    def include_dir(self, recipe: PackageRecipe) -> Path:
        """Path to installed headers."""
        return self.install_dir(recipe) / "include"

    def lib_dir(self, recipe: PackageRecipe) -> Path:
        """Path to installed libraries."""
        return self.install_dir(recipe) / "lib"

    def log_file(self, recipe: PackageRecipe) -> Path:
        """Build log file path."""
        return self.package_dir(recipe) / "build.log"

    def _marker_path(self, recipe: PackageRecipe) -> Path:
        return self.package_dir(recipe) / ".built"

    def is_built(self, recipe: PackageRecipe) -> bool:
        """Check if a package has been successfully built and cached."""
        marker = self._marker_path(recipe)
        if not marker.exists():
            return False

        try:
            data = json.loads(marker.read_text(encoding="utf-8"))
            return (
                data.get("name") == recipe.name
                and data.get("version") == recipe.version
                and data.get("checksum") == recipe.checksum
            )
        except (json.JSONDecodeError, OSError):
            return False

    def mark_built(self, recipe: PackageRecipe) -> None:
        """Record that a package was successfully built."""
        marker = self._marker_path(recipe)
        marker.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "name": recipe.name,
            "version": recipe.version,
            "checksum": recipe.checksum,
            "build_system": recipe.build_system,
        }
        marker.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def invalidate(self, recipe: PackageRecipe) -> None:
        """Remove the built marker, forcing a rebuild next time."""
        marker = self._marker_path(recipe)
        marker.unlink(missing_ok=True)

    def clean(self, recipe: PackageRecipe) -> None:
        """Remove all cached data for a package."""
        import shutil

        pkg_dir = self.package_dir(recipe)
        if pkg_dir.exists():
            shutil.rmtree(pkg_dir)

    def ensure_dirs(self, recipe: PackageRecipe) -> None:
        """Create the cache directory structure for a package."""
        self.src_dir(recipe).mkdir(parents=True, exist_ok=True)
        self.build_dir(recipe).mkdir(parents=True, exist_ok=True)
        self.install_dir(recipe).mkdir(parents=True, exist_ok=True)
