# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""YAML configuration parser for ebuild.

Loads and validates build.yaml project files defining targets,
dependencies, compiler flags, and cross-compilation toolchains.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class ConfigError(Exception):
    """Raised when a build configuration is invalid."""


@dataclass
class PackageDep:
    """An external package dependency declared in build.yaml."""

    name: str
    version: Optional[str] = None


@dataclass
class TargetConfig:
    """A single build target (executable, static_library, or shared_library)."""

    name: str
    target_type: str
    sources: List[str] = field(default_factory=list)
    includes: List[str] = field(default_factory=list)
    cflags: List[str] = field(default_factory=list)
    ldflags: List[str] = field(default_factory=list)
    defines: List[str] = field(default_factory=list)
    depends: List[str] = field(default_factory=list)
    uses: List[str] = field(default_factory=list)

    VALID_TYPES = ("executable", "static_library", "shared_library")

    def validate(self) -> None:
        if not self.name:
            raise ConfigError("Target must have a 'name' field.")
        if self.target_type not in self.VALID_TYPES:
            raise ConfigError(
                f"Target '{self.name}' has invalid type '{self.target_type}'. "
                f"Must be one of {self.VALID_TYPES}."
            )
        if not self.sources:
            raise ConfigError(f"Target '{self.name}' must list at least one source file.")


@dataclass
class ToolchainConfig:
    """Cross-compilation toolchain settings."""

    compiler: str = "gcc"
    arch: str = "x86_64"
    prefix: Optional[str] = None
    sysroot: Optional[str] = None
    extra_cflags: List[str] = field(default_factory=list)
    extra_ldflags: List[str] = field(default_factory=list)


@dataclass
class ProjectConfig:
    """Top-level project configuration parsed from build.yaml."""

    name: str
    version: str
    targets: List[TargetConfig] = field(default_factory=list)
    toolchain: Optional[ToolchainConfig] = None
    packages: List[PackageDep] = field(default_factory=list)
    source_dir: Path = field(default_factory=lambda: Path("."))
    backend: str = "auto"
    backend_config: Dict[str, Any] = field(default_factory=dict)

    def get_target(self, name: str) -> Optional[TargetConfig]:
        for t in self.targets:
            if t.name == name:
                return t
        return None

    def target_names(self) -> List[str]:
        return [t.name for t in self.targets]


def _parse_target(raw: Dict[str, Any]) -> TargetConfig:
    """Parse a single target dictionary into a TargetConfig."""
    target = TargetConfig(
        name=raw.get("name", ""),
        target_type=raw.get("type", ""),
        sources=raw.get("sources", []),
        includes=raw.get("includes", []),
        cflags=raw.get("cflags", []),
        ldflags=raw.get("ldflags", []),
        defines=raw.get("defines", []),
        depends=raw.get("depends", []),
        uses=raw.get("uses", []),
    )
    target.validate()
    return target


def _parse_toolchain(raw: Dict[str, Any]) -> ToolchainConfig:
    """Parse toolchain section into a ToolchainConfig."""
    return ToolchainConfig(
        compiler=raw.get("compiler", "gcc"),
        arch=raw.get("arch", "x86_64"),
        prefix=raw.get("prefix"),
        sysroot=raw.get("sysroot"),
        extra_cflags=raw.get("extra_cflags", []),
        extra_ldflags=raw.get("extra_ldflags", []),
    )


def load_config(config_path: str | Path) -> ProjectConfig:
    """Load and validate a build.yaml configuration file.

    Args:
        config_path: Path to the YAML config file.

    Returns:
        A validated ProjectConfig instance.

    Raises:
        ConfigError: If the config is missing required fields or has invalid values.
        FileNotFoundError: If the config file does not exist.
    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ConfigError(f"Invalid config file: expected a YAML mapping, got {type(raw).__name__}.")

    # --- project section ---
    # Support both "project:" section format and flat format
    project_section = raw.get("project")
    if project_section and isinstance(project_section, dict):
        project_name = project_section.get("name")
        project_version = project_section.get("version", "0.0.0")
    else:
        project_name = raw.get("name")
        project_version = raw.get("version", "0.0.0")

    if not project_name:
        raise ConfigError("Project 'name' is required (in 'project' section or top-level).")

    # --- backend (optional) ---
    backend = raw.get("backend", "auto")
    backend_config = raw.get("backend_config", {})

    # For system builds, pull from 'system' section
    if raw.get("system") and isinstance(raw["system"], dict):
        backend_config.update(raw["system"])
        if backend == "auto":
            backend = "system"

    # For cmake/make/meson builds, pull defines from config
    if raw.get("cmake") and isinstance(raw["cmake"], dict):
        backend_config.update(raw["cmake"])
        if backend == "auto":
            backend = "cmake"

    # --- targets section (optional for external build systems) ---
    raw_targets = raw.get("targets", [])
    if not isinstance(raw_targets, list):
        raise ConfigError("'targets' must be a list of target definitions.")

    targets = [_parse_target(t) for t in raw_targets]

    # validate dependency references
    known_names = {t.name for t in targets}
    for t in targets:
        for dep in t.depends:
            if dep not in known_names:
                raise ConfigError(
                    f"Target '{t.name}' depends on unknown target '{dep}'."
                )

    # --- toolchain section (optional) ---
    toolchain = None
    raw_toolchain = raw.get("toolchain")
    if raw_toolchain and isinstance(raw_toolchain, dict):
        toolchain = _parse_toolchain(raw_toolchain)

    # --- packages section (optional, Phase 2) ---
    packages: List[PackageDep] = []
    raw_packages = raw.get("packages", [])
    if isinstance(raw_packages, list):
        for p in raw_packages:
            if isinstance(p, dict):
                pkg_name = p.get("name", "")
                pkg_version = p.get("version")
                if pkg_name:
                    packages.append(PackageDep(name=pkg_name, version=pkg_version))

    return ProjectConfig(
        name=project_name,
        version=str(project_version),
        targets=targets,
        toolchain=toolchain,
        packages=packages,
        source_dir=config_path.parent,
        backend=backend,
        backend_config=backend_config,
    )
