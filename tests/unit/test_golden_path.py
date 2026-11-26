"""ebuild init / sim / platforms: the getting-started guide's commands."""
from __future__ import annotations

import json
import shlex
import shutil
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
    """A stand-in qemu: a Python script that prints like a guest would.

    Launched through a /bin/sh wrapper rather than a `#!{sys.executable}`
    shebang, because a shebang cannot carry an interpreter path containing
    spaces (e.g. a checkout under "My Projects/"), and the exec then fails
    with ENOENT before the test exercises anything.
    """
    guest = tmp_path / "fake_guest.py"
    guest.write_text(textwrap.dedent(body), encoding="utf-8")
    script = tmp_path / "fake-qemu"
    script.write_text(
        f'#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(guest))} "$@"\n',
        encoding="utf-8")
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
        project = _project(tmp_path, board="imx8mp")
        r = _invoke_in(project, ["sim"])
        assert r.exit_code == 1
        assert "no simulation target for board 'imx8mp'" in r.output

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


def test_esp32_maps_to_espressifs_qemu_and_keeps_the_arm_targets():
    assert golden_path.SIM_TARGETS["esp32"] == "qemu_esp32"
    # Adding the ESP32 removed no Cortex-M board.
    for board in ("stm32f4", "stm32h7", "stm32l4", "nrf52", "nrf52840", "rp2040",
                  "raspi-pico", "qemu_cortex_m3"):
        assert golden_path.SIM_TARGETS[board] == "qemu_cortex_m3"


@pytest.mark.skipif(sys.platform == "win32", reason="shebang stand-in needs POSIX")
def test_flash_targets_boot_from_the_flash_image(tmp_path):
    """qemu.flash_arg replaces -kernel: the guest gets the flash file."""
    qemu = _fake_qemu(tmp_path, '''
        import sys
        print(" ".join(sys.argv[1:]))
    ''')
    spec = {"qemu": {"machine": "esp32", "args": ["-nographic"],
                     "flash_arg": "-drive file={flash},if=mtd,format=raw"}}
    flash = tmp_path / "firmware.flash.bin"
    result = golden_path.run_qemu(qemu, spec, flash, 5, None, tmp_path / "log")
    assert f"-M esp32 -nographic -drive file={flash},if=mtd,format=raw" in result["lines"][0]
    assert "-kernel" not in result["lines"][0]


@pytest.mark.skipif(sys.platform == "win32", reason="shebang stand-in needs POSIX")
def test_flash_image_is_made_with_esptool(tmp_path):
    """elf2image with options esptool 4.x and 5.x both accept, then the image
    at its offset in erased flash of the flash size."""
    calls = tmp_path / "calls"
    esptool = _fake_qemu(tmp_path, f'''
        import sys
        open({str(calls)!r}, "a").write(" ".join(sys.argv[1:]) + "\\n")
        open(sys.argv[sys.argv.index("-o") + 1], "wb").write(b"\\xe9IMAGE")
    ''')
    spec = {"image": {"chip": "esp32", "flash_mode": "dio", "flash_freq": "40m",
                      "flash_size": "4MB", "offset": "0x1000"}}
    elf = tmp_path / "firmware.elf"
    out = golden_path.build_flash_image(spec, elf, esptool, golden_path.Logger())
    assert out == tmp_path / "firmware.flash.bin"
    (elf2image,) = calls.read_text().splitlines()
    assert elf2image.startswith("--chip esp32 elf2image --flash_mode dio --flash_freq 40m "
                                "--flash_size 4MB")
    assert elf2image.endswith(f"-o {tmp_path / 'firmware.bin'} {elf}")
    flash = out.read_bytes()
    assert len(flash) == 4 << 20
    assert flash[0x1000:0x1006] == b"\xe9IMAGE"
    assert set(flash[:0x1000]) == {0xFF} and set(flash[0x1006:]) == {0xFF}


@pytest.mark.skipif(sys.platform == "win32", reason="shebang stand-in needs POSIX")
def test_flash_image_too_big_or_unknown_size_is_refused(tmp_path):
    esptool = _fake_qemu(tmp_path, '''
        import sys
        open(sys.argv[sys.argv.index("-o") + 1], "wb").write(b"\\x00" * 4096)
    ''')
    elf = tmp_path / "firmware.elf"
    spec = {"image": {"chip": "esp32", "flash_mode": "dio", "flash_freq": "40m",
                      "flash_size": "1MB", "offset": hex((1 << 20) - 100)}}
    with pytest.raises(golden_path.SimError, match="does not fit"):
        golden_path.build_flash_image(spec, elf, esptool, golden_path.Logger())
    spec["image"].update(flash_size="3MB", offset="0x1000")
    with pytest.raises(golden_path.SimError, match="is not one of"):
        golden_path.build_flash_image(spec, elf, esptool, golden_path.Logger())


