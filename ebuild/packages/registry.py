"""Local package registry — discovers and indexes package recipes.

Scans recipe directories for YAML files and provides lookup by
package name and version.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from ebuild.packages.recipe import PackageRecipe, RecipeError, load_recipe


class PackageRegistry:
    """Registry of available package recipes.

    Scans one or more directories for recipe YAML files and provides
    lookup, listing, and search functionality.
    """

    def __init__(self) -> None:
        self._recipes: Dict[str, Dict[str, PackageRecipe]] = {}
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
        for search_path in self._search_paths:
            for recipe_file in sorted(search_path.glob("*.yaml")):
                try:
                    recipe = load_recipe(recipe_file)
                    self._register(recipe)
                    count += 1
                except (RecipeError, FileNotFoundError):
                    continue
            for recipe_file in sorted(search_path.glob("*.yml")):
                try:
                    recipe = load_recipe(recipe_file)
                    self._register(recipe)
                    count += 1
                except (RecipeError, FileNotFoundError):
                    continue
        return count

    def _register(self, recipe: PackageRecipe) -> None:
        """Register a recipe in the internal index."""
        if recipe.name not in self._recipes:
            self._recipes[recipe.name] = {}
        self._recipes[recipe.name][recipe.version] = recipe

    def get(self, name: str, version: Optional[str] = None) -> Optional[PackageRecipe]:
        """Look up a package recipe by name and optional version.

        If no version is specified, returns the latest (highest) version.
        """
        versions = self._recipes.get(name)
        if not versions:
            return None

        if version:
            return versions.get(version)

        latest_version = sorted(versions.keys())[-1]
        return versions[latest_version]

    def has(self, name: str, version: Optional[str] = None) -> bool:
        """Check if a recipe exists."""
        return self.get(name, version) is not None

    def list_packages(self) -> List[PackageRecipe]:
        """Return all registered recipes (latest version of each)."""
        result = []
        for name in sorted(self._recipes.keys()):
            versions = self._recipes[name]
            latest = sorted(versions.keys())[-1]
            result.append(versions[latest])
        return result

    def list_all_versions(self, name: str) -> List[PackageRecipe]:
        """Return all versions of a package."""
        versions = self._recipes.get(name, {})
        return [versions[v] for v in sorted(versions.keys())]

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
