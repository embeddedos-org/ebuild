# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Tests for ebuild.build.dispatch — backend detection, dispatch, dry-run."""

import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from ebuild.build.dispatch import (
    ALL_BACKENDS,
    BackendDispatcher,
    BackendError,
    UnknownBackendError,
    detect_backend,
)


# ── detect_backend() ────────────────────────────────────────


class TestDetectBackend:
    """Tests for auto-detection of build backends from project files."""

    def test_cmake(self, tmp_path):
        (tmp_path / "CMakeLists.txt").touch()
        assert detect_backend(tmp_path) == "cmake"

    def test_meson(self, tmp_path):
        (tmp_path / "meson.build").touch()
        assert detect_backend(tmp_path) == "meson"

    def test_cargo(self, tmp_path):
        (tmp_path / "Cargo.toml").touch()
        assert detect_backend(tmp_path) == "cargo"

    def test_kbuild(self, tmp_path):
        (tmp_path / "Kbuild").touch()
        assert detect_backend(tmp_path) == "kbuild"

    def test_kconfig(self, tmp_path):
        (tmp_path / "Kconfig").touch()
        assert detect_backend(tmp_path) == "kbuild"

    def test_makefile(self, tmp_path):
        (tmp_path / "Makefile").touch()
        assert detect_backend(tmp_path) == "make"

    def test_makefile_lower(self, tmp_path):
        (tmp_path / "makefile").touch()
        assert detect_backend(tmp_path) == "make"

    def test_fallback_ninja(self, tmp_path):
        """Empty directory defaults to ninja."""
        assert detect_backend(tmp_path) == "ninja"

    def test_cmake_takes_priority_over_makefile(self, tmp_path):
        """CMakeLists.txt should be detected before Makefile."""
        (tmp_path / "CMakeLists.txt").touch()
        (tmp_path / "Makefile").touch()
        assert detect_backend(tmp_path) == "cmake"


# ── BackendDispatcher — unknown backend ─────────────────────


class TestUnknownBackend:
    """Unknown backends must raise BackendError rather than silently skip."""

    def test_configure_unknown_raises(self, tmp_path):
        d = BackendDispatcher(tmp_path, tmp_path / "build")
        with pytest.raises(BackendError, match="Unknown build backend 'bazel'"):
            d.configure("bazel")

    def test_build_unknown_raises(self, tmp_path):
        d = BackendDispatcher(tmp_path, tmp_path / "build")
        with pytest.raises(BackendError, match="Unknown build backend"):
            d.build("gradle")

    def test_clean_unknown_raises(self, tmp_path):
        d = BackendDispatcher(tmp_path, tmp_path / "build")
        with pytest.raises(BackendError, match="Unknown build backend"):
            d.clean("scons")


# ── BackendDispatcher — dry-run mode ────────────────────────


class TestDryRun:
    """Dry-run mode should log commands instead of executing them."""

    @patch("ebuild.build.dispatch.subprocess")
    def test_build_cmake_dry_run_does_not_call_subprocess(self, mock_sub, tmp_path):
        d = BackendDispatcher(tmp_path, tmp_path / "build")
        d.build("cmake", dry_run=True)
        mock_sub.run.assert_not_called()

    @patch("ebuild.build.dispatch.subprocess")
    def test_clean_meson_dry_run_does_not_call_subprocess(self, mock_sub, tmp_path):
        d = BackendDispatcher(tmp_path, tmp_path / "build")
        d.clean("meson", dry_run=True)
        mock_sub.run.assert_not_called()

    @patch("ebuild.build.dispatch.subprocess")
    def test_configure_dry_run_does_not_call_subprocess(self, mock_sub, tmp_path):
        d = BackendDispatcher(tmp_path, tmp_path / "build")
        d.configure("cmake", dry_run=True)
        mock_sub.run.assert_not_called()

    def test_dry_run_logs_command(self, tmp_path, caplog):
        d = BackendDispatcher(tmp_path, tmp_path / "build")
        with caplog.at_level(logging.INFO, logger="ebuild.build.dispatch"):
            d.build("cmake", dry_run=True)
        assert "[dry-run]" in caplog.text
        assert "cmake" in caplog.text


# ── BackendDispatcher — clean coverage ──────────────────────


