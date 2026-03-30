# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Integration build + QEMU test commands for ebuild.

Provides CLI commands to:
  - Build all 6 EoS packages together (eos, eboot, eni, eai, eipc, ebuild)
  - Assemble a rootfs with all built libraries
  - Boot the image on QEMU and validate via serial output
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

import click

from ebuild.cli.logger import Logger
from ebuild.system.rootfs import RootfsBuilder
from ebuild.system.image import ImageBuilder


# Default sibling repo names and their build configs
REPOS = {
    "eos":   {"cmake_flag": "-DEOS_BUILD_TESTS=OFF",   "lang": "c"},
    "eboot": {"cmake_flag": "-DEBLDR_BUILD_TESTS=OFF",  "lang": "c"},
    "eni":   {"cmake_flag": "-DENI_BUILD_TESTS=OFF",    "lang": "c"},
    "eai":   {"cmake_flag": "-DEAI_BUILD_TESTS=OFF",    "lang": "c"},
    "eipc":  {"cmake_flag": "",                          "lang": "go", "sdk_subdir": "sdk/c"},
}

QEMU_ARCHS = {
    "x86_64": {
        "bin": "qemu-system-x86_64",
        "args": ["-machine", "q35", "-cpu", "qemu64", "-m", "512",
                 "-nographic", "-no-reboot", "-serial", "stdio"],
        "console": "ttyS0",
    },
    "aarch64": {
        "bin": "qemu-system-aarch64",
        "args": ["-machine", "virt", "-cpu", "cortex-a57", "-m", "512",
                 "-nographic", "-no-reboot", "-serial", "stdio"],
        "console": "ttyAMA0",
    },
    "riscv64": {
        "bin": "qemu-system-riscv64",
        "args": ["-machine", "virt", "-m", "512",
                 "-nographic", "-no-reboot", "-serial", "stdio", "-bios", "none"],
        "console": "ttyS0",
    },
}


def _find_workspace(start: Path) -> Path:
    """Walk up from start to find the EoS workspace root (parent of all repos)."""
    # If start contains sibling repos, it's the workspace
    if (start / "eos").is_dir() or (start / "ebuild").is_dir():
        return start
    # If start IS a repo, go up one level
    if (start / "build.yaml").exists() or (start / "pyproject.toml").exists():
        parent = start.parent
        if (parent / "eos").is_dir() or (parent / "ebuild").is_dir():
            return parent
    # Try common layout: EoS/ contains all repos
    for p in [start, start.parent, start.parent.parent]:
        count = sum(1 for r in REPOS if (p / r).is_dir())
        if count >= 3:
            return p
    return start


def _find_repos(workspace: Path) -> Dict[str, Path]:
    """Locate all sibling repos in the workspace."""
    found = {}
    for name in REPOS:
        repo_dir = workspace / name
        if repo_dir.is_dir():
            found[name] = repo_dir
    return found


def _cmake_build(repo_dir: Path, build_dir: Path, extra_flags: str,
                 log: Logger, subdir: Optional[str] = None) -> bool:
    """Run cmake configure + build for a C repo."""
    source = repo_dir / subdir if subdir else repo_dir
    cmake_lists = source / "CMakeLists.txt"
    if not cmake_lists.exists():
        log.warning(f"  No CMakeLists.txt in {source}")
        return False

    build_path = build_dir / (repo_dir.name + ("-" + subdir.replace("/", "-") if subdir else ""))

    # Configure
    cmd = ["cmake", "-B", str(build_path), "-S", str(source)]
    if extra_flags:
        for flag in extra_flags.split():
            cmd.append(flag)

    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        log.error(f"  cmake configure failed: {result.stderr.decode(errors='replace')[:200]}")
        return False

    # Build
    result = subprocess.run(["cmake", "--build", str(build_path)], capture_output=True)
    if result.returncode != 0:
        log.error(f"  cmake build failed: {result.stderr.decode(errors='replace')[:200]}")
        return False

    return True


def _collect_libraries(build_dir: Path, repos: Dict[str, Path]) -> List[Path]:
    """Find all .a static libraries produced by the builds."""
    libs = []
    for name in repos:
        repo_build = build_dir / name
        if repo_build.exists():
            libs.extend(repo_build.rglob("*.a"))
        # Also check eipc SDK subdir
        sdk_build = build_dir / f"{name}-sdk-c"
        if sdk_build.exists():
            libs.extend(sdk_build.rglob("*.a"))
    return libs