def test_sim_on_esp32_runs_the_rtos_template(tmp_path):
    """End to end: the unmodified rtos template, built for the ESP32 and run
    on Espressif's QEMU.

    Needs xtensa-esp32-elf-gcc, qemu-system-xtensa (Espressif's fork),
    esptool and an eos checkout with sim/qemu_esp32 (EBUILD_EOS_PATH, or
    ~/.ebuild/repos/eos). Skipped, with the reason, when any is missing.
    """
    import os
    import shutil

    for tool in ("xtensa-esp32-elf-gcc", "qemu-system-xtensa", "esptool"):
        if not shutil.which(tool):
            pytest.skip(f"{tool} not on PATH")
    eos = Path(os.environ.get("EBUILD_EOS_PATH", Path.home() / ".ebuild" / "repos" / "eos"))
    if not (eos / "sim" / "qemu_esp32" / "sim.yaml").is_file():
        pytest.skip(f"{eos} has no sim/qemu_esp32 (eos predates the ESP32 port)")
    r = _invoke_in(tmp_path, ["init", "demo", "--template", "rtos", "--target", "esp32"])
    assert r.exit_code == 0, r.output
    old = os.environ.get("EBUILD_EOS_PATH")
    os.environ["EBUILD_EOS_PATH"] = str(eos)
    try:
        r = _invoke_in(tmp_path / "demo", ["sim", "--expect", r"\[consumer\] id=2",
                                           "--timeout", "60"])
    finally:
        if old is None:
            os.environ.pop("EBUILD_EOS_PATH", None)
        else:
            os.environ["EBUILD_EOS_PATH"] = old
    assert r.exit_code == 0, r.output
    assert "Starting kernel" in r.output


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


# ── Review of #260: paths with spaces, mismatched specs, tool discovery ──


@pytest.mark.skipif(sys.platform == "win32", reason="shebang stand-in needs POSIX")
def test_an_esptool_path_with_spaces_is_one_argument(tmp_path):
    """Review of #260: the esptool path was shlex.split(), so an install
    under "/opt/ESP Tools/bin" made "/opt/ESP" the executable (and POSIX
    splitting ate the backslashes of a Windows path). _require_tool
    returns a resolved path, not a command line."""
    spaced = tmp_path / "ESP Tools" / "bin"
    spaced.mkdir(parents=True)
    calls = tmp_path / "calls"
    esptool = _fake_qemu(tmp_path, f'''
        import sys
        open({str(calls)!r}, "a").write(" ".join(sys.argv[1:]) + "\\n")
        open(sys.argv[sys.argv.index("-o") + 1], "wb").write(b"\\xe9IMG")
    ''')
    spaced_tool = spaced / "esptool"
    shutil.copy(esptool, spaced_tool)
    spaced_tool.chmod(spaced_tool.stat().st_mode | stat.S_IEXEC)

    spec = {"image": {"chip": "esp32", "flash_mode": "dio", "flash_freq": "40m",
                      "flash_size": "4MB", "offset": "0x1000"}}
    out = golden_path.build_flash_image(
        spec, tmp_path / "firmware.elf", str(spaced_tool), golden_path.Logger())

    assert out.read_bytes()[0x1000:0x1004] == b"\xe9IMG"
    assert calls.exists(), "esptool was never launched"


@pytest.mark.skipif(sys.platform == "win32", reason="shebang stand-in needs POSIX")
def test_a_project_path_with_spaces_stays_one_qemu_argument(tmp_path):
    """Review of #260: flash_arg was formatted and *then* split, so a
    directory containing a space cut the -drive value in half."""
    qemu = _fake_qemu(tmp_path, '''
        import json, sys
        print(json.dumps(sys.argv[1:]))
    ''')
    spec = {"qemu": {"machine": "esp32", "args": [],
                     "flash_arg": "-drive file={flash},if=mtd,format=raw"}}
    spaced = tmp_path / "ESP Demo"
    spaced.mkdir()
    flash = spaced / "firmware.flash.bin"

    result = golden_path.run_qemu(qemu, spec, flash, 5, None, tmp_path / "log")

    argv = json.loads(result["lines"][0])
    assert argv == ["-M", "esp32", "-drive", f"file={flash},if=mtd,format=raw"]


@pytest.mark.skipif(sys.platform == "win32", reason="shebang stand-in needs POSIX")
def test_an_apostrophe_in_the_path_does_not_raise(tmp_path):
    """Review of #260: formatting before splitting also meant a directory
    named e.g. "Jane's board" made shlex.split raise ValueError on an
    unbalanced quote, before QEMU ever ran."""
    qemu = _fake_qemu(tmp_path, '''
        import json, sys
        print(json.dumps(sys.argv[1:]))
    ''')
    spec = {"qemu": {"machine": "esp32", "args": [],
                     "flash_arg": "-drive file={flash},if=mtd,format=raw"}}
    quoted = tmp_path / "Jane's board"
    quoted.mkdir()
    flash = quoted / "firmware.flash.bin"

    result = golden_path.run_qemu(qemu, spec, flash, 5, None, tmp_path / "log")

    argv = json.loads(result["lines"][0])
    assert argv[-1] == f"file={flash},if=mtd,format=raw"


