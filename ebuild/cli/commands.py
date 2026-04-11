# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""CLI commands for ebuild using Click.

Provides build, clean, configure, info, install, add, list-packages,
pipeline, and hardware analysis commands.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ebuild.eos_ai.eos_hw_analyzer import HardwareProfile

import click
import yaml

from ebuild import __version__
from ebuild.build.ninja_backend import NinjaBackend, PackagePaths
from ebuild.build.toolchain import resolve_toolchain
from ebuild.cli.logger import Logger
from ebuild.core.config import ConfigError, load_config, ProjectConfig
from ebuild.core.graph import CycleError, build_dependency_graph
from ebuild.packages.builder import BuildError, PackageBuilder
from ebuild.packages.cache import PackageCache
from ebuild.packages.fetcher import FetchError, PackageFetcher
from ebuild.packages.lockfile import Lockfile
from ebuild.packages.recipe import RecipeError
from ebuild.packages.registry import create_registry
from ebuild.packages.resolver import PackageResolver, ResolveError


pass_logger = click.make_pass_decorator(Logger, ensure=True)

# Default recipe search paths (relative to project root)
_RECIPE_DIRS = ["recipes"]


def _find_recipe_dirs(project_dir: Path) -> List[Path]:
    """Locate recipe directories: project-local and install-level."""
    dirs = []
    for name in _RECIPE_DIRS:
        d = project_dir / name
        if d.is_dir():
            dirs.append(d)

    # Also check ebuild install location
    pkg_recipes = Path(__file__).resolve().parent.parent.parent / "recipes"
    if pkg_recipes.is_dir() and pkg_recipes not in dirs:
        dirs.append(pkg_recipes)

    return dirs


def _install_packages(
    cfg: ProjectConfig,
    build_dir: Path,
    log: Logger,
    verbose: bool = False,
) -> Dict[str, PackagePaths]:
    """Resolve, fetch, build, and return PackagePaths for all declared packages.

    Returns a dict mapping package name to PackagePaths for use by NinjaBackend.
    """
    if not cfg.packages:
        return {}

    log.step("Resolving packages...")

    recipe_dirs = _find_recipe_dirs(cfg.source_dir)
    if not recipe_dirs:
        log.warning("No recipe directories found. Create a 'recipes/' directory.")
        return {}

    registry = create_registry(*recipe_dirs)
    log.debug(f"Registry: {registry.package_count} recipes from {[str(p) for p in registry.search_paths]}")

    resolver = PackageResolver(registry)
    requested = [{"name": p.name, "version": p.version} for p in cfg.packages]
    resolved = resolver.resolve(requested)

    log.info(f"Packages to install: {', '.join(r.name + ' v' + r.version for r in resolved)}")

    # Lockfile
    lock_path = cfg.source_dir / Lockfile.FILENAME
    lockfile = Lockfile(lock_path)

    # Cache and fetcher
    pkg_cache_dir = build_dir / "packages"
    cache = PackageCache(pkg_cache_dir)
    fetcher = PackageFetcher(pkg_cache_dir / "_downloads")

    # Build each package in order
    builder = PackageBuilder(cache, verbose=verbose)
    install_dirs: Dict[str, Path] = {}

    for recipe in resolved:
        if cache.is_built(recipe):
            log.info(f"  {recipe.name} v{recipe.version} — cached ✓")
            install_dirs[recipe.name] = cache.install_dir(recipe)
            continue

        log.step(f"  Fetching {recipe.name} v{recipe.version}...")
        fetcher.fetch(recipe, cache.src_dir(recipe))

        log.step(f"  Building {recipe.name} v{recipe.version}...")
        dep_dirs = [install_dirs[dep] for dep in recipe.dependencies if dep in install_dirs]
        install_dir = builder.build(recipe, dep_install_dirs=dep_dirs)
        install_dirs[recipe.name] = install_dir
        log.success(f"  {recipe.name} v{recipe.version} — built ✓")

    # Update lockfile
    lockfile.lock(resolved)
    lockfile.save()
    log.debug(f"Lockfile written: {lock_path}")

    # Build PackagePaths for ninja
    package_paths: Dict[str, PackagePaths] = {}
    for recipe in resolved:
        idir = install_dirs.get(recipe.name)
        if idir:
            inc = idir / "include"
            lib = idir / "lib"
            libs = _detect_libraries(lib, recipe.name)
            package_paths[recipe.name] = PackagePaths(
                include_dirs=[inc] if inc.exists() else [],
                lib_dirs=[lib] if lib.exists() else [],
                libraries=libs,
            )

    return package_paths


def _detect_libraries(lib_dir: Path, pkg_name: str) -> List[str]:
    """Detect installed library names from a lib/ directory."""
    if not lib_dir.exists():
        return [pkg_name]

    libs = []
    for f in sorted(lib_dir.iterdir()):
        name = f.name
        if name.startswith("lib") and (name.endswith(".a") or name.endswith(".so")):
            lib_name = name[3:]  # strip "lib"
            if lib_name.endswith(".a"):
                lib_name = lib_name[:-2]
            elif lib_name.endswith(".so"):
                lib_name = lib_name[:-3]
            if lib_name and lib_name not in libs:
                libs.append(lib_name)

    return libs if libs else [pkg_name]


# ═══════════════════════════════════════════════════════════════
#  Pipeline helper — shared by `pipeline` and `build --board`
# ═══════════════════════════════════════════════════════════════

def _run_pipeline_steps(
    board: str,
    hardware: Optional[str],
    build_dir: Path,
    log: Logger,
) -> Tuple[Any, Dict[str, Path], Dict[str, Path]]:
    """Run the full pipeline: analyze -> generate configs -> generate eboot -> generate SDK.

    Returns (profile, config_outputs, boot_outputs).
    """
    from ebuild.eos_ai.eos_hw_analyzer import EosHardwareAnalyzer
    from ebuild.eos_ai.eos_config_generator import EosConfigGenerator
    from ebuild.eos_ai.eos_boot_integrator import EosBootIntegrator
    from ebuild.sdk_generator import generate_sdk

    configs_dir = build_dir / "configs"
    sdk_dir = build_dir / "sdk"
    configs_dir.mkdir(parents=True, exist_ok=True)
    sdk_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Analyze hardware
    log.step("[1/6] Analyzing hardware...")
    analyzer = EosHardwareAnalyzer()

    if hardware:
        hw_path = Path(hardware)
        if not hw_path.exists():
            raise FileNotFoundError("Hardware file not found: " + hardware)
        log.info("  Reading hardware design: " + str(hw_path))
        profile = analyzer.interpret_file(str(hw_path))
    else:
        log.info("  Using board name: " + board)
        profile = analyzer.interpret_text(board)

    # Override MCU from --board if the profile didn't detect one
    if board and (not profile.mcu or profile.mcu.lower() != board.lower()):
        mcu_info = analyzer.MCU_DATABASE.get(board.lower())
        if mcu_info:
            profile.mcu = board.upper()
            profile.arch = mcu_info["arch"]
            profile.core = mcu_info["core"]
            profile.vendor = mcu_info["vendor"]
            profile.mcu_family = mcu_info["family"]

    log.info("  MCU: " + profile.mcu + " (" + profile.core + ")")
    log.info("  Arch: " + profile.arch)
    log.info("  Peripherals: " + str(len(profile.peripherals)) + " detected")

    # Step 2: Generate configs (board.yaml, boot.yaml, build.yaml, eos_product_config.h)
    log.step("[2/6] Generating configs...")
    config_gen = EosConfigGenerator(str(configs_dir))
    config_outputs = config_gen.generate_all(profile)
    for name, path in config_outputs.items():
        log.success("  " + name + ": " + str(path))

    # Step 3: Generate eboot integration (flash layout, linker, pack script, cmake defs)
    log.step("[3/6] Generating eboot integration files...")
    integrator = EosBootIntegrator(str(configs_dir))
    boot_outputs = integrator.generate_from_boot_yaml(str(config_outputs["boot"]))
    for name, path in boot_outputs.items():
        log.success("  " + name + ": " + str(path))

    # Step 4: Generate SDK (toolchain.cmake, environment-setup, eboot target config)
    log.step("[4/6] Generating SDK...")
    target_name = board.lower()
    generate_sdk(target_name, str(sdk_dir))
    log.success("  SDK generated in " + str(sdk_dir))

    # Step 5: Copy generated headers to build include path
    log.step("[5/6] Copying headers to build include path...")
    include_dir = build_dir / "include" / "generated"
    include_dir.mkdir(parents=True, exist_ok=True)

    for header_name in ["eos_product_config.h", "eboot_flash_layout.h"]:
        src = configs_dir / header_name
        if src.exists():
            dst = include_dir / header_name
            shutil.copy2(str(src), str(dst))
            log.info("  " + header_name + " -> " + str(dst))

    return profile, config_outputs, boot_outputs


