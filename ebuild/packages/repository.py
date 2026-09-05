# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Remote package repository — index-based package discovery.

Provides search, info, and listing of packages available from
local recipe directories, shipped package catalogs, or remote repository indices.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from ebuild.packages.index_sync import IndexSyncManager, get_default_index_dir, sanitize_package_name
from ebuild.packages.registry import PackageRegistry, create_registry, find_recipe_dirs

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

    def to_dict(self) -> Dict[str, Any]:
        """Convert PackageInfo dataclass to a JSON-serializable dictionary."""
        return asdict(self)


class PackageRepository:
    """Repository index for discovering and querying available packages.

    Wraps one or more PackageRegistry instances and remote index files,
    providing unified search, info, and listing functionality.
    """

    def __init__(self, sync_manager: Optional[IndexSyncManager] = None) -> None:
        self._registries: List[PackageRegistry] = []
        self._index: Dict[str, PackageInfo] = {}
        self.sync_manager = sync_manager or IndexSyncManager()

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
            # Local/earlier recipe directory overrides later directories if already loaded
            if recipe.name not in self._index:
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

        try:
            with open(index_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to parse repository index %s: %s", index_path, e)
            return 0

        if not isinstance(data, list):
            logger.warning("Invalid index format: expected array")
            return 0

        count = 0
        for entry in data:
            if not isinstance(entry, dict) or "name" not in entry:
                continue
            try:
                name = sanitize_package_name(str(entry["name"]))
            except ValueError:
                continue
            info = PackageInfo(
                name=name,
                version=str(entry.get("version", "0.0.0")),
                description=entry.get("description", ""),
                license=entry.get("license", ""),
                build_system=entry.get("build_system", entry.get("build", "cmake")),
                dependencies=entry.get("dependencies", []),
                url=entry.get("url", ""),
                checksum=entry.get("checksum", ""),
            )
            # Local recipe directory overrides remote index if already loaded
            if name not in self._index:
                self._index[name] = info
                count += 1

        return count

    def load_all_sources(self, project_dir: Optional[Path | str] = None) -> int:
        """Load all available sources: project recipes, shipped recipes, and remote cache.

        Args:
            project_dir: Optional path to project root.

        Returns:
            Total count of packages indexed across all sources.
        """
        for rdir in find_recipe_dirs(project_dir, remote_index_dir=self.sync_manager.index_dir):
            self.add_recipe_directory(rdir)

        # Cached remote JSON index
        if self.sync_manager.packages_json.is_file():
            self.load_index(self.sync_manager.packages_json)

        return self.package_count

    def search(
        self,
        query: str = "",
        build_system: Optional[str] = None,
        license_filter: Optional[str] = None,
    ) -> List[PackageInfo]:
        """Search for packages matching query and filters.

        Args:
            query: Search query string (matches name, description, license).
            build_system: Optional build system filter (e.g., 'cmake', 'make').
            license_filter: Optional license filter.

        Returns:
            List of matching PackageInfo objects sorted by name.
        """
        effective_lic = license_filter
        query_lower = query.strip().lower()
        results = []

        for info in sorted(self._index.values(), key=lambda p: p.name):
            if query_lower:
                name_match = query_lower in info.name.lower()
                desc_match = query_lower in info.description.lower()
                lic_match = query_lower in info.license.lower()
                if not (name_match or desc_match or lic_match):
                    continue

            if build_system and info.build_system.lower() != build_system.strip().lower():
                continue

            if effective_lic and effective_lic.strip().lower() not in info.license.lower():
                continue

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
        entries = [info.to_dict() for info in sorted(self._index.values(), key=lambda p: p.name)]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)

        logger.info("Exported %d packages to %s", len(entries), output_path)
