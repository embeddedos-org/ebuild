# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Unit tests for ebuild.build.ninja_backend.NinjaBackend."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import pytest

from ebuild.build.ninja_backend import NinjaBackend, escape_ninja_path
from ebuild.build.toolchain import ResolvedToolchain
from ebuild.core.config import ProjectConfig, TargetConfig


def _toolchain():
    return SimpleNamespace(cc="cc", cxx="c++", ar="ar")


class TestNinjaBackendSharedLibrary(unittest.TestCase):
    """A shared_library target must link with the platform's shared-object
    flag and get the same -L/-l wiring as executables. Previously it used the
    link_shared rule but emitted no ldflags and no libs line at all, so any
    -L/-l from `uses` and any target ldflags were silently dropped."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)

    def _generate(self, name: str, target: TargetConfig, package_paths=None) -> str:
        build_dir = Path(self._tmpdir.name) / name
        config = ProjectConfig(name="proj", version="1.0", targets=[target], source_dir=build_dir)
        backend = NinjaBackend(config, build_dir, _toolchain(), package_paths=package_paths)
        backend.generate()
        return (build_dir / "build.ninja").read_text(encoding="utf-8")

    def test_shared_library_gets_shared_flag(self):
        target = TargetConfig(name="mylib", target_type="shared_library", sources=["lib.c"])
        ninja = self._generate("shared", target)

        shared_flag = "-dynamiclib" if sys.platform == "darwin" else "-shared"
        self.assertIn(shared_flag, ninja)
        # It must go through a compiler-driver rule, not the `ar` archiver.
        # link_shared is that rule, and it carries the shared-object flag so
        # the flag is never repeated in the edge's ldflags.
        lib_line = next(line for line in ninja.splitlines() if "libmylib" in line and line.startswith("build"))
        self.assertIn(": link_shared ", lib_line)
        self.assertNotIn(": ar_rule", lib_line)

    def test_shared_library_gets_lib_dirs_and_libs(self):
        target = TargetConfig(
            name="mylib", target_type="shared_library", sources=["lib.c"], uses=["zlib"]
        )
        lib_dir = Path(self._tmpdir.name) / "zlib-lib"
        package_paths = {
            "zlib": SimpleNamespace(include_dirs=[], lib_dirs=[lib_dir], libraries=["z"])
        }
        ninja = self._generate("shared_libs", target, package_paths=package_paths)

        self.assertIn(f"-L{lib_dir}", ninja)
        self.assertIn("libs = -lz", ninja)

    def test_static_library_unaffected(self):
        target = TargetConfig(name="mylib", target_type="static_library", sources=["lib.c"])
        ninja = self._generate("static", target)

        self.assertIn(": ar_rule", ninja)

        # The link_shared *rule* is always declared in the preamble, so the
        # bare string "-shared" is present in every generated file. What must
        # be absent is any build *edge* that uses it.
        edges = [line for line in ninja.splitlines() if line.startswith("build ")]
        self.assertTrue(edges, "no build edges were generated")
        for edge in edges:
            self.assertNotIn(": link_shared ", edge)
            self.assertNotIn(": link ", edge)


class TestNinjaPathEscapingContract(unittest.TestCase):
    """Ninja splits build statements on unescaped spaces and colons.

    Renamed from TestNinjaPathEscaping: a second class of that name is
    defined further down this file, and the later definition replaced this
    one, so none of these four ever ran.

    A Windows absolute path puts a drive-letter colon into the output field, so
    Ninja read the statement as a rule separator and rejected every generated
    file with "expected build command name" -- the backend produced no usable
    build on Windows at all. Paths in build statements must be escaped;
    variable values must not be, or the flags reach the compiler mangled.
    """

    def test_colons_and_spaces_in_paths_are_escaped(self):
        self.assertEqual(escape_ninja_path(r"C:\build\main.o"), r"C$:\build\main.o")
        self.assertEqual(escape_ninja_path("/tmp/my project/main.o"), "/tmp/my$ project/main.o")

    def test_dollar_is_escaped_before_the_escapes_it_introduces(self):
        self.assertEqual(escape_ninja_path("a$b"), "a$$b")
        self.assertEqual(escape_ninja_path("a$b:c"), "a$$b$:c")

    def test_ordinary_posix_paths_are_unchanged(self):
        self.assertEqual(escape_ninja_path("/tmp/build/obj/app/src/main.o"),
                         "/tmp/build/obj/app/src/main.o")

    def test_every_build_statement_has_one_unescaped_colon(self):
        with tempfile.TemporaryDirectory() as tmp:
            build_dir = Path(tmp) / "b"
            target = TargetConfig(name="app", target_type="executable",
                                  sources=["main.c"])
            config = ProjectConfig(name="proj", version="1.0", targets=[target],
                                   source_dir=build_dir)
            NinjaBackend(config, build_dir, _toolchain()).generate()
            ninja = (build_dir / "build.ninja").read_text(encoding="utf-8")

            for line in ninja.splitlines():
                if not line.startswith("build "):
                    continue
                # The only unescaped colon is the one separating outputs from
                # the rule name.
                stripped = line.replace("$:", "").replace("$$", "")
                self.assertEqual(stripped.count(":"), 1, line)


@pytest.mark.ebuild
class TestObjectPathNamespacing:
    """Object files are namespaced by target: ``obj/<target>/<source>.o``.

    Two targets may legitimately list the same source -- a library and a test
    binary sharing a helper, or one source built twice with different defines.
    Naming an object from the source alone makes both targets claim one
    output, which ninja rejects with "multiple rules generate ...", and
    silently drops one target's cflags before it ever gets there.
    """

    @staticmethod
    def _shared_source_config(tmp_path, app_sources):
        return ProjectConfig(
            name="shared_source",
            version="1.0.0",
            targets=[
                TargetConfig(
                    name="util",
                    target_type="static_library",
                    sources=["src/util.c"],
                    defines=["BUILD_LIB=1"],
                ),
                TargetConfig(
                    name="app",
                    target_type="executable",
                    sources=app_sources,
                    defines=["BUILD_APP=1"],
                ),
            ],
            source_dir=tmp_path,
        )

    def test_shared_source_gets_one_object_per_target(self, tmp_path):
        """A source used by two targets must compile to two distinct objects."""
        config = self._shared_source_config(tmp_path, ["src/main.c", "src/util.c"])

        build_dir = tmp_path / "_build"
        NinjaBackend(config, build_dir, ResolvedToolchain()).generate()

        ninja_content = (build_dir / "build.ninja").read_text(encoding="utf-8")

        # Split on the rule separator rather than the first colon: on Windows
        # the object path starts with a drive letter.
        outputs = [
            line[len("build "):].split(": cc ", 1)[0].strip()
            for line in ninja_content.splitlines()
            if line.startswith("build ") and ": cc " in line
        ]
        assert len(outputs) == 3, f"expected 3 compile edges, got {outputs}"
        assert len(set(outputs)) == 3, f"duplicate object outputs: {outputs}"

        # Each target's defines must survive onto its own object.
        assert "-DBUILD_LIB=1" in ninja_content
        assert "-DBUILD_APP=1" in ninja_content

    @pytest.mark.parametrize("app_sources", [
        ["src/main.c", "src/util.c"],
        ["src/util.c", "src/util.S"],
    ])
    def test_shared_source_manifest_is_valid_ninja(self, tmp_path, monkeypatch, app_sources):
        """The generated manifest must load in real ninja, not just look right.

        Ninja treats two edges producing one output as an error, so this is
        the check that actually proves the generated build is usable.

        The build directory is relative and the working directory is the
        project root, mirroring how ``ebuild build`` invokes the backend.
        """
        pytest.importorskip("ninja", reason="ninja package not installed")

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "util.c").write_text(
            "int util_answer(void) { return 42; }\n", encoding="utf-8"
        )
        (src_dir / "main.c").write_text(
            "int util_answer(void);\n"
            "int main(void) { return util_answer() == 42 ? 0 : 1; }\n",
            encoding="utf-8",
        )
        (src_dir / "util.S").write_text("", encoding="utf-8")

        config = self._shared_source_config(tmp_path, app_sources)

        monkeypatch.chdir(tmp_path)
        build_dir = Path("_build")
        NinjaBackend(config, build_dir, ResolvedToolchain()).generate()

        # -n parses and validates the manifest without running the compiler,
        # so this test needs no toolchain on the machine running it.
        result = subprocess.run(
            [sys.executable, "-m", "ninja", "-f", str(build_dir / "build.ninja"), "-n"],
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            "ninja rejected the generated manifest:\n"
            f"{result.stdout}\n{result.stderr}"
        )

    @pytest.mark.parametrize("sources", [["src/main.c"], ["src/start.c", "src/start.S"]])
    def test_object_outputs_preserve_source_extensions(self, tmp_path, sources):
        """Distinct source filenames must stay distinct in both generated files."""
        config = ProjectConfig(
            name="source_extensions", version="1.0", source_dir=tmp_path,
            targets=[TargetConfig(name="app", target_type="executable", sources=sources)],
        )
        build_dir = tmp_path / "_build"
        NinjaBackend(config, build_dir, ResolvedToolchain()).generate()

        manifest = (build_dir / "build.ninja").read_text(encoding="utf-8")
        compile_edges = [line for line in manifest.splitlines() if ": cc " in line]
        objects = [build_dir / "obj" / "app" / (src + ".o") for src in sources]
        assert compile_edges == [
            f"build {escape_ninja_path(obj)}: cc {escape_ninja_path(src)}"
            for src, obj in zip(sources, objects)
        ]
        link_edge = next(line for line in manifest.splitlines() if ": link " in line)
        assert link_edge.split(": link ", 1)[1] == " ".join(
            escape_ninja_path(obj) for obj in objects
        )

        commands = json.loads((build_dir / "compile_commands.json").read_text(encoding="utf-8"))
        assert [entry["file"] for entry in commands] == sources
        assert [entry["command"].split(" -o ", 1)[1] for entry in commands] == [
            str(obj) for obj in objects
        ]

    def test_compile_commands_distinguishes_shared_source_entries(self, tmp_path):
        """compile_commands.json entries for a shared source must differ.

        Two targets compiling one file legitimately produce two entries; each
        needs its own -o so a consumer can tell them apart.
        """
        config = self._shared_source_config(tmp_path, ["src/util.c"])

        build_dir = tmp_path / "_build"
        NinjaBackend(config, build_dir, ResolvedToolchain()).generate()

        cc_data = json.loads(
            (build_dir / "compile_commands.json").read_text(encoding="utf-8")
        )
        shared = [e for e in cc_data if e["file"] == "src/util.c"]
        assert len(shared) == 2
        assert shared[0]["command"] != shared[1]["command"]

        # Differing commands alone are not enough -- the per-target defines
        # would differ regardless. It is the object each entry names that has
        # to be distinct, which is what a consumer keys on.
        objects = [e["command"].split(" -o ", 1)[1].strip() for e in shared]
        assert len(set(objects)) == 2, f"entries name the same object: {objects}"


@pytest.mark.ebuild
class TestNinjaPathEscaping:
    """Paths in build statements must be escaped for Ninja's lexer.

    Ninja ends the output list at the first unescaped ``:`` and splits on
    unescaped spaces. Neither is an error -- a Windows drive letter or a
    directory with a space parses into several wrong targets instead of one
    right one, so the manifest either fails to build the requested target or
    fails much later with a confusing message.
    """

    def test_escapes_space_colon_and_dollar(self):
        assert escape_ninja_path("a b") == "a$ b"
        assert escape_ninja_path("C:/x") == "C$:/x"
        assert escape_ninja_path("a$b") == "a$$b"

    def test_dollar_is_escaped_before_the_others(self):
        """Order matters. Escaping the space first would leave a ``$`` that
        the dollar pass then doubles, yielding ``$$ `` -- a literal dollar
        followed by a separator rather than an escaped space."""
        assert escape_ninja_path("a b:c") == "a$ b$:c"

    def test_leaves_ordinary_paths_untouched(self):
        assert escape_ninja_path("src/main.c") == "src/main.c"

    @staticmethod
    def _config_in(build_dir, source_dir):
        return ProjectConfig(
            name="spacey",
            version="1.0.0",
            targets=[
                TargetConfig(
                    name="app",
                    target_type="executable",
                    sources=["main.c"],
                )
            ],
            source_dir=source_dir,
        )

    def test_build_dir_with_a_space_is_escaped_in_the_manifest(self, tmp_path):
        build_dir = tmp_path / "dir with space" / "_build"
        NinjaBackend(
            self._config_in(build_dir, tmp_path), build_dir, ResolvedToolchain()
        ).generate()

        manifest = (build_dir / "build.ninja").read_text(encoding="utf-8")
        build_lines = [ln for ln in manifest.splitlines() if ln.startswith("build ")]
        assert build_lines

        for line in build_lines:
            # The path is escaped, so no raw space survives before the rule
            # separator, and the drive colon does not terminate the outputs.
            outputs = line[len("build "):].split(": ", 1)[0]
            assert " " not in outputs.replace("$ ", ""), line
            assert "$ " in outputs, line

    def test_ninja_parses_a_spacey_path_as_one_target(self, tmp_path):
        """The check that matters: real ninja must resolve one target, not four.

        A string assertion cannot catch this -- an unescaped path parses
        cleanly and is simply wrong.
        """
        pytest.importorskip("ninja", reason="ninja package not installed")

        source_dir = tmp_path / "dir with space"
        source_dir.mkdir()
        (source_dir / "main.c").write_text("int main(void){return 0;}\n", encoding="utf-8")

        build_dir = source_dir / "_build"
        NinjaBackend(
            self._config_in(build_dir, source_dir), build_dir, ResolvedToolchain()
        ).generate()

        result = subprocess.run(
            [
                sys.executable, "-m", "ninja",
                "-f", str(build_dir / "build.ninja"),
                "-t", "targets", "all",
            ],
            cwd=str(source_dir),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"ninja rejected the manifest:\n{result.stdout}\n{result.stderr}"
        )

        # One compile edge and one link edge -- not one per path fragment.
        targets = [ln for ln in result.stdout.strip().splitlines() if ln.strip()]
        assert len(targets) == 2, f"expected 2 targets, got {targets}"
        assert all("dir with space" in t for t in targets), targets

    def test_escaping_does_not_leak_into_compile_commands(self, tmp_path):
        """compile_commands.json is JSON consumed by clang tooling, not a
        Ninja manifest. A ``$:`` or ``$ `` there would be a corrupt path."""
        source_dir = tmp_path / "dir with space"
        source_dir.mkdir()
        build_dir = source_dir / "_build"
        NinjaBackend(
            self._config_in(build_dir, source_dir), build_dir, ResolvedToolchain()
        ).generate()

        cc_data = json.loads(
            (build_dir / "compile_commands.json").read_text(encoding="utf-8")
        )
        assert cc_data
        for entry in cc_data:
            assert "$:" not in entry["command"]
            assert "$ " not in entry["command"]


if __name__ == "__main__":
    unittest.main()
