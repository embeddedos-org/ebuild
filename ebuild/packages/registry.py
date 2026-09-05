# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Local package registry — discovers and indexes package recipes.

Scans recipe directories for YAML files and provides lookup by
package name and version.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ebuild.packages.recipe import PackageRecipe, RecipeError, load_recipe

logger = logging.getLogger(__name__)

# Everything from the first '-' or '+' is a suffix: a pre-release tag
# ("3.6.0-rc1") or build metadata ("1.3.1+patch2").
_SUFFIX_SPLIT = re.compile(r"[-+]")

# digits then letters: the 1.2.11b patch-respin form.
_RESPIN = re.compile(r"(\d+)([A-Za-z]+)")

_ComponentKey = Tuple[int, int, str]


def _component_key(component: str) -> _ComponentKey:
    """Order one dot-separated component of a version string.

    Numeric components compare numerically, so 1.10.0 still sorts above
    1.9.0. Anything else compares as text and ranks below any numeric
    component, which keeps the ordering total without inventing a meaning
    for identifiers the recipe format does not define.

    A component that is digits followed by letters -- the patch-respin form
    zlib and OpenSSL use, 1.2.11b after 1.2.11 -- keeps the numeric rank of
    its digits and orders on the letters after it, so 1.2.11 < 1.2.11b and
    1.2.11b < 1.2.11c. Treating it as text instead put it below every
    numeric component, which sorted the respin *below* the release it
    supersedes.
    """
    if component.isdigit():
        return (1, int(component), "")
    respin = _RESPIN.fullmatch(component)
    if respin:
        return (1, int(respin.group(1)), respin.group(2))
    return (0, 0, component)


def version_sort_key(version: str) -> tuple:
    """Sort key for a package version string.

    ``PackageRecipe.validate()`` accepts any non-empty version, and real
    embedded recipes use more than dotted integers: a leading ``v``
    (``v2.9.3``, littlefs's own tag format), pre-release tags
    (``3.6.0-rc1``) and build metadata (``1.3.1+patch2``). Ordering used to
    be ``[int(x) for x in version.split('.')]``, which raised ValueError on
    every one of them -- and did so from ``get()``, ``list_packages()`` and
    ``list_all_versions()``, so a single such recipe anywhere in the
    registry took down package lookup for the whole project.

    Ordering rules:
      * an optional leading ``v`` or ``V`` is ignored;
      * the release part is compared component by component, numerically
        where a component is all digits;
      * a version carrying a pre-release or build suffix sorts below the
        otherwise-equal version without one, so 3.6.0-rc1 < 3.6.0;
      * nothing raises -- any string has a place in the order.
    """
    text = version.strip()
    if text[:1] in ("v", "V"):
        text = text[1:]

    parts = _SUFFIX_SPLIT.split(text, maxsplit=1)
    release = tuple(_component_key(c) for c in parts[0].split("."))

    if len(parts) == 1:
        return (release, 1, ())
    suffix = tuple(_component_key(c) for c in re.split(r"[.\-+]", parts[1]))
    return (release, 0, suffix)


