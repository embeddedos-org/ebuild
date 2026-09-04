# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""A relative --build-dir must be anchored to the project, not the cwd.

`ebuild build` generates build.ninja with Python, then launches ninja with
``cwd=cfg.source_dir`` so the relative source paths inside it resolve. The
``-f`` argument and the output paths are relative too, so the build directory
has to mean the same thing to both sides.

It did not. Python created and reported it relative to the *process* cwd. The
two bases coincide exactly when the cwd is the project directory -- the
documented golden path -- and diverge as soon as ``--config`` names a project
elsewhere:

  * `build` wrote build.ninja under the cwd, then ninja, running in the
    project directory, could not open it: "ninja: error: loading
    '_build/build.ninja': No such file or directory" -- one line after ebuild
    reported "Generated _build/build.ninja".
  * `configure` reported success, leaving build.ninja where a later build
    would not look for it.

An absolute --build-dir was already unambiguous, which is why it worked.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from ebuild.cli import commands


pytestmark = pytest.mark.needs_yaml


def _make_project(root: Path) -> Path:
    """A minimal ninja-backed project at *root*; returns its build.yaml."""
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src" / "main.c").write_text(
        "int main(void) { return 0; }\n", encoding="utf-8"
    )
    config_path = root / "build.yaml"
    config_path.write_text(textwrap.dedent("""\
        project:
          name: subdir_demo
          version: "1.0.0"

        targets:
          - name: app
            type: executable
            sources: ["src/main.c"]
        """), encoding="utf-8")
    return config_path


@pytest.fixture
def outside_project(tmp_path, monkeypatch):
    """A project in ``<tmp>/myproj`` with the cwd left at ``<tmp>``."""
    project_dir = tmp_path / "myproj"
    config_path = _make_project(project_dir)
    monkeypatch.chdir(tmp_path)
    return SimpleNamespace(cwd=tmp_path, project_dir=project_dir,
                           config_path=config_path)


@pytest.fixture
def record_ninja(monkeypatch):
    """Capture the ninja invocation instead of running a real build."""
    calls = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(SimpleNamespace(cmd=[str(c) for c in cmd],
                                     cwd=kwargs.get("cwd")))
        return subprocess.CompletedProcess(cmd, returncode=0,
                                           stdout=b"", stderr=b"")

    monkeypatch.setattr("ebuild.cli.commands.subprocess.run", fake_run)
    monkeypatch.setattr(commands, "_install_packages", lambda *a, **k: {})
    return calls


# ── build ───────────────────────────────────────────────────


