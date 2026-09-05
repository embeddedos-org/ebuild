# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Remote package index synchronization and offline cache manager.

Manages downloading, verifying, and caching package indices and recipe
definitions from remote repositories (HTTPS) into a local user cache directory
(~/.ebuild/index/). Supports offline fallback and security sanitization.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

import yaml

from ebuild.packages.recipe import PackageRecipe, RecipeError, parse_recipe

logger = logging.getLogger(__name__)

# Default remote repository index URL (empty until official registry repository is published)
DEFAULT_INDEX_URL = ""

# Maximum response size allowed for index download (10 MB)
MAX_INDEX_SIZE_BYTES = 10 * 1024 * 1024

# Network timeout in seconds
DEFAULT_NETWORK_TIMEOUT_SECONDS = 10

# Cache TTL in seconds (24 hours) for freshness check
CACHE_TTL_SECONDS = 86400

# Valid package name pattern (strict validation to prevent path traversal)
_SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


class IndexSyncError(Exception):
    """Raised when index synchronization fails and cannot fallback."""


class SyncResult(NamedTuple):
    """Result of index synchronization, preserving tuple unpacking (count, message)."""

    count: int
    message: str
    is_fallback: bool = False
    sha256: Optional[str] = None
    pruned: int = 0


def is_offline(offline_flag: bool = False) -> bool:
    """Check if the execution environment is configured for offline operation."""
    if offline_flag:
        return True
    env_val = os.environ.get("EBUILD_OFFLINE", "").strip().lower()
    return env_val in ("1", "true", "yes", "on")


def get_default_index_dir() -> Path:
    """Get the local index cache directory path, respecting env overrides."""
    if "EBUILD_INDEX_PATH" in os.environ:
        return Path(os.environ["EBUILD_INDEX_PATH"])
    if "EBUILD_CACHE_DIR" in os.environ:
        return Path(os.environ["EBUILD_CACHE_DIR"]) / "index"
    return Path.home() / ".ebuild" / "index"


def sanitize_package_name(name: str) -> str:
    """Validate and sanitize a package name to prevent path traversal attacks.

    Args:
        name: The candidate package name.

    Returns:
        The validated package name.

    Raises:
        ValueError: If the package name contains invalid or unsafe characters.
    """
    cleaned = name.strip()
    if not cleaned or not _SAFE_NAME_RE.match(cleaned):
        raise ValueError(
            f"Invalid package name '{name}': names must only contain alphanumeric "
            f"characters, underscores, or hyphens."
        )
    return cleaned


