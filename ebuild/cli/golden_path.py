# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""Getting-started commands: ``ebuild init``, ``ebuild sim``, ``ebuild platforms``.

These are the commands https://www.embeddedos.org/getting-started documents:

    ebuild init my-blink --template rtos --target stm32f4
    cd my-blink && ebuild sim
    ebuild platforms list

``init`` is ``new`` under the guide's spelling. ``platforms`` reads EoSim's
platform registry. ``sim`` builds the project for a QEMU machine with the
cross compiler and runs it there. It returns success only if the guest
produced output: an image that prints nothing has not been shown to run.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional

import click
import yaml

from ebuild.cli.logger import Logger

# The guide's short template names, and the ``ebuild new`` templates they mean.
INIT_TEMPLATES: Dict[str, str] = {
    "rtos": "rtos-app",
    "bare-metal": "bare-metal",
    "ble-sensor": "ble-sensor",
    "linux": "linux-app",
    "secure-boot": "secure-boot",
    "safety-critical": "safety-critical",
}

# Boards whose application code ``ebuild sim`` can run, and the eos sim target
# each runs on. All of them are Arm Cortex-M parts: the code is rebuilt for
# QEMU's Cortex-M3 machine, which is a stand-in for the board, not a model of it.
SIM_TARGETS: Dict[str, str] = {
    "stm32f4": "qemu_cortex_m3",
    "stm32h7": "qemu_cortex_m3",
    "stm32l4": "qemu_cortex_m3",
    "nrf52": "qemu_cortex_m3",
    "nrf52840": "qemu_cortex_m3",
    "rp2040": "qemu_cortex_m3",
    "raspi-pico": "qemu_cortex_m3",
    "qemu_cortex_m3": "qemu_cortex_m3",
    # Cortex-M33 with the FPU (QEMU mps2-an505). Only by name: it runs the
    # FPU half of the context switch, but it is not a stand-in for any one
    # board, so no board maps to it.
    "qemu_cortex_m33": "qemu_cortex_m33",
}


class SimError(click.ClickException):
    """A failure the developer can act on. Exit code 1, no traceback."""


def _project_board(project_dir: Path) -> Optional[str]:
    eos_yaml = project_dir / "eos.yaml"
    if not eos_yaml.is_file():
        return None
    data = yaml.safe_load(eos_yaml.read_text(encoding="utf-8")) or {}
    system = data.get("system") or {}
    board = system.get("board")
    return str(board) if board else None


def _application(project_dir: Path, config_name: str) -> Dict[str, List[Path]]:
    """Sources and include dirs of the first executable target in build.yaml."""
    cfg_path = project_dir / config_name
    if not cfg_path.is_file():
        raise SimError(f"{cfg_path} not found. Run `ebuild sim` in a project "
                       "created with `ebuild init` or `ebuild new`.")
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    for target in data.get("targets") or []:
        if target.get("type") == "executable":
            sources = [project_dir / s for s in target.get("sources") or []]
            includes = [project_dir / i for i in
                        (target.get("includes") or target.get("include_dirs") or [])]
            missing = [str(s) for s in sources if not s.is_file()]
            if missing:
                raise SimError(f"build.yaml lists sources that do not exist: {missing}")
            if not sources:
                raise SimError("the executable target in build.yaml has no sources")
            return {"sources": sources, "includes": includes}
    raise SimError(f"{cfg_path} has no target of type 'executable' to simulate")


def _eos_root(project_dir: Path) -> Path:
    from ebuild.deps.manager import DepsManager

    root = DepsManager().get_repo_path("eos", project_dir=project_dir)
    if root is None:
        raise SimError("no eos checkout found. Run `ebuild setup` "
                       "(or set EBUILD_EOS_PATH to an eos checkout).")
    return root


def _load_sim_target(eos_root: Path, name: str) -> Dict:
    spec = eos_root / "sim" / name / "sim.yaml"
    if not spec.is_file():
        raise SimError(
            f"{spec} not found. This eos checkout predates the {name} simulation "
            "target. Update it with `ebuild repos update` (or `git pull` in "
            f"{eos_root}).")
    data = yaml.safe_load(spec.read_text(encoding="utf-8")) or {}
    if data.get("schema") != 1:
        raise SimError(f"{spec}: unsupported schema {data.get('schema')!r} (expected 1)")
    return data


def _require_tool(name: str, hint: str) -> str:
    path = shutil.which(name)
    if not path:
        raise SimError(f"{name} not found on PATH. {hint}")
    return path


