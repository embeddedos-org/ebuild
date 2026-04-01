# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Package dependency resolver — resolves transitive package dependencies.

Reuses the DependencyGraph from ebuild.core.graph to determine the
correct build order for external packages.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from ebuild.core.graph import CycleError, DependencyGraph
from ebuild.packages.recipe import PackageRecipe, RecipeError
from ebuild.packages.registry import PackageRegistry


class ResolveError(Exception):
    """Raised when package dependencies cannot be resolved."""


class PackageResolver:
    """Resolves package dependency graphs and determines build order.

    Uses the registry to look up recipes and the DependencyGraph
    to compute a topological ordering.
    """

    def __init__(self, registry: PackageRegistry) -> None:
        self.registry = registry

    def resolve(
        self,
        requested: List[Dict[str, str]],
    ) -> List[PackageRecipe]:
        """Resolve a list of requested packages into a full build order.

        Args:
            requested: List of dicts with 'name' and optional 'version' keys.

        Returns:
            List of PackageRecipe in correct build order (dependencies first).

        Raises:
            ResolveError: If a package or dependency cannot be found.
        """
        resolved: Dict[str, PackageRecipe] = {}
        graph = DependencyGraph()

        for pkg in requested:
            name = pkg.get("name", "")
            version = pkg.get("version")
            self._collect(name, version, resolved, graph)

        try:
            order = graph.topological_sort()
        except CycleError as e:
            raise ResolveError(f"Package dependency cycle: {e}")

        return [resolved[name] for name in order if name in resolved]

    def _collect(
        self,
        name: str,
        version: Optional[str],
        resolved: Dict[str, PackageRecipe],
        graph: DependencyGraph,
    ) -> None:
        """Recursively collect a package and its transitive dependencies."""
        if name in resolved:
            return

        recipe = self.registry.get(name, version)
        if recipe is None:
            raise ResolveError(
                f"Package '{name}'"
                + (f" v{version}" if version else "")
                + " not found in registry. "
                f"Available: {[r.name for r in self.registry.list_packages()]}"
            )

        resolved[name] = recipe
        graph.add_node(name)

        for dep_name in recipe.dependencies:
            self._collect(dep_name, None, resolved, graph)
            graph.add_edge(name, dep_name)

    def resolve_single(self, name: str, version: Optional[str] = None) -> PackageRecipe:
        """Resolve a single package recipe from the registry."""
        recipe = self.registry.get(name, version)
        if recipe is None:
            raise ResolveError(f"Package '{name}' not found in registry.")
        return recipe