class IndexSyncManager:
    """Coordinates remote index fetching, integrity validation, and local caching."""

    def __init__(
        self,
        index_dir: Optional[Path | str] = None,
        default_url: str = DEFAULT_INDEX_URL,
    ) -> None:
        self.index_dir = (
            Path(index_dir) if index_dir is not None else get_default_index_dir()
        )
        self.default_url = default_url
        self.packages_json = self.index_dir / "packages.json"
        self.recipes_dir = self.index_dir / "recipes"
        self.meta_json = self.index_dir / "index-meta.json"

    def ensure_directories(self) -> None:
        """Create necessary index directories if they do not exist."""
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.recipes_dir.mkdir(parents=True, exist_ok=True)

    def get_recipe_dirs(self) -> List[Path]:
        """Return list of recipe directories managed by this sync index."""
        if self.recipes_dir.is_dir():
            return [self.recipes_dir]
        return []

    def load_cached_entries(self) -> List[Dict[str, Any]]:
        """Load entries from the local packages.json cache if present."""
        if not self.packages_json.is_file():
            return []
        try:
            with open(self.packages_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            logger.warning("Cached index at %s is not a list", self.packages_json)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load cached index: %s", e)
        return []

    def sync(
        self,
        url: Optional[str] = None,
        force: bool = False,
        offline: bool = False,
        timeout: int = DEFAULT_NETWORK_TIMEOUT_SECONDS,
    ) -> SyncResult:
        """Synchronize the index from the remote URL to the local cache.

        Args:
            url: The remote index URL (defaults to configured default_url).
            force: If True, re-download even if recently synced.
            offline: If True, skip network download and use cached files.
            timeout: Network timeout in seconds.

        Returns:
            SyncResult of (package_count, status_message, is_fallback).
        """
        target_url = (url or self.default_url).strip()
        self.ensure_directories()

        # Offline mode
        if is_offline(offline):
            cached = self.load_cached_entries()
            count = len(cached)
            return SyncResult(count, f"Offline mode: using cached index ({count} packages)", is_fallback=False)

        # First check target_url validity before using or validating against it
        if not target_url:
            raise IndexSyncError(
                "No remote package index URL configured. Provide a repository URL with '--url <https://...>' until a default registry is published."
            )

        if not target_url.startswith("https://"):
            raise IndexSyncError(
                f"Insecure index URL '{target_url}': only HTTPS URLs are permitted."
            )

        # Staleness check: if cache exists, is fresh (< 24h), matches origin URL, and force=False
        cached_meta: Dict[str, Any] = {}
        if self.meta_json.is_file():
            try:
                with open(self.meta_json, "r", encoding="utf-8") as mf:
                    cached_meta = json.load(mf)
            except Exception:
                cached_meta = {}

        cached_url = cached_meta.get("url")
        same_origin = (cached_url == target_url) if cached_url else (url is None)

        if not force and same_origin and self.packages_json.is_file():
            try:
                cache_age = time.time() - self.packages_json.stat().st_mtime
                if cache_age < CACHE_TTL_SECONDS:
                    cached = self.load_cached_entries()
                    count = len(cached)
                    cached_meta_sha = cached_meta.get("sha256")
                    return SyncResult(
                        count,
                        f"Cache is up-to-date (synced recently). Use --force to re-download. ({count} packages)",
                        is_fallback=False,
                        sha256=cached_meta_sha,
                    )
            except OSError:
                pass

        logger.info("Fetching remote package index from %s", target_url)

        # 1. Network download with narrow exception handling
        try:
            req = urllib.request.Request(
                target_url,
                headers={"User-Agent": "ebuild-package-manager/3.0"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                content_length = response.headers.get("Content-Length")
                if content_length:
                    try:
                        declared_length = int(str(content_length).strip())
                        if declared_length > MAX_INDEX_SIZE_BYTES:
                            raise IndexSyncError(
                                f"Index download exceeds maximum allowed size ({MAX_INDEX_SIZE_BYTES} bytes)"
                            )
                    except ValueError:
                        # Malformed header is advisory; bounded read below enforces size limit
                        pass
                raw_bytes = response.read(MAX_INDEX_SIZE_BYTES + 1)
                if len(raw_bytes) > MAX_INDEX_SIZE_BYTES:
                    raise IndexSyncError(
                        f"Index download exceeded maximum size limit of {MAX_INDEX_SIZE_BYTES} bytes"
                    )
        except IndexSyncError:
            raise
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            # Fallback to local cache if available on network error
            cached = self.load_cached_entries()
            if cached:
                logger.warning("Remote sync failed (%s). Falling back to cached index.", e)
                cached_meta_sha = cached_meta.get("sha256")
                return SyncResult(
                    len(cached),
                    f"Network sync failed ({e}); fell back to cached index ({len(cached)} packages)",
                    is_fallback=True,
                    sha256=cached_meta_sha,
                )
            raise IndexSyncError(f"Failed to fetch remote package index and no cache is available: {e}") from e

        # 2. Parse and validate JSON index
        try:
            data = json.loads(raw_bytes.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as err:
            raise IndexSyncError(f"Corrupted or invalid JSON index from {target_url}: {err}") from err

        if not isinstance(data, list):
            raise IndexSyncError("Invalid index schema: expected top-level JSON array")

        # 3. Filter, sanitize, and deduplicate entries in memory BEFORE caching to disk
        valid_entries: List[Dict[str, Any]] = []
        seen_names: set[str] = set()
        for entry in data:
            if not isinstance(entry, dict) or "name" not in entry:
                continue
            try:
                pkg_name = sanitize_package_name(str(entry["name"]))
                if pkg_name in seen_names:
                    logger.warning("Discarding duplicate package entry in index: %s", pkg_name)
                    continue
                seen_names.add(pkg_name)
                valid_entries.append(entry)
            except ValueError as ve:
                logger.warning("Skipping unsafe package entry: %s", ve)
                continue

        # 4. Write cached packages.json atomically with sanitized entries only
        temp_json = self.packages_json.with_suffix(".tmp")
        with open(temp_json, "w", encoding="utf-8") as f:
            json.dump(valid_entries, f, indent=2)
        temp_json.replace(self.packages_json)

        # 5. Record SHA-256 digest of the downloaded index for integrity visibility
        index_sha256 = hashlib.sha256(raw_bytes).hexdigest()
        sha_file = self.packages_json.with_name(self.packages_json.name + ".sha256")
        temp_sha = sha_file.with_suffix(".tmp")
        with open(temp_sha, "w", encoding="utf-8") as sf:
            sf.write(f"{index_sha256}  packages.json\n")
        temp_sha.replace(sha_file)

        # Write index metadata (origin URL, digest, sync time)
        meta_data = {
            "url": target_url,
            "sha256": index_sha256,
            "synced_at": time.time(),
        }
        temp_meta = self.meta_json.with_suffix(".tmp")
        with open(temp_meta, "w", encoding="utf-8") as mf:
            json.dump(meta_data, mf, indent=2)
        temp_meta.replace(self.meta_json)

        logger.info("Remote index SHA-256 digest: %s", index_sha256)

        # 6. Process and cache full recipe YAML definitions
        keep = {f"{sanitize_package_name(str(e['name']))}.yaml" for e in valid_entries}
        synced_count = 0
        for entry in valid_entries:
            pkg_name = sanitize_package_name(str(entry["name"]))
            recipe_filename = f"{pkg_name}.yaml"
            recipe_path = self.recipes_dir / recipe_filename

            recipe_dict = {
                "package": pkg_name,
                "version": str(entry.get("version", "1.0.0")),
                "description": entry.get("description", ""),
                "license": entry.get("license", ""),
                "url": entry.get("url", ""),
                "checksum": entry.get("checksum", ""),
                "build": entry.get("build_system", entry.get("build", "cmake")),
                "dependencies": entry.get("dependencies", []),
                "configure_args": entry.get("configure_args", []),
                "build_args": entry.get("build_args", []),
                "patches": entry.get("patches", []),
            }

            # Only write recipe file if entry provides a download URL
            if recipe_dict["url"]:
                try:
                    recipe = parse_recipe(recipe_dict)
                    with open(recipe_path, "w", encoding="utf-8") as rf:
                        yaml.safe_dump(recipe.to_dict(), rf, sort_keys=False)
                    synced_count += 1
                except (RecipeError, ValueError) as re_err:
                    logger.warning("Skipping invalid recipe entry %s: %s", pkg_name, re_err)
                    continue

        # Prune stale cached recipes not present in the newly synchronized index
        pruned_count = 0
        if self.recipes_dir.is_dir():
            for existing_file in list(self.recipes_dir.glob("*.yaml")) + list(self.recipes_dir.glob("*.yml")):
                if existing_file.name not in keep:
                    try:
                        existing_file.unlink()
                        pruned_count += 1
                        logger.debug("Pruned stale cached recipe: %s", existing_file.name)
                    except OSError as oe:
                        logger.warning("Failed to prune stale recipe %s: %s", existing_file.name, oe)

        return SyncResult(
            synced_count,
            f"Successfully synchronized {synced_count} packages from remote index",
            is_fallback=False,
            sha256=index_sha256,
            pruned=pruned_count,
        )
