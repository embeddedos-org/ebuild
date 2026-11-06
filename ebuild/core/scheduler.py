# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Concurrent execution of a dependency graph.

``topological_sort`` yields a single sequence, so building in that order
serialises work that has no relationship. ``run_graph`` keeps the same
guarantee — a node starts only once its dependencies have finished — while
running independent nodes at the same time.

The schedule is dynamic rather than level-by-level: a node becomes eligible as
soon as its own dependencies complete, instead of waiting for every other node
at the same depth.
"""

from __future__ import annotations

import threading
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from typing import Callable, Dict, List, Set, TypeVar

from ebuild.core.graph import DependencyGraph

T = TypeVar("T")


class SchedulerError(Exception):
    """Raised when the graph cannot be scheduled to completion."""


def run_graph(
    graph: DependencyGraph,
    task: Callable[[str], T],
    jobs: int = 1,
    on_skip: Callable[[str, BaseException], None] | None = None,
) -> Dict[str, T]:
    """Run *task* for every node in *graph*, honouring dependency order.

    Args:
        graph: The dependency graph. Validated for cycles before anything runs.
        task: Called with a node name; must be safe to call from a worker
            thread. Its return value is collected into the result mapping.
        jobs: Maximum nodes to run at once. ``1`` runs everything sequentially
            in ``topological_sort`` order.
        on_skip: Optional callback invoked as ``(node, cause)`` for each node
            that never ran because a dependency failed.

    Returns:
        Mapping of node name to whatever *task* returned. Nodes that did not
        run are absent.

    Raises:
        CycleError: If the graph contains a cycle.
        Exception: The first exception raised by *task*, re-raised unchanged.
    """
    order = graph.topological_sort()

    if jobs <= 1:
        sequential: Dict[str, T] = {}
        for index, node in enumerate(order):
            try:
                sequential[node] = task(node)
            except BaseException as exc:          # noqa: BLE001 - re-raised
                if on_skip is not None:
                    for skipped in order[index + 1:]:
                        on_skip(skipped, exc)
                raise
        return sequential

    # Restricted to nodes in `order` so stray edges cannot deadlock us.
    known: Set[str] = set(order)
    pending: Dict[str, Set[str]] = {
        node: {d for d in graph.dependencies_of(node) if d in known} for node in order
    }
    dependents: Dict[str, List[str]] = {node: [] for node in order}
    for node in order:
        for dep in pending[node]:
            dependents[dep].append(node)

    # Seeding and refilling from `order` keeps dispatch deterministic.
    # `order.index` would be a linear scan per freed node; a position map makes
    # the same ordering O(1) per lookup.
    position: Dict[str, int] = {node: i for i, node in enumerate(order)}
    ready: List[str] = [n for n in order if not pending[n]]
    results: Dict[str, T] = {}
    failure: BaseException | None = None
    failed_node: str | None = None
    lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        running: Dict[Future, str] = {}

        while (ready or running) and failure is None:
            while ready and len(running) < jobs:
                node = ready.pop(0)
                running[pool.submit(task, node)] = node

            if not running:
                break

            done, _ = wait(running, return_when=FIRST_COMPLETED)

            for fut in done:
                node = running.pop(fut)
                try:
                    value = fut.result()
                except BaseException as exc:      # noqa: BLE001 - re-raised below
                    with lock:
                        if failure is None:
                            failure, failed_node = exc, node
                    continue

                results[node] = value

                freed = []
                for dependent in dependents[node]:
                    pending[dependent].discard(node)
                    if not pending[dependent]:
                        freed.append(dependent)
                ready.extend(sorted(freed, key=position.__getitem__))

        # A failure stops new work; already-running nodes finish rather than
        # being abandoned mid-build.
        for fut, node in running.items():
            try:
                value = fut.result()
            except BaseException as exc:          # noqa: BLE001
                with lock:
                    if failure is None:
                        failure, failed_node = exc, node
            else:
                results[node] = value

    if failure is not None:
        if on_skip is not None:
            for node in order:
                if node not in results and node != failed_node:
                    on_skip(node, failure)
        raise failure

    if len(results) != len(order):
        stalled = sorted(set(order) - set(results))
        raise SchedulerError(
            f"Scheduler stalled with unbuilt targets: {', '.join(stalled)}"
        )

    return results
