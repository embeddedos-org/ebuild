# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""A missing or unknown cross toolchain is a user error, not a crash.

`resolve_toolchain` raises ToolchainError when `toolchain.target` names an
unknown toolchain or one whose compiler is not on PATH (#171). The `build`,
`configure` and `test` commands did not catch it, so the user got a Python
traceback ending in `ebuild.build.toolchain.ToolchainError` instead of the
one-line reason and exit code 1 that every other configuration error gets.
"""

import os
from unittest import mock

import pytest
import yaml
from click.testing import CliRunner

from ebuild.cli.commands import cli


def _project(root, target, target_type="executable"):
    (root / "main.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")
    (root / "build.yaml").write_text(
        yaml.safe_dump(
            {
                "project": {"name": "demo", "version": "0.1.0"},
                "toolchain": {"target": target},
                "targets": [
                    {"name": "app", "type": target_type, "sources": ["main.c"]}
                ],
            }
        ),
        encoding="utf-8",
    )


def _invoke(monkeypatch, root, *args):
    monkeypatch.chdir(root)
    # An empty PATH guarantees no cross compiler is found on any machine.
    with mock.patch.dict(os.environ, {"PATH": str(root / "no-such-bin")}):
        return CliRunner().invoke(cli, list(args))


@pytest.mark.parametrize(
    "command,target_type",
    [("build", "executable"), ("configure", "executable"), ("test", "test")],
)
@pytest.mark.parametrize(
    "target,reason",
    [
        ("arm-none-eabi", "not found on PATH"),
        ("arm-none-eabii", "unknown toolchain target"),
    ],
)
def test_toolchain_error_is_reported_not_raised(
    tmp_path, monkeypatch, command, target_type, target, reason
):
    _project(tmp_path, target, target_type)
    result = _invoke(monkeypatch, tmp_path, command)

    # Exit 1 through SystemExit, with no exception escaping the command.
    assert result.exception is None or isinstance(result.exception, SystemExit), (
        f"{command} raised {result.exception!r}"
    )
    assert result.exit_code == 1
    assert "Traceback" not in result.output
    assert "Toolchain error:" in result.output
    assert reason in result.output
