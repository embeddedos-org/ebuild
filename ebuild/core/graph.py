# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Directed Acyclic Graph for build dependency resolution.

Provides topological sorting, cycle detection, and dependency
queries for build target ordering.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict, List, Set


class CycleError(Exception):
    """Raised when a dependency cycle is detected in the build graph."""


class DependencyGraph:
    """A DAG representing build target dependencies.

    Nodes are target names (strings). An edge from A → B means
    "A depends on B" (B must be built before A).
    """

    def __init__(self) -> None:
        self._adj: Dict[str, Set[str]] = defaultdict(set)
        self._nodes: Set[str] = set()

    def add_node(self, name: str) -> None:
        """Register a build target node."""
        self._nodes.add(name)

    def add_edge(self, dependent: str, dependency: str) -> None:
        """Add a dependency edge: *dependent* depends on *dependency*.

        Both nodes are auto-registered if not already present.
        """
        self._nodes.add(dependent)
        self._nodes.add(dependency)
        self._adj[dependent].add(dependency)

    @property
    def nodes(self) -> Set[str]:
        return set(self._nodes)

    def dependencies_of(self, node: str) -> Set[str]:
        """Return direct dependencies of *node*."""
        return set(self._adj.get(node, set()))

    def dependents_of(self, node: str) -> Set[str]:
        """Return nodes that directly depend on *node*."""
        return {n for n, deps in self._adj.items() if node in deps}

    def all_dependencies(self, node: str) -> Set[str]:
        """Return the transitive closure of dependencies for *node*."""
        visited: Set[str] = set()
        stack = list(self._adj.get(node, set()))
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            stack.extend(self._adj.get(current, set()))
        return visited

    def topological_sort(self) -> List[str]:
        """Return nodes in build order (dependencies first).

        Uses Kahn's algorithm. Raises CycleError if a cycle exists.
        """
        in_degree: Dict[str, int] = {n: 0 for n in self._nodes}
        reverse_adj: Dict[str, Set[str]] = defaultdict(set)

        for dependent, deps in self._adj.items():
            for dep in deps:
                reverse_adj[dep].add(dependent)
                in_degree[dependent] = in_degree.get(dependent, 0) + 1

        queue: deque[str] = deque()
        for node in self._nodes:
            if in_degree.get(node, 0) == 0:
                queue.append(node)

        result: List[str] = []
        while queue:
            node = queue.popleft()
            result.append(node)
            for dependent in sorted(reverse_adj.get(node, set())):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(result) != len(self._nodes):
            built = set(result)
            cycle_members = self._nodes - built
            raise CycleError(
                f"Dependency cycle detected among targets: {', '.join(sorted(cycle_members))}"
            )

        return result

    def validate(self) -> None:
        """Check the graph for cycles. Raises CycleError if found."""
        self.topological_sort()

    def __repr__(self) -> str:
        edges = []
        for node, deps in sorted(self._adj.items()):
            for dep in sorted(deps):
                edges.append(f"{node} -> {dep}")
        return f"DependencyGraph(nodes={sorted(self._nodes)}, edges=[{', '.join(edges)}])"


def build_dependency_graph(targets: list) -> DependencyGraph:
    """Construct a DependencyGraph from a list of TargetConfig objects.

    Args:
        targets: List of TargetConfig with .name and .depends attributes.

    Returns:
        A populated and validated DependencyGraph.
    """
    graph = DependencyGraph()
    for target in targets:
        graph.add_node(target.name)
    for target in targets:
        for dep in target.depends:
            graph.add_edge(target.name, dep)
    graph.validate()
    return graph
