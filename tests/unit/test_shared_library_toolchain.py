# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Regression tests for toolchain settings in shared-library link commands."""

import shutil
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from ebuild.build.ninja_backend import NinjaBackend, PackagePaths
from ebuild.build.toolchain import ResolvedToolchain
from ebuild.cli.commands import cli
from ebuild.core.config import ProjectConfig, TargetConfig


@pytest.mark.parametrize("sysroot", [None, "/opt/target-sysroot"])
def test_shared_link_preserves_toolchain_flags_without_mutation(tmp_path, sysroot):
    toolchain = ResolvedToolchain(ldflags=["-Wl,--no-undefined"], sysroot=sysroot)
    targets = [
        TargetConfig(
            name=name,
            target_type="shared_library",
            sources=[f"{name}.c"],
            ldflags=[f"-Wl,-soname,lib{name}.so"],
            uses=[name],
        )
        for name in ("first", "second")
    ]
    packages = {
        name: PackagePaths(lib_dirs=[Path(f"vendor/{name}")], libraries=[name])
        for name in ("first", "second")
    }
    config = ProjectConfig(name="libs", version="1.0", targets=targets)
    NinjaBackend(config, tmp_path, toolchain, packages).generate()
    manifest = (tmp_path / "build.ninja").read_text(encoding="utf-8")

    for target in targets:
        edge = next(
            block for block in manifest.split("\n\n")
            if ": link_shared " in block and f"lib{target.name}." in block
        )
        expected = ["-Wl,--no-undefined"]
        if sysroot:
            expected.append(f"--sysroot={sysroot}")
        expected += target.ldflags + [f"-L{Path('vendor') / target.name}"]
        assert edge.splitlines()[1:] == [
            f"  ldflags = {' '.join(expected)}",
            f"  libs = -l{target.name}",
        ]
        assert target.ldflags == [f"-Wl,-soname,lib{target.name}.so"]
    assert toolchain.ldflags == ["-Wl,--no-undefined"]


@pytest.mark.skipif(
    not sys.platform.startswith("linux") or shutil.which("gcc") is None,
    reason="requires Linux and GCC for --no-undefined shared-library linking",
)
def test_cli_shared_library_honors_toolchain_no_undefined(tmp_path, monkeypatch):
    pytest.importorskip("ninja", reason="ninja Python package not installed")
    monkeypatch.chdir(tmp_path)
    (tmp_path / "build.yaml").write_text(
        "project:\n  name: shared-link-check\n  version: '1.0'\n"
        "toolchain:\n  compiler: gcc\n"
        "  extra_ldflags: ['-Wl,--no-undefined']\n"
        "targets:\n  - name: example\n    type: shared_library\n"
        "    sources: [example.c]\n    cflags: [-fPIC]\n",
        encoding="utf-8",
    )
    source = tmp_path / "example.c"
    source.write_text("int example(void) { return 42; }\n", encoding="utf-8")
    runner = CliRunner()
    good = runner.invoke(cli, ["build", "--backend", "ninja", "--build-dir", "good"])
    assert good.exit_code == 0, good.output
    assert (tmp_path / "good" / "libexample.so").is_file()

    source.write_text(
        "extern int missing_symbol(void);\n"
        "int example(void) { return missing_symbol(); }\n",
        encoding="utf-8",
    )
    # A separate output directory avoids timestamp-based incremental decisions.
    bad = runner.invoke(cli, ["build", "--backend", "ninja", "--build-dir", "bad"])
    assert bad.exit_code != 0, bad.output
    assert "undefined reference" in bad.output, bad.output
    assert "missing_symbol" in bad.output, bad.output
