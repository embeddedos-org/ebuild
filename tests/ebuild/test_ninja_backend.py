import importlib.util
import json
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

from ebuild.build.ninja_backend import NinjaBackend
from ebuild.core.config import ProjectConfig, TargetConfig


def _shared_library_config(tmp_path, target_cflags=None):
    return ProjectConfig(
        name="shared-example",
        version="1.0.0",
        source_dir=tmp_path,
        targets=[
            TargetConfig(
                name="example",
                target_type="shared_library",
                sources=["example.c"],
                cflags=target_cflags or [],
            )
        ],
    )


def test_shared_library_links_with_the_platform_shared_flag(tmp_path):
    """A shared_library must link through the compiler driver with the
    platform's shared-object flag.

    An earlier revision emitted a dedicated `link_shared` rule hardcoding
    `-shared`, which is wrong on macOS (it needs `-dynamiclib`) and skipped the
    -L/-l wiring, so the rule was dropped in favour of the generic `link` rule
    with the flag pushed into ldflags.
    """
    config = ProjectConfig(
        name="shared-example",
        version="1.0.0",
        source_dir=tmp_path,
        targets=[
            TargetConfig(
                name="example",
                target_type="shared_library",
                sources=["example.c"],
            )
        ],
    )
    toolchain = SimpleNamespace(cc="cc", cxx="c++", ar="ar")

    NinjaBackend(config, tmp_path / "build", toolchain).generate()

    ninja_file = (tmp_path / "build" / "build.ninja").read_text(encoding="utf-8")
    # macOS links dynamic libraries with -dynamiclib, ELF platforms with
    # -shared. _shared_flag() picks the right one; asserting the literal
    # "-shared" failed this test on every macOS runner.
    shared_flag = "-dynamiclib" if sys.platform == "darwin" else "-shared"
    assert f"rule link_shared\n  command = $cc {shared_flag}" in ninja_file
    assert "build " in ninja_file
    assert ": link_shared " in ninja_file


def test_cc_rule_emits_and_consumes_a_depfile(tmp_path):
    """The compile rule must generate a depfile and tell Ninja to read it.

    Without this, a target is only rebuilt when one of its *listed* sources
    changes. Headers are never listed, so editing a header leaves stale
    object files behind and the build silently reports success.
    """
    config = ProjectConfig(
        name="depfile-example",
        version="1.0.0",
        source_dir=tmp_path,
        targets=[
            TargetConfig(
                name="app",
                target_type="executable",
                sources=["main.c"],
            )
        ],
    )
    toolchain = SimpleNamespace(cc="cc", cxx="c++", ar="ar")

    NinjaBackend(config, tmp_path / "build", toolchain).generate()

    ninja_file = (tmp_path / "build" / "build.ninja").read_text(encoding="utf-8")

    assert "-MMD -MF $out.d" in ninja_file
    assert "  depfile = $out.d" in ninja_file
    assert "  deps = gcc" in ninja_file

    # The directives have to sit inside the `cc` rule, not just anywhere.
    cc_rule = ninja_file.split("rule cc\n", 1)[1].split("\nrule ", 1)[0]
    assert "depfile = $out.d" in cc_rule
    assert "deps = gcc" in cc_rule


def test_depfile_directives_do_not_leak_into_compile_commands(tmp_path):
    """compile_commands.json describes the *compile*, not Ninja's bookkeeping.

    Clang tooling chokes on a stray ``-MF $out.d`` because ``$out`` is a Ninja
    variable, not a path.
    """
    config = ProjectConfig(
        name="depfile-ccjson",
        version="1.0.0",
        source_dir=tmp_path,
        targets=[
            TargetConfig(
                name="app",
                target_type="executable",
                sources=["main.c"],
            )
        ],
    )
    toolchain = SimpleNamespace(cc="cc", cxx="c++", ar="ar")

    NinjaBackend(config, tmp_path / "build", toolchain).generate()

    cc_json = json.loads(
        (tmp_path / "build" / "compile_commands.json").read_text(encoding="utf-8")
    )

    assert cc_json, "expected at least one compile command"
    for entry in cc_json:
        assert "-MMD" not in entry["command"]
        assert "$out" not in entry["command"]


