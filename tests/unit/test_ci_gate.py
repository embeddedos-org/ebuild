"""The CI workflow must expose one job that summarises all the others.

#87 asks for a required status check on `master`. Branch protection can only
require a check by name, and the names this workflow produces are not usable
for that directly: `test` is a matrix, so it arrives as nine generated names
that change with the matrix, and `release` is skipped on every pull request.

So `ci-gate` exists to be the one name to require. These tests keep it honest
-- specifically, they fail if someone adds a job to the workflow and does not
wire it into the gate, which would otherwise silently create a job that the
required check does not cover.
"""

import yaml
import pytest
from pathlib import Path


WORKFLOWS_DIR = Path(__file__).resolve().parents[2] / ".github" / "workflows"
WORKFLOW = WORKFLOWS_DIR / "ci.yml"

# The name branch protection is pointed at. Changing it silently un-requires
# the check, so it is pinned here rather than merely read.
GATE_ID = "ci-gate"
GATE_NAME = "CI Gate"

#: Every workflow that produces a pull-request status, and the display name a
#: maintainer must require for it. `CI Gate` covers ci.yml and nothing else --
#: cross-workflow `needs` is not something GitHub offers -- so the full
#: required set is this mapping, not one name.
#:
#: A workflow may sit in NO_GATE only with a reason about the workflow itself.
#: "It has no gate yet" is not one: that is the gap this table exists to make
#: visible.
REQUIRED_CHECKS = {
    "ci.yml": GATE_NAME,
}

NO_GATE = {
    "auto-assign.yml":
        "assigns a reviewer; it verifies nothing, so requiring it would block "
        "merges on a housekeeping step",
    "claude-code-review.yml":
        "posts advisory review comments and never fails on content",
    "codeql.yml":
        "already reports a single stable name, `CodeQL`, which should be "
        "required directly rather than wrapped in a gate",
    "book-build.yml":
        "builds documentation; a docs failure should not block a code merge, "
        "and this is a deliberate policy choice rather than an oversight",
    "simulation-test.yml":
        "has a gate job whose body still fails open on part of its `needs` -- "
        "tracked separately; requiring it today would assert more than it "
        "checks",
    "vendor-drift.yml":
        "reports third-party drift for triage and is expected to fail while a "
        "vendored dependency is behind",
}


def _load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _runs_on_pull_request(doc):
    # PyYAML parses a bare `on:` key as the boolean True.
    triggers = doc.get("on", doc.get(True, {}))
    if isinstance(triggers, dict):
        return "pull_request" in triggers
    if isinstance(triggers, list):
        return "pull_request" in triggers
    return triggers == "pull_request"


def _pr_workflows():
    found = {}
    for path in sorted(WORKFLOWS_DIR.glob("*.yml")):
        doc = _load(path)
        if isinstance(doc, dict) and _runs_on_pull_request(doc):
            found[path.name] = doc
    assert found, f"no pull-request workflows found under {WORKFLOWS_DIR}"
    return found


@pytest.fixture(scope="module")
def workflow():
    assert WORKFLOW.is_file(), f"{WORKFLOW} does not exist"
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def jobs(workflow):
    return workflow["jobs"]


def _only_runs_on_tags(job):
    """Is this job gated to tag builds, and therefore skipped on every PR?"""
    condition = str(job.get("if", ""))
    return "refs/tags" in condition


def test_gate_job_exists(jobs):
    assert GATE_ID in jobs, (
        f"no {GATE_ID!r} job; branch protection has no single name to require"
    )


def test_gate_display_name_is_pinned(jobs):
    assert jobs[GATE_ID]["name"] == GATE_NAME, (
        "the gate's display name is what branch protection matches on; "
        "renaming it un-requires the check without failing anything"
    )


def test_gate_runs_even_when_an_earlier_job_fails(jobs):
    condition = str(jobs[GATE_ID].get("if", "")).strip()
    assert condition == "always()", (
        "the gate needs `if: always()`. Without it the gate is skipped when an "
        "earlier job fails, and a skipped required check never reports -- the "
        "pull request waits for a status that never arrives instead of showing "
        "a failure"
    )


def test_gate_covers_every_job_that_runs_on_a_pull_request(jobs):
    expected = {
        name for name, job in jobs.items()
        if name != GATE_ID and not _only_runs_on_tags(job)
    }
    declared = set(jobs[GATE_ID].get("needs", []))

    missing = expected - declared
    assert not missing, (
        f"these jobs run on pull requests but the gate does not wait for them: "
        f"{sorted(missing)}. A job outside the gate is a job the required "
        f"check does not cover."
    )

    unknown = declared - set(jobs)
    assert not unknown, f"the gate needs jobs that do not exist: {sorted(unknown)}"