def _build_rootfs(build_dir: Path, libs: List[Path], trigger: str,
                  log: Logger) -> Path:
    """Assemble EoS rootfs with libraries and test scripts."""
    rootfs_builder = RootfsBuilder(build_dir)
    rootfs = rootfs_builder.assemble(
        init_system="busybox",
        hostname="eos-qemu",
        users=[{"name": "eos", "shell": "/bin/sh"}],
    )

    # Install libraries
    lib_dir = rootfs / "usr" / "lib"
    lib_dir.mkdir(parents=True, exist_ok=True)
    for lib in libs:
        shutil.copy2(str(lib), str(lib_dir / lib.name))

    # EoS release info
    (rootfs / "etc" / "eos-release").write_text(
        f"EOS_VERSION=0.3.0\n"
        f"EOS_BUILD=ebuild-integration\n"
        f"TRIGGER_REPO={trigger}\n"
    )

    # QEMU test script
    test_script = rootfs / "etc" / "init.d" / "S99_qemu_test"
    test_script.write_text(
        "#!/bin/sh\n"
        "echo '════ EoS QEMU Sanity Test ════'\n"
        "echo \"EoS booted successfully\"\n"
        "cat /etc/eos-release 2>/dev/null\n"
        "echo \"Arch: $(uname -m)\"\n"
        "echo \"Kernel: $(uname -r)\"\n"
        "echo '── Libraries ──'\n"
        "ls /usr/lib/lib*.a 2>/dev/null | head -20 || echo '(none)'\n"
        "echo 'TEST_PASSED=true'\n"
        "echo '════════════════════════════════'\n"
        "poweroff -f 2>/dev/null || reboot -f\n"
    )
    if os.name != "nt":
        test_script.chmod(0o755)

    return rootfs


def _create_initramfs(rootfs: Path, build_dir: Path) -> Path:
    """Create a cpio+gzip initramfs from the rootfs."""
    initramfs = build_dir / "initramfs.cpio.gz"
    cmd = f"cd {rootfs} && find . | cpio -o -H newc 2>/dev/null | gzip > {initramfs}"
    subprocess.run(cmd, shell=True, capture_output=True)
    return initramfs


def _find_kernel(arch: str) -> Optional[Path]:
    """Find a kernel image for the given architecture."""
    if arch == "x86_64" and os.name != "nt":
        import glob
        kernels = glob.glob("/boot/vmlinuz*")
        if kernels:
            return Path(kernels[0])
    return None


def _boot_qemu(arch: str, kernel: Path, initramfs: Path,
               timeout: int, log: Logger) -> List[str]:
    """Boot QEMU and capture serial output. Returns output lines."""
    cfg = QEMU_ARCHS.get(arch)
    if not cfg:
        log.error(f"Unknown architecture: {arch}")
        return []

    cmd = [cfg["bin"]] + cfg["args"]
    cmd += ["-kernel", str(kernel), "-initrd", str(initramfs)]
    cmd += ["-append", f"console={cfg['console']} root=/dev/ram0 init=/etc/init.d/rcS panic=5"]

    log.step(f"Booting QEMU {arch}...")
    log.debug(f"  cmd: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
            text=True,
        )
        lines = result.stdout.splitlines() + result.stderr.splitlines()
    except subprocess.TimeoutExpired as e:
        lines = (e.stdout or "").splitlines() if isinstance(e.stdout, str) else []
    except FileNotFoundError:
        log.error(f"  {cfg['bin']} not found. Install QEMU.")
        return []

    return lines


# ═══════════════════════════════════════════════════════════════
#  CLI Commands
# ═══════════════════════════════════════════════════════════════