@pytest.mark.skipif(sys.platform == "win32", reason="shebang stand-in needs POSIX")
def test_a_negative_flash_offset_is_refused(tmp_path):
    """Review of #260: a negative offset passed the fit check, then
    Python's negative slice assignment *grew* the bytearray and returned a
    flash file bigger than the chip."""
    esptool = _fake_qemu(tmp_path, '''
        import sys
        open(sys.argv[sys.argv.index("-o") + 1], "wb").write(b"\\x00" * 4096)
    ''')
    spec = {"image": {"chip": "esp32", "flash_mode": "dio", "flash_freq": "40m",
                      "flash_size": "1MB", "offset": "-1"}}
    with pytest.raises(golden_path.SimError, match="negative"):
        golden_path.build_flash_image(
            spec, tmp_path / "firmware.elf", esptool, golden_path.Logger())

    # The control: an image that exactly fills the flash is still accepted.
    spec["image"]["offset"] = hex((1 << 20) - 4096)
    out = golden_path.build_flash_image(
        spec, tmp_path / "firmware.elf", esptool, golden_path.Logger())
    assert len(out.read_bytes()) == 1 << 20


@pytest.mark.skipif(sys.platform == "win32", reason="shebang stand-in needs POSIX")
def test_undecodable_esptool_output_still_gives_an_actionable_error(tmp_path):
    """Review of #260: subprocess(text=True) decodes with the process
    locale and raises UnicodeDecodeError, replacing the actionable
    "esptool failed" with a traceback from the decoder."""
    esptool = _fake_qemu(tmp_path, '''
        import sys
        sys.stderr.buffer.write(b"fatal: \\xff\\xfe not utf-8\\n")
        sys.exit(2)
    ''')
    spec = {"image": {"chip": "esp32", "flash_mode": "dio", "flash_freq": "40m",
                      "flash_size": "4MB", "offset": "0x1000"}}
    with pytest.raises(golden_path.SimError, match="elf2image failed"):
        golden_path.build_flash_image(
            spec, tmp_path / "firmware.elf", esptool, golden_path.Logger())


def test_esptool_is_found_under_either_name(tmp_path, monkeypatch):
    """Review of #260: esptool installs as `esptool` (pip 5.x) or
    `esptool.py` (4.x, ESP-IDF's export script). Looking for only one
    stopped the sim on a machine where the tool was installed."""
    found = {}

    def fake_which(name):
        return "/opt/esp/esptool.py" if name == "esptool.py" else None

    monkeypatch.setattr(golden_path.shutil, "which", fake_which)
    assert golden_path._require_any_tool(
        ["esptool", "esptool.py"], "hint") == "/opt/esp/esptool.py"

    monkeypatch.setattr(golden_path.shutil, "which", lambda name: None)
    with pytest.raises(golden_path.SimError, match="esptool or esptool.py"):
        golden_path._require_any_tool(["esptool", "esptool.py"], "hint")
    assert found == {}


@pytest.mark.parametrize("spec_yaml, missing", [
    # An image section with no flash_arg: sim builds a flash image, then
    # boots the ELF with -kernel and the image is never loaded.
    ("""
schema: 1
qemu: {binary: qemu-system-xtensa, machine: esp32, args: []}
cpu: esp32
image: {chip: esp32, flash_mode: dio, flash_freq: 40m, flash_size: 4MB, offset: '0x1000'}
""", "qemu.flash_arg"),
    # A flash_arg with no image section: QEMU is pointed at a flash file
    # that was never made.
    ("""
schema: 1
qemu:
  binary: qemu-system-xtensa
  machine: esp32
  args: []
  flash_arg: "-drive file={flash},if=mtd,format=raw"
cpu: esp32
""", "image"),
])
def test_half_a_flash_boot_spec_is_refused(tmp_path, monkeypatch, spec_yaml, missing):
    """Review of #260: `image` and `qemu.flash_arg` are the two halves of
    one flash boot -- one makes the image, the other loads it. With only
    one, the target silently does not boot. Caught before anything builds.
    """
    eos = tmp_path / "eos"
    target = eos / "sim" / "qemu_esp32"
    target.mkdir(parents=True)
    (target / "sim.yaml").write_text(spec_yaml, encoding="utf-8")

    r = _invoke_in(tmp_path, ["init", "demo", "--template", "rtos",
                              "--target", "esp32"])
    assert r.exit_code == 0, r.output
    monkeypatch.setenv("EBUILD_EOS_PATH", str(eos))

    r = _invoke_in(tmp_path / "demo", ["sim"])

    assert r.exit_code != 0
    assert missing in r.output, r.output
    assert "needs both" in r.output, r.output
