# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Dependency manager for eos/eboot repositories.

Handles cloning, caching, linking, and versioning of external repos
so that all ebuild commands share a single source of truth for repo
locations instead of each command re-cloning into temp directories.
"""

from __future__ import annotations

import os
import subprocess
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from ebuild.deps import (
    DEFAULT_CONFIG,
    DEFAULT_EBOOT_REPO_URL,
    DEFAULT_EOS_REPO_URL,
    EBUILD_CONFIG_PATH,
    EBUILD_REPOS_DIR,
    ensure_ebuild_home,
)

# Known repo names
KNOWN_REPOS = ("eos", "eboot")

# Environment variable names for path overrides
ENV_PATH_VARS = {
    "eos": "EBUILD_EOS_PATH",
    "eboot": "EBUILD_EBOOT_PATH",
}


class DepsManager:
    """Manages eos/eboot repository clones, caches, and local overrides.

    Resolution order for finding a repo at build time:

    1. Explicit ``cli_overrides`` (``--eos-repo`` / ``--eboot-repo``)
    2. Environment variables ``EBUILD_EOS_PATH`` / ``EBUILD_EBOOT_PATH``
    3. ``~/.ebuild/config.yaml`` custom ``path:`` override
    4. ``~/.ebuild/repos/<name>/`` (cached git clone)
    5. Sibling directory ``../<name>/`` (workspace layout)
    6. Embedded ``core/<name>/`` (legacy fallback — prints deprecation warning)
    """

    def __init__(self, cli_overrides: Optional[Dict[str, str]] = None) -> None:
        ensure_ebuild_home()
        self._config = self.load_config()
        self._cli_overrides: Dict[str, str] = cli_overrides or {}

    # ------------------------------------------------------------------
    # Config persistence
    # ------------------------------------------------------------------

    def load_config(self) -> Dict[str, Any]:
        """Load ``~/.ebuild/config.yaml``, creating it with defaults if missing."""
        if EBUILD_CONFIG_PATH.exists():
            with open(EBUILD_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            # Merge missing keys from defaults
            for key, val in DEFAULT_CONFIG.items():
                if key not in data:
                    data[key] = val
                elif key == "repos" and isinstance(val, dict):
                    for rname, rval in val.items():
                        if rname not in data["repos"]:
                            data["repos"][rname] = rval
            return data

        self._config = dict(DEFAULT_CONFIG)
        self.save_config()
        return self._config

    def save_config(self) -> None:
        """Write the current configuration to ``~/.ebuild/config.yaml``."""
        ensure_ebuild_home()
        with open(EBUILD_CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(self._config, f, default_flow_style=False, sort_keys=False)

    @property
    def config(self) -> Dict[str, Any]:
        return self._config

    # ------------------------------------------------------------------
    # Cache directory
    # ------------------------------------------------------------------

    @property
    def cache_dir(self) -> Path:
        """Resolved cache directory (from config or env var)."""
        env = os.environ.get("EBUILD_REPOS_DIR")
        if env:
            return Path(env)
        raw = self._config.get("cache_dir", str(EBUILD_REPOS_DIR))
        return Path(os.path.expanduser(raw))

    # ------------------------------------------------------------------
    # Setup / clone
    # ------------------------------------------------------------------

    def setup(
        self,
        repo_name: str,
        url: Optional[str] = None,
        branch: Optional[str] = None,
        path: Optional[str] = None,
        shallow: bool = True,
    ) -> Path:
        """Clone or link a repo.

        Args:
            repo_name: ``"eos"`` or ``"eboot"``.
            url: Git URL override. Falls back to config → default.
            branch: Branch/tag override. Falls back to config → ``"main"``.
            path: If given, register this local path instead of cloning.
            shallow: Use ``--depth 1`` for faster clones (default *True*).

        Returns:
            The resolved local path of the repo.
        """
        repo_cfg = self._config.setdefault("repos", {}).setdefault(repo_name, {})

        if url:
            repo_cfg["url"] = url
        if branch:
            repo_cfg["branch"] = branch

        if path:
            # Link to local repo — no clone needed
            p = Path(path).resolve()
            if not p.is_dir():
                raise FileNotFoundError(f"Local repo path does not exist: {p}")
            repo_cfg["path"] = str(p)
            self.save_config()
            return p

        # Clone to cache
        effective_url = repo_cfg.get("url") or self._default_url(repo_name)
        effective_branch = repo_cfg.get("branch") or "main"

        dest = self.cache_dir / repo_name
        if dest.exists():
            # Already cloned — optionally switch branch
            self._checkout_branch(dest, effective_branch)
            self.save_config()
            return dest

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._git_clone(effective_url, dest, effective_branch, shallow)
        self.save_config()
        return dest

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    def get_repo_path(
        self,
        repo_name: str,
        project_dir: Optional[Path] = None,
    ) -> Optional[Path]:
        """Resolve the path for *repo_name* using the priority chain.

        Args:
            repo_name: ``"eos"`` or ``"eboot"``.
            project_dir: Current project directory (for sibling/core fallback).

        Returns:
            Absolute path to the repo, or *None* if not found anywhere.
        """
        # 1. CLI override
        cli_path = self._cli_overrides.get(repo_name)
        if cli_path:
            p = Path(cli_path).resolve()
            if p.is_dir():
                return p

        # 2. Environment variable
        env_var = ENV_PATH_VARS.get(repo_name)
        if env_var:
            env_val = os.environ.get(env_var)
            if env_val:
                p = Path(env_val).resolve()
                if p.is_dir():
                    return p

        # 3. Config path override
        repo_cfg = self._config.get("repos", {}).get(repo_name, {})
        config_path = repo_cfg.get("path")
        if config_path:
            p = Path(config_path).resolve()
            if p.is_dir():
                return p

        # 4. Cached clone
        cached = self.cache_dir / repo_name
        if cached.is_dir():
            return cached

        # 5. Sibling directory
        if project_dir:
            sibling = project_dir.parent / repo_name
            if sibling.is_dir():
                return sibling

        # 6. Legacy embedded core/<name>/ (deprecation warning)
        if project_dir:
            core_path = project_dir / "core" / repo_name
            if core_path.is_dir():
                warnings.warn(
                    f"Using embedded core/{repo_name}/ is deprecated. "
                    f"Run 'ebuild setup' to clone repos to ~/.ebuild/repos/.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                return core_path

        return None

    def is_available(self, repo_name: str, project_dir: Optional[Path] = None) -> bool:
        """Check if *repo_name* is resolvable anywhere."""
        return self.get_repo_path(repo_name, project_dir) is not None

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, repo_name: Optional[str] = None) -> Dict[str, str]:
        """Git pull latest for one or all repos.

        Returns:
            Dict mapping repo name to result string (e.g. ``"updated"``).
        """
        names = [repo_name] if repo_name else list(KNOWN_REPOS)
        results: Dict[str, str] = {}

        for name in names:
            repo_dir = self.cache_dir / name
            if not repo_dir.is_dir():
                results[name] = "not cloned"
                continue

            repo_cfg = self._config.get("repos", {}).get(name, {})
            if repo_cfg.get("path"):
                results[name] = "linked (skipped)"
                continue

            try:
                subprocess.run(
                    ["git", "-C", str(repo_dir), "pull", "--ff-only"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                results[name] = "updated"
            except subprocess.CalledProcessError as e:
                results[name] = f"failed: {e.stderr.strip()}"

        return results

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> List[Dict[str, Any]]:
        """Return status info for all known repos."""
        entries: List[Dict[str, Any]] = []
        for name in KNOWN_REPOS:
            repo_cfg = self._config.get("repos", {}).get(name, {})
            cached = self.cache_dir / name

            info: Dict[str, Any] = {
                "name": name,
                "url": repo_cfg.get("url", self._default_url(name)),
                "branch": repo_cfg.get("branch", "main"),
                "config_path": repo_cfg.get("path"),
                "cached": cached.is_dir(),
                "cache_location": str(cached) if cached.is_dir() else None,
            }

            # Get current git branch/commit if cloned
            if cached.is_dir():
                info["git_branch"] = self._git_current_branch(cached)
                info["git_commit"] = self._git_head_commit(cached)

            entries.append(info)

        return entries

    # ------------------------------------------------------------------
    # Link / unlink
    # ------------------------------------------------------------------

    def link(self, repo_name: str, local_path: str) -> None:
        """Register a local path override (no symlink — just config entry)."""
        p = Path(local_path).resolve()
        if not p.is_dir():
            raise FileNotFoundError(f"Path does not exist: {p}")
        repo_cfg = self._config.setdefault("repos", {}).setdefault(repo_name, {})
        repo_cfg["path"] = str(p)
        self.save_config()

    def unlink(self, repo_name: str) -> None:
        """Remove a local path override, reverting to cache."""
        repo_cfg = self._config.get("repos", {}).get(repo_name, {})
        repo_cfg.pop("path", None)
        self.save_config()

    # ------------------------------------------------------------------
    # URL / branch setters
    # ------------------------------------------------------------------

    def set_url(self, repo_name: str, url: str) -> None:
        """Change the git URL for a repo."""
        repo_cfg = self._config.setdefault("repos", {}).setdefault(repo_name, {})
        repo_cfg["url"] = url
        self.save_config()

    def set_branch(self, repo_name: str, branch: str) -> None:
        """Change the branch/tag for a repo."""
        repo_cfg = self._config.setdefault("repos", {}).setdefault(repo_name, {})
        repo_cfg["branch"] = branch
        self.save_config()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _default_url(repo_name: str) -> str:
        if repo_name == "eos":
            return DEFAULT_EOS_REPO_URL
        if repo_name == "eboot":
            return DEFAULT_EBOOT_REPO_URL
        return ""

    @staticmethod
    def _git_clone(url: str, dest: Path, branch: str, shallow: bool) -> None:
        cmd = ["git", "clone"]
        if shallow:
            cmd.extend(["--depth", "1"])
        cmd.extend(["--branch", branch, url, str(dest)])

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to clone {url}: {result.stderr.strip()}")

    @staticmethod
    def _checkout_branch(repo_dir: Path, branch: str) -> None:
        current = DepsManager._git_current_branch(repo_dir)
        if current != branch:
            subprocess.run(
                ["git", "-C", str(repo_dir), "fetch", "--all"],
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "-C", str(repo_dir), "checkout", branch],
                capture_output=True,
                text=True,
            )

    @staticmethod
    def _git_current_branch(repo_dir: Path) -> str:
        try:
            result = subprocess.run(
                ["git", "-C", str(repo_dir), "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "(unknown)"

    @staticmethod
    def _git_head_commit(repo_dir: Path) -> str:
        try:
            result = subprocess.run(
                ["git", "-C", str(repo_dir), "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "(unknown)"
