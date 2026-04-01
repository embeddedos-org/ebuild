# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Pytest configuration for ebuild test suite.

Handles:
  - Sibling-repo path resolution (../eos, ../eboot)
  - Graceful skipping when optional dependencies (pyyaml) are absent
  - Custom markers for selective test runs
"""

import importlib
from pathlib import Path

import pytest

# ── Repo roots (available to all tests via conftest) ─────────
EBUILD_ROOT = Path(__file__).resolve().parent.parent
EOS_ROOT = EBUILD_ROOT.parent / "eos"
EBOOT_ROOT = EBUILD_ROOT.parent / "eboot"


def _module_available(name: str) -> bool:
    """Check whether a Python module is importable."""
    try:
        importlib.import_module(name)
        return True
    except ImportError:
        return False


# ── Automatic marker application ─────────────────────────────

def pytest_collection_modifyitems(config, items):
    """Auto-skip tests marked ``needs_yaml`` when pyyaml is not installed."""
    if _module_available("yaml"):
        return

    skip_yaml = pytest.mark.skip(reason="pyyaml not installed")
    for item in items:
        if "needs_yaml" in item.keywords:
            item.add_marker(skip_yaml)


# ── Fixtures ─────────────────────────────────────────────────

@pytest.fixture
def ebuild_root():
    """Path to the ebuild repo root."""
    return EBUILD_ROOT


@pytest.fixture
def eos_root():
    """Path to the eos repo root. Skips if not found."""
    if not EOS_ROOT.is_dir():
        pytest.skip("eos sibling repo not found")
    return EOS_ROOT


@pytest.fixture
def eboot_root():
    """Path to the eboot repo root. Skips if not found."""
    if not EBOOT_ROOT.is_dir():
        pytest.skip("eboot sibling repo not found")
    return EBOOT_ROOT
