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

import re

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

    #: A bare SHA-256 digest, with or without the "sha256:" prefix.
    _SHA256_RE = re.compile(r"^(?:sha256:)?[0-9a-fA-F]{64}$")

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

        # A recipe with a checksum is a pin: a URL plus the digest of exactly
        # what should be at it. The digest is not required here -- a recipe is
        # also used to model packages that are never downloaded -- but a
        # checksum that is present has to be a real one. "sha256:placeholder"
        # parsed fine and then failed every single fetch with a mismatch, which
        # is how two shipped recipes stayed unfetchable. PackageFetcher.fetch()
        # separately refuses to download anything with no checksum at all.
        if self.checksum and not self._SHA256_RE.match(self.checksum):
            raise RecipeError(
                f"Package '{self.name}': checksum '{self.checksum}' is not a "
                f"sha256 digest. Expected 64 hex characters, optionally "
                f"prefixed with 'sha256:'. Placeholder values are rejected — "
                f"they turn every fetch of this package into a checksum "
                f"mismatch."
            )

        # Plaintext HTTP defeats the pin's purpose in the common case where a
        # recipe is edited without recomputing the digest, and it leaks what is
        # being built. Every shipped recipe already uses https.
        if self.url.startswith("http://"):
            raise RecipeError(
                f"Package '{self.name}': plaintext http:// is not accepted for "
                f"'{self.url}'. Use https://."
            )

        if self.build_system not in self.VALID_BUILD_SYSTEMS:
            raise RecipeError(
                f"Package '{self.name}': invalid build system '{self.build_system}'. "
                f"Must be one of {self.VALID_BUILD_SYSTEMS}."
            )


def _parse_string_list(
    raw: Dict[str, Any],
    field_name: str,
    fallback_field: Optional[str] = None,
) -> List[str]:
    """Parse a recipe field that must be a list of strings.

    Args:
        raw: Raw recipe mapping loaded from YAML.
        field_name: Preferred field name.
        fallback_field: Optional legacy/alternate field name used when the
            preferred field is absent.

    Returns:
        A copy of the validated list.

    Raises:
        RecipeError: If the field is not a list or contains non-string items.
    """
    if field_name in raw:
        value = raw[field_name]
    elif fallback_field is not None and fallback_field in raw:
        value = raw[fallback_field]
    else:
        value = []

    if not isinstance(value, list):
        raise RecipeError(f"'{field_name}' must be a list.")

    if not all(isinstance(item, str) for item in value):
        raise RecipeError(f"'{field_name}' must contain only strings.")

    return list(value)


def _parse_recipe(
    raw: Dict[str, Any],
    source_path: Optional[Path] = None,
) -> PackageRecipe:
    """Parse a raw YAML dict into a PackageRecipe."""
    recipe = PackageRecipe(
        name=raw.get("package", raw.get("name", "")),
        version=str(raw.get("version", "")),
        url=raw.get("url", ""),
        checksum=raw.get("checksum", ""),
        build_system=raw.get("build", raw.get("build_system", "cmake")),
        dependencies=_parse_string_list(
            raw,
            "dependencies",
            fallback_field="depends",
        ),
        patches=_parse_string_list(raw, "patches"),
        configure_args=_parse_string_list(raw, "configure_args"),
        build_args=_parse_string_list(raw, "build_args"),
        install_args=_parse_string_list(raw, "install_args"),
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