def _run_cmake_build(profile, board, source_dir, build_dir, log):
    """Run cmake configure + build with EOS_ENABLE_* defines injected."""
    from ebuild.build.dispatch import BackendDispatcher

    enables = profile.get_eos_enables()
    cmake_defines = {}
    cmake_defines["EOS_BOARD"] = board.lower()
    cmake_defines["EOS_ARCH"] = profile.arch or "arm"
    cmake_defines["EOS_CORE"] = profile.core or "cortex-m4"

    for flag, val in enables.items():
        cmake_defines[flag] = "ON" if val else "OFF"

    # Point cmake to generated config headers
    gen_include = build_dir / "include" / "generated"
    if gen_include.exists():
        cmake_defines["EOS_GENERATED_INCLUDE_DIR"] = str(gen_include).replace("\\", "/")

    # Point to eboot cmake defs if present
    eboot_cmake = build_dir / "configs" / "eboot_config.cmake"
    if eboot_cmake.exists():
        cmake_defines["EBOOT_CONFIG_FILE"] = str(eboot_cmake).replace("\\", "/")

    log.step("[6/6] Building with cmake...")
    log.info("  Defines: " + str(len(cmake_defines)) + " cmake variables")

    dispatcher = BackendDispatcher(source_dir, build_dir)

    log.step("  Configuring (cmake)...")
    dispatcher.configure(backend="cmake", config={"defines": cmake_defines})

    log.step("  Building (cmake)...")
    dispatcher.build(backend="cmake", config={})


def _run_pack_image(build_dir, log):
    """Run pack_image.sh if it exists and firmware output is present."""
    pack_script = build_dir / "configs" / "pack_image.sh"
    if not pack_script.exists():
        return

    firmware_candidates = list(build_dir.glob("*.bin")) + list(build_dir.glob("*.elf"))
    if not firmware_candidates:
        log.info("No firmware binary found -- skipping image packing.")
        return

    firmware = firmware_candidates[0]
    log.step("Packing firmware image: " + firmware.name + "...")

    if os.name == "nt":
        log.info("  Pack script is a bash script -- skipping on Windows.")
        log.info("  Run manually: bash " + str(pack_script) + " " + str(firmware))
    else:
        try:
            subprocess.run(
                ["bash", str(pack_script), str(firmware)],
                check=True,
                cwd=str(build_dir),
            )
            log.success("  Firmware image packed.")
        except subprocess.CalledProcessError as e:
            log.warning("  Pack script failed: " + str(e))


def _get_target_class(board):
    """Look up the target class (mcu, sbc, soc, pc, virtual, devboard) for a board."""
    from ebuild.sdk_generator import TARGET_ARCH
    info = TARGET_ARCH.get(board.lower())
    if info:
        return info.get("class", "mcu")
    return "mcu"