class PackageRegistry:
    """Registry of available package recipes.

    Scans one or more directories for recipe YAML files and provides
    lookup, listing, and search functionality.
    """

    def __init__(self) -> None:
        self._recipes: Dict[str, Dict[str, Tuple[int, PackageRecipe]]] = {}
        self._search_paths: List[Path] = []

    def add_search_path(self, path: str | Path) -> None:
        """Add a directory to scan for recipe files."""
        path = Path(path)
        if path.is_dir() and path not in self._search_paths:
            self._search_paths.append(path)

    def scan(self) -> int:
        """Scan all search paths for recipe YAML files.

        Returns:
            Number of recipes loaded.
        """
        count = 0
        for rank, search_path in enumerate(self._search_paths):
            for recipe_file in sorted(search_path.glob("*.yaml")):
                try:
                    recipe = load_recipe(recipe_file)
                    self._register(recipe, rank=rank)
                    count += 1
                except (RecipeError, FileNotFoundError):
                    continue
            for recipe_file in sorted(search_path.glob("*.yml")):
                try:
                    recipe = load_recipe(recipe_file)
                    self._register(recipe, rank=rank)
                    count += 1
                except (RecipeError, FileNotFoundError):
                    continue
        return count

    def _register(self, recipe: PackageRecipe, rank: int = 0) -> None:
        """Register a recipe in the internal index (higher-priority source wins for same version)."""
        if recipe.name not in self._recipes:
            self._recipes[recipe.name] = {}
        if recipe.version not in self._recipes[recipe.name]:
            self._recipes[recipe.name][recipe.version] = (rank, recipe)
        else:
            existing_rank, _ = self._recipes[recipe.name][recipe.version]
            if rank < existing_rank:
                self._recipes[recipe.name][recipe.version] = (rank, recipe)

    def get(self, name: str, version: Optional[str] = None) -> Optional[PackageRecipe]:
        """Look up a package recipe by name and optional version.

        If no version is specified, returns the latest (highest) version
        within the highest-priority source that defines this package.
        """
        versions = self._recipes.get(name)
        if not versions:
            return None

        if version:
            entry = versions.get(version)
            return entry[1] if entry else None

        min_rank = min(rank for rank, _ in versions.values())
        source_versions = {
            v: r for v, (rank, r) in versions.items() if rank == min_rank
        }
        latest_version = sorted(source_versions.keys(), key=version_sort_key)[-1]
        return source_versions[latest_version]

    def has(self, name: str, version: Optional[str] = None) -> bool:
        """Check if a recipe exists."""
        return self.get(name, version) is not None

    def list_packages(self) -> List[PackageRecipe]:
        """Return all registered recipes (latest version within highest-priority source of each)."""
        result = []
        for name in sorted(self._recipes.keys()):
            recipe = self.get(name)
            if recipe is not None:
                result.append(recipe)
        return result

    def list_all_versions(self, name: str) -> List[PackageRecipe]:
        """Return all versions of a package."""
        versions = self._recipes.get(name, {})
        return [
            versions[v][1]
            for v in sorted(
                versions.keys(),
                key=version_sort_key,
            )
        ]

    @property
    def package_count(self) -> int:
        return len(self._recipes)

    @property
    def search_paths(self) -> List[Path]:
        return list(self._search_paths)


def create_registry(*recipe_dirs: str | Path) -> PackageRegistry:
    """Create and populate a registry from the given directories.

    Convenience function that creates a registry, adds search paths,
    and scans for recipes.
    """
    registry = PackageRegistry()
    for d in recipe_dirs:
        registry.add_search_path(d)
    registry.scan()
    return registry


def find_recipe_dirs(
    project_dir: Optional[Path | str] = None,
    remote_index_dir: Optional[Path | str] = None,
) -> List[Path]:
    """Locate recipe directories in priority order: project-local, install-level, and remote synced cache.

    Args:
        project_dir: Optional path to project root.
        remote_index_dir: Optional custom remote index cache directory.

    Returns:
        List of existing recipe directory Paths in priority order.
    """
    dirs: List[Path] = []
    if project_dir is not None:
        p_dir = Path(project_dir)
        local_recipes = p_dir / "recipes"
        if local_recipes.is_dir():
            dirs.append(local_recipes)

    # Shipped system recipes
    pkg_recipes = Path(__file__).resolve().parent.parent.parent / "recipes"
    if pkg_recipes.is_dir() and pkg_recipes not in dirs:
        dirs.append(pkg_recipes)

    # Remote synced cache in ~/.ebuild/index/recipes/ (or custom index_dir)
    try:
        if remote_index_dir is not None:
            cached_recipes = Path(remote_index_dir) / "recipes"
        else:
            from ebuild.packages.index_sync import get_default_index_dir
            cached_recipes = get_default_index_dir() / "recipes"
        if cached_recipes.is_dir() and cached_recipes not in dirs:
            dirs.append(cached_recipes)
    except (ImportError, OSError) as e:
        logger.warning("Failed to resolve remote index recipes directory: %s", e)

    return dirs
