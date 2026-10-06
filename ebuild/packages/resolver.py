# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Package dependency resolver — resolves transitive package dependencies.

Reuses the DependencyGraph from ebuild.core.graph to determine the
correct build order for external packages.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from ebuild.core.graph import CycleError, DependencyGraph
from ebuild.packages.lockfile import Lockfile
from ebuild.packages.recipe import PackageRecipe
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
        lockfile: Optional[Lockfile] = None,
    ) -> List[PackageRecipe]:
        """Resolve a list of requested packages into a full build order.

        Version selection, in order of precedence:
            1. An explicitly requested version pins the package for the whole
               resolution, no matter where in the dependency graph the package
               is first reached. Requesting two different versions of the same
               package is a conflict and raises rather than silently selecting
               one of them.
            2. A version recorded in ``lockfile`` pins the package the same
               way. That is what the lockfile is for: the next resolution on
               this or any other machine lands on the same recipe, not on
               whatever is newest by then. A locked version that no recipe
               provides is an error, not a fallback -- silently resolving to
               something else is exactly what the lock exists to prevent. A
               locked entry that names a URL or checksum is also checked
               against the recipe it resolves to: the same version behind
               different bytes is refused.
            3. Otherwise the newest version in the registry.

        Args:
            requested: List of dicts with 'name' and optional 'version' keys.
            lockfile: An already-loaded Lockfile, or None to resolve without
                one. The caller decides whether to rewrite it afterwards.

        Returns:
            List of PackageRecipe in correct build order (dependencies first).

        Raises:
            ResolveError: If a package or dependency cannot be found, if two
                incompatible versions of the same package are requested, if
                the lockfile pins a version or bytes the registry does not
                provide, or if the dependency graph contains a cycle.
        """
        resolved: Dict[str, PackageRecipe] = {}
        graph = DependencyGraph()

        # Collect explicit pins up front. Doing this before walking the graph
        # is what makes the result independent of request order: otherwise the
        # first traversal to reach a package fixes its version, and a pin
        # appearing later in the list is swallowed by the memoization in
        # _collect().
        pins = self._collect_pins(requested)
        locked = self._locked_entries(lockfile, pins)

        for pkg in requested:
            self._collect(pkg.get("name", ""), pins, locked, resolved, graph)

        try:
            order = graph.topological_sort()
        except CycleError as e:
            raise ResolveError(f"Package dependency cycle: {e}")

        return [resolved[name] for name in order if name in resolved]

    @staticmethod
    def _collect_pins(requested: List[Dict[str, str]]) -> Dict[str, str]:
        """Map package name → explicitly requested version.

        Raises:
            ResolveError: If the same package is requested at two different
                versions.
        """
        pins: Dict[str, str] = {}

        for pkg in requested:
            name = pkg.get("name", "")
            version = pkg.get("version")
            if not version:
                continue

            existing = pins.get(name)
            if existing is not None and existing != version:
                raise ResolveError(
                    f"Conflicting versions requested for package '{name}': "
                    f"'{existing}' and '{version}'. "
                    "Request a single version of each package."
                )
            pins[name] = version

        return pins

    @staticmethod
    def _locked_entries(
        lockfile: Optional[Lockfile],
        pins: Dict[str, str],
    ) -> Dict[str, Dict[str, str]]:
        """Lockfile entries that take part in this resolution.

        An explicit pin outranks the lock for that package: the request is
        the statement of intent, the lock is the record of the last
        resolution, and the caller rewrites the record afterwards.
        """
        if lockfile is None:
            return {}
        return {
            name: entry
            for name, entry in lockfile.locked_packages.items()
            if name not in pins and isinstance(entry, dict) and entry.get("version")
        }

    def _collect(
        self,
        name: str,
        pins: Dict[str, str],
        locked: Dict[str, Dict[str, str]],
        resolved: Dict[str, PackageRecipe],
        graph: DependencyGraph,
    ) -> None:
        """Recursively collect a package and its transitive dependencies."""
        if name in resolved:
            return

        version = pins.get(name)
        entry = locked.get(name)
        if version is None and entry is not None:
            version = str(entry["version"])

        recipe = self.registry.get(name, version)
        if recipe is None:
            if entry is not None:
                raise ResolveError(
                    f"{Lockfile.FILENAME} pins '{name}' at v{version}, and no "
                    f"recipe provides that version. Restore the recipe, or "
                    f"request the version you want explicitly, or delete "
                    f"{Lockfile.FILENAME} to resolve afresh."
                )
            raise ResolveError(
                f"Package '{name}'"
                + (f" v{version}" if version else "")
                + " not found in registry. "
                f"Available: {[r.name for r in self.registry.list_packages()]}"
            )

        if entry is not None:
            self._check_locked_bytes(name, entry, recipe)

        resolved[name] = recipe
        graph.add_node(name)

        for dep_name in recipe.dependencies:
            self._collect(dep_name, pins, locked, resolved, graph)
            graph.add_edge(name, dep_name)

    @staticmethod
    def _check_locked_bytes(
        name: str, entry: Dict[str, str], recipe: PackageRecipe
    ) -> None:
        """The locked version must still mean the same artifact.

        A recipe can be edited to keep its version and change its URL or
        checksum; the version alone would then reproduce the name, not the
        bytes. The build system is part of what turns those bytes into the
        installed artifact, so it is held to the same rule. Only fields the
        lock recorded are compared.
        """
        for field, attr in Lockfile.CHECKED_FIELDS:
            locked_value = entry.get(field)
            if locked_value and locked_value != getattr(recipe, attr):
                raise ResolveError(
                    f"{Lockfile.FILENAME} pins '{name}' v{recipe.version} with "
                    f"{field} '{locked_value}', but the recipe for that version "
                    f"now has '{getattr(recipe, attr)}'. The lock exists to "
                    f"notice this; if the change is intended, delete "
                    f"{Lockfile.FILENAME} or pin the version explicitly."
                )

    def resolve_single(self, name: str, version: Optional[str] = None) -> PackageRecipe:
        """Resolve a single package recipe from the registry."""
        recipe = self.registry.get(name, version)
        if recipe is None:
            raise ResolveError(f"Package '{name}' not found in registry.")
        return recipe
