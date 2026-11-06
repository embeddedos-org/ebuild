# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Unit tests for the dependency-graph scheduler.

These import only ebuild.core.{graph,scheduler}, so they run without
yaml/click. Concurrency is proven with a threading.Barrier that times out if
the scheduler serialised the work, rather than with sleeps.
"""

import threading
import time

import pytest

from ebuild.core.graph import CycleError, DependencyGraph
from ebuild.core.scheduler import SchedulerError, run_graph


def _graph(edges, extra_nodes=()):
    g = DependencyGraph()
    for node in extra_nodes:
        g.add_node(node)
    for dependent, dependency in edges:
        g.add_edge(dependent, dependency)
    return g


class TestOrdering:
    def test_sequential_matches_topological_order(self):
        g = _graph([("app", "lib"), ("lib", "base")])
        seen = []
        results = run_graph(g, lambda n: seen.append(n) or n, jobs=1)

        assert seen == g.topological_sort()
        assert seen == ["base", "lib", "app"]
        assert results == {"base": "base", "lib": "lib", "app": "app"}

    @pytest.mark.parametrize("jobs", [1, 2, 4, 8])
    def test_dependencies_complete_before_dependents_start(self, jobs):
        g = _graph(
            [("app", "left"), ("app", "right"), ("left", "base"), ("right", "base")],
            extra_nodes=["solo"],
        )

        lock = threading.Lock()
        finished = set()
        violations = []

        def task(node):
            with lock:
                missing = g.dependencies_of(node) - finished
                if missing:
                    violations.append((node, sorted(missing)))
            time.sleep(0.01)
            with lock:
                finished.add(node)
            return node

        run_graph(g, task, jobs=jobs)

        assert violations == []
        assert finished == {"base", "left", "right", "app", "solo"}

    def test_every_node_runs_exactly_once(self):
        g = _graph([("b", "a"), ("c", "a"), ("d", "b"), ("d", "c")])
        counts = {}
        lock = threading.Lock()

        def task(node):
            with lock:
                counts[node] = counts.get(node, 0) + 1
            return node

        run_graph(g, task, jobs=4)
        assert counts == {"a": 1, "b": 1, "c": 1, "d": 1}


class TestConcurrency:
    def test_independent_nodes_run_in_parallel(self):
        g = DependencyGraph()
        g.add_node("alpha")
        g.add_node("beta")

        barrier = threading.Barrier(2, timeout=5)

        def task(node):
            barrier.wait()
            return node

        results = run_graph(g, task, jobs=2)
        assert set(results) == {"alpha", "beta"}

    def test_sequential_mode_does_not_run_in_parallel(self):
        g = DependencyGraph()
        g.add_node("alpha")
        g.add_node("beta")

        barrier = threading.Barrier(2, timeout=0.5)

        def task(node):
            try:
                barrier.wait()
            except threading.BrokenBarrierError:
                return "alone"
            return "concurrent"

        results = run_graph(g, task, jobs=1)
        assert set(results.values()) == {"alone"}

    def test_concurrency_never_exceeds_jobs(self):
        g = DependencyGraph()
        for i in range(8):
            g.add_node(f"n{i}")

        lock = threading.Lock()
        current = 0
        peak = 0

        def task(node):
            nonlocal current, peak
            with lock:
                current += 1
                peak = max(peak, current)
            time.sleep(0.02)
            with lock:
                current -= 1
            return node

        run_graph(g, task, jobs=3)
        assert peak <= 3
        assert peak > 1

    def test_dependency_chain_cannot_parallelise(self):
        g = _graph([("c", "b"), ("b", "a")])

        lock = threading.Lock()
        current = 0
        peak = 0

        def task(node):
            nonlocal current, peak
            with lock:
                current += 1
                peak = max(peak, current)
            time.sleep(0.01)
            with lock:
                current -= 1
            return node

        run_graph(g, task, jobs=8)
        assert peak == 1


class TestFailures:
    @pytest.mark.parametrize("jobs", [1, 4])
    def test_exception_is_reraised_unchanged(self, jobs):
        g = _graph([("app", "lib")])

        class BuildBoom(RuntimeError):
            pass

        def task(node):
            if node == "lib":
                raise BuildBoom("lib failed to compile")
            return node

        with pytest.raises(BuildBoom, match="lib failed to compile"):
            run_graph(g, task, jobs=jobs)

    @pytest.mark.parametrize("jobs", [1, 4])
    def test_dependents_of_a_failure_do_not_run(self, jobs):
        g = _graph([("app", "lib"), ("shipped", "app")])
        ran = []
        lock = threading.Lock()

        def task(node):
            if node == "lib":
                raise RuntimeError("boom")
            with lock:
                ran.append(node)
            return node

        with pytest.raises(RuntimeError):
            run_graph(g, task, jobs=jobs)

        assert "app" not in ran
        assert "shipped" not in ran

    @pytest.mark.parametrize("jobs", [1, 2])
    def test_on_skip_reports_unbuilt_nodes(self, jobs):
        g = _graph([("app", "lib"), ("shipped", "app")])
        skipped = []

        def task(node):
            if node == "lib":
                raise RuntimeError("boom")
            return node

        with pytest.raises(RuntimeError):
            run_graph(
                g,
                task,
                jobs=jobs,
                on_skip=lambda name, cause: skipped.append(name),
            )

        assert set(skipped) == {"app", "shipped"}

    def test_first_failure_is_the_one_raised(self):
        g = DependencyGraph()
        g.add_node("x")
        g.add_node("y")

        def task(node):
            raise RuntimeError(f"{node} failed")

        with pytest.raises(RuntimeError, match=r"(x|y) failed"):
            run_graph(g, task, jobs=2)


class TestValidation:
    def test_cycle_is_rejected_before_anything_runs(self):
        g = _graph([("a", "b"), ("b", "a")])
        ran = []

        with pytest.raises(CycleError):
            run_graph(g, lambda n: ran.append(n), jobs=4)

        assert ran == []

    def test_empty_graph_is_a_noop(self):
        assert run_graph(DependencyGraph(), lambda n: n, jobs=4) == {}

    def test_single_node(self):
        g = DependencyGraph()
        g.add_node("only")
        assert run_graph(g, lambda n: n.upper(), jobs=4) == {"only": "ONLY"}


class TestDeterminism:
    def test_sequential_dispatch_order_is_stable(self):
        g = _graph([("app", "left"), ("app", "right"), ("left", "base"), ("right", "base")])
        runs = []
        for _ in range(5):
            seen = []
            run_graph(g, lambda n: seen.append(n) or n, jobs=1)
            runs.append(seen)
        assert all(r == runs[0] for r in runs)

    def test_parallel_dispatch_follows_topological_order(self, monkeypatch):
        """Nodes freed by one completion are submitted in topological order."""
        import ebuild.core.scheduler as scheduler

        submitted = []

        class RecordingPool(scheduler.ThreadPoolExecutor):
            def submit(self, fn, node):
                submitted.append(node)
                return super().submit(fn, node)

        monkeypatch.setattr(scheduler, "ThreadPoolExecutor", RecordingPool)
        mids = [f"m{i}" for i in range(6)]
        g = _graph([(m, "root") for m in mids] + [("sink", m) for m in mids])

        run_graph(g, lambda n: n, jobs=2)

        assert submitted == g.topological_sort()

    def test_results_complete_regardless_of_job_count(self):
        g = _graph([("d", "b"), ("d", "c"), ("b", "a"), ("c", "a")])
        expected = {"a": "a", "b": "b", "c": "c", "d": "d"}
        for jobs in (1, 2, 3, 16):
            assert run_graph(g, lambda n: n, jobs=jobs) == expected


def test_scheduler_error_is_exported():
    assert issubclass(SchedulerError, Exception)