def test_build_from_outside_puts_build_ninja_where_ninja_looks(
    outside_project, record_ninja
):
    """The regression: the generated file must be the one ninja is given."""
    result = CliRunner().invoke(
        commands.cli,
        ["build", "--config", str(outside_project.config_path)],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    assert (outside_project.project_dir / "_build" / "build.ninja").is_file()
    assert not (outside_project.cwd / "_build").exists(), (
        "build directory was created beside the cwd instead of the project"
    )

    assert len(record_ninja) == 1
    invocation = record_ninja[0]
    assert invocation.cwd == str(outside_project.project_dir)
    ninja_file = Path(invocation.cmd[invocation.cmd.index("-f") + 1])
    # Whatever form the path takes, resolving it from ninja's cwd must land
    # on a file that exists -- that is precisely what used to fail.
    resolved = ninja_file if ninja_file.is_absolute() else Path(invocation.cwd) / ninja_file
    assert resolved.is_file(), f"ninja was given {ninja_file}, which does not exist"


def test_build_from_inside_project_is_unchanged(tmp_path, monkeypatch, record_ninja):
    """The golden path must keep producing ``./_build`` exactly as before."""
    _make_project(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(commands.cli, ["build"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    assert (tmp_path / "_build" / "build.ninja").is_file()
    # The path is printed with the platform separator, so asserting the
    # POSIX spelling failed on Windows against "Generated _build\\build.ninja".
    assert f"Generated {os.path.join('_build', 'build.ninja')}" in result.output


def test_absolute_build_dir_is_honoured_verbatim(outside_project, record_ninja, tmp_path):
    out = tmp_path / "elsewhere" / "out"
    result = CliRunner().invoke(
        commands.cli,
        ["build", "--config", str(outside_project.config_path),
         "--build-dir", str(out)],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    assert (out / "build.ninja").is_file()
    assert not (outside_project.project_dir / "_build").exists()


def test_relative_build_dir_with_a_name_is_anchored_to_the_project(
    outside_project, record_ninja
):
    result = CliRunner().invoke(
        commands.cli,
        ["build", "--config", str(outside_project.config_path),
         "--build-dir", "out"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    assert (outside_project.project_dir / "out" / "build.ninja").is_file()
    assert not (outside_project.cwd / "out").exists()


def test_relative_config_path_is_handled(outside_project, record_ninja):
    """A *relative* --config must work too.

    Anchoring the build directory to the project is not sufficient on its own:
    ``--config myproj/build.yaml`` makes cfg.source_dir relative, so a
    project-relative build directory is ``myproj/_build`` -- and ninja, which
    runs in ``myproj``, would resolve that to ``myproj/myproj/_build``.
    Resolving to an absolute path is what removes the second interpretation.
    """
    result = CliRunner().invoke(
        commands.cli, ["build", "--config", "myproj/build.yaml"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    assert (outside_project.project_dir / "_build" / "build.ninja").is_file()

    invocation = record_ninja[-1]
    ninja_file = Path(invocation.cmd[invocation.cmd.index("-f") + 1])
    assert ninja_file.is_absolute(), (
        "a relative -f is re-interpreted against ninja's cwd"
    )
    assert ninja_file.is_file()


def test_two_projects_built_from_one_cwd_do_not_share_a_build_dir(
    tmp_path, monkeypatch, record_ninja
):
    """Each project gets its own tree, so neither clobbers the other."""
    for name in ("alpha", "beta"):
        _make_project(tmp_path / name)
    monkeypatch.chdir(tmp_path)

    for name in ("alpha", "beta"):
        result = CliRunner().invoke(
            commands.cli, ["build", "--config", f"{name}/build.yaml"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output

    assert (tmp_path / "alpha" / "_build" / "build.ninja").is_file()
    assert (tmp_path / "beta" / "_build" / "build.ninja").is_file()
    assert not (tmp_path / "_build").exists()


# ── configure ───────────────────────────────────────────────


def test_configure_and_build_from_outside_agree_on_the_build_dir(
    outside_project, record_ninja
):
    """`configure` then `build` must target the same directory.

    `configure` used to report success having written build.ninja beside the
    cwd, where the `build` that followed did not look.
    """
    configured = CliRunner().invoke(
        commands.cli,
        ["configure", "--config", str(outside_project.config_path)],
        catch_exceptions=False,
    )
    assert configured.exit_code == 0, configured.output

    generated = outside_project.project_dir / "_build" / "build.ninja"
    assert generated.is_file()
    assert not (outside_project.cwd / "_build").exists()

    built = CliRunner().invoke(
        commands.cli,
        ["build", "--config", str(outside_project.config_path)],
        catch_exceptions=False,
    )
    assert built.exit_code == 0, built.output

    invocation = record_ninja[-1]
    ninja_file = Path(invocation.cmd[invocation.cmd.index("-f") + 1])
    resolved = (ninja_file if ninja_file.is_absolute()
                else Path(invocation.cwd) / ninja_file)
    assert resolved.resolve() == generated.resolve()


# ── end to end, with a real compiler ────────────────────────


@pytest.mark.skipif(
    shutil.which("gcc") is None,
    reason="needs a working gcc to link the executable",
)
def test_end_to_end_build_from_outside_produces_the_binary(tmp_path, monkeypatch):
    """No stubs: the real ninja run must produce the real executable."""
    project_dir = tmp_path / "myproj"
    config_path = _make_project(project_dir)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        commands.cli, ["build", "--config", str(config_path)],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    # gcc appends .exe on Windows; the backend now names the edge to match.
    exe = "app.exe" if os.name == "nt" else "app"
    assert (project_dir / "_build" / exe).is_file()
