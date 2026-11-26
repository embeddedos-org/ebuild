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


def _report(
    callback: Callable[[str], None] | None,
    node: str,
    problems: List[str],
) -> None:
    """Invoke a reporting callback without letting it hijack the failure.

    ``on_skip`` and ``on_failure`` only report. If one raises, the caller
    must still see the build's own exception, and the remaining nodes must
    still be reported -- otherwise a bug in a logging callback hides which
    package actually failed, and replaces it with a traceback from the
    logger.

    The callback's error is not swallowed silently: it is collected and
    attached to the exception that is re-raised (see _attach_problems).
    """
    if callback is None:
        return
    try:
        callback(node)
    except Exception as exc:  # noqa: BLE001 - reported, never re-raised here
        problems.append(f"{node}: {type(exc).__name__}: {exc}")


def _attach_problems(exc: BaseException, problems: List[str]) -> None:
    """Record reporting-callback failures on the exception being raised.

    ``add_note`` is Python 3.11+; this package supports 3.8, so older
    interpreters simply carry the original exception unchanged rather than
    losing it to a note that cannot be attached.
    """
    if not problems:
        return
    add_note = getattr(exc, "add_note", None)
    if add_note is None:
        return
    add_note(
        "scheduler reporting callback failed for " + "; ".join(problems)
    )


def run_graph(
    graph: DependencyGraph,
    task: Callable[[str], T],
    jobs: int = 1,
    on_skip: Callable[[str, BaseException], None] | None = None,
    on_failure: Callable[[str, BaseException], None] | None = None,
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
        on_failure: Optional callback invoked as ``(node, exc)`` for each node
            that ran and raised. Only one exception can be re-raised, so
            without this the second and later failures of a parallel run are
            not reported anywhere.

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
                # Same contract as the parallel path: the node that ran and
                # raised is reported through on_failure before the skips.
                problems: List[str] = []
                if on_failure is not None:
                    _report(lambda n: on_failure(n, exc), node, problems)
                if on_skip is not None:
                    for skipped in order[index + 1:]:
                        _report(lambda n: on_skip(n, exc), skipped, problems)
                _attach_problems(exc, problems)
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
    # Every node that ran and raised, with its exception. Not just the one
    # whose error is re-raised: none of them were skipped, and only one of
    # them can be raised, so the rest reach the caller through on_failure.
    failed: Dict[str, BaseException] = {}
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
                        failed[node] = exc
                        if failure is None:
                            failure = exc
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
                    failed[node] = exc
                    if failure is None:
                        failure = exc
            else:
                results[node] = value

    if failure is not None:
        problems = []
        if on_failure is not None:
            # In graph order, so a run reports the same way every time.
            for node in order:
                if node in failed:
                    _report(
                        lambda n: on_failure(n, failed[n]), node, problems
                    )
        if on_skip is not None:
            for node in order:
                if node not in results and node not in failed:
                    _report(lambda n: on_skip(n, failure), node, problems)
        _attach_problems(failure, problems)
        raise failure

    if len(results) != len(order):
        stalled = sorted(set(order) - set(results))
        raise SchedulerError(
            f"Scheduler stalled with unbuilt targets: {', '.join(stalled)}"
        )

    return results
