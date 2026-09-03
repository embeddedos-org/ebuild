# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""The MVP golden path must stay walkable.

The MVP is defined as a developer running eight commands in order and
reaching a verified first firmware run. Each of those commands has to exist,
and the scaffolding has to produce a project they succeed on. These are the
regression guards for the steps that were missing or broken.
"""

import re
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from ebuild.cli.commands import (
    _board_config,
    _cached_repo_libraries,
    _record_board_selection,
    _resolve_test_runner,
    _selected_board,
    cli,
)
from ebuild.core.config import TargetConfig


GOLDEN_PATH_COMMANDS = [
    "setup", "new", "configure", "build", "test", "flash", "monitor",
]


@pytest.mark.ebuild
class TestGoldenPathCommandsExist:
    """Every command the MVP walk names must be registered on the CLI."""

    @pytest.mark.parametrize("name", GOLDEN_PATH_COMMANDS)
    def test_command_is_registered(self, name):
        assert name in cli.commands, (
            f"'ebuild {name}' is step of the MVP golden path but is not a "
            f"registered command"
        )

    @pytest.mark.parametrize("name", GOLDEN_PATH_COMMANDS)
    def test_command_help_runs(self, name):
        result = CliRunner().invoke(cli, [name, "--help"])
        assert result.exit_code == 0, result.output

    def test_configure_accepts_board(self):
        """`ebuild configure --board <board>` is the documented step four."""
        result = CliRunner().invoke(cli, ["configure", "--help"])
        assert result.exit_code == 0
        assert "--board" in result.output


@pytest.mark.ebuild
class TestBoardSelection:
    """--board has to outlive the configure process: the next step is a
    bare `ebuild build`, which can only find the board by reading it back."""

    def test_board_round_trips_through_eos_yaml(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        Path("eos.yaml").write_text("system:\n  kind: baremetal\n", encoding="utf-8")

        _record_board_selection("stm32f4", _SilentLog())

        assert _selected_board() == "stm32f4"
        data = yaml.safe_load(Path("eos.yaml").read_text(encoding="utf-8"))
        assert data["system"]["board"] == "stm32f4"
        # Recording a board must not discard the rest of the file.
        assert data["system"]["kind"] == "baremetal"

    def test_board_defaults_when_unset(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert _selected_board() == "generic"

    def test_board_without_a_project_is_an_error(self, tmp_path, monkeypatch):
        """Refuse rather than write an eos.yaml into whatever directory the
        developer happened to be standing in."""
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit):
            _record_board_selection("stm32f4", _SilentLog())
        assert not Path("eos.yaml").exists()


@pytest.mark.ebuild
class TestProjectBoardConfig:
    """A family spans several densities -- an STM32F407 has 1 MB of flash and
    an STM32F401 has 256 KB -- so a project that states its own numbers must
    not be measured against the reference part for its family."""

    def test_no_board_yaml_is_not_an_error(self, tmp_path, monkeypatch):
        """Most projects ship none, and the reference table covers them."""
        monkeypatch.chdir(tmp_path)
        assert _board_config() is None

    def test_the_project_s_own_numbers_are_read_back(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        Path("board.yaml").write_text(
            yaml.safe_dump({"memory": {"flash": "256K", "ram": "64K"}}),
            encoding="utf-8")
        assert _board_config() == {"memory": {"flash": "256K", "ram": "64K"}}

    def test_unparseable_yaml_falls_back_instead_of_failing_the_build(
            self, tmp_path, monkeypatch):
        """The footprint report is a convenience. Failing a build that linked
        over a malformed board.yaml would be worse than the silence it
        replaces, so this degrades to the reference table."""
        monkeypatch.chdir(tmp_path)
        Path("board.yaml").write_text("memory: {flash: [unclosed\n",
                                      encoding="utf-8")
        assert _board_config() is None

    def test_a_yaml_document_that_is_not_a_mapping_is_ignored(
            self, tmp_path, monkeypatch):
        """`board_capacity` indexes into it, so a list or a bare string would
        raise out of a build that had already succeeded."""
        monkeypatch.chdir(tmp_path)
        Path("board.yaml").write_text("- stm32f4\n", encoding="utf-8")
        assert _board_config() is None

    def test_an_empty_board_yaml_is_ignored(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        Path("board.yaml").write_text("", encoding="utf-8")
        assert _board_config() is None


@pytest.mark.ebuild
class TestTestTargetType:
    """`test` is a distinct target type so `ebuild test` knows which binaries
    to run without pattern-matching target names."""

    def test_test_type_is_valid(self):
        TargetConfig(name="t", target_type="test", sources=["a.c"]).validate()

    def test_unknown_type_still_rejected(self):
        from ebuild.core.config import ConfigError
        with pytest.raises(ConfigError):
            TargetConfig(name="t", target_type="fixture", sources=["a.c"]).validate()

    def test_test_target_links_like_an_executable(self, tmp_path):
        """A test target must produce a runnable binary, not an archive."""
        from types import SimpleNamespace
        from ebuild.build.ninja_backend import NinjaBackend
        from ebuild.core.config import ProjectConfig

        cfg = ProjectConfig(
            name="p", version="1", source_dir=tmp_path,
            targets=[TargetConfig(name="t_smoke", target_type="test",
                                  sources=["t.c"])],
        )
        NinjaBackend(cfg, tmp_path / "b",
                     SimpleNamespace(cc="cc", cxx="c++", ar="ar")).generate()
        ninja = (tmp_path / "b" / "build.ninja").read_text(encoding="utf-8")

        # Split on the first *unescaped* colon: that is the one separating
        # outputs from the rule name. A plain l.split(":")[0] picks the drive
        # letter apart from the rest on Windows, so the .o filter never matched
        # and this selected the compile edge instead of the link edge.
        def outputs(line):
            return re.split(r"(?<!\$):", line, maxsplit=1)[0]

        edge = next(l for l in ninja.splitlines()
                    if l.startswith("build ") and "t_smoke" in l
                    and ".o" not in outputs(l))
        assert ": link " in edge
        assert ": ar_rule" not in edge

    def test_native_runner_asks_ninja_for_the_linked_binary(self, tmp_path, monkeypatch):
        """`ebuild test` must name the same output NinjaBackend linked.

        On Windows the edge is ``t_smoke.exe`` because gcc appends ``.exe``.
        Asking ninja to build ``t_smoke`` is an unknown target, and looking
        for the unsuffixed path then reports "built, but no binary".

        ``_exe_suffix()`` is forced to ``.exe`` rather than switching on
        ``sys.platform``, so this exercises the Windows path — and fails
        against the pre-fix code — on any host the suite runs on.
        """
        from types import SimpleNamespace

        from ebuild.build import ninja_backend
        from ebuild.build.ninja_backend import NinjaBackend
        from ebuild.cli import commands
        from ebuild.core.config import ProjectConfig

        monkeypatch.setattr(ninja_backend, "_exe_suffix", lambda: ".exe")

        cfg = ProjectConfig(
            name="p", version="1", source_dir=tmp_path,
            targets=[TargetConfig(name="t_smoke", target_type="test",
                                  sources=["t.c"])],
        )
        build = tmp_path / "b"
        NinjaBackend(cfg, build,
                     SimpleNamespace(cc="cc", cxx="c++", ar="ar")).generate()

        expected = build / "t_smoke.exe"
        expected.write_bytes(b"")

        monkeypatch.setattr(commands, "_configure_ninja_backend",
                            lambda *a, **k: None)

        runs = []

        def fake_run(argv, *a, **k):
            runs.append([str(x) for x in argv])
            return SimpleNamespace(returncode=0)

        monkeypatch.setattr(commands.subprocess, "run", fake_run)

        commands._run_native_tests(
            cfg, list(cfg.targets), build, _SilentLog(), None)

        assert runs, "expected ninja to be invoked"
        assert str(expected) in runs[0], runs[0]


@pytest.mark.ebuild
class TestExternalTestRunners:
    """Projects that already have a runner keep using it."""

    def test_ctest_wins_when_a_cmake_test_registry_exists(self, tmp_path):
        build = tmp_path / "b"
        build.mkdir()
        (build / "CTestTestfile.cmake").touch()
        name, argv, cwd = _resolve_test_runner(tmp_path, build, None)
        assert name == "ctest"
        assert "--output-on-failure" in argv

    def test_filter_is_passed_through(self, tmp_path):
        build = tmp_path / "b"
        build.mkdir()
        (build / "CTestTestfile.cmake").touch()
        _, argv, _ = _resolve_test_runner(tmp_path, build, "kernel")
        assert argv[-2:] == ["-R", "kernel"]

    def test_make_test_requires_an_actual_test_target(self, tmp_path):
        """A Makefile with no `test:` rule is not a test runner; claiming it
        is would make `ebuild test` report success for a project with no
        tests at all."""
        (tmp_path / "Makefile").write_text("all:\n\techo hi\n", encoding="utf-8")
        assert _resolve_test_runner(tmp_path, tmp_path / "b", None) is None

    def test_make_test_is_used_when_declared(self, tmp_path):
        (tmp_path / "Makefile").write_text("test:\n\techo ok\n", encoding="utf-8")
        name, argv, _ = _resolve_test_runner(tmp_path, tmp_path / "b", None)
        assert name == "make test"

    def test_no_runner_for_a_bare_directory(self, tmp_path):
        assert _resolve_test_runner(tmp_path, tmp_path / "b", None) is None


@pytest.mark.ebuild
class TestCachedRepoLibraries:
    """Headers alone leave the developer at an undefined-reference wall, so a
    cached repo has to offer libraries too -- and must degrade quietly when
    it cannot."""

    def test_non_cmake_repo_yields_nothing(self, tmp_path):
        assert _cached_repo_libraries(tmp_path) == ([], [])

    def test_prebuilt_archives_are_reused(self, tmp_path):
        (tmp_path / "CMakeLists.txt").touch()
        build = tmp_path / "_ebuild" / "core"
        build.mkdir(parents=True)
        (build / "libeos_kernel.a").touch()

        lib_dirs, libs = _cached_repo_libraries(tmp_path)

        assert lib_dirs == [build]
        assert libs == ["eos_kernel"]

    def test_non_lib_archives_are_not_offered_as_l_flags(self, tmp_path):
        """-l wants the name with the lib prefix stripped; an archive that is
        not named libX.a has no -l spelling and must be skipped."""
        (tmp_path / "CMakeLists.txt").touch()
        build = tmp_path / "_ebuild"
        build.mkdir(parents=True)
        (build / "strays.a").touch()
        (build / "libgood.a").touch()

        _, libs = _cached_repo_libraries(tmp_path)

        assert libs == ["good"]


class _SilentLog:
    """Minimal Logger stand-in: these tests assert on state, not output."""

    verbose = False

    def _noop(self, *a, **k):
        return None

    info = step = success = warning = debug = header = _noop

    def error(self, *a, **k):
        return None
