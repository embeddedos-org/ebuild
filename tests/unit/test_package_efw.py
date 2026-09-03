# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""`ebuild package` — the step §29 puts between eBuild and the device.

    eBuild -> {EoS, eBoot, application} -> eFirmware artifact -> {EoSim, hardware}

Every piece of that existed except the arrow into eFirmware. The eFirmware
repository implements the image format and ships `efwtool`; nothing in ebuild
referenced it, so a developer had to know the tool existed, build it, and run
it by hand.

These cover the wiring, not the format. `efwtool` owns the format and has its
own tests; duplicating them here would mean a second definition of the header
to keep in step, which is the failure this repository has spent the week
repairing.
"""

import os
import stat
import sys

import pytest
import yaml
from click.testing import CliRunner

from ebuild.build.firmware_image import (
    FirmwareImageError,
    find_efwtool,
    missing_tool_message,
    pack,
)
from ebuild.cli.commands import cli


def _fake_efwtool(tmp_path, *, exit_code=0, stderr="", writes_output=False,
                  records_argv=False):
    """A stand-in for efwtool, so the wiring is testable without building C.

    Driven through sys.executable rather than written as a /bin/sh script:
    Windows cannot execute one, so every test here failed there with
    "WinError 193: %1 is not a valid Win32 application" as soon as the
    `package` command was registered and these tests began running.
    """
    script = tmp_path / "_efwtool_impl.py"
    script.write_text(
        "import pathlib, sys\n"
        f"if {records_argv!r}:\n"
        "    pathlib.Path(__file__).with_name('argv.txt').write_text(\n"
        "        ' '.join(sys.argv[1:]), encoding='utf-8')\n"
        f"if {writes_output!r}:\n"
        "    pathlib.Path(sys.argv[3]).touch()\n"
        f"sys.stderr.write({stderr!r})\n"
        f"sys.exit({exit_code!r})\n",
        encoding="utf-8",
    )
    if os.name == "nt":
        tool = tmp_path / "efwtool.bat"
        tool.write_text(
            f'@echo off\r\n"{sys.executable}" "{script}" %*\r\n', encoding="utf-8"
        )
    else:
        tool = tmp_path / "efwtool"
        tool.write_text(
            f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding="utf-8"
        )
        tool.chmod(tool.stat().st_mode | stat.S_IEXEC)
    return tool


class TestToolDiscovery:
    def test_an_efwtool_on_path_wins(self, tmp_path, monkeypatch):
        """A developer with their own build should not have one silently
        compiled behind their back."""
        monkeypatch.setattr("ebuild.build.firmware_image.shutil.which",
                            lambda n: "/usr/local/bin/efwtool" if n == "efwtool" else None)
        assert str(find_efwtool(tmp_path)).endswith("efwtool")

    def test_no_checkout_and_no_tool_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ebuild.build.firmware_image.shutil.which", lambda n: None)
        assert find_efwtool(tmp_path) is None

    def test_a_prebuilt_tool_in_the_cache_is_reused(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ebuild.build.firmware_image.shutil.which", lambda n: None)
        root = tmp_path / "efirmware"
        (root / "_ebuild" / "tools").mkdir(parents=True)
        (root / "CMakeLists.txt").touch()
        tool = root / "_ebuild" / "tools" / "efwtool"
        tool.touch()
        tool.chmod(tool.stat().st_mode | stat.S_IEXEC)
        assert find_efwtool(tmp_path) == tool


class TestMissingToolMessage:
    def test_it_names_setup_when_the_checkout_is_absent(self, tmp_path):
        """"efwtool not found" leaves the developer guessing at what fetches
        it."""
        assert "ebuild setup" in missing_tool_message(tmp_path)

    def test_it_gives_the_build_command_when_the_checkout_exists(self, tmp_path):
        (tmp_path / "efirmware").mkdir()
        msg = missing_tool_message(tmp_path)
        assert "cmake" in msg
        assert "ebuild setup" not in msg


class TestPack:
    def test_a_missing_artifact_is_refused_before_the_tool_runs(self, tmp_path):
        tool = _fake_efwtool(tmp_path)
        with pytest.raises(FirmwareImageError, match="no artifact"):
            pack(tool, tmp_path / "nope", tmp_path / "out.efw")

    def test_a_tool_that_writes_nothing_is_caught(self, tmp_path):
        """efwtool exiting 0 without producing a file would otherwise be
        reported as a successful package."""
        tool = _fake_efwtool(tmp_path)
        payload = tmp_path / "app"
        payload.write_bytes(b"\x7fELF")
        with pytest.raises(FirmwareImageError, match="wrote no image"):
            pack(tool, payload, tmp_path / "out.efw")

    def test_a_failing_tool_surfaces_its_own_message(self, tmp_path):
        tool = _fake_efwtool(tmp_path, stderr="bad magic\n", exit_code=3)
        payload = tmp_path / "app"
        payload.write_bytes(b"x")
        with pytest.raises(FirmwareImageError, match="bad magic"):
            pack(tool, payload, tmp_path / "out.efw")

    def test_version_and_addresses_reach_the_tool(self, tmp_path):
        tool = _fake_efwtool(tmp_path, records_argv=True, writes_output=True)
        payload = tmp_path / "app"
        payload.write_bytes(b"x")
        pack(tool, payload, tmp_path / "out.efw", version="2.1.0",
             load_addr="0x08000000", entry_addr="0x08000100")
        argv = (tmp_path / "argv.txt").read_text()
        assert "--version 2.1.0" in argv
        assert "--load 0x08000000" in argv
        assert "--entry 0x08000100" in argv

    def test_addresses_are_omitted_when_not_given(self, tmp_path):
        """A host build has no load address, and passing an empty one would
        make efwtool reject the call."""
        tool = _fake_efwtool(tmp_path, records_argv=True, writes_output=True)
        payload = tmp_path / "app"
        payload.write_bytes(b"x")
        pack(tool, payload, tmp_path / "out.efw")
        argv = (tmp_path / "argv.txt").read_text()
        assert "--load" not in argv
        assert "--entry" not in argv


class TestCommand:
    def test_package_is_registered(self):
        assert "package" in cli.commands

    def _project(self, tmp_path, built=True):
        (tmp_path / "build.yaml").write_text(yaml.safe_dump({
            "project": {"name": "node", "version": "2.1.0"},
            "workspace": {"backend": "ninja", "build_dir": "build"},
            "toolchain": {"target": "host"},
            "targets": [{"name": "node", "type": "executable",
                         "sources": ["src/main.c"]}],
        }))
        if built:
            (tmp_path / "_build").mkdir()
            (tmp_path / "_build" / "node").write_bytes(b"\x7fELF" + b"\x00" * 64)
        return tmp_path

    def test_it_refuses_before_a_build(self, tmp_path, monkeypatch):
        """Packaging a stale or absent artifact silently is worse than
        saying which command to run."""
        monkeypatch.chdir(self._project(tmp_path, built=False))
        result = CliRunner().invoke(cli, ["package"])
        assert result.exit_code == 1
        assert "ebuild build" in result.output

    def test_it_refuses_without_an_executable_target(self, tmp_path, monkeypatch):
        (tmp_path / "build.yaml").write_text(yaml.safe_dump({
            "project": {"name": "lib", "version": "1.0"},
            "workspace": {"backend": "ninja", "build_dir": "build"},
            "toolchain": {"target": "host"},
            "targets": [{"name": "lib", "type": "static_library",
                         "sources": ["a.c"]}],
        }))
        monkeypatch.chdir(tmp_path)
        result = CliRunner().invoke(cli, ["package"])
        assert result.exit_code == 1
        assert "nothing to package" in result.output

    def test_it_says_how_to_get_efwtool(self, tmp_path, monkeypatch):
        """Pointing the cache at an empty directory as well as clearing PATH:
        this machine has a real efwtool cached, and without both the test
        passes by finding it and asserts nothing."""
        monkeypatch.chdir(self._project(tmp_path))
        monkeypatch.setattr("ebuild.build.firmware_image.shutil.which",
                            lambda n: None)
        monkeypatch.setattr("ebuild.deps.EBUILD_REPOS_DIR", tmp_path / "empty")
        result = CliRunner().invoke(cli, ["package"])
        assert result.exit_code == 1
        assert "ebuild setup" in result.output


def _efwtool_that_packs(tmp_path, *, verdict="efw v1  node  4128 bytes  OK"):
    """A stand-in that answers both subcommands `package` drives.

    `_fake_efwtool` above writes argv[3] unconditionally, which `verify` --
    invoked as `efwtool verify <image>` -- does not have. The command runs
    pack and then verify against the same binary, so a fake that serves only
    one of them cannot exercise the path between them.
    """
    script = tmp_path / "_efwtool_both.py"
    script.write_text(
        "import pathlib, sys\n"
        "if sys.argv[1] == 'pack':\n"
        "    pathlib.Path(sys.argv[3]).write_bytes(b'EFW0' + b'\\x00' * 60)\n"
        f"elif sys.argv[1] == 'verify':\n"
        f"    sys.stdout.write({verdict!r} + '\\n')\n"
        "sys.exit(0)\n",
        encoding="utf-8",
    )
    if os.name == "nt":
        tool = tmp_path / "efwtool_both.bat"
        tool.write_text(
            f'@echo off\r\n"{sys.executable}" "{script}" %*\r\n', encoding="utf-8")
    else:
        tool = tmp_path / "efwtool_both"
        tool.write_text(
            f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding="utf-8")
        tool.chmod(tool.stat().st_mode | stat.S_IEXEC)
    return tool


class TestCommandPacks:
    """The refusals above are the cheap half. These cover the path a developer
    actually takes -- a built artifact, a tool on PATH, an image on disk."""

    def _project(self, tmp_path):
        (tmp_path / "build.yaml").write_text(yaml.safe_dump({
            "project": {"name": "node", "version": "2.1.0"},
            "workspace": {"backend": "ninja", "build_dir": "build"},
            "toolchain": {"target": "host"},
            "targets": [{"name": "node", "type": "executable",
                         "sources": ["src/main.c"]}],
        }))
        (tmp_path / "_build").mkdir()
        (tmp_path / "_build" / "node").write_bytes(b"\x7fELF" + b"\x00" * 64)
        return tmp_path

    def _packaged(self, tmp_path, monkeypatch, argv=(), **tool_kw):
        tool = _efwtool_that_packs(tmp_path, **tool_kw)
        monkeypatch.chdir(self._project(tmp_path))
        monkeypatch.setattr("ebuild.build.firmware_image.shutil.which",
                            lambda n: str(tool) if n == "efwtool" else None)
        return CliRunner().invoke(cli, ["package", *argv])

    def test_it_writes_the_image_and_reports_its_size(self, tmp_path, monkeypatch):
        result = self._packaged(tmp_path, monkeypatch)
        assert result.exit_code == 0, result.output
        image = tmp_path / "node.efw"
        assert image.is_file()
        assert str(image.stat().st_size) in result.output

    def test_the_default_name_comes_from_the_project(self, tmp_path, monkeypatch):
        """Not from the target or the build directory: `--output` is optional,
        so the fallback is the name a developer will look for."""
        result = self._packaged(tmp_path, monkeypatch)
        assert result.exit_code == 0, result.output
        assert (tmp_path / "node.efw").is_file()

    def test_output_overrides_the_default_path(self, tmp_path, monkeypatch):
        result = self._packaged(tmp_path, monkeypatch,
                                argv=["--output", "dist.efw"])
        assert result.exit_code == 0, result.output
        assert (tmp_path / "dist.efw").is_file()
        assert not (tmp_path / "node.efw").exists()

    def test_the_verify_verdict_is_shown(self, tmp_path, monkeypatch):
        """Packing and verifying with the same tool does not prove the format
        is right, but the developer is entitled to see that the file on disk
        parses at all."""
        result = self._packaged(tmp_path, monkeypatch,
                                verdict="header ok\npayload crc ok")
        assert result.exit_code == 0, result.output
        assert "header ok" in result.output
        assert "payload crc ok" in result.output

    def test_it_says_how_to_inspect_the_result(self, tmp_path, monkeypatch):
        result = self._packaged(tmp_path, monkeypatch)
        assert "inspect" in result.output

    def test_a_tool_failure_is_reported_rather_than_raised(self, tmp_path, monkeypatch):
        """FirmwareImageError has to become an error message and exit 1. An
        uncaught one would print a stack trace over a build that succeeded."""
        tool = _fake_efwtool(tmp_path, stderr="bad magic\n", exit_code=3)
        monkeypatch.chdir(self._project(tmp_path))
        monkeypatch.setattr("ebuild.build.firmware_image.shutil.which",
                            lambda n: str(tool) if n == "efwtool" else None)
        result = CliRunner().invoke(cli, ["package"])
        assert result.exit_code == 1
        assert "bad magic" in result.output
        assert "Traceback" not in result.output


class TestCommandConfigErrors:
    """`package` is reachable from any directory, so it has to say which one
    it is standing in rather than raising FileNotFoundError at the developer."""

    def test_no_build_yaml_names_the_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = CliRunner().invoke(cli, ["package"])
        assert result.exit_code == 1
        assert "build.yaml" in result.output
        assert "Traceback" not in result.output

    def test_a_malformed_build_yaml_is_reported_as_a_config_error(
            self, tmp_path, monkeypatch):
        (tmp_path / "build.yaml").write_text("project: [not, a, mapping]\n",
                                             encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        result = CliRunner().invoke(cli, ["package"])
        assert result.exit_code == 1
        assert "Configuration error" in result.output
        assert "Traceback" not in result.output