def test_jobs_left_out_of_the_gate_are_genuinely_tag_only(jobs):
    """Excluding a job from the gate must be justified, not just convenient."""
    declared = set(jobs[GATE_ID].get("needs", []))
    for name, job in jobs.items():
        if name == GATE_ID or name in declared:
            continue
        assert _only_runs_on_tags(job), (
            f"job {name!r} is not in the gate and is not tag-only; either add "
            f"it to `needs` or give it an `if:` that explains why it cannot run "
            f"on a pull request"
        )


def test_every_pull_request_workflow_is_accounted_for():
    """A new workflow must be gated or explicitly excused, not silently added.

    `CI Gate` summarises ci.yml only. Requiring that one name -- which is what
    this PR's own description asked a maintainer to do -- leaves every other
    workflow's checks unrequired, and the rot-guard above cannot see them
    either. This is the test that notices.
    """
    unaccounted = [
        name for name in _pr_workflows()
        if name not in REQUIRED_CHECKS and name not in NO_GATE
    ]
    assert not unaccounted, (
        f"these workflows produce pull-request checks but are neither gated "
        f"nor excused: {sorted(unaccounted)}. Add a gate job and list it in "
        f"REQUIRED_CHECKS, or add it to NO_GATE with the reason."
    )


def test_gated_workflows_really_have_their_gate():
    """Each entry in REQUIRED_CHECKS names a job that exists and is a gate."""
    workflows = _pr_workflows()
    for filename, display in REQUIRED_CHECKS.items():
        assert filename in workflows, (
            f"{filename} is in REQUIRED_CHECKS but produces no pull-request "
            f"checks; the required set names a check that never reports"
        )
        jobs = workflows[filename]["jobs"]
        matching = [j for j in jobs.values() if j.get("name") == display]
        assert matching, (
            f"{filename} has no job displaying as {display!r}, so branch "
            f"protection would wait forever for a status that never arrives"
        )


def test_gate_fails_on_any_non_success_result(jobs):
    """A skipped or cancelled job must fail the gate, not pass it."""
    steps = jobs[GATE_ID]["steps"]
    script = "\n".join(str(s.get("run", "")) for s in steps)

    assert '!= "success"' in script, (
        "the gate must require success specifically. Checking only for "
        "'failure' lets a skipped or cancelled job through, which is the "
        "fail-open shape this repository has been removing elsewhere"
    )
    assert "exit 1" in script, "the gate must actually fail the job"


# ── Check names must be distinct ─────────────────────────────────────────────
#
# Branch protection addresses a check by name, and so does anyone reading the
# checks list on a pull request. A matrix job whose `name:` does not mention
# every dimension produces several check runs sharing one name: this workflow
# reported three runs called "Test (Python 3.10)" until the `os` dimension was
# added to the template. That is not cosmetic -- a required rule naming that
# check cannot say which of the three it means, and a Windows-only failure is
# indistinguishable from the other two legs without opening the run.

import itertools
import re

# `include` and `exclude` shape a matrix but are not dimensions of it, so they
# are not part of the cartesian product.
_NOT_A_DIMENSION = {"include", "exclude"}


def _substitute(name, values):
    for key, value in values.items():
        name = name.replace("${{ matrix.%s }}" % key, str(value))
        name = name.replace("${{matrix.%s}}" % key, str(value))
    return name


def _matches(combo, spec):
    """Does this combination match an `exclude:` entry?"""
    return all(str(combo.get(k)) == str(v) for k, v in spec.items())