@pytest.mark.skipif(
    shutil.which("cc") is None and shutil.which("gcc") is None,
    reason="no host C compiler available",
)
def test_editing_a_header_triggers_a_rebuild(tmp_path):
    """End-to-end: change a header, and the object that includes it recompiles.

    This is the regression that motivated the depfile change. The header is
    rewritten to contain ``#error``; if the object is genuinely recompiled the
    build must fail. A build that still succeeds means a stale object was
    reused.
    """
    ninja = importlib.util.find_spec("ninja")
    if ninja is None:
        pytest.skip("ninja python package not installed")

    (tmp_path / "greeting.h").write_text(
        "#ifndef GREETING_H\n#define GREETING_H\n#define GREETING 1\n#endif\n",
        encoding="utf-8",
    )
    (tmp_path / "main.c").write_text(
        '#include "greeting.h"\nint main(void) { return GREETING - 1; }\n',
        encoding="utf-8",
    )

    build_dir = tmp_path / "build"
    cc = shutil.which("cc") or shutil.which("gcc")
    toolchain = SimpleNamespace(cc=cc, cxx="c++", ar="ar")
    config = ProjectConfig(
        name="header-dep",
        version="1.0.0",
        source_dir=tmp_path,
        targets=[
            TargetConfig(
                name="app",
                target_type="executable",
                sources=["main.c"],
                includes=["."],
            )
        ],
    )

    def run_ninja():
        NinjaBackend(config, build_dir, toolchain).generate()
        return subprocess.run(
            [sys.executable, "-m", "ninja", "-f", str(build_dir / "build.ninja")],
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
        )

    first = run_ninja()
    assert first.returncode == 0, f"initial build failed:\n{first.stderr}"

    # Poison the header. Nothing in build.yaml changed — only the header.
    (tmp_path / "greeting.h").write_text(
        '#error "header was recompiled"\n', encoding="utf-8"
    )

    second = run_ninja()
    assert second.returncode != 0, (
        "editing a header did not trigger a recompile — a stale object file "
        "was reused and the build wrongly reported success"
    )
    assert "header was recompiled" in (second.stdout + second.stderr)


@pytest.mark.parametrize("directory", ["project", "project with spaces"])
def test_removing_source_removes_archive_member(tmp_path, directory):
    """Incremental archives must contain only the current source objects."""
    cc = shutil.which("cc") or shutil.which("gcc")
    ar = shutil.which("ar")
    if not cc or not ar or importlib.util.find_spec("ninja") is None:
        pytest.skip("host C compiler, ar, and ninja are required")

    source_dir = tmp_path / directory
    source_dir.mkdir()
    (source_dir / "keep.c").write_text("int keep(void) { return 1; }\n")
    (source_dir / "removed.c").write_text("int removed(void) { return 42; }\n")
    main = source_dir / "main.c"
    main.write_text("int removed(void); int main(void) { return removed(); }\n")
    library = TargetConfig(
        name="helpers", target_type="static_library",
        sources=["keep.c", "removed.c"],
    )
    config = ProjectConfig(
        name="archive-regression", version="1.0", source_dir=source_dir,
        targets=[library],
    )
    build_dir = source_dir / "build"
    archive = build_dir / "libhelpers.a"
    toolchain = SimpleNamespace(cc=cc, cxx="c++", ar=ar)

    def build():
        NinjaBackend(config, build_dir, toolchain).generate()
        result = subprocess.run(
            [sys.executable, "-m", "ninja", "-f", str(build_dir / "build.ninja")],
            cwd=source_dir, capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr

    def link():
        return subprocess.run(
            [cc, str(main), str(archive), "-o", str(build_dir / "app")],
            capture_output=True, text=True,
        )

    build()
    assert link().returncode == 0
    initial_mtime = archive.stat().st_mtime_ns
    build()
    assert archive.stat().st_mtime_ns == initial_mtime, "unchanged archive rebuilt"

    library.sources.remove("removed.c")
    (source_dir / "removed.c").unlink()
    build()
    members = subprocess.check_output([ar, "t", str(archive)], text=True)
    assert "removed.o" not in members.splitlines(), members
    assert "keep.o" in members.splitlines(), members
    assert link().returncode != 0, "deleted function still links from stale code"

    # The retained function still links, so this is not merely a broken archive.
    main.write_text("int keep(void); int main(void) { return keep() - 1; }\n")
    result = link()
    assert result.returncode == 0, result.stdout + result.stderr


def test_archive_failure_is_reported_by_ninja(tmp_path):
    """The Python wrapper must preserve the archiver's failure status."""
    cc = shutil.which("cc") or shutil.which("gcc")
    if not cc or importlib.util.find_spec("ninja") is None:
        pytest.skip("host C compiler and ninja are required")
    (tmp_path / "lib.c").write_text("int value(void) { return 1; }\n")
    config = ProjectConfig(
        name="archive-failure", version="1.0", source_dir=tmp_path,
        targets=[TargetConfig(
            name="helpers", target_type="static_library", sources=["lib.c"],
        )],
    )
    # Python receives 'rcs' as a script name and fails: a portable stand-in
    # for an archiver returning a nonzero status, without a shell script.
    toolchain = SimpleNamespace(cc=cc, cxx="c++", ar=sys.executable)
    build_dir = tmp_path / "build"
    NinjaBackend(config, build_dir, toolchain).generate()
    result = subprocess.run(
        [sys.executable, "-m", "ninja", "-f", str(build_dir / "build.ninja")],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert result.returncode != 0, result.stdout + result.stderr
    assert "rcs" in result.stdout + result.stderr