def _generate_image(board, build_dir, log):
    """Generate a testable image based on target class.

    MCU targets: handled by _run_pack_image() (firmware .bin).
    Linux-class targets: assemble rootfs + create tar.gz disk image.
    """
    from ebuild.system.rootfs import RootfsBuilder
    from ebuild.system.image import ImageBuilder

    target_class = _get_target_class(board)

    if target_class == "mcu":
        _run_pack_image(build_dir, log)
        return None

    # Linux-class target: assemble rootfs + create disk image
    log.step("[7/7] Generating system image...")

    # Assemble rootfs skeleton
    log.info("  Assembling rootfs...")
    rootfs_builder = RootfsBuilder(build_dir)
    rootfs_dir = rootfs_builder.assemble(
        init_system="busybox",
        hostname="eos-" + board.lower(),
    )
    log.success("  Rootfs assembled: " + str(rootfs_dir))

    # Copy built libraries into rootfs
    lib_dest = rootfs_dir / "usr" / "lib" / "eos"
    lib_dest.mkdir(parents=True, exist_ok=True)
    lib_count = 0
    for lib_file in build_dir.glob("*.a"):
        shutil.copy2(str(lib_file), str(lib_dest / lib_file.name))
        lib_count += 1
    # Also check subdirectories for libraries
    for lib_file in build_dir.rglob("*.a"):
        dest = lib_dest / lib_file.name
        if not dest.exists():
            shutil.copy2(str(lib_file), str(dest))
            lib_count += 1
    if lib_count > 0:
        log.info("  Installed " + str(lib_count) + " libraries into rootfs")

    # Copy generated headers into rootfs
    gen_include = build_dir / "include" / "generated"
    if gen_include.exists():
        inc_dest = rootfs_dir / "usr" / "include" / "eos"
        inc_dest.mkdir(parents=True, exist_ok=True)
        header_count = 0
        for header in gen_include.glob("*.h"):
            shutil.copy2(str(header), str(inc_dest / header.name))
            header_count += 1
        if header_count > 0:
            log.info("  Installed " + str(header_count) + " headers into rootfs")

    # Copy SDK info into rootfs
    sdk_dir = build_dir / "sdk"
    if sdk_dir.exists():
        sdk_dest = rootfs_dir / "opt" / "eos-sdk"
        sdk_dest.mkdir(parents=True, exist_ok=True)
        for item in sdk_dir.rglob("*"):
            if item.is_file():
                rel = item.relative_to(sdk_dir)
                dest = sdk_dest / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(item), str(dest))

    # Create disk image (tar.gz — cross-platform, always works)
    log.info("  Creating disk image...")
    imager = ImageBuilder(build_dir, log=log)
    image_path = imager.create(
        rootfs_dir=rootfs_dir,
        image_format="tar",
        label="eos-" + board.lower(),
    )
    log.success("  Image created: " + str(image_path))

    # Report image size
    if image_path.exists():
        size_kb = image_path.stat().st_size // 1024
        if size_kb > 1024:
            log.info("  Size: " + str(size_kb // 1024) + " MB")
        else:
            log.info("  Size: " + str(size_kb) + " KB")

    return image_path


@click.group()
@click.version_option(version=__version__, prog_name="ebuild")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output.")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """ebuild — A unified embedded OS build system."""
    ctx.ensure_object(dict)
    ctx.obj = Logger(verbose=verbose)


@cli.command()
@click.option(
    "--config", "config_path",
    default="build.yaml",
    type=click.Path(exists=False),
    help="Path to the build configuration file.",
)
@click.option(
    "--build-dir",
    default="_build",
    type=click.Path(),
    help="Build output directory.",
)
@click.option(
    "--backend",
    default=None,
    type=click.Choice(["auto", "cmake", "make", "meson", "cargo", "ninja", "kbuild"]),
    help="Force a specific build backend.",
)
@click.option(
    "--board",
    default=None,
    help="Target board name (e.g., stm32f4, nrf52). Triggers full pipeline before build.",
)
@click.option(
    "--hardware",
    default=None,
    type=click.Path(exists=True),
    help="Hardware design file (.kicad_sch, .sch, .csv). Used with --board for analysis.",
)
@click.pass_obj
def build(log: Logger, config_path: str, build_dir: str, backend: Optional[str],
          board: Optional[str], hardware: Optional[str]) -> None:
    """Parse config, detect backend, and build the project.

    When --board is provided, runs the full pipeline (analyze -> generate ->
    build) before the normal cmake build. Generated configs are stored in
    _build/configs/ and EOS_ENABLE_* defines are passed to cmake automatically.
    """
    log.header("ebuild — Build")

    build_path = Path(build_dir)

    try:
        # Pipeline mode: --board triggers full analyze -> generate -> build
        if board:
            log.info("Board pipeline mode: " + board)

            profile, config_outputs, boot_outputs = _run_pipeline_steps(
                board=board,
                hardware=hardware,
                build_dir=build_path,
                log=log,
            )

            source_dir = Path(".")
            if (source_dir / "CMakeLists.txt").exists():
                _run_cmake_build(profile, board, source_dir, build_path, log)
            else:
                log.info("No CMakeLists.txt found -- pipeline steps complete (no cmake build).")

            _generate_image(board, build_path, log)

            log.success("Build completed successfully (pipeline mode).")
            return

        # Normal mode: standard config-based build
        log.step("Loading configuration...")
        cfg = load_config(config_path)
        log.info(f"Project: {cfg.name} v{cfg.version}")

        build_path = Path(build_dir)
        resolved_backend = backend or cfg.backend

        # Auto-detect from project files if needed
        if resolved_backend == "auto":
            from ebuild.build.dispatch import detect_backend
            resolved_backend = detect_backend(cfg.source_dir)
            log.info(f"Auto-detected backend: {resolved_backend}")

        # Route: external build systems (cmake, make, meson, cargo, kbuild)
        # go through the dispatcher. ebuild's own ninja backend handles
        # projects with targets defined in build.yaml.
        if resolved_backend != "ninja" or not cfg.targets:
            from ebuild.build.dispatch import BackendDispatcher

            log.step(f"Using {resolved_backend} backend...")
            dispatcher = BackendDispatcher(cfg.source_dir, build_path)

            # Tier 2+3: configure first
            from ebuild.build.dispatch import TIER_1
            if resolved_backend not in TIER_1:
                log.step(f"Configuring ({resolved_backend})...")
                dispatcher.configure(
                    backend=resolved_backend,
                    config=cfg.backend_config,
                )

            # Build
            log.step(f"Building ({resolved_backend})...")
            dispatcher.build(
                backend=resolved_backend,
                config=cfg.backend_config,
            )

            log.success(f"Build completed successfully ({resolved_backend}).")
            return

        # ebuild's own Ninja backend path (build.yaml with targets)
        log.step("Resolving dependency graph...")
        graph = build_dependency_graph(cfg.targets)
        build_order = graph.topological_sort()
        log.debug(f"Build order: {' → '.join(build_order)}")

        log.step("Resolving toolchain...")
        compiler = resolve_toolchain(cfg.toolchain)
        log.debug(f"Compiler: {compiler.cc}")

        # Install packages if any are declared
        package_paths = _install_packages(cfg, build_path, log, verbose=log.verbose)

        log.step(f"Generating build.ninja in {build_path}/...")
        ninja_backend = NinjaBackend(cfg, build_path, compiler, package_paths=package_paths)
        ninja_backend.generate()
        log.success(f"Generated {build_path / 'build.ninja'}")
        log.success(f"Generated {build_path / 'compile_commands.json'}")

        log.step("Invoking ninja...")
        ninja_cmd = [sys.executable, "-m", "ninja", "-f", str(build_path / "build.ninja")]
        if log.verbose:
            ninja_cmd.append("-v")

        result = subprocess.run(ninja_cmd, capture_output=not log.verbose, cwd=str(cfg.source_dir))
        if result.returncode != 0:
            if not log.verbose and result.stderr:
                log.error(result.stderr.decode(errors="replace"))
            log.error("Build failed.")
            raise SystemExit(1)

        log.success("Build completed successfully.")

    except FileNotFoundError as e:
        log.error(str(e))
        raise SystemExit(1)
    except (ConfigError, RecipeError) as e:
        log.error(f"Configuration error: {e}")
        raise SystemExit(1)
    except CycleError as e:
        log.error(f"Dependency error: {e}")
        raise SystemExit(1)
    except (ResolveError, FetchError, BuildError) as e:
        log.error(f"Package error: {e}")
        raise SystemExit(1)
    except RuntimeError as e:
        log.error(str(e))
        raise SystemExit(1)


@cli.command()
@click.option(
    "--board",
    required=True,
    help="Target board name (e.g., stm32f4, nrf52, stm32h7).",
)
@click.option(
    "--hardware",
    default=None,
    type=click.Path(exists=True),
    help="Hardware design file (.kicad_sch, .sch, .csv) for schematic analysis.",
)
@click.option(
    "--build-dir",
    default="_build",
    type=click.Path(),
    help="Build output directory.",
)
@click.option(
    "--skip-build",
    is_flag=True,
    default=False,
    help="Only generate configs and SDK -- skip cmake build.",
)
@click.pass_obj
def pipeline(log: Logger, board: str, hardware: Optional[str],
             build_dir: str, skip_build: bool) -> None:
    """Run the full end-to-end build pipeline for a target board.

    Chains: analyze hardware -> generate configs -> generate eboot integration ->
    generate SDK -> cmake build -> pack firmware image.

    Examples:\n
        ebuild pipeline --board stm32f4\n
        ebuild pipeline --board stm32f4 --hardware board.kicad_sch\n
        ebuild pipeline --board nrf52 --skip-build
    """
    log.header("ebuild — Full Pipeline")

    build_path = Path(build_dir)

    try:
        profile, config_outputs, boot_outputs = _run_pipeline_steps(
            board=board,
            hardware=hardware,
            build_dir=build_path,
            log=log,
        )

        if skip_build:
            log.info("--skip-build: skipping cmake build and image generation.")
        else:
            source_dir = Path(".")
            if (source_dir / "CMakeLists.txt").exists():
                _run_cmake_build(profile, board, source_dir, build_path, log)
            else:
                log.info("No CMakeLists.txt found -- skipping cmake build step.")

            _generate_image(board, build_path, log)

        # Summary
        log.header("Pipeline Summary")
        configs_dir = build_path / "configs"
        sdk_dir = build_path / "sdk"
        images_dir = build_path / "images"
        rootfs_dir = build_path / "rootfs"
        if configs_dir.exists():
            config_files = list(configs_dir.iterdir())
            log.info("  Configs: " + str(len(config_files)) + " files in " + str(configs_dir))
            for f in sorted(config_files):
                log.info("    " + f.name)
        if sdk_dir.exists():
            sdk_subdirs = [d for d in sdk_dir.iterdir() if d.is_dir()]
            log.info("  SDK: " + str(len(sdk_subdirs)) + " target(s) in " + str(sdk_dir))
        if images_dir.exists():
            image_files = list(images_dir.iterdir())
            log.info("  Images: " + str(len(image_files)) + " file(s) in " + str(images_dir))
            for f in sorted(image_files):
                size_kb = f.stat().st_size // 1024
                size_str = str(size_kb // 1024) + " MB" if size_kb > 1024 else str(size_kb) + " KB"
                log.info("    " + f.name + " (" + size_str + ")")
        if rootfs_dir.exists():
            rootfs_dirs = [d for d in rootfs_dir.iterdir() if d.is_dir()]
            log.info("  Rootfs: " + str(len(rootfs_dirs)) + " directories in " + str(rootfs_dir))

        log.success("Pipeline completed successfully.")

    except FileNotFoundError as e:
        log.error(str(e))
        raise SystemExit(1)
    except SystemExit:
        raise
    except Exception as e:
        log.error("Pipeline failed: " + str(e))
        raise SystemExit(1)


@cli.command()
@click.option(
    "--build-dir",
    default="_build",
    type=click.Path(),
    help="Build output directory to remove.",
)
@click.pass_obj
def clean(log: Logger, build_dir: str) -> None:
    """Remove the build output directory."""
    log.header("ebuild — Clean")
    build_path = Path(build_dir)

    if build_path.exists():
        shutil.rmtree(build_path)
        log.success(f"Removed {build_path}/")
    else:
        log.info(f"Nothing to clean — {build_path}/ does not exist.")


@cli.command()
@click.option(
    "--config", "config_path",
    default="build.yaml",
    type=click.Path(exists=False),
    help="Path to the build configuration file.",
)
@click.option(
    "--build-dir",
    default="_build",
    type=click.Path(),
    help="Build output directory.",
)
@click.pass_obj
def configure(log: Logger, config_path: str, build_dir: str) -> None:
    """Generate build files without building."""
    log.header("ebuild — Configure")

    try:
        log.step("Loading configuration...")
        cfg = load_config(config_path)
        log.info(f"Project: {cfg.name} v{cfg.version}")

        log.step("Resolving toolchain...")
        compiler = resolve_toolchain(cfg.toolchain)

        build_path = Path(build_dir)

        package_paths = _install_packages(cfg, build_path, log, verbose=log.verbose)

        log.step(f"Generating build.ninja in {build_path}/...")
        backend = NinjaBackend(cfg, build_path, compiler, package_paths=package_paths)
        backend.generate()

        log.success(f"Generated {build_path / 'build.ninja'}")
        log.success(f"Generated {build_path / 'compile_commands.json'}")
        log.info("Run 'ebuild build' to compile.")

    except FileNotFoundError as e:
        log.error(str(e))
        raise SystemExit(1)
    except (ConfigError, RecipeError) as e:
        log.error(f"Configuration error: {e}")
        raise SystemExit(1)
    except (CycleError, ResolveError, FetchError, BuildError) as e:
        log.error(f"Error: {e}")
        raise SystemExit(1)


@cli.command()
@click.option(
    "--config", "config_path",
    default="build.yaml",
    type=click.Path(exists=False),
    help="Path to the build configuration file.",
)
@click.pass_obj
def info(log: Logger, config_path: str) -> None:
    """Show project info, targets, packages, and dependency graph."""
    log.header("ebuild — Project Info")

    try:
        cfg = load_config(config_path)

        log.info(f"Project : {cfg.name}")
        log.info(f"Version : {cfg.version}")
        log.info(f"Source  : {cfg.source_dir.resolve()}")

        if cfg.toolchain:
            tc = cfg.toolchain
            log.info(f"Compiler: {tc.compiler} (arch: {tc.arch})")
            if tc.prefix:
                log.info(f"Prefix  : {tc.prefix}")
        else:
            log.info("Compiler: gcc (native)")

        if cfg.packages:
            log.header("Packages")
            for p in cfg.packages:
                ver = f" v{p.version}" if p.version else ""
                log.step(f"{p.name}{ver}")

        log.header("Targets")
        for t in cfg.targets:
            deps = f" depends=[{', '.join(t.depends)}]" if t.depends else ""
            uses = f" uses=[{', '.join(t.uses)}]" if t.uses else ""
            log.step(f"{t.name} ({t.target_type}){deps}{uses}")
            if t.sources:
                log.debug(f"  sources: {t.sources}")
            if t.cflags:
                log.debug(f"  cflags : {t.cflags}")
            if t.ldflags:
                log.debug(f"  ldflags: {t.ldflags}")

        graph = build_dependency_graph(cfg.targets)
        build_order = graph.topological_sort()
        log.header("Build Order")
        for i, name in enumerate(build_order, 1):
            log.step(f"{i}. {name}")

    except FileNotFoundError as e:
        log.error(str(e))
        raise SystemExit(1)
    except ConfigError as e:
        log.error(f"Configuration error: {e}")
        raise SystemExit(1)
    except CycleError as e:
        log.error(f"Dependency error: {e}")
        raise SystemExit(1)


@cli.command()
@click.option(
    "--config", "config_path",
    default="build.yaml",
    type=click.Path(exists=False),
    help="Path to the build configuration file.",
)
@click.option(
    "--build-dir",
    default="_build",
    type=click.Path(),
    help="Build output directory.",
)
@click.pass_obj
def install(log: Logger, config_path: str, build_dir: str) -> None:
    """Resolve, fetch, and build all declared packages."""
    log.header("ebuild — Install Packages")

    try:
        cfg = load_config(config_path)
        log.info(f"Project: {cfg.name} v{cfg.version}")

        if not cfg.packages:
            log.info("No packages declared in build.yaml.")
            return

        build_path = Path(build_dir)
        _install_packages(cfg, build_path, log, verbose=log.verbose)
        log.success("All packages installed successfully.")

    except FileNotFoundError as e:
        log.error(str(e))
        raise SystemExit(1)
    except (ConfigError, RecipeError) as e:
        log.error(f"Configuration error: {e}")
        raise SystemExit(1)
    except (ResolveError, FetchError, BuildError) as e:
        log.error(f"Package error: {e}")
        raise SystemExit(1)


@cli.command("add")
@click.argument("package_name")
@click.option("--version", "pkg_version", default=None, help="Package version to add.")
@click.option(
    "--config", "config_path",
    default="build.yaml",
    type=click.Path(exists=False),
    help="Path to the build configuration file.",
)
@click.pass_obj
def add_package(log: Logger, package_name: str, pkg_version: Optional[str], config_path: str) -> None:
    """Add a package dependency to build.yaml."""
    log.header("ebuild — Add Package")

    config_path_obj = Path(config_path)
    if not config_path_obj.exists():
        log.error(f"Config file not found: {config_path}")
        raise SystemExit(1)

    # Verify the package exists in registry
    recipe_dirs = _find_recipe_dirs(config_path_obj.parent)
    if recipe_dirs:
        registry = create_registry(*recipe_dirs)
        recipe = registry.get(package_name, pkg_version)
        if recipe:
            log.info(f"Found recipe: {recipe.name} v{recipe.version}")
            if pkg_version is None:
                pkg_version = recipe.version
        else:
            log.warning(f"No recipe found for '{package_name}' — adding anyway.")

    # Load and update config
    with open(config_path_obj, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if "packages" not in raw:
        raw["packages"] = []

    # Check for duplicates
    for p in raw["packages"]:
        if isinstance(p, dict) and p.get("name") == package_name:
            log.info(f"Package '{package_name}' already in build.yaml.")
            return

    entry: Dict[str, str] = {"name": package_name}
    if pkg_version:
        entry["version"] = pkg_version

    raw["packages"].append(entry)

    with open(config_path_obj, "w", encoding="utf-8") as f:
        yaml.dump(raw, f, default_flow_style=False, sort_keys=False)

    log.success(f"Added {package_name}" + (f" v{pkg_version}" if pkg_version else "") + f" to {config_path}")


@cli.command()
@click.option(
    "--config", "config_path",
    default="build.yaml",
    type=click.Path(exists=False),
    help="Path to the build configuration file.",
)
@click.option(
    "--build-dir",
    default="_build",
    type=click.Path(),
    help="Build output directory.",
)
@click.option(
    "--format", "img_format",
    default="tar",
    type=click.Choice(["raw", "qcow2", "tar", "ext4", "squashfs"]),
    help="Output image format.",
)
@click.option(
    "--size", "size_mb",
    default=256,
    type=int,
    help="Image size in MB (for raw/ext4).",
)
@click.pass_obj
def system(log: Logger, config_path: str, build_dir: str, img_format: str, size_mb: int) -> None:
    """Build a complete Linux system image (rootfs + kernel + image)."""
    log.header("ebuild — System Image Build")

    try:
        from ebuild.system.rootfs import RootfsBuilder
        from ebuild.system.image import ImageBuilder

        build_path = Path(build_dir)

        log.step("Assembling root filesystem...")
        rootfs = RootfsBuilder(build_path)
        rootfs_dir = rootfs.assemble(init_system="busybox", hostname="eos")
        log.success(f"Rootfs assembled: {rootfs_dir}")

        log.step(f"Creating {img_format} image...")
        imager = ImageBuilder(build_path, log=log)
        image_path = imager.create(
            rootfs_dir=rootfs_dir,
            image_format=img_format,
            image_size_mb=size_mb,
        )
        log.success(f"Image created: {image_path}")

    except Exception as e:
        log.error(f"System build failed: {e}")
        raise SystemExit(1)


@cli.command()
@click.option(
    "--config", "config_path",
    default="build.yaml",
    type=click.Path(exists=False),
    help="Path to the build configuration file.",
)
@click.option(
    "--build-dir",
    default="_build",
    type=click.Path(),
    help="Build output directory.",
)
@click.option(
    "--rtos",
    default="generic",
    type=click.Choice(["zephyr", "freertos", "nuttx", "generic"]),
    help="Target RTOS.",
)
@click.option(
    "--board",
    default="generic",
    help="Target board name.",
)
@click.pass_obj
def firmware(log: Logger, config_path: str, build_dir: str, rtos: str, board: str) -> None:
    """Build RTOS firmware for an embedded target."""
    log.header("ebuild — Firmware Build")

    try:
        from ebuild.firmware.firmware import FirmwareBuilder

        cfg = load_config(config_path)
        log.info(f"Project: {cfg.name} v{cfg.version}")

        build_path = Path(build_dir)
        builder = FirmwareBuilder(build_path, log=log)

        log.step(f"Building {rtos} firmware for {board}...")
        output = builder.build(
            source_dir=cfg.source_dir,
            rtos=rtos,
            board=board,
        )
        log.success(f"Firmware built: {output}")

    except FileNotFoundError as e:
        log.error(str(e))
        raise SystemExit(1)
    except Exception as e:
        log.error(f"Firmware build failed: {e}")
        raise SystemExit(1)


@cli.command("list-packages")
@click.option(
    "--config", "config_path",
    default="build.yaml",
    type=click.Path(exists=False),
    help="Path to the build configuration file.",
)
@click.pass_obj
def list_packages(log: Logger, config_path: str) -> None:
    """List available package recipes and project packages."""
    log.header("ebuild — Package Registry")

    config_path_obj = Path(config_path)
    project_dir = config_path_obj.parent if config_path_obj.exists() else Path(".")

    recipe_dirs = _find_recipe_dirs(project_dir)
    if not recipe_dirs:
        log.warning("No recipe directories found.")
        return

    registry = create_registry(*recipe_dirs)
    packages = registry.list_packages()

    if not packages:
        log.info("No recipes found.")
        return

    log.info(f"Available recipes ({len(packages)}):")
    for recipe in packages:
        deps = f" (depends: {', '.join(recipe.dependencies)})" if recipe.dependencies else ""
        desc = f" — {recipe.description}" if recipe.description else ""
        log.step(f"{recipe.name} v{recipe.version} [{recipe.build_system}]{deps}{desc}")

    # Show project packages if config exists
    if config_path_obj.exists():
        try:
            cfg = load_config(config_path_obj)
            if cfg.packages:
                log.header("Project Packages")
                for p in cfg.packages:
                    ver = f" v{p.version}" if p.version else " (latest)"
                    status = "✓ recipe found" if registry.has(p.name, p.version) else "✗ no recipe"
                    log.step(f"{p.name}{ver} — {status}")
        except (ConfigError, FileNotFoundError):
            pass


@cli.command()
@click.argument("input_text", required=False)
@click.option("--file", "input_file", type=click.Path(exists=True), help="Hardware design file (KiCad .kicad_sch, Eagle .sch, BOM .csv, YAML, text).")
@click.option("--output-dir", default="_generated", help="Output directory for generated configs.")
@click.option("--eos-schemas", default=None, help="Path to eos/schemas/ for hardware vocabulary.")
@click.option("--llm", "use_llm", is_flag=True, default=False, help="Enable LLM-enhanced analysis (Ollama local or OPENAI_API_KEY).")
@click.pass_obj
def analyze(log: Logger, input_text: Optional[str], input_file: Optional[str],
            output_dir: str, eos_schemas: Optional[str], use_llm: bool) -> None:
    """Analyze hardware design and generate eos + eboot + ebuild configs.

    Accepts text description, KiCad schematic (.kicad_sch), Eagle schematic (.sch),
    BOM CSV (.csv), or any text/YAML file. Auto-detects format by file extension.

    Generates board.yaml, boot.yaml, build.yaml, and eos_product_config.h.

    Examples:

        ebuild analyze "nRF52840 BLE sensor with I2C and SPI flash"

        ebuild analyze --file design.kicad_sch

        ebuild analyze --file design.sch

        ebuild analyze --file bom.csv

        ebuild analyze "STM32H7 with CAN Ethernet" --llm
    """
    log.header("ebuild — Hardware Analysis")

    try:
        from ebuild.eos_ai.eos_hw_analyzer import EosHardwareAnalyzer
        from ebuild.eos_ai.eos_config_generator import EosConfigGenerator
        from ebuild.eos_ai.eos_validator import EosConfigValidator
        from ebuild.eos_ai.eos_boot_integrator import EosBootIntegrator

        interpreter = EosHardwareAnalyzer(eos_schemas_path=eos_schemas)

        if input_file:
            path = Path(input_file)
            log.step(f"Reading hardware design: {path}")
            profile = interpreter.interpret_file(str(path))
        elif input_text:
            log.step("Analyzing text description...")
            profile = interpreter.interpret_text(input_text)
        else:
            log.error("Provide hardware description text or --file <path>")
            raise SystemExit(1)

        log.info(f"MCU: {profile.mcu or '(unknown)'} ({profile.core})")
        log.info(f"Arch: {profile.arch or '(unknown)'}")
        log.info(f"Peripherals: {len(profile.peripherals)} detected")
        for p in profile.peripherals:
            extra = ""
            if p.config.get("i2c_addr"):
                extra = f" (I2C addr: {p.config['i2c_addr']})"
            log.info(f"  - {p.peripheral_type}: {p.name}{extra}")
        log.info(f"Confidence: {profile.confidence:.0%}")

        # Optional LLM-enhanced analysis
        if use_llm:
            log.step("Running LLM-enhanced analysis...")
            llm_info = interpreter.llm_client.get_provider_info()
            log.info(f"  Provider: {llm_info}")
            if interpreter.llm_client.is_available():
                profile = interpreter.analyze_with_llm(profile)
                log.success("  LLM analysis complete")
            else:
                log.warning("  No LLM available. Install Ollama or set OPENAI_API_KEY.")

        log.step("Generating configs...")
        generator = EosConfigGenerator(output_dir)
        outputs = generator.generate_all(profile)

        for name, path in outputs.items():
            log.success(f"  {name}: {path}")

        log.step("Validating generated configs...")
        validator = EosConfigValidator()
        result = validator.validate_all(output_dir)
        log.info(result.summary())

        log.step("Generating eboot integration files...")
        integrator = EosBootIntegrator(output_dir)
        boot_outputs = integrator.generate_from_boot_yaml(str(outputs["boot"]))
        for name, path in boot_outputs.items():
            log.success(f"  {name}: {path}")

        prompt = interpreter.generate_prompt(profile)
        prompt_path = Path(output_dir) / "llm_prompt.txt"
        prompt_path.write_text(prompt)
        log.info(f"LLM prompt saved: {prompt_path}")

        log.success("Analysis complete.")

    except Exception as e:
        log.error(f"Analysis failed: {e}")
        raise SystemExit(1)


@cli.command("generate-project")
@click.option("--text", "input_text", default=None, help="Hardware description text.")
@click.option("--file", "input_file", type=click.Path(exists=True), help="Hardware design file (YAML, KiCad, BOM).")
@click.option("--config", "config_yaml", type=click.Path(exists=True), help="Existing board.yaml from ebuild analyze.")
@click.option("--eos-repo", type=click.Path(exists=True), default=None, help="Path to local eos repo. Auto-clones from GitHub if omitted.")
@click.option("--eboot-repo", type=click.Path(exists=True), default=None, help="Path to local eboot repo. Auto-clones from GitHub if omitted.")
@click.option("--eos-url", default=None, help="Git URL for eos repo (overrides default GitHub URL).")
@click.option("--eboot-url", default=None, help="Git URL for eboot repo (overrides default GitHub URL).")
@click.option("--clone-dir", default=None, type=click.Path(), help="Directory to clone repos into. Uses temp dir if omitted.")
@click.option("--output", default="_project", help="Output directory (copy mode).")
@click.option("--mode", type=click.Choice(["copy", "branch"]), default="copy", help="Output mode.")
@click.option("--branch", default=None, help="Git branch name (branch mode only).")
@click.option("--eos-schemas", default=None, help="Path to eos/schemas/ for hardware vocabulary.")
@click.pass_obj
def generate_project(
    log: Logger,
    input_text: Optional[str],
    input_file: Optional[str],
    config_yaml: Optional[str],
    eos_repo: Optional[str],
    eboot_repo: Optional[str],
    eos_url: Optional[str],
    eboot_url: Optional[str],
    clone_dir: Optional[str],
    output: str,
    mode: str,
    branch: Optional[str],
    eos_schemas: Optional[str],
) -> None:
    """Generate a stripped-down eos/eboot project for specific hardware.

    Analyzes hardware requirements and prunes the full eos and eboot
    repositories to only the modules needed for the target hardware.
    Auto-clones eos and eboot from GitHub when local repo paths are not given.

    Examples:

        # Auto-clone from GitHub — no local repos needed:
        ebuild generate-project --text "nRF52 BLE sensor with I2C and SPI" \\
            --output customer-ble-sensor

        # With local repos:
        ebuild generate-project --text "nRF52 BLE sensor with I2C and SPI" \\
            --eos-repo ../eos --eboot-repo ../eboot --output customer-ble-sensor

        # From existing hardware analysis:
        ebuild generate-project --config _generated/board.yaml \\
            --output gateway-project

        # Custom GitHub fork:
        ebuild generate-project --text "STM32H7 industrial controller" \\
            --eos-url https://github.com/myorg/eos.git \\
            --eboot-url https://github.com/myorg/eboot.git \\
            --output industrial-project

        # Branch mode on local repos:
        ebuild generate-project --config _generated/board.yaml \\
            --eos-repo ../eos --eboot-repo ../eboot \\
            --mode branch --branch customer/ble-sensor
    """
    log.header("ebuild — Project Generator")

    try:
        from ebuild.eos_ai.eos_hw_analyzer import EosHardwareAnalyzer
        from ebuild.eos_ai.eos_project_generator import EosProjectGenerator

        # Step 1: Obtain a HardwareProfile
        if config_yaml:
            log.step(f"Loading hardware profile from {config_yaml}...")
            profile = _load_profile_from_board_yaml(config_yaml)
        elif input_file:
            log.step(f"Analyzing hardware design: {input_file}...")
            analyzer = EosHardwareAnalyzer(eos_schemas_path=eos_schemas)
            path = Path(input_file)
            if path.suffix == ".kicad_sch":
                profile = analyzer.interpret_kicad(str(path))
            else:
                content = path.read_text(encoding="utf-8", errors="replace")
                if "," in content and len(content.split("\n")) > 2:
                    profile = analyzer.interpret_bom(content)
                else:
                    profile = analyzer.interpret_text(content)
        elif input_text:
            log.step("Analyzing text description...")
            analyzer = EosHardwareAnalyzer(eos_schemas_path=eos_schemas)
            profile = analyzer.interpret_text(input_text)
        else:
            log.error("Provide hardware description via --text, --file, or --config.")
            raise SystemExit(1)

        log.info(f"MCU: {profile.mcu or '(unknown)'} ({profile.core})")
        log.info(f"Arch: {profile.arch or '(unknown)'}")
        log.info(f"Peripherals: {len(profile.peripherals)} detected")

        # Step 2: Create generator and auto-clone repos if needed
        generator = EosProjectGenerator(
            eos_repo=eos_repo,
            eboot_repo=eboot_repo,
            eos_url=eos_url,
            eboot_url=eboot_url,
        )

        if not eos_repo or not eboot_repo:
            log.step("Cloning repos from GitHub (repos not provided locally)...")
            generator.ensure_repos(
                need_eos=(eos_repo is None),
                need_eboot=(eboot_repo is None),
                clone_dir=clone_dir,
            )
            if generator.eos_repo and not eos_repo:
                log.info(f"  eos cloned to: {generator.eos_repo}")
            if generator.eboot_repo and not eboot_repo:
                log.info(f"  eboot cloned to: {generator.eboot_repo}")

        manifest = generator.resolve_manifest(profile)
        log.info(f"eos modules: {len(manifest.eos_dirs)} dirs, product={manifest.eos_product}")
        log.info(f"eboot modules: {len(manifest.eboot_files)} core files, board={manifest.eboot_board}")
        if manifest.eos_toolchain:
            log.info(f"eos toolchain: {manifest.eos_toolchain}")
        if manifest.eos_examples:
            log.info(f"eos examples: {', '.join(manifest.eos_examples)}")
        log.info(f"eos extras: {', '.join(manifest.eos_extras)}")
        log.info(f"eboot extras: {', '.join(manifest.eboot_extras)}")

        log.step(f"Generating project ({mode} mode)...")
        outputs = generator.generate(
            profile=profile,
            output=output,
            mode=mode,
            branch=branch,
        )

        for name, path in outputs.items():
            log.success(f"  {name}: {path}")

        log.success("Project generation complete.")

    except SystemExit:
        raise
    except Exception as e:
        log.error(f"Project generation failed: {e}")
        raise SystemExit(1)


def _load_profile_from_board_yaml(board_yaml_path: str) -> "HardwareProfile":
    """Load a HardwareProfile from a board.yaml produced by ``ebuild analyze``."""
    from ebuild.eos_ai.eos_hw_analyzer import (
        HardwareProfile,
        PeripheralInfo,
    )

    path = Path(board_yaml_path)
    data = yaml.safe_load(path.read_text())
    board = data.get("board", data)

    profile = HardwareProfile(
        mcu=board.get("mcu", ""),
        mcu_family=board.get("family", ""),
        arch=board.get("arch", ""),
        core=board.get("core", ""),
        vendor=board.get("vendor", ""),
        clock_hz=board.get("clock_hz", 0),
        flash_size=board.get("memory", {}).get("flash", 0),
        ram_size=board.get("memory", {}).get("ram", 0),
        features=board.get("features", []),
    )

    for p in board.get("peripherals", []):
        profile.peripherals.append(PeripheralInfo(
            name=p.get("name", ""),
            peripheral_type=p.get("type", ""),
            bus=p.get("bus", ""),
        ))

    return profile


@cli.command("new")
@click.argument("project_name")
@click.option(
    "--template", "template_name",
    default="bare-metal",
    type=click.Choice(["bare-metal", "ble-sensor", "rtos-app", "linux-app", "secure-boot", "safety-critical"]),
    help="Project template to use.",
)
@click.option(
    "--board", "board_name",
    default="generic",
    help="Target board name (e.g., nrf52, stm32h7, rpi4, generic).",
)
@click.option(
    "--output-dir",
    default=None,
    type=click.Path(),
    help="Parent directory for the new project. Defaults to current directory.",
)
@click.pass_obj
def new(log: Logger, project_name: str, template_name: str, board_name: str,
        output_dir: Optional[str]) -> None:
    """Scaffold a new EoS project from a template.

    Creates a ready-to-build project directory with src/main.c, build.yaml,
    eos.yaml, and README.md pre-configured for the selected template and board.

    Examples:

        ebuild new my-sensor --template ble-sensor --board nrf52

        ebuild new my-controller --template rtos-app --board stm32h7

        ebuild new my-app --template bare-metal

        ebuild new my-gateway --template linux-app --board rpi4
    """
    log.header("ebuild — New Project")

    # Resolve template directory
    templates_dir = Path(__file__).resolve().parent.parent.parent / "templates"
    template_dir = templates_dir / template_name

    if not template_dir.is_dir():
        log.error(f"Template '{template_name}' not found at {templates_dir}")
        log.info(f"Available templates: {', '.join(t.name for t in templates_dir.iterdir() if t.is_dir())}")
        raise SystemExit(1)

    # Resolve output directory
    parent = Path(output_dir) if output_dir else Path(".")
    project_dir = parent / project_name

    if project_dir.exists():
        log.error(f"Directory already exists: {project_dir}")
        raise SystemExit(1)

    # Board → arch/toolchain mapping
    board_map = {
        "nrf52":   {"arch": "arm", "core": "cortex-m4f", "toolchain": "arm-none-eabi", "vendor": "nordic"},
        "nrf52840": {"arch": "arm", "core": "cortex-m4f", "toolchain": "arm-none-eabi", "vendor": "nordic"},
        "stm32h7": {"arch": "arm", "core": "cortex-m7", "toolchain": "arm-none-eabi", "vendor": "st"},
        "stm32f4": {"arch": "arm", "core": "cortex-m4f", "toolchain": "arm-none-eabi", "vendor": "st"},
        "rpi4":    {"arch": "arm64", "core": "cortex-a72", "toolchain": "aarch64-linux-gnu", "vendor": "broadcom"},
        "esp32":   {"arch": "xtensa", "core": "lx6", "toolchain": "xtensa-esp32-elf", "vendor": "espressif"},
        "rp2040":  {"arch": "arm", "core": "cortex-m0+", "toolchain": "arm-none-eabi", "vendor": "raspberrypi"},
        "tms570":  {"arch": "arm", "core": "cortex-r5f", "toolchain": "arm-none-eabi", "vendor": "ti"},
        "am64x":   {"arch": "hybrid", "core": "cortex-a53+r5f", "toolchain": "aarch64-linux-gnu", "vendor": "ti"},
        "generic": {"arch": "host", "core": "host", "toolchain": "host", "vendor": "generic"},
    }
    board_info = board_map.get(board_name, board_map["generic"])

    log.step(f"Creating project '{project_name}' from '{template_name}' template...")
    log.info(f"Board: {board_name} (arch={board_info['arch']}, core={board_info['core']})")

    # Create project directory structure
    src_dir = project_dir / "src"
    src_dir.mkdir(parents=True)

    # Template variable substitution
    replacements = {
        "{{PROJECT_NAME}}": project_name,
        "{{BOARD_NAME}}": board_name,
        "{{ARCH}}": board_info["arch"],
        "{{CORE}}": board_info["core"],
        "{{TOOLCHAIN}}": board_info["toolchain"],
        "{{VENDOR}}": board_info["vendor"],
        "{{TEMPLATE}}": template_name,
    }

    # Copy and process template files
    file_mapping = {
        "main.c.template": src_dir / "main.c",
        "build.yaml.template": project_dir / "build.yaml",
        "eos.yaml.template": project_dir / "eos.yaml",
        "README.md.template": project_dir / "README.md",
    }

    for template_file, output_path in file_mapping.items():
        src_path = template_dir / template_file
        if not src_path.exists():
            log.warning(f"Template file missing: {template_file}")
            continue

        content = src_path.read_text(encoding="utf-8")
        for key, val in replacements.items():
            content = content.replace(key, val)

        output_path.write_text(content, encoding="utf-8")
        log.success(f"  {output_path.relative_to(parent)}")

    log.success(f"\nProject created: {project_dir}")
    log.info("\nNext steps:")
    log.info(f"  cd {project_name}")
    log.info("  ebuild build")


@cli.command("generate-boot")
@click.argument("boot_yaml", type=click.Path(exists=True))
@click.option("--output-dir", default="_generated", help="Output directory.")
@click.pass_obj
def generate_boot(log: Logger, boot_yaml: str, output_dir: str) -> None:
    """Generate eboot C headers, linker scripts, and pack scripts from boot.yaml."""
    log.header("ebuild — eboot Config Generation")

    try:
        from ebuild.eos_ai.eos_boot_integrator import EosBootIntegrator
        from ebuild.eos_ai.eos_validator import EosConfigValidator

        log.step(f"Validating {boot_yaml}...")
        validator = EosConfigValidator()
        result = validator.validate_boot(boot_yaml)
        log.info(result.summary())

        if not result.valid:
            log.error("Boot config validation failed. Fix errors before generating.")
            raise SystemExit(1)

        log.step("Generating eboot build inputs...")
        integrator = EosBootIntegrator(output_dir)
        outputs = integrator.generate_from_boot_yaml(boot_yaml)

        for name, path in outputs.items():
            log.success(f"  {name}: {path}")

        log.success("eboot configs generated successfully.")

    except SystemExit:
        raise
    except Exception as e:
        log.error(f"Generation failed: {e}")
        raise SystemExit(1)


# ═══════════════════════════════════════════════════════════════
#  Dependency management commands
# ═══════════════════════════════════════════════════════════════

@cli.command()
@click.option("--eos-url", default=None, help="Git URL for eos repo (overrides default).")
@click.option("--eboot-url", default=None, help="Git URL for eboot repo (overrides default).")
@click.option("--eos-branch", default=None, help="Branch/tag for eos repo.")
@click.option("--eboot-branch", default=None, help="Branch/tag for eboot repo.")
@click.option("--eos-path", default=None, type=click.Path(exists=True), help="Link to local eos repo (no clone).")
@click.option("--eboot-path", default=None, type=click.Path(exists=True), help="Link to local eboot repo (no clone).")
@click.pass_obj
def setup(
    log: Logger,
    eos_url: Optional[str],
    eboot_url: Optional[str],
    eos_branch: Optional[str],
    eboot_branch: Optional[str],
    eos_path: Optional[str],
    eboot_path: Optional[str],
) -> None:
    """Clone eos + eboot repos to the local cache (~/.ebuild/repos/).

    On first run this clones both repos with default settings.
    Use flags to override URLs, branches, or link to local repos.

    Examples:

        ebuild setup

        ebuild setup --eos-url https://github.com/myfork/eos.git

        ebuild setup --eboot-branch v0.2.0

        ebuild setup --eos-path /path/to/local/eos
    """
    from ebuild.deps.manager import DepsManager

    log.header("ebuild — Setup")
    mgr = DepsManager()

    try:
        log.step("Setting up eos...")
        eos_dir = mgr.setup("eos", url=eos_url, branch=eos_branch, path=eos_path)
        log.success(f"  eos: {eos_dir}")

        log.step("Setting up eboot...")
        eboot_dir = mgr.setup("eboot", url=eboot_url, branch=eboot_branch, path=eboot_path)
        log.success(f"  eboot: {eboot_dir}")

        log.success("Setup complete. Repos are ready.")
    except Exception as e:
        log.error(f"Setup failed: {e}")
        raise SystemExit(1)


@cli.group()
@click.pass_context
def repos(ctx: click.Context) -> None:
    """Manage cached eos/eboot repositories."""
    pass


@repos.command("status")
@click.pass_obj
def repos_status(log: Logger) -> None:
    """Show all repos, URLs, branches, and paths."""
    from ebuild.deps.manager import DepsManager

    log.header("ebuild — Repo Status")
    mgr = DepsManager()
    entries = mgr.status()

    for info in entries:
        log.step(f"{info['name']}")
        log.info(f"  URL:    {info['url']}")
        log.info(f"  Branch: {info['branch']}")
        if info.get("config_path"):
            log.info(f"  Linked: {info['config_path']}")
        if info.get("cached"):
            log.info(f"  Cached: {info['cache_location']}")
            log.info(f"  Git:    {info.get('git_branch', '?')} @ {info.get('git_commit', '?')}")
        else:
            log.info("  Cached: no")


@repos.command("update")
@click.argument("repo_name", required=False, default=None)
@click.pass_obj
def repos_update(log: Logger, repo_name: Optional[str]) -> None:
    """Git pull latest for one or all repos."""
    from ebuild.deps.manager import DepsManager

    log.header("ebuild — Repo Update")
    mgr = DepsManager()
    results = mgr.update(repo_name)

    for name, result in results.items():
        if "updated" in result:
            log.success(f"  {name}: {result}")
        elif "failed" in result:
            log.error(f"  {name}: {result}")
        else:
            log.info(f"  {name}: {result}")


@repos.command("set-url")
@click.argument("repo_name")
@click.argument("url")
@click.pass_obj
def repos_set_url(log: Logger, repo_name: str, url: str) -> None:
    """Change the git URL for a repo."""
    from ebuild.deps.manager import DepsManager

    mgr = DepsManager()
    mgr.set_url(repo_name, url)
    log.success(f"Set {repo_name} URL to {url}")


@repos.command("set-branch")
@click.argument("repo_name")
@click.argument("branch")
@click.pass_obj
def repos_set_branch(log: Logger, repo_name: str, branch: str) -> None:
    """Change the branch/tag for a repo."""
    from ebuild.deps.manager import DepsManager

    mgr = DepsManager()
    mgr.set_branch(repo_name, branch)
    log.success(f"Set {repo_name} branch to {branch}")


@repos.command("link")
@click.argument("repo_name")
@click.argument("local_path", type=click.Path(exists=True))
@click.pass_obj
def repos_link(log: Logger, repo_name: str, local_path: str) -> None:
    """Link a repo to a local directory (no clone)."""
    from ebuild.deps.manager import DepsManager

    mgr = DepsManager()
    mgr.link(repo_name, local_path)
    log.success(f"Linked {repo_name} → {Path(local_path).resolve()}")


@repos.command("unlink")
@click.argument("repo_name")
@click.pass_obj
def repos_unlink(log: Logger, repo_name: str) -> None:
    """Remove local path override, reverting to cache."""
    from ebuild.deps.manager import DepsManager

    mgr = DepsManager()
    mgr.unlink(repo_name)
    log.success(f"Unlinked {repo_name} — will use cached clone.")


# ═══════════════════════════════════════════════════════════════
#  Board generation command
# ═══════════════════════════════════════════════════════════════

@cli.command("generate-board")
@click.option("--mcu", default=None, help="MCU name (e.g., stm32f407, nrf52840).")
@click.option("--from-kicad", "kicad_file", default=None, type=click.Path(exists=True), help="KiCad schematic (.kicad_sch).")
@click.option("--from-eagle", "eagle_file", default=None, type=click.Path(exists=True), help="Eagle schematic (.sch).")
@click.option("--from-bom", "bom_file", default=None, type=click.Path(exists=True), help="BOM CSV file.")
@click.option("--describe", "description", default=None, help="Text description of hardware.")
@click.option("--product", default=None, help="Product profile for auto-config (e.g., ble-sensor, gateway).")
@click.option("--output", "output_dir", default="_generated", help="Output directory for generated configs.")
@click.option("--eos-schemas", default=None, help="Path to eos/schemas/ for hardware vocabulary.")
@click.pass_obj
def generate_board(
    log: Logger,
    mcu: Optional[str],
    kicad_file: Optional[str],
    eagle_file: Optional[str],
    bom_file: Optional[str],
    description: Optional[str],
    product: Optional[str],
    output_dir: str,
    eos_schemas: Optional[str],
) -> None:
    """Generate board/boot/build YAML configs from hardware inputs.

    Accepts an MCU name, KiCad schematic, Eagle schematic, BOM CSV,
    or text description. Generates board.yaml, boot.yaml, build.yaml,
    eos_product_config.h, and eboot integration files.

    Examples:

        ebuild generate-board --mcu stm32f407 --output ./config/

        ebuild generate-board --from-kicad design.kicad_sch --output ./config/

        ebuild generate-board --from-eagle design.sch --output ./config/

        ebuild generate-board --from-bom parts.csv --output ./config/

        ebuild generate-board --describe "STM32H743 with CAN, SPI flash" --output ./config/

        ebuild generate-board --mcu nrf52840 --product ble-sensor --output ./config/
    """
    log.header("ebuild — Board Config Generator")

    try:
        from ebuild.eos_ai.eos_hw_analyzer import EosHardwareAnalyzer
        from ebuild.eos_ai.eos_config_generator import EosConfigGenerator
        from ebuild.eos_ai.eos_validator import EosConfigValidator
        from ebuild.eos_ai.eos_boot_integrator import EosBootIntegrator

        analyzer = EosHardwareAnalyzer(eos_schemas_path=eos_schemas)

        # Determine input source
        if kicad_file:
            log.step(f"Analyzing KiCad schematic: {kicad_file}")
            profile = analyzer.interpret_kicad(kicad_file)
        elif eagle_file:
            log.step(f"Analyzing Eagle schematic: {eagle_file}")
            profile = analyzer.interpret_file(eagle_file)
        elif bom_file:
            log.step(f"Analyzing BOM: {bom_file}")
            content = Path(bom_file).read_text(encoding="utf-8", errors="replace")
            profile = analyzer.interpret_bom(content)
        elif description:
            log.step("Analyzing text description...")
            profile = analyzer.interpret_text(description)
        elif mcu:
            log.step(f"Generating config for MCU: {mcu}")
            profile = analyzer.interpret_text(mcu)
        else:
            log.error("Provide --mcu, --from-kicad, --from-eagle, --from-bom, or --describe.")
            raise SystemExit(1)

        # Override MCU if explicitly provided alongside another input
        if mcu and profile.mcu != mcu:
            profile.mcu = mcu

        log.info(f"MCU: {profile.mcu or '(unknown)'} ({profile.core})")
        log.info(f"Arch: {profile.arch or '(unknown)'}")
        log.info(f"Peripherals: {len(profile.peripherals)} detected")
        for p in profile.peripherals:
            log.info(f"  - {p.peripheral_type}: {p.name}")

        # Generate configs
        log.step("Generating board/boot/build configs...")
        gen = EosConfigGenerator(output_dir)
        outputs = gen.generate_all(profile)

        for name, path in outputs.items():
            log.success(f"  {name}: {path}")

        # Validate
        log.step("Validating generated configs...")
        validator = EosConfigValidator()
        val_result = validator.validate_all(output_dir)
        log.info(val_result.summary())

        # Generate eboot integration files
        log.step("Generating eboot integration files...")
        integrator = EosBootIntegrator(output_dir)
        boot_outputs = integrator.generate_from_boot_yaml(str(outputs["boot"]))
        for name, path in boot_outputs.items():
            log.success(f"  {name}: {path}")

        log.success("Board config generation complete.")

    except SystemExit:
        raise
    except Exception as e:
        log.error(f"Board generation failed: {e}")
        raise SystemExit(1)
