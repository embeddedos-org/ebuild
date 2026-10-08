# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""The CLI reads ebuild.lock before resolving, and rewrites it after.

:mod:`tests.unit.test_resolver` proves what the resolver does with a lock;
this proves the CLI hands it one. Before this, ``_install_packages`` built a
``Lockfile`` only after ``resolve()`` had run and only ever wrote it, so the
file on disk pinned nothing.
"""

from types import SimpleNamespace

import pytest

from ebuild.cli import commands
from ebuild.cli.logger import Logger

pytestmark = pytest.mark.ebuild


def test_install_packages_resolves_with_the_lock_it_finds(tmp_path, monkeypatch):
    src = tmp_path / "project"
    (src / "recipes").mkdir(parents=True)
    (src / "ebuild.lock").write_text(
        "lockfile_version: 1\n"
        "packages:\n"
        "  zlib: {version: '1.2.13', url: 'https://example.invalid/z.tgz', checksum: '', build: cmake}\n",
        encoding="utf-8",
    )

    seen = {}

    class RecordingResolver:
        def __init__(self, registry):
            seen["registry"] = registry

        def resolve(self, requested, lockfile=None):
            seen["requested"] = requested
            seen["locked"] = None if lockfile is None else lockfile.locked_packages
            return []   # nothing to fetch or build; the lock is then rewritten empty

    monkeypatch.setattr(commands, "PackageResolver", RecordingResolver)
    monkeypatch.setattr(commands, "_find_recipe_dirs", lambda root: [src / "recipes"])

    cfg = SimpleNamespace(
        packages=[SimpleNamespace(name="zlib", version=None)],
        source_dir=src,
    )
    result = commands._install_packages(cfg, tmp_path / "build", Logger())

    assert result == {}
    assert seen["requested"] == [{"name": "zlib", "version": None}]
    assert seen["locked"] == {
        "zlib": {"version": "1.2.13", "url": "https://example.invalid/z.tgz",
                 "checksum": "", "build": "cmake"},
    }, "the resolver must be given the lock that was on disk"

    # Rewritten from this resolution: nothing resolved, so nothing locked.
    rewritten = (src / "ebuild.lock").read_text(encoding="utf-8")
    assert "zlib" not in rewritten
    assert "lockfile_version: 1" in rewritten


def test_install_packages_reports_a_corrupt_lock_as_a_resolve_error(tmp_path, monkeypatch):
    """Every caller of _install_packages already catches ResolveError and
    prints it as ``[error] ...``; a lock that is not YAML has to arrive
    there, not as a yaml.scanner.ScannerError traceback."""
    from ebuild.packages.resolver import ResolveError

    src = tmp_path / "project"
    (src / "recipes").mkdir(parents=True)
    (src / "ebuild.lock").write_text(
        "lockfile_version: 1\npackages:\n  zlib: {version: '1.2.13\n",   # unterminated quote
        encoding="utf-8",
    )
    monkeypatch.setattr(commands, "_find_recipe_dirs", lambda root: [src / "recipes"])
    cfg = SimpleNamespace(packages=[SimpleNamespace(name="zlib", version=None)], source_dir=src)

    with pytest.raises(ResolveError, match="ebuild.lock is not valid YAML"):
        commands._install_packages(cfg, tmp_path / "build", Logger())


def test_build_command_prints_a_corrupt_lock_without_a_traceback(tmp_path, monkeypatch):
    """End to end through the CLI: exit 1, the message, and no traceback."""
    import textwrap

    from click.testing import CliRunner

    from ebuild.cli.commands import cli

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.c").write_text("int main(void) { return 0; }\n")
    (tmp_path / "recipes").mkdir()
    (tmp_path / "build.yaml").write_text(textwrap.dedent("""\
        project:
          name: demo
          version: "1.0.0"
        packages:
          - name: zlib
        targets:
          - name: demo
            type: executable
            sources: ["src/main.c"]
        toolchain:
          arch: x86_64
        """))
    (tmp_path / "ebuild.lock").write_text("packages:\n  zlib: {version: '1.2.13\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(cli, ["build"])

    output = result.output or ""
    try:
        output += result.stderr or ""
    except ValueError:
        pass
    assert result.exit_code == 1, output
    assert "ebuild.lock is not valid YAML" in output, output
    assert "Traceback" not in output, output
    assert result.exception is None or isinstance(result.exception, SystemExit), repr(result.exception)
