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
    """Unknown backends must raise rather than silently skip.

    All three methods raise RuntimeError for this one condition, so a caller
    can guard the whole dispatcher with a single ``except RuntimeError``.
    """

    def test_configure_unknown_raises(self, tmp_path):
        d = BackendDispatcher(tmp_path, tmp_path / "build")
        with pytest.raises(RuntimeError, match="bazel"):
            d.configure("bazel")

    def test_build_unknown_raises(self, tmp_path):
        d = BackendDispatcher(tmp_path, tmp_path / "build")
        with pytest.raises(RuntimeError, match="Unknown build backend"):
            d.build("gradle")

    def test_clean_unknown_raises(self, tmp_path):
        d = BackendDispatcher(tmp_path, tmp_path / "build")
        with pytest.raises(RuntimeError, match="Unknown build backend"):
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