def _expanded_names(job_name, matrix, has_explicit_name=True):
    """Every check name this job produces, one per matrix combination.

    `include` and `exclude` are not dimensions of the product, but ignoring
    them entirely left a blind spot: a matrix expressed *entirely* through
    `include:` has no list dimensions at all, so this returned [job_name] --
    one name for however many legs the job really has. release.yml and
    eosim-sanity.yml both use that form today, so the blind spot goes live
    the moment this guard is pointed at them.
    """
    dimensions = {k: v for k, v in matrix.items()
                  if k not in _NOT_A_DIMENSION and isinstance(v, list)}

    combos = []
    if dimensions:
        keys = list(dimensions)
        for values in itertools.product(*(dimensions[k] for k in keys)):
            combos.append(dict(zip(keys, values)))

    # exclude removes combinations rather than being ignored: counting a
    # combination that never runs could report a duplicate that cannot happen.
    for spec in matrix.get("exclude", []) or []:
        if isinstance(spec, dict):
            combos = [c for c in combos if not _matches(c, spec)]

    # include adds legs. An entry that only refines an existing combination
    # does not add a name; one that introduces new values does.
    for spec in matrix.get("include", []) or []:
        if not isinstance(spec, dict):
            continue
        refines = [c for c in combos if _matches(c, {k: v for k, v in spec.items()
                                                    if k in c})]
        if refines:
            for c in refines:
                c.update(spec)
        else:
            combos.append(dict(spec))

    if not combos:
        return [job_name]

    # A job with no `name:` gets GitHub's auto-generated one, which already
    # carries the matrix values -- `smoke (ubuntu-22.04)`, `smoke (macos-
    # latest)`. Modelling that matters: falling back to the bare job id made
    # every leg of an unnamed matrix look like the same check name, so this
    # reported a collision GitHub would never produce and sent the reader
    # looking for a bug that is not there.
    if not has_explicit_name:
        return [f"{job_name} ({', '.join(str(c[k]) for k in sorted(c))})"
                for c in combos]

    return [_substitute(job_name, c) for c in combos]


def _all_check_names(jobs):
    names = []
    for job_id, job in jobs.items():
        job_name = job.get("name", job_id)
        matrix = job.get("strategy", {}).get("matrix", {})
        names.extend(_expanded_names(job_name, matrix or {},
                                     has_explicit_name="name" in job))
    return names


def test_every_check_name_is_unique(jobs):
    names = _all_check_names(jobs)
    duplicates = sorted({n for n in names if names.count(n) > 1})
    assert not duplicates, (
        f"these check names are produced more than once: {duplicates}. "
        f"A name that maps to several check runs cannot be required, and cannot "
        f"be read -- add the missing matrix dimension to the job's `name:`."
    )


def test_check_names_are_unique_across_every_workflow():
    """Branch protection matches check-run names repo-wide, not per file.

    The per-file test above catches a matrix that collides with itself; this
    one catches ci.yml colliding with book-build.yml, and a static-named
    matrix in any workflow (nightly.yml's Full Test Suite was one: three
    Python legs, one name, invisible to the per-file check because the
    fixture reads ci.yml only).
    """
    names = []
    for doc in _pr_workflows().values():
        names.extend(_all_check_names(doc["jobs"]))
    # nightly.yml is schedule-only, so _pr_workflows() misses it -- but its
    # names still land in the same namespace branch protection matches on.
    for path in sorted(WORKFLOWS_DIR.glob("*.yml")):
        doc = _load(path)
        if isinstance(doc, dict) and not _runs_on_pull_request(doc):
            names.extend(_all_check_names(doc.get("jobs", {}) or {}))
    duplicates = sorted({n for n in names if names.count(n) > 1})
    assert not duplicates, (
        f"these check names are produced more than once across the "
        f"repository's workflows: {duplicates}. A name backed by several "
        f"check runs cannot be required, whichever files produce them."
    )


def test_a_matrix_job_names_every_dimension_it_varies(jobs):
    """The rule behind the test above, stated where it will be read.

    An earlier version of this docstring claimed release.yml and
    eosim-sanity.yml used the include:-only form and were the live blind
    spot. Expansion showed neither does -- every matrix job in both names
    every dimension it varies -- while nightly.yml's full-test-suite was the
    one real offender in the repository, now fixed. The repo is clean; the
    cross-file test below is what keeps it that way.
    """
    for job_id, job in jobs.items():
        matrix = job.get("strategy", {}).get("matrix", {}) or {}
        dimensions = [k for k, v in matrix.items()
                      if k not in _NOT_A_DIMENSION
                      and isinstance(v, list) and len(v) > 1]
        if not dimensions:
            continue
        if "name" not in job:
            # No `name:` means GitHub generates one that already carries the
            # matrix values, so the rule is satisfied by the default. The rule
            # is about a `name:` that varies less than the matrix does.
            continue
        name = job["name"]
        missing = [k for k in dimensions
                   if not re.search(r"\$\{\{\s*matrix\.%s\s*\}\}" % re.escape(k), name)]
        assert not missing, (
            f"job {job_id!r} varies {missing} but its `name:` does not mention "
            f"them, so its legs share a check name"
        )
