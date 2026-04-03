# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Modular build profiles — composable package selection.

Profiles define which packages to include or exclude from a build,
replacing monolithic builds with à la carte package selection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

import yaml


class ProfileError(Exception):
    """Raised when a build profile is invalid or cannot be loaded."""


@dataclass
class BuildProfile:
    """A composable build profile defining package selection.

    Attributes:
        name: Profile name (e.g., 'minimal', 'standard', 'full').
        description: Human-readable description.
        packages: List of package/module names to include.
        exclude: List of package/module names to exclude.
        extends: Name of a parent profile to inherit from.
        variables: Extra build variables set by this profile.
    """

    name: str
    description: str = ""
    packages: List[str] = field(default_factory=list)
    exclude: List[str] = field(default_factory=list)
    extends: str = ""
    variables: Dict[str, str] = field(default_factory=dict)

    def effective_packages(self, parent: Optional["BuildProfile"] = None) -> Set[str]:
        """Compute the effective set of included packages.

        If this profile extends a parent, merges the parent's
        packages and applies this profile's includes/excludes.

        Args:
            parent: Optional parent profile to inherit from.

        Returns:
            Set of package names to include.
        """
        if parent:
            base = set(parent.packages)
        else:
            base = set()

        base.update(self.packages)
        base -= set(self.exclude)
        return base

    def validate(self) -> None:
        """Validate the profile configuration."""
        if not self.name:
            raise ProfileError("Profile must have a 'name' field.")

        overlap = set(self.packages) & set(self.exclude)
        if overlap:
            raise ProfileError(
                f"Profile '{self.name}': packages appear in both "
                f"include and exclude lists: {overlap}"
            )


# Predefined profiles
BUILTIN_PROFILES: Dict[str, BuildProfile] = {
    "minimal": BuildProfile(
        name="minimal",
        description="Bare minimum for boot + HAL",
        packages=["core", "hal", "drivers"],
        exclude=["networking", "ai", "graphics", "filesystem", "debug", "ota"],
    ),
    "standard": BuildProfile(
        name="standard",
        description="Standard embedded build with common features",
        packages=[
            "core", "hal", "drivers", "crypto", "ota",
            "filesystem", "logging", "sensor",
        ],
        exclude=["ai", "graphics"],
    ),
    "full": BuildProfile(
        name="full",
        description="Everything including AI, networking, and graphics",
        packages=[
            "core", "hal", "drivers", "crypto", "ota",
            "filesystem", "logging", "sensor", "motor",
            "networking", "ai", "graphics", "debug",
            "devicetree", "services",
        ],
    ),
    "safety": BuildProfile(
        name="safety",
        description="IEC 61508 / ISO 26262 safety-critical profile",
        packages=[
            "core", "hal", "drivers", "crypto", "ota",
            "logging", "watchdog", "sensor",
        ],
        exclude=["ai", "graphics", "networking", "filesystem", "debug"],
        variables={
            "EOS_SAFETY_CRITICAL": "ON",
            "EOS_STACK_CANARY": "ON",
            "EOS_MPU_ENABLED": "ON",
        },
    ),
}


def load_profile(profile_path: str | Path) -> BuildProfile:
    """Load a build profile from a YAML file.

    Args:
        profile_path: Path to the profile YAML file.

    Returns:
        A validated BuildProfile instance.

    Raises:
        ProfileError: If the profile is invalid.
        FileNotFoundError: If the file doesn't exist.
    """
    profile_path = Path(profile_path)
    if not profile_path.exists():
        raise FileNotFoundError(f"Profile file not found: {profile_path}")

    with open(profile_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ProfileError(f"Invalid profile format in {profile_path}")

    profile = BuildProfile(
        name=raw.get("profile", raw.get("name", "")),
        description=raw.get("description", ""),
        packages=raw.get("packages", []),
        exclude=raw.get("exclude", []),
        extends=raw.get("extends", ""),
        variables=raw.get("variables", {}),
    )
    profile.validate()
    return profile


def get_profile(name: str, custom_dirs: Optional[List[Path]] = None) -> BuildProfile:
    """Get a build profile by name.

    Checks builtin profiles first, then scans custom directories
    for YAML profile files.

    Args:
        name: Profile name.
        custom_dirs: Optional directories to search for custom profiles.

    Returns:
        BuildProfile instance.

    Raises:
        ProfileError: If the profile is not found.
    """
    if name in BUILTIN_PROFILES:
        return BUILTIN_PROFILES[name]

    if custom_dirs:
        for d in custom_dirs:
            d = Path(d)
            for ext in (".yaml", ".yml"):
                profile_file = d / f"{name}{ext}"
                if profile_file.exists():
                    return load_profile(profile_file)

    raise ProfileError(
        f"Profile '{name}' not found. "
        f"Available builtin profiles: {list(BUILTIN_PROFILES.keys())}"
    )


def resolve_profile(
    name: str, custom_dirs: Optional[List[Path]] = None
) -> BuildProfile:
    """Resolve a profile and its inheritance chain.

    If the profile extends another, resolves the parent recursively
    and merges packages.

    Args:
        name: Profile name.
        custom_dirs: Optional directories for custom profiles.

    Returns:
        Fully resolved BuildProfile with merged packages.
    """
    profile = get_profile(name, custom_dirs)

    if profile.extends:
        parent = resolve_profile(profile.extends, custom_dirs)
        effective = profile.effective_packages(parent)
        merged_vars = {**parent.variables, **profile.variables}
        return BuildProfile(
            name=profile.name,
            description=profile.description,
            packages=sorted(effective),
            exclude=[],
            extends="",
            variables=merged_vars,
        )

    return profile
