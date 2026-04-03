# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Plugin system for ebuild.

Discovers and loads plugins via Python entry points.
Plugins extend build lifecycle, CLI commands, and package resolution.
"""

from __future__ import annotations

import importlib.metadata
import logging
from typing import List

from ebuild.plugins.base import PluginBase

logger = logging.getLogger(__name__)

_loaded_plugins: List[PluginBase] = []


def discover_plugins() -> List[PluginBase]:
    """Discover and instantiate all registered ebuild plugins.

    Scans the ``ebuild.plugins`` entry point group for registered
    plugin classes and instantiates them.

    Returns:
        List of instantiated plugin objects.
    """
    global _loaded_plugins

    if _loaded_plugins:
        return _loaded_plugins

    plugins: List[PluginBase] = []

    try:
        entry_points = importlib.metadata.entry_points()
        if hasattr(entry_points, "select"):
            eps = entry_points.select(group="ebuild.plugins")
        else:
            eps = entry_points.get("ebuild.plugins", [])

        for ep in eps:
            try:
                plugin_class = ep.load()
                if isinstance(plugin_class, type) and issubclass(plugin_class, PluginBase):
                    plugin = plugin_class()
                    plugins.append(plugin)
                    logger.info("Loaded plugin: %s v%s", plugin.name, plugin.version)
                else:
                    logger.warning(
                        "Entry point '%s' is not a PluginBase subclass, skipping",
                        ep.name,
                    )
            except Exception as exc:
                logger.warning("Failed to load plugin '%s': %s", ep.name, exc)
    except Exception as exc:
        logger.debug("Plugin discovery failed: %s", exc)

    _loaded_plugins = plugins
    return plugins


def get_plugins() -> List[PluginBase]:
    """Return the list of currently loaded plugins."""
    return list(_loaded_plugins)


def notify_pre_build(context) -> None:
    """Notify all plugins of a pre-build event."""
    for plugin in _loaded_plugins:
        try:
            plugin.on_pre_build(context)
        except Exception as exc:
            logger.warning("Plugin '%s' on_pre_build failed: %s", plugin.name, exc)


def notify_post_build(context, result) -> None:
    """Notify all plugins of a post-build event."""
    for plugin in _loaded_plugins:
        try:
            plugin.on_post_build(context, result)
        except Exception as exc:
            logger.warning("Plugin '%s' on_post_build failed: %s", plugin.name, exc)


def notify_package_resolve(package_name: str, version: str) -> None:
    """Notify all plugins of a package resolution event."""
    for plugin in _loaded_plugins:
        try:
            plugin.on_package_resolve(package_name, version)
        except Exception as exc:
            logger.warning("Plugin '%s' on_package_resolve failed: %s", plugin.name, exc)


def notify_hardware_analyze(profile) -> None:
    """Notify all plugins of a hardware analysis event."""
    for plugin in _loaded_plugins:
        try:
            plugin.on_hardware_analyze(profile)
        except Exception as exc:
            logger.warning("Plugin '%s' on_hardware_analyze failed: %s", plugin.name, exc)


def register_plugin_commands(cli) -> None:
    """Let all plugins register custom CLI commands."""
    for plugin in _loaded_plugins:
        try:
            plugin.register_commands(cli)
        except Exception as exc:
            logger.warning("Plugin '%s' register_commands failed: %s", plugin.name, exc)
