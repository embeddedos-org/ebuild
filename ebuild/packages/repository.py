# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Remote package repository — index-based package discovery.

Provides search, info, and listing of packages available from
local recipe directories or remote repository indices.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from ebuild.packages.registry import PackageRegistry, create_registry

logger = logging.getLogger(__name__)


@dataclass
class PackageInfo:
    """Summary information about a package in the repository."""

    name: str
    version: str
    description: str = ""
    license: str = ""
    build_system: str = "cmake"
    dependencies: List[str] = field(default_factory=list)
    url: str = ""
    checksum: str = ""


class PackageRepository:
    """Repository index for discovering and querying available packages.

    Wraps one or more PackageRegistry instances and provides
    search, info, and listing functionality.
    """

    def __init__(self) -> None:
        self._registries: List[PackageRegistry] = []
        self._index: Dict[str, PackageInfo] = {}

    def add_recipe_directory(self, path: str | Path) -> int:
        """Add a local recipe directory to the repository.

        Args:
            path: Directory containing recipe YAML files.

        Returns:
            Number of recipes loaded from this directory.
        """
        registry = create_registry(path)
        self._registries.append(registry)

        count = 0
        for recipe in registry.list_packages():
            info = PackageInfo(
                name=recipe.name,
                version=recipe.version,
                description=recipe.description,
                license=recipe.license,
                build_system=recipe.build_system,
                dependencies=recipe.dependencies,
                url=recipe.url,
                checksum=recipe.checksum,
            )
            self._index[recipe.name] = info
            count += 1

        return count

    def load_index(self, index_path: str | Path) -> int:
        """Load a repository index from a JSON file.

        The index file contains an array of package entries with
        fields matching the PackageInfo dataclass.

        Args:
            index_path: Path to the JSON index file.

        Returns:
            Number of packages loaded.
        """
        index_path = Path(index_path)
        if not index_path.exists():
            logger.warning("Repository index not found: %s", index_path)
            return 0

        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            logger.warning("Invalid index format: expected array")
            return 0

        count = 0
        for entry in data:
            if not isinstance(entry, dict) or "name" not in entry:
                continue
            info = PackageInfo(
                name=entry["name"],
                version=entry.get("version", "0.0.0"),
                description=entry.get("description", ""),
                license=entry.get("license", ""),
                build_system=entry.get("build_system", entry.get("build", "cmake")),
                dependencies=entry.get("dependencies", []),
                url=entry.get("url", ""),
                checksum=entry.get("checksum", ""),
            )
            self._index[info.name] = info
            count += 1

        return count

    def search(self, query: str) -> List[PackageInfo]:
        """Search for packages matching a query string.

        Matches against package name and description (case-insensitive).

        Args:
            query: Search query string.

        Returns:
            List of matching PackageInfo objects.
        """
        query_lower = query.lower()
        results = []
        for info in sorted(self._index.values(), key=lambda p: p.name):
            if (
                query_lower in info.name.lower()
                or query_lower in info.description.lower()
            ):
                results.append(info)
        return results

    def info(self, name: str) -> Optional[PackageInfo]:
        """Get detailed information about a specific package.

        Args:
            name: Package name.

        Returns:
            PackageInfo if found, None otherwise.
        """
        return self._index.get(name)

    def list_all(self) -> List[PackageInfo]:
        """List all packages in the repository.

        Returns:
            Sorted list of all PackageInfo objects.
        """
        return sorted(self._index.values(), key=lambda p: p.name)

    @property
    def package_count(self) -> int:
        """Total number of packages in the repository."""
        return len(self._index)

    def export_index(self, output_path: str | Path) -> None:
        """Export the current repository as a JSON index file.

        Args:
            output_path: Path to write the JSON index file.
        """
        output_path = Path(output_path)
        entries = []
        for info in sorted(self._index.values(), key=lambda p: p.name):
            entries.append({
                "name": info.name,
                "version": info.version,
                "description": info.description,
                "license": info.license,
                "build_system": info.build_system,
                "dependencies": info.dependencies,
                "url": info.url,
                "checksum": info.checksum,
            })

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)

        logger.info("Exported %d packages to %s", len(entries), output_path)