def build_sim_image(eos_root: Path, spec: Dict, app: Dict[str, List[Path]],
                    out_dir: Path, cc: str, log: Logger) -> Path:
    """Compile eos + the application for the sim target; return the ELF path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    obj_dir = out_dir / "obj"
    obj_dir.mkdir(exist_ok=True)
    includes = [f"-I{eos_root / d}" for d in spec["includes"]]
    includes += [f"-I{d}" for d in app["includes"]]
    sources = [eos_root / s for s in spec["sources"]] + list(app["sources"])
    objects: List[str] = []
    for index, src in enumerate(sources):
        obj = obj_dir / f"{index:02d}_{src.name}.o"
        cmd = [cc, *spec["cflags"], *includes, "-c", str(src), "-o", str(obj)]
        log.debug(" ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise SimError(f"compiling {src} failed:\n{result.stderr.strip()}")
        objects.append(str(obj))
    elf = out_dir / "firmware.elf"
    cmd = [cc, *spec["ldflags"], "-T", str(eos_root / spec["linker_script"]),
           *objects, *spec.get("libs", []), "-o", str(elf)]
    log.debug(" ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise SimError(f"linking {elf} failed:\n{result.stderr.strip()}")
    return elf


def run_qemu(qemu: str, spec: Dict, elf: Path, timeout: float,
             expect: Optional[str], log_path: Path) -> Dict:
    """Run *elf* under QEMU, echoing guest output. Returns a result summary.

    QEMU exits on its own when the guest calls exit() through semihosting,
    and its status is then the guest's status. An RTOS application usually
    never exits, so the run is also bounded by *timeout*.
    """
    import queue
    import threading

    cmd = [qemu, "-M", spec["qemu"]["machine"], *spec["qemu"].get("args", []),
           "-kernel", str(elf)]
    pattern = re.compile(expect) if expect else None
    lines: List[str] = []
    matched = False
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL, text=True, bufsize=1,
                            errors="replace")
    pending: "queue.Queue[Optional[str]]" = queue.Queue()

    def pump() -> None:
        assert proc.stdout is not None
        for raw in proc.stdout:
            pending.put(raw.rstrip("\r\n"))
        pending.put(None)  # EOF: QEMU closed stdout, i.e. it exited

    threading.Thread(target=pump, daemon=True).start()
    deadline = time.monotonic() + timeout
    timed_out = False
    eof = False
    try:
        while not matched:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                break
            try:
                line = pending.get(timeout=min(remaining, 0.25))
            except queue.Empty:
                continue
            if line is None:
                eof = True
                break
            lines.append(line)
            click.echo(line)
            if pattern and pattern.search(line):
                matched = True
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    exited = eof and not matched
    if exited:
        proc.wait()
    return {
        "command": cmd,
        "lines": lines,
        "matched": matched,
        "timed_out": timed_out,
        "guest_exited": exited,
        "exit_code": proc.returncode if exited else None,
    }


def register_commands(cli_group: click.Group) -> None:
    """Add ``init``, ``sim`` and ``platforms`` to the ebuild CLI."""

    @cli_group.command("init")
    @click.argument("project_name")
    @click.option("--template", "template", default="rtos", show_default=True,
                  type=click.Choice(sorted(INIT_TEMPLATES)),
                  help="Project template (guide names; see `ebuild new` for the full set).")
    @click.option("--target", "target", default="generic", show_default=True,
                  help="Target board, e.g. stm32f4, nrf52840, esp32.")
    @click.option("--output-dir", default=None, type=click.Path(),
                  help="Parent directory for the new project.")
    @click.pass_context
    def init(ctx: click.Context, project_name: str, template: str, target: str,
             output_dir: Optional[str]) -> None:
        """Create a new EoS project (the getting-started guide's `ebuild new`).

        Example:

            ebuild init my-blink --template rtos --target stm32f4
        """
        new_cmd = cli_group.commands["new"]
        ctx.invoke(new_cmd, project_name=project_name,
                   template_name=INIT_TEMPLATES[template], board_name=target,
                   output_dir=output_dir)
        if target in SIM_TARGETS:
            click.echo(f"  then: cd {project_name} && ebuild sim")

    @cli_group.command("sim")
    @click.option("--platform", "platform", default=None,
                  help="Board to simulate. Defaults to the board in eos.yaml.")
    @click.option("--config", "config_name", default="build.yaml", show_default=True,
                  help="Project build file, relative to the project directory.")
    @click.option("--timeout", default=10.0, show_default=True, type=float,
                  help="Seconds to let the guest run before stopping it.")
    @click.option("--expect", default=None,
                  help="Regex that must appear in guest output; stop as soon as it does.")
    @click.option("--build-dir", default="_build/sim", show_default=True,
                  help="Where the simulation image and log are written.")
    @click.pass_obj
    def sim(log: Logger, platform: Optional[str], config_name: str, timeout: float,
            expect: Optional[str], build_dir: str) -> None:
        """Build the project for a QEMU machine and run it there.

        Arm Cortex-M boards (stm32f4, stm32h7, nrf52840, rp2040, ...) run on
        QEMU's Cortex-M3 machine (lm3s6965evb) with console output via
        semihosting. This proves the kernel and application logic. It does not
        model the board's own peripherals or timing.

        Needs arm-none-eabi-gcc, qemu-system-arm, and an eos checkout
        (`ebuild setup`).

        Passes when --expect matches, or, with no --expect, when the guest
        printed anything and did not exit with a nonzero status.
        """
        log.header("ebuild — Simulate")
        project_dir = Path.cwd()
        board = platform or _project_board(project_dir)
        if not board:
            raise SimError("no board given: pass --platform or set system.board in eos.yaml")
        target = SIM_TARGETS.get(board)
        if target is None:
            supported = ", ".join(sorted(SIM_TARGETS))
            raise SimError(f"no simulation target for board '{board}' yet. "
                           f"Boards ebuild sim can run: {supported}")
        app = _application(project_dir, config_name)
        eos_root = _eos_root(project_dir)
        spec = _load_sim_target(eos_root, target)
        cc = _require_tool("arm-none-eabi-gcc",
                           "Install the Arm GNU toolchain (Ubuntu: sudo apt install gcc-arm-none-eabi).")
        qemu = _require_tool(spec["qemu"]["binary"],
                             "Install QEMU (Ubuntu: sudo apt install qemu-system-arm).")
        out_dir = (project_dir / build_dir).resolve()
        log.step(f"Building {board} application for {target} ({spec['qemu']['machine']})...")
        elf = build_sim_image(eos_root, spec, app, out_dir, cc, log)
        log.success(f"Image: {elf}")
        log.step(f"Running on {spec['qemu']['machine']} (timeout {timeout:g}s)...")
        result = run_qemu(qemu, spec, elf, timeout, expect, out_dir / "sim.log")
        guest_lines = [line for line in result["lines"] if line.strip()
                       and not line.startswith("qemu-system")]
        if expect:
            if result["matched"]:
                log.success(f"Matched /{expect}/")
                return
            raise SimError(f"/{expect}/ never appeared in guest output "
                           f"(log: {out_dir / 'sim.log'})")
        if result["guest_exited"] and result["exit_code"] not in (0, None):
            raise SimError(f"guest exited with status {result['exit_code']} "
                           f"(log: {out_dir / 'sim.log'})")
        if not guest_lines:
            raise SimError("the image produced no output, so it has not been shown "
                           f"to run (log: {out_dir / 'sim.log'})")
        how = "guest exited 0" if result["guest_exited"] else f"stopped after {timeout:g}s"
        log.success(f"Simulation ran: {len(guest_lines)} line(s) of output, {how}")

    @cli_group.group("platforms")
    def platforms() -> None:
        """Simulation platforms known to EoSim."""

    @platforms.command("list")
    @click.option("--format", "fmt", default="table", show_default=True,
                  type=click.Choice(["table", "names", "json"]))
    def platforms_list(fmt: str) -> None:
        """List EoSim's platform registry (needs the eosim package)."""
        try:
            from eosim.cli.main import _load_registry
        except ImportError as exc:  # pragma: no cover - exercised without eosim
            raise SimError("EoSim is not installed: pip install "
                           "'embeddedos-eosim @ git+https://github.com/embeddedos-org/EoSim'"
                           ) from exc
        entries = sorted(_load_registry().all(), key=lambda p: p.name)
        if not entries:
            raise SimError("EoSim's platform registry is empty")
        if fmt == "names":
            for p in entries:
                click.echo(p.name)
        elif fmt == "json":
            import json
            click.echo(json.dumps([
                {"name": p.name, "arch": p.arch, "vendor": p.vendor,
                 "class": p.platform_class, "ebuild_sim": p.name in SIM_TARGETS}
                for p in entries], indent=2))
        else:
            click.echo(f"{len(entries)} EoSim platforms "
                       "(* = runnable with `ebuild sim`):")
            for p in entries:
                mark = "*" if p.name in SIM_TARGETS else " "
                click.echo(f" {mark} {p.name:<24} {p.arch:<8} {p.vendor or '-'}")
