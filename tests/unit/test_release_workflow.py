# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""The release workflow's triggers and staging, asserted structurally.

This file exists because `yaml.safe_load(...)` succeeding was mistaken for
verification. A `workflow_dispatch:` key inserted between two tag patterns
parses perfectly well -- and turns the second pattern into its value:

    on:
      push:
        tags:
          - "v*.*.*"
      workflow_dispatch:
          - "v*.*.*-*"      # now workflow_dispatch's value, not a tag

    {"push": {"tags": ["v*.*.*"]}, "workflow_dispatch": ["v*.*.*-*"]}

Pre-release tags stop triggering the workflow, and `workflow_dispatch` as a
sequence is not valid in GitHub's schema at all. Neither shows up as a parse
error. The lesson generalises: assert the shape you meant, not that the file
is loadable.
"""

import re
import shlex
from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "release.yml"

#: Tag patterns release.yml must fire on. -rc.N is the org's recognised
#: pre-release suffix (.github/STANDARDS.md) and the release job handles it
#: explicitly with --prerelease, so a tag pattern that does not match it makes
#: that code unreachable.
EXPECTED_TAGS = ["v*.*.*", "v*.*.*-*"]

#: Jobs that publish. A workflow_dispatch run must never reach these.
PUBLISHING_JOBS = ("pypi", "release")


def _executable_lines(script):
    """Shell lines with comments stripped.

    A comment explaining why a `|| true` was removed must not read as a
    `|| true`. Splitting on an unquoted `#` is enough here and does not
    mistake a `#` inside a string for the start of a comment.
    """
    out = []
    for raw in str(script).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            lexer = shlex.shlex(raw, posix=True, punctuation_chars=True)
            lexer.whitespace_split = True
            list(lexer)          # raises on an unbalanced quote
        except ValueError:
            pass
        code = re.split(r'(?<![\\"\'])#', raw, maxsplit=1)[0]
        if code.strip():
            out.append(code)
    return out


@pytest.fixture(scope="module")
def workflow():
    assert WORKFLOW.is_file(), f"{WORKFLOW} does not exist"
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def triggers(workflow):
    # PyYAML parses a bare `on:` key as the boolean True.
    return workflow.get("on", workflow.get(True))


def test_push_tags_are_exactly_the_patterns_we_mean(triggers):
    assert isinstance(triggers, dict), "`on:` must be a mapping"
    assert "push" in triggers, "release.yml must trigger on a tag push"
    tags = triggers["push"]["tags"]
    assert tags == EXPECTED_TAGS, (
        f"push.tags is {tags!r}, expected {EXPECTED_TAGS!r}. A pattern that "
        f"goes missing here does not fail anything -- it just stops releasing."
    )


def test_workflow_dispatch_is_a_null_key_not_a_value(triggers):
    """`workflow_dispatch:` takes null or a mapping, never a sequence."""
    assert "workflow_dispatch" in triggers, (
        "without workflow_dispatch the first execution of any change to this "
        "workflow is a real release"
    )
    value = triggers["workflow_dispatch"]
    assert value is None or isinstance(value, dict), (
        f"workflow_dispatch is {value!r}. A sequence here is invalid in "
        f"GitHub's schema, and it means the line above it was absorbed as its "
        f"value rather than being a trigger of its own."
    )


def test_a_manual_run_cannot_publish(workflow):
    """workflow_dispatch is for exercising the build, not for releasing."""
    for job in PUBLISHING_JOBS:
        condition = str(workflow["jobs"][job].get("if", ""))
        assert "github.event_name == 'push'" in condition, (
            f"job {job!r} publishes but is not gated on a tag push, so a "
            f"workflow_dispatch run would release"
        )


def test_artifact_staging_cannot_publish_an_empty_dist(workflow):
    """A release that ships less than it was asked to must fail, not publish.

    `mv wheelhouse/*.whl dist/ 2>/dev/null || true` swallowed the case where no
    wheel had been produced at all, and the publish step ran anyway.
    """
    steps = workflow["jobs"]["pypi"]["steps"]
    stage = [s for s in steps if s.get("name") == "Stage dist"]
    assert stage, "the pypi job has no 'Stage dist' step"
    code = "\n".join(_executable_lines(stage[0]["run"]))

    assert "|| true" not in code, (
        "staging must not swallow its own failure: publishing a release with "
        "no wheels is worse than failing the job"
    )
    assert "exit 1" in code, (
        "staging must fail explicitly when no wheel was produced"
    )


def test_no_build_or_publish_step_swallows_its_exit_status(workflow):
    """`|| true` on a step that produces a release artefact.

    .ai/reviewer.md names this shape directly. Reporting steps may still use
    it -- they claim no verdict -- so this checks the jobs that build or ship.
    """
    offenders = []
    for job_id in ("validate", "cibuildwheel", "cross-compile", "pypi"):
        for step in workflow["jobs"][job_id].get("steps", []):
            for line in _executable_lines(step.get("run", "")):
                if re.search(r"\|\|\s*true\s*$", line):
                    offenders.append(
                        f"{job_id}/{step.get('name', '?')}: {line.strip()}"
                    )
    assert not offenders, (
        "these steps discard their exit status:\n  " + "\n  ".join(offenders)
    )
