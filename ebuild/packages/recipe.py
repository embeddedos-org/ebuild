# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Package recipe format — YAML-based descriptions of external dependencies.

Each recipe defines how to fetch, verify, and build an external library
(e.g., zlib, openssl) for use in ebuild projects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class RecipeError(Exception):
    """Raised when a package recipe is invalid or cannot be loaded."""


@dataclass
class PackageRecipe:
    """Description of an external library package."""

    name: str
    version: str
    url: str
    checksum: str = ""
    build_system: str = "cmake"
    dependencies: List[str] = field(default_factory=list)
    patches: List[str] = field(default_factory=list)
    configure_args: List[str] = field(default_factory=list)
    build_args: List[str] = field(default_factory=list)
    install_args: List[str] = field(default_factory=list)
    description: str = ""
    license: str = ""

    VALID_BUILD_SYSTEMS = ("cmake", "autoconf", "make", "meson", "custom")

    @property
    def slug(self) -> str:
        """Unique identifier: name-version."""
        return f"{self.name}-{self.version}"

    def validate(self) -> None:
        """Validate recipe fields."""
        if not self.name:
            raise RecipeError("Package recipe must have a 'package' (name) field.")
        if not self.version:
            raise RecipeError(f"Package '{self.name}' must have a 'version' field.")
        if not self.url:
            raise RecipeError(f"Package '{self.name}' must have a 'url' field.")
        if self.build_system not in self.VALID_BUILD_SYSTEMS:
            raise RecipeError(
                f"Package '{self.name}': invalid build system '{self.build_system}'. "
                f"Must be one of {self.VALID_BUILD_SYSTEMS}."
            )


def _parse_recipe(raw: Dict[str, Any], source_path: Optional[Path] = None) -> PackageRecipe:
    """Parse a raw YAML dict into a PackageRecipe."""
    recipe = PackageRecipe(
        name=raw.get("package", raw.get("name", "")),
        version=str(raw.get("version", "")),
        url=raw.get("url", ""),
        checksum=raw.get("checksum", ""),
        build_system=raw.get("build", raw.get("build_system", "cmake")),
        dependencies=raw.get("dependencies", raw.get("depends", [])),
        patches=raw.get("patches", []),
        configure_args=raw.get("configure_args", []),
        build_args=raw.get("build_args", []),
        install_args=raw.get("install_args", []),
        description=raw.get("description", ""),
        license=raw.get("license", ""),
    )
    recipe.validate()
    return recipe


def load_recipe(recipe_path: str | Path) -> PackageRecipe:
    """Load a package recipe from a YAML file.

    Args:
        recipe_path: Path to the recipe YAML file.

    Returns:
        A validated PackageRecipe instance.

    Raises:
        RecipeError: If the recipe is invalid.
        FileNotFoundError: If the file doesn't exist.
    """
    recipe_path = Path(recipe_path)
    if not recipe_path.exists():
        raise FileNotFoundError(f"Recipe file not found: {recipe_path}")

    with open(recipe_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise RecipeError(f"Invalid recipe format in {recipe_path}")

    return _parse_recipe(raw, recipe_path)


def load_recipe_from_string(content: str) -> PackageRecipe:
    """Load a package recipe from a YAML string."""
    raw = yaml.safe_load(content)
    if not isinstance(raw, dict):
        raise RecipeError("Invalid recipe format: expected a YAML mapping.")
    return _parse_recipe(raw)
