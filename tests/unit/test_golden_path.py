"""ebuild init / sim / platforms: the getting-started guide's commands."""
from __future__ import annotations

import stat
import sys
import textwrap
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from ebuild.cli import golden_path
from ebuild.cli.commands import cli


def _fake_qemu(tmp_path: Path, body: str) -> str:
    """A stand-in qemu: a Python script that prints like a guest would."""
    script = tmp_path / "fake-qemu"
    script.write_text(f"#!{sys.executable}\n" + textwrap.dedent(body), encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return str(script)


SPEC = {"qemu": {"machine": "lm3s6965evb", "args": ["-nographic"]}}


@pytest.mark.skipif(sys.platform == "win32", reason="shebang stand-in needs POSIX")
class TestRunQemu:
    def test_guest_exit_status_and_output_are_reported(self, tmp_path):
        qemu = _fake_qemu(tmp_path, """
            import sys
            print("booted"); print("PASS")
            sys.exit(0)
        """)
        r = golden_path.run_qemu(qemu, SPEC, tmp_path / "x.elf", 5, None, tmp_path / "log")
        assert r["lines"] == ["booted", "PASS"]
        assert r["guest_exited"] and r["exit_code"] == 0
        assert not r["timed_out"]
        assert (tmp_path / "log").read_text(encoding="utf-8") == "booted\nPASS\n"
        assert r["command"][1:3] == ["-M", "lm3s6965evb"]

    def test_expect_stops_the_run_as_soon_as_it_matches(self, tmp_path):
        qemu = _fake_qemu(tmp_path, """
            import time
            print("tick 1", flush=True); print("ready", flush=True)
            time.sleep(30)
        """)
        r = golden_path.run_qemu(qemu, SPEC, tmp_path / "x.elf", 20, r"read.", tmp_path / "log")
        assert r["matched"] and not r["timed_out"]
        assert r["lines"][-1] == "ready"

    def test_timeout_bounds_a_guest_that_never_exits(self, tmp_path):
        qemu = _fake_qemu(tmp_path, """
            import time
            print("running", flush=True)
            time.sleep(30)
        """)
        r = golden_path.run_qemu(qemu, SPEC, tmp_path / "x.elf", 1, None, tmp_path / "log")
        assert r["timed_out"] and not r["guest_exited"]
        assert r["lines"] == ["running"]

    def test_nonzero_guest_exit_is_kept(self, tmp_path):
        qemu = _fake_qemu(tmp_path, """
            import sys
            print("FAILED"); sys.exit(3)
        """)
        r = golden_path.run_qemu(qemu, SPEC, tmp_path / "x.elf", 5, None, tmp_path / "log")
        assert r["guest_exited"] and r["exit_code"] == 3


def _project(tmp_path: Path, board: str = "stm32f4") -> Path:
    result = CliRunner().invoke(cli, ["init", "proj", "--template", "rtos",
                                      "--target", board, "--output-dir", str(tmp_path)])
    assert result.exit_code == 0, result.output
    return tmp_path / "proj"


class TestInit:
    def test_init_is_new_with_the_guides_names(self, tmp_path):
        project = _project(tmp_path)
        assert (project / "src" / "main.c").is_file()
        assert (project / "tests" / "test_main.c").is_file()
        eos = yaml.safe_load((project / "eos.yaml").read_text(encoding="utf-8"))
        assert eos["system"]["board"] == "stm32f4"
        # rtos -> the rtos-app template, which has the producer/consumer app
        assert "producer_task" in (project / "src" / "main.c").read_text(encoding="utf-8")

    def test_templates_ship_inside_the_package(self):
        # A wheel only carries the package; the templates must live in it.
        templates = Path(golden_path.__file__).resolve().parent.parent / "templates"
        assert sorted(p.name for p in templates.iterdir() if p.is_dir()) == sorted(
            golden_path.INIT_TEMPLATES.values())


class TestSimFailsClosed:
    def test_board_without_a_sim_target_is_an_error(self, tmp_path):
        project = _project(tmp_path, board="esp32")
        r = _invoke_in(project, ["sim"])
        assert r.exit_code == 1
        assert "no simulation target for board 'esp32'" in r.output

    def test_missing_sim_spec_in_eos_checkout_is_an_error(self, tmp_path, monkeypatch):
        project = _project(tmp_path)
        fake_eos = tmp_path / "eos"
        fake_eos.mkdir()
        monkeypatch.setenv("EBUILD_EOS_PATH", str(fake_eos))
        r = _invoke_in(project, ["sim"])
        assert r.exit_code == 1
        assert "predates the qemu_cortex_m3 simulation target" in r.output

    def test_image_that_prints_nothing_is_not_a_pass(self, tmp_path, monkeypatch):
        project = _project(tmp_path)
        self._stub_toolchain(tmp_path, monkeypatch, lines=[], exit_code=None)
        r = _invoke_in(project, ["sim"])
        assert r.exit_code == 1
        assert "produced no output" in r.output

    def test_nonzero_guest_exit_fails(self, tmp_path, monkeypatch):
        project = _project(tmp_path)
        self._stub_toolchain(tmp_path, monkeypatch, lines=["boom"], exit_code=2)
        r = _invoke_in(project, ["sim"])
        assert r.exit_code == 1
        assert "guest exited with status 2" in r.output

    def test_output_without_expect_passes(self, tmp_path, monkeypatch):
        project = _project(tmp_path)
        self._stub_toolchain(tmp_path, monkeypatch, lines=["[proj] Starting kernel..."],
                             exit_code=None)
        r = _invoke_in(project, ["sim"])
        assert r.exit_code == 0, r.output
        assert "Simulation ran: 1 line(s)" in r.output

    def test_unmatched_expect_fails(self, tmp_path, monkeypatch):
        project = _project(tmp_path)
        self._stub_toolchain(tmp_path, monkeypatch, lines=["hello"], exit_code=None)
        r = _invoke_in(project, ["sim", "--expect", "PASSED"])
        assert r.exit_code == 1
        assert "/PASSED/ never appeared" in r.output

    @staticmethod
    def _stub_toolchain(tmp_path, monkeypatch, lines, exit_code):
        eos = tmp_path / "eos"
        (eos / "sim" / "qemu_cortex_m3").mkdir(parents=True)
        (eos / "sim" / "qemu_cortex_m3" / "sim.yaml").write_text(yaml.safe_dump({
            "schema": 1, "qemu": {"binary": "qemu-system-arm", "machine": "lm3s6965evb"},
            "cflags": [], "includes": [], "ldflags": [], "linker_script": "x.ld",
            "sources": []}), encoding="utf-8")
        monkeypatch.setenv("EBUILD_EOS_PATH", str(eos))
        monkeypatch.setattr(golden_path, "_require_tool", lambda name, hint: name)
        monkeypatch.setattr(golden_path, "build_sim_image",
                            lambda *a, **k: tmp_path / "firmware.elf")
        exited = exit_code is not None
        monkeypatch.setattr(golden_path, "run_qemu", lambda *a, **k: {
            "command": [], "lines": lines, "matched": False, "timed_out": not exited,
            "guest_exited": exited, "exit_code": exit_code})


def _invoke_in(project: Path, args):
    import os
    old = os.getcwd()
    os.chdir(project)
    try:
        return CliRunner().invoke(cli, args)
    finally:
        os.chdir(old)


def test_platforms_list_reads_eosim_registry():
    pytest.importorskip("eosim")
    r = CliRunner().invoke(cli, ["platforms", "list", "--format", "names"])
    assert r.exit_code == 0, r.output
    names = r.output.split()
    assert "stm32f4" in names and len(names) >= 100


def test_qemu_cortex_m33_is_a_named_target_but_no_board_maps_to_it():
    # A name the developer can ask for. Not a silent stand-in for a board.
    assert golden_path.SIM_TARGETS["qemu_cortex_m33"] == "qemu_cortex_m33"
    assert [b for b, t in golden_path.SIM_TARGETS.items() if t == "qemu_cortex_m33"] == ["qemu_cortex_m33"]


def test_sim_on_qemu_cortex_m33_runs_the_fpu_context_test(tmp_path):
    """End to end: ebuild sim builds eos for mps2-an505 and the guest exits 0.

    Needs arm-none-eabi-gcc, qemu-system-arm and an eos checkout with
    sim/qemu_cortex_m33 (EBUILD_EOS_PATH, or ~/.ebuild/repos/eos). Skipped,
    with the reason, when any of them is missing.
    """
    import os
    import shutil

    for tool in ("arm-none-eabi-gcc", "qemu-system-arm"):
        if not shutil.which(tool):
            pytest.skip(f"{tool} not on PATH")
    eos = Path(os.environ.get("EBUILD_EOS_PATH", Path.home() / ".ebuild" / "repos" / "eos"))
    test_src = eos / "sim" / "qemu_cortex_m33" / "fpu_context_test.c"
    if not test_src.is_file():
        pytest.skip(f"{test_src} not found (eos predates the qemu_cortex_m33 target)")
    # A real project, made the way the guide makes one, with its main.c
    # replaced by eos's FPU context test.
    r = _invoke_in(tmp_path, ["init", "fpu", "--template", "rtos", "--target", "stm32f4"])
    assert r.exit_code == 0, r.output
    project = tmp_path / "fpu"
    shutil.copy(test_src, project / "src" / "main.c")
    old = os.environ.get("EBUILD_EOS_PATH")
    os.environ["EBUILD_EOS_PATH"] = str(eos)
    try:
        r = _invoke_in(project, ["sim", "--platform", "qemu_cortex_m33",
                                 "--expect", "FPU CONTEXT TEST PASSED", "--timeout", "60"])
    finally:
        if old is None:
            os.environ.pop("EBUILD_EOS_PATH", None)
        else:
            os.environ["EBUILD_EOS_PATH"] = old
    assert r.exit_code == 0, r.output
    assert "0 corrupted" in r.output