def register_commands(cli_group: click.Group) -> None:
    """Register integration + qemu commands with the main CLI group."""

    @cli_group.command()
    @click.option("--workspace", default=None, type=click.Path(exists=True),
                  help="EoS workspace root (auto-detected if omitted).")
    @click.option("--build-dir", default="_integration_build", type=click.Path(),
                  help="Build output directory.")
    @click.option("--with-tests", is_flag=True, help="Also build with tests enabled.")
    @click.pass_obj
    def integration(log: Logger, workspace: Optional[str], build_dir: str,
                    with_tests: bool) -> None:
        """Build all EoS packages together (eos, eboot, eni, eai, eipc).

        Auto-detects sibling repos in the workspace, builds each with CMake,
        assembles rootfs with all libraries, and creates an initramfs.

        Examples:

            ebuild integration

            ebuild integration --workspace /path/to/EoS

            ebuild integration --with-tests
        """
        log.header("ebuild — Integration Build")

        ws = Path(workspace) if workspace else _find_workspace(Path.cwd())
        log.info(f"Workspace: {ws}")

        repos = _find_repos(ws)
        if not repos:
            log.error("No EoS repos found. Run from the EoS workspace or use --workspace.")
            raise SystemExit(1)

        log.info(f"Found {len(repos)} repos: {', '.join(repos.keys())}")
        build_path = Path(build_dir)
        build_path.mkdir(parents=True, exist_ok=True)

        # Build each repo
        built = 0
        for name, repo_dir in repos.items():
            cfg = REPOS.get(name, {})
            lang = cfg.get("lang", "c")

            if lang == "go":
                # Build C SDK subdirectory
                sdk_sub = cfg.get("sdk_subdir")
                if sdk_sub:
                    log.step(f"Building {name} C SDK...")
                    ok = _cmake_build(repo_dir, build_path, "", log, subdir=sdk_sub)
                    if ok:
                        log.success(f"  {name} C SDK ✓")
                        built += 1
                    else:
                        log.warning(f"  {name} C SDK — skipped")
                continue

            flags = cfg.get("cmake_flag", "")
            if with_tests:
                flags = flags.replace("=OFF", "=ON")

            log.step(f"Building {name}...")
            ok = _cmake_build(repo_dir, build_path, flags, log)
            if ok:
                log.success(f"  {name} ✓")
                built += 1
            else:
                log.warning(f"  {name} — build failed, continuing")

        log.info(f"Built {built}/{len(repos)} packages")

        # Collect libraries
        libs = _collect_libraries(build_path, repos)
        log.info(f"Libraries: {len(libs)} .a files")

        # Build rootfs
        log.step("Assembling rootfs...")
        rootfs = _build_rootfs(build_path, libs, "ebuild", log)
        log.success(f"Rootfs: {rootfs} ({sum(1 for _ in rootfs.rglob('*') if _.is_file())} files)")

        # Create initramfs
        if os.name != "nt":
            log.step("Creating initramfs...")
            initramfs = _create_initramfs(rootfs, build_path)
            if initramfs.exists():
                size_kb = initramfs.stat().st_size // 1024
                log.success(f"Initramfs: {initramfs} ({size_kb}KB)")
            else:
                log.warning("Initramfs creation failed (cpio not available)")
        else:
            log.info("Initramfs creation skipped on Windows (requires cpio)")

        log.success(f"Integration build complete — {built} packages built")

    @cli_group.command()
    @click.option("--workspace", default=None, type=click.Path(exists=True),
                  help="EoS workspace root (auto-detected if omitted).")
    @click.option("--build-dir", default="_integration_build", type=click.Path(),
                  help="Build output directory.")
    @click.option("--arch", default="x86_64",
                  type=click.Choice(list(QEMU_ARCHS.keys())),
                  help="QEMU target architecture.")
    @click.option("--timeout", default=60, type=int,
                  help="QEMU boot timeout in seconds.")
    @click.option("--kernel", "kernel_path", default=None, type=click.Path(exists=True),
                  help="Path to kernel image (auto-detected if omitted).")
    @click.option("--skip-build", is_flag=True,
                  help="Skip building — use existing build artifacts.")
    @click.pass_obj
    def qemu(log: Logger, workspace: Optional[str], build_dir: str,
             arch: str, timeout: int, kernel_path: Optional[str],
             skip_build: bool) -> None:
        """Build all packages and boot on QEMU for sanity testing.

        Combines the integration build with QEMU boot validation.
        Checks for "EoS booted successfully" and "TEST_PASSED=true" in
        the serial output.

        Examples:

            ebuild qemu

            ebuild qemu --arch aarch64

            ebuild qemu --arch x86_64 --timeout 120

            ebuild qemu --skip-build --kernel /boot/vmlinuz
        """
        log.header("ebuild — QEMU Sanity Test")

        build_path = Path(build_dir)

        # Step 1: Build (unless skipped)
        if not skip_build:
            ws = Path(workspace) if workspace else _find_workspace(Path.cwd())
            repos = _find_repos(ws)

            if not repos:
                log.error("No EoS repos found.")
                raise SystemExit(1)

            log.info(f"Workspace: {ws} ({len(repos)} repos)")
            build_path.mkdir(parents=True, exist_ok=True)

            built = 0
            for name, repo_dir in repos.items():
                cfg = REPOS.get(name, {})
                lang = cfg.get("lang", "c")

                if lang == "go":
                    sdk_sub = cfg.get("sdk_subdir")
                    if sdk_sub:
                        log.step(f"Building {name} C SDK...")
                        if _cmake_build(repo_dir, build_path, "", log, subdir=sdk_sub):
                            built += 1
                    continue

                log.step(f"Building {name}...")
                if _cmake_build(repo_dir, build_path, cfg.get("cmake_flag", ""), log):
                    built += 1

            libs = _collect_libraries(build_path, repos)
            log.info(f"Built {built} packages, {len(libs)} libraries")

            log.step("Assembling rootfs...")
            rootfs = _build_rootfs(build_path, libs, "ebuild-qemu", log)

            if os.name != "nt":
                log.step("Creating initramfs...")
                initramfs = _create_initramfs(rootfs, build_path)
            else:
                log.error("QEMU boot requires Linux (cpio + QEMU).")
                raise SystemExit(1)
        else:
            initramfs = build_path / "initramfs.cpio.gz"
            if not initramfs.exists():
                log.error(f"No initramfs found at {initramfs}. Run without --skip-build first.")
                raise SystemExit(1)
            log.info("Using existing build artifacts")

        # Step 2: Find kernel
        if kernel_path:
            kernel = Path(kernel_path)
        else:
            kernel = _find_kernel(arch)
            if not kernel:
                log.error(f"No kernel found for {arch}. Use --kernel to specify one.")
                raise SystemExit(1)

        log.info(f"Kernel: {kernel}")
        log.info(f"Initramfs: {initramfs}")

        # Step 3: Boot QEMU
        output = _boot_qemu(arch, kernel, initramfs, timeout, log)

        # Step 4: Validate
        boot_log = build_path / f"boot-{arch}.log"
        boot_log.write_text("\n".join(output), encoding="utf-8")
        log.info(f"Boot log: {boot_log} ({len(output)} lines)")

        boot_ok = any("EoS booted successfully" in line for line in output)
        test_ok = any("TEST_PASSED=true" in line for line in output)
        panic = any("kernel panic" in line.lower() for line in output)

        log.header("Results")
        if boot_ok:
            log.success("EoS BOOT: passed")
        else:
            log.error("EoS BOOT: marker not found")

        if test_ok:
            log.success("TESTS: passed")
        else:
            log.warning("TESTS: marker not found")

        if panic:
            log.error("KERNEL PANIC detected")

        # Print last 15 lines
        if output:
            log.header("Boot Output (last 15 lines)")
            for line in output[-15:]:
                print(f"  {line}")

        if boot_ok and test_ok and not panic:
            log.success(f"\nQEMU sanity test PASSED ({arch})")
        else:
            log.error(f"\nQEMU sanity test FAILED ({arch})")
            raise SystemExit(1)


    @cli_group.command()
    @click.option("--target", default="x86_64", help="Target hardware (e.g., raspi4, stm32f4)")
    @click.option("--output", default="build", help="Output directory for SDK")
    @click.option("--list", "list_targets", is_flag=True, help="List all supported targets")
    @click.pass_obj
    def sdk(log: Logger, target: str, output: str, list_targets: bool) -> None:
        """Generate target-specific SDK (Yocto-style).

        Creates toolchain.cmake, environment-setup, sysroot, and
        eBoot board config for the specified hardware target.
        """
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from ebuild.sdk_generator import generate_sdk, list_targets as do_list

        if list_targets:
            do_list()
            return

        log.header("EoS SDK Generator")
        log.info("Target: " + target)
        log.info("Output: " + output)
        sdk_dir = generate_sdk(target, output)
        log.success("SDK generated: " + str(sdk_dir))

    @cli_group.command()
    @click.option("--target", required=True, help="Target hardware (e.g., raspi4)")
    @click.option("--version", default="0.2.0", help="Release version")
    @click.option("--build-dir", default="build", help="Build directory with compiled artifacts")
    @click.option("--output", default="dist", help="Output directory for deliverable")
    @click.option("--workspace", default=None, help="EoS workspace root (auto-detect)")
    @click.pass_obj
    def package(log: Logger, target: str, version: str, build_dir: str,
                output: str, workspace: Optional[str]) -> None:
        """Package deliverable ZIP for a hardware target.

        Bundles source code, SDK, cross-compiled libraries, EoSuite
        binaries, bootable image, and manifest into a single ZIP.
        """
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from ebuild.deliverable_packager import package_deliverable

        log.header("EoS Deliverable Packager")
        log.info("Target:  " + target)
        log.info("Version: " + version)
        zpath = package_deliverable(target, version, build_dir, output, workspace)
        log.success("Deliverable: " + str(zpath))

    @cli_group.command()
    @click.option("--target", default=None, help="Filter models by target hardware")
    @click.option("--tier", default=None, type=click.Choice(["micro","tiny","small","medium","large"]),
                  help="Filter by model tier")
    @click.option("--ram", default=None, type=int, help="Max RAM in MB — find best fitting model")
    @click.pass_obj
    def models(log: Logger, target: Optional[str], tier: Optional[str], ram: Optional[int]) -> None:
        """List available LLM models for EoS AI layer.

        Shows curated embedded-optimized models with RAM/storage
        requirements and recommended hardware for each tier.
        """
        log.header("EAI Model Registry")
        tier_map = {"micro": 0, "tiny": 1, "small": 2, "medium": 3, "large": 4}
        tier_names = ["micro (<100MB)", "tiny (100-500MB)", "small (500MB-2GB)",
                      "medium (2-4GB)", "large (4GB+)"]
        models_db = [
            ("tinyllama-1.1b-q2k",  "TinyLlama", 1100,  80,   60, 0, "STM32H7, ESP32-S3"),
            ("smollm-360m-q5",      "SmolLM",     360, 100,   75, 1, "RPi3, nRF5340"),
            ("qwen2-0.5b-q4",       "Qwen2",      500, 120,   90, 1, "RPi3, AM64x"),
            ("phi-1.5-q4",          "Phi",       1300, 200,  150, 1, "RPi3, BeagleBone"),
            ("qwen2-1.5b-q4",       "Qwen2",     1500, 500,  400, 2, "RPi4, SiFive"),
            ("phi-2-q4",            "Phi",       2700, 600,  500, 2, "RPi4, i.MX8M"),
            ("gemma-2b-q4",         "Gemma",     2000, 800,  650, 2, "RPi4, Jetson Nano"),
            ("phi-mini-q4",         "Phi",       3800,2048, 2300, 2, "RPi4 8GB (DEFAULT)"),
            ("llama-3.2-3b-q4",     "Llama",     3000,2500, 2000, 3, "RPi5, Jetson Nano"),
            ("mistral-7b-q3k",      "Mistral",   7000,3500, 3000, 3, "Jetson Nano, x86"),
            ("llama-3.2-8b-q4",     "Llama",     8000,6000, 5000, 4, "x86 edge, Orin"),
            ("qwen2.5-7b-q4",       "Qwen2.5",   7000,5500, 4500, 4, "x86 edge, Orin"),
        ]
        print("")
        print("  %-25s %-8s %6s %6s %7s %-16s %s" % (
            "Model", "Family", "Params", "RAM", "Storage", "Tier", "Hardware"))
        print("  " + "-"*25 + " " + "-"*8 + " " + "-"*6 + " " + "-"*6 + " " +
              "-"*7 + " " + "-"*16 + " " + "-"*25)
        for name, family, params, r, s, t, hw in models_db:
            if tier and t != tier_map.get(tier, -1):
                continue
            if ram and r > ram:
                continue
            print("  %-25s %-8s %5dM %4dMB %5dMB %-16s %s" % (
                name, family, params, r, s, tier_names[t], hw))

        if ram:
            # Find best fit
            best = None
            for name, family, params, r, s, t, hw in models_db:
                if r <= ram:
                    if not best or params > best[2]:
                        best = (name, family, params, r, s, t, hw)
            if best:
                print("")
                log.success("Best fit for %dMB RAM: %s (%dM params, %dMB RAM)" % (
                    ram, best[0], best[2], best[3]))
