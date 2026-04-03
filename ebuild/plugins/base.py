# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Plugin base class and data types for ebuild plugins.

Plugins extend ebuild by hooking into build lifecycle events,
adding CLI commands, and intercepting package resolution.
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class BuildContext:
    """Context passed to plugin build hooks.

    Attributes:
        target: Build target name (e.g., 'raspi4', 'stm32h7').
        config: Parsed build configuration dictionary.
        build_dir: Path to the build output directory.
        source_dir: Path to the source directory.
        toolchain: Toolchain name (e.g., 'aarch64-linux-gnu').
        layers: List of enabled layers.
        profile: Build profile name (e.g., 'minimal', 'full').
        extra: Arbitrary extra data for plugin use.
    """

    target: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    build_dir: Optional[Path] = None
    source_dir: Optional[Path] = None
    toolchain: str = ""
    layers: List[str] = field(default_factory=list)
    profile: str = "standard"
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BuildResult:
    """Result of a build operation.

    Attributes:
        success: Whether the build succeeded.
        duration_s: Build duration in seconds.
        artifacts: List of produced artifact paths.
        errors: List of error messages (empty on success).
        warnings: List of warning messages.
    """

    success: bool = False
    duration_s: float = 0.0
    artifacts: List[Path] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class PluginBase(ABC):
    """Abstract base class for ebuild plugins.

    Subclass this to create a plugin. Override any hooks you need.
    All hooks have default no-op implementations so you only need
    to override the ones relevant to your plugin.

    Class attributes:
        name: Plugin name (must be unique).
        version: Plugin version string.
        description: Short description of the plugin.
    """

    name: str = "unnamed-plugin"
    version: str = "0.0.0"
    description: str = ""

    def on_pre_build(self, context: BuildContext) -> None:
        """Called before the build orchestrator dispatches the build.

        Use this to validate configuration, inject build flags,
        modify the build context, or perform pre-build tasks.

        Args:
            context: Build context with target, config, and paths.
        """

    def on_post_build(self, context: BuildContext, result: BuildResult) -> None:
        """Called after the build completes (success or failure).

        Use this for post-processing, artifact collection,
        notifications, or cleanup.

        Args:
            context: Build context used for the build.
            result: Build result with success status and artifacts.
        """

    def on_package_resolve(self, package_name: str, version: str) -> None:
        """Called when a package dependency is resolved.

        Use this to log, validate, or modify package resolution.

        Args:
            package_name: Name of the resolved package.
            version: Resolved version string.
        """

    def on_hardware_analyze(self, profile) -> None:
        """Called after hardware analysis produces a HardwareProfile.

        Use this to extend or modify hardware detection results.

        Args:
            profile: HardwareProfile instance from the analyzer.
        """

    def register_commands(self, cli) -> None:
        """Register custom CLI commands with the ebuild CLI.

        Use this to add new subcommands to the ``ebuild`` CLI.
        The ``cli`` parameter is a Click group.

        Args:
            cli: Click CLI group to add commands to.
        """

    def __repr__(self) -> str:
        return f"<Plugin {self.name} v{self.version}>"
