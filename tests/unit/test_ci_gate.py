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
