# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Every ebuild command shown in the docs must exist.

§8 lists "consistent documentation generated from tested examples" as an MLP
requirement. Generating prose from examples is a large change; verifying that
the examples we already publish actually run is the part that stops the docs
lying, and it is cheap.

The failure this prevents is real and has bitten this organisation. EoStudio
carried this line for the tool it is a front end for:

    f"ebuild --platform {platform} --config board.yaml {source_dir}"

ebuild has no top-level --platform or --config. The string was stored in a dict
and never executed, so nothing found out it could not work. A published command
nobody runs decays the same way, and a developer following the README is the one
who discovers it.

Only fenced code blocks are read. Prose says things like "ebuild is a unified
build system", and treating "is" as a subcommand would make this fail for no
reason.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS = ["README.md", "demo.md"]

#: A shell line invoking ebuild, e.g. "ebuild configure --board stm32f4" or
#: "$ ebuild build". Captures the subcommand only.
_INVOCATION = re.compile(r"^\s*(?:\$\s*)?ebuild\s+([a-z][a-z0-9-]*)", re.M)

#: Long options are not subcommands.
_NOT_A_SUBCOMMAND = {"--help", "--version"}


def _code_blocks(text: str):
    """The contents of every fenced code block."""
    return re.findall(r"```[a-zA-Z]*\n(.*?)```", text, re.S)


def _documented_commands():
    """(subcommand, source file) for every ebuild invocation in the docs."""
    found = []
    for name in DOCS:
        path = REPO_ROOT / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for block in _code_blocks(text):
            for sub in _INVOCATION.findall(block):
                if sub not in _NOT_A_SUBCOMMAND:
                    found.append((sub, name))
    return found


def _real_commands():
    """Every subcommand the CLI actually registers."""
    from ebuild.cli.commands import cli
    return set(cli.commands)


def test_the_docs_actually_show_commands():
    # A guard on the guard: if the extraction silently stopped matching, every
    # assertion below would pass vacuously and the check would be worthless.
    documented = _documented_commands()
    assert len(documented) >= 5, (
        "expected several ebuild invocations in the docs, found %d — the "
        "extraction is probably broken rather than the docs being empty"
        % len(documented))


@pytest.mark.parametrize("subcommand,source", sorted(set(_documented_commands())))
def test_a_documented_command_exists(subcommand, source):
    real = _real_commands()
    assert subcommand in real, (
        "%s documents `ebuild %s`, which the CLI does not provide. "
        "Available: %s" % (source, subcommand, ", ".join(sorted(real))))


def test_every_golden_path_step_is_a_real_command():
    # §7.1 names these eight verbatim. They are asserted directly rather than
    # via the docs so the golden path cannot be quietly broken by editing the
    # README instead of the CLI.
    real = _real_commands()
    for step in ("setup", "new", "configure", "build",
                 "test", "flash", "monitor"):
        assert step in real, "golden path step `ebuild %s` is missing" % step