class TestCleanBackends:
    """Verify clean() dispatches correctly for all supported backends."""

    @patch("ebuild.build.dispatch.subprocess")
    def test_clean_cmake(self, mock_sub, tmp_path):
        d = BackendDispatcher(tmp_path, tmp_path / "build")
        d.clean("cmake")
        mock_sub.run.assert_called_once()
        cmd = mock_sub.run.call_args[0][0]
        assert "cmake" in cmd
        assert "--target" in cmd
        assert "clean" in cmd

    @patch("ebuild.build.dispatch.subprocess")
    def test_clean_make(self, mock_sub, tmp_path):
        d = BackendDispatcher(tmp_path, tmp_path / "build")
        d.clean("make")
        mock_sub.run.assert_called_once()
        cmd = mock_sub.run.call_args[0][0]
        assert "clean" in cmd

    @patch("ebuild.build.dispatch.subprocess")
    def test_clean_meson(self, mock_sub, tmp_path):
        """Meson clean must be supported (was previously missing)."""
        d = BackendDispatcher(tmp_path, tmp_path / "build")
        d.clean("meson")
        mock_sub.run.assert_called_once()
        cmd = mock_sub.run.call_args[0][0]
        assert "meson" in cmd
        assert "--clean" in cmd

    @patch("ebuild.build.dispatch.subprocess")
    def test_clean_cargo(self, mock_sub, tmp_path):
        d = BackendDispatcher(tmp_path, tmp_path / "build")
        d.clean("cargo")
        mock_sub.run.assert_called_once()
        cmd = mock_sub.run.call_args[0][0]
        assert "cargo" in cmd
        assert "clean" in cmd

    @patch("ebuild.build.dispatch.subprocess")
    def test_clean_kbuild(self, mock_sub, tmp_path):
        d = BackendDispatcher(tmp_path, tmp_path / "build")
        d.clean("kbuild")
        mock_sub.run.assert_called_once()
        cmd = mock_sub.run.call_args[0][0]
        assert "clean" in cmd


# ── BackendDispatcher — unknown-backend error contract ──────


class TestUnknownBackendError:
    """The error raised for an unhandled backend.

    ``configure()`` and ``build()`` grew two independent unhandled-backend
    branches on separate branches; merging them left duplicated ``else``
    clauses (a SyntaxError that made the module unimportable) raising two
    different types. ``UnknownBackendError`` is the single type, derived
    from both so neither caller contract broke.
    """

    def test_error_is_both_value_and_runtime_error(self, tmp_path):
        """Callers catching either legacy type must keep working.

        ``ebuild build`` funnels this through ``except RuntimeError``; the
        older dispatcher tests catch ``ValueError``.
        """
        assert issubclass(UnknownBackendError, ValueError)
        assert issubclass(UnknownBackendError, RuntimeError)

        d = BackendDispatcher(tmp_path, tmp_path / "build")
        with pytest.raises(UnknownBackendError):
            d.build("gradle")

    def test_configure_ninja_raises_instead_of_silently_passing(self, tmp_path):
        """``backend: ninja`` with no targets reaches the dispatcher.

        A silent no-op here let the CLI report "Build completed
        successfully" with exit code 0 having built nothing.
        """
        d = BackendDispatcher(tmp_path, tmp_path / "build")
        with pytest.raises(UnknownBackendError, match="ninja"):
            d.configure("ninja")
        assert not (tmp_path / "build").exists()

    def test_ninja_error_explains_the_targets_requirement(self, tmp_path):
        """The message must be actionable, not just a rejection."""
        d = BackendDispatcher(tmp_path, tmp_path / "build")
        with pytest.raises(UnknownBackendError, match="targets"):
            d.build("ninja")

    def test_error_does_not_list_the_rejected_backend_as_supported(self, tmp_path):
        """ALL_BACKENDS contains 'ninja', so listing it here contradicted
        the rejection. Each step reports only what it actually handles."""
        d = BackendDispatcher(tmp_path, tmp_path / "build")
        with pytest.raises(UnknownBackendError) as excinfo:
            d.configure("ninja")

        supported = str(excinfo.value).split("BackendDispatcher can configure:")[1]
        supported = supported.split(".")[0]
        assert "ninja" not in supported

    def test_clean_still_accepts_ninja(self, tmp_path):
        """clean() genuinely handles ninja -- only configure/build do not."""
        d = BackendDispatcher(tmp_path, tmp_path / "build")
        d.clean("ninja", dry_run=True)  # must not raise

    @patch("ebuild.build.dispatch.subprocess")
    def test_no_configure_step_backends_stay_noops(self, mock_sub, tmp_path):
        """cargo/make/kbuild are accepted-and-skipped, not errors."""
        d = BackendDispatcher(tmp_path, tmp_path / "build")
        for backend in ("cargo", "make", "kbuild"):
            d.configure(backend)
        mock_sub.run.assert_not_called()
