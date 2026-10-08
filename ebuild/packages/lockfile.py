# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Version lockfile — records exact resolved package versions.

Produces and reads `ebuild.lock` files that pin exact versions,
URLs, and checksums for reproducible builds.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from ebuild.packages.recipe import PackageRecipe


class LockfileError(Exception):
    """``ebuild.lock`` exists but could not be read.

    Distinct from a lock of the wrong *shape*, which :meth:`Lockfile.load`
    sanitises to an empty lock: a file that is not YAML, or cannot be opened,
    is a condition the user has to resolve, and the CLI reports it as a
    resolution error rather than a traceback.
    """


class Lockfile:
    """Manages the ebuild.lock file for reproducible package resolution.

    Records exact versions, URLs, and checksums of all resolved packages
    so that subsequent builds use identical dependencies.
    """

    FILENAME = "ebuild.lock"

    # Lock field -> PackageRecipe attribute, for every field lock() records
    # that identifies the artifact. The resolver compares each of these; a
    # field recorded here and compared nowhere is what this file used to be.
    CHECKED_FIELDS = (
        ("url", "url"),
        ("checksum", "checksum"),
        ("build", "build_system"),
    )

    def __init__(self, lock_path: str | Path) -> None:
        self.lock_path = Path(lock_path)
        self._entries: Dict[str, Dict[str, str]] = {}

    def is_locked(self) -> bool:
        """Check if a lockfile exists."""
        return self.lock_path.exists()

    def load(self) -> None:
        """Load the lockfile from disk."""
        if not self.lock_path.exists():
            return

        try:
            with open(self.lock_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f)
        except (yaml.YAMLError, UnicodeDecodeError) as e:
            # A lock that is not UTF-8 (a foreign editor, a bad binary merge)
            # fails in the codec, not the parser, and UnicodeDecodeError is a
            # ValueError -- neither a YAMLError nor an OSError. Same message:
            # the file is not something this tool wrote, and the remedy is
            # the same.
            raise LockfileError(
                f"{self.lock_path} is not valid YAML: {e}. "
                f"Fix it, or delete it to resolve afresh."
            ) from e
        except OSError as e:
            raise LockfileError(
                f"{self.lock_path} could not be read: {e}. "
                f"Fix it, or delete it to resolve afresh."
            ) from e

        if not isinstance(raw, dict):
            return

        packages = raw.get("packages", {})
        if isinstance(packages, dict):
            # Keep only well-formed entries; a hand-edited or truncated file
            # must not turn into a KeyError deep inside the resolver.
            self._entries = {
                str(name): {str(k): str(v) for k, v in entry.items() if v is not None}
                for name, entry in packages.items()
                if isinstance(entry, dict)
            }

    def save(self) -> None:
        """Write the lockfile to disk."""
        data: Dict[str, Any] = {
            "lockfile_version": 1,
            "packages": self._entries,
        }
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.lock_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=True)

    def lock(self, recipes: List[PackageRecipe]) -> None:
        """Lock a set of resolved package recipes."""
        self._entries = {}
        for recipe in recipes:
            self._entries[recipe.name] = {
                "version": recipe.version,
                "url": recipe.url,
                "checksum": recipe.checksum,
                "build": recipe.build_system,
            }

    def get_locked_version(self, name: str) -> Optional[str]:
        """Get the locked version for a package name."""
        entry = self._entries.get(name)
        return entry.get("version") if entry else None

    def get_locked_entry(self, name: str) -> Optional[Dict[str, str]]:
        """Get the full locked entry for a package."""
        return self._entries.get(name)

    @property
    def locked_packages(self) -> Dict[str, Dict[str, str]]:
        """Return all locked package entries."""
        return dict(self._entries)

    @property
    def package_names(self) -> List[str]:
        """Return names of all locked packages."""
        return sorted(self._entries.keys())

    def clear(self) -> None:
        """Clear all locked entries."""
        self._entries = {}

    def remove(self, name: str) -> None:
        """Remove a package from the lockfile."""
        self._entries.pop(name, None)
