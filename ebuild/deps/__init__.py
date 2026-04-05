# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""ebuild.deps — Dependency management for eos/eboot repositories.

Auto-creates the ``~/.ebuild/`` directory structure on first import and
provides the default configuration template for ``config.yaml``.
"""

from __future__ import annotations

from pathlib import Path

# Default location for ebuild's persistent state
EBUILD_HOME = Path.home() / ".ebuild"
EBUILD_REPOS_DIR = EBUILD_HOME / "repos"
EBUILD_CONFIG_PATH = EBUILD_HOME / "config.yaml"

# Default repo URLs (same as eos_project_generator.py)
DEFAULT_EOS_REPO_URL = "https://github.com/spatchava/eos.git"
DEFAULT_EBOOT_REPO_URL = "https://github.com/spatchava/eboot.git"

DEFAULT_CONFIG = {
    "repos": {
        "eos": {
            "url": DEFAULT_EOS_REPO_URL,
            "branch": "main",
            "path": None,
        },
        "eboot": {
            "url": DEFAULT_EBOOT_REPO_URL,
            "branch": "main",
            "path": None,
        },
    },
    "cache_dir": str(EBUILD_REPOS_DIR),
}


def ensure_ebuild_home() -> Path:
    """Create ``~/.ebuild/`` and ``~/.ebuild/repos/`` if they don't exist.

    Returns the ``~/.ebuild/`` path.
    """
    EBUILD_HOME.mkdir(parents=True, exist_ok=True)
    EBUILD_REPOS_DIR.mkdir(parents=True, exist_ok=True)
    return EBUILD_HOME
