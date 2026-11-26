# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Package fetcher — downloads, verifies, and extracts source archives.

Handles HTTP/HTTPS downloads, SHA-256 checksum verification, and
tar/zip extraction into the package cache directory.

Downloads are bounded and atomic: a socket timeout keeps a stalled mirror
from hanging the build forever, an overall size cap keeps a runaway
response from filling the disk, and the archive is streamed to a ``.part``
file that is renamed into place only once complete, so a crashed download
never leaves a truncated archive behind to satisfy the cache.
"""

from __future__ import annotations

import hashlib
import http.client
import os
import re
import tarfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional

from ebuild.hashing import sha256_file
from ebuild.packages.index_sync import is_offline
from ebuild.packages.recipe import PackageRecipe

# Seconds a download may stall before it is abandoned. urlretrieve() carried
# no timeout at all, so one unresponsive mirror hung `ebuild build` until the
# user killed it.
DEFAULT_DOWNLOAD_TIMEOUT_SECONDS = 30

# Upper bound on a single downloaded archive (512 MB). Enforced while
# streaming, so a server that lies about (or omits) Content-Length still
# cannot fill the disk.
MAX_ARCHIVE_SIZE_BYTES = 512 * 1024 * 1024

# Chunk size for streaming a download to disk.
DOWNLOAD_CHUNK_SIZE_BYTES = 256 * 1024


class FetchError(Exception):
    """Raised when a package cannot be fetched or verified."""


class PackageFetcher:
    """Downloads and extracts package source archives.

    Downloads are cached so repeated builds don't re-download.
    Checksums are verified to ensure integrity.
    """

    def __init__(
        self,
        download_dir: str | Path,
        timeout: int = DEFAULT_DOWNLOAD_TIMEOUT_SECONDS,
    ) -> None:
        self.download_dir = Path(download_dir)
        self.timeout = timeout
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def fetch(self, recipe: PackageRecipe, extract_to: str | Path) -> Path:
        """Fetch a package: download archive, verify checksum, extract.

        Args:
            recipe: The package recipe describing what to fetch.
            extract_to: Directory to extract source into.

        Returns:
            Path to the extracted source directory.

        Raises:
            FetchError: If download or verification fails, or if offline
                mode is active and the archive is not already cached.
        """
        # Offline mode must gate archive fetching the same way it gates index
        # synchronization: a fetch that is not already in the download cache
        # requires the network, and in offline mode there is no network.
        if is_offline() and not self.is_downloaded(recipe):
            archive_path = self._archive_path(recipe)
            where = f" ({archive_path})" if archive_path else ""
            raise FetchError(
                f"Offline mode (EBUILD_OFFLINE=1): package {recipe.name} "
                f"v{recipe.version} is not in the download cache{where}. "
                f"Re-run without offline mode to download it."
            )

        # PackageRecipe.validate() rejects a recipe without a checksum, but
        # fetch() is reachable with a hand-built recipe too, so refuse here as
        # well rather than falling through to an unverified extract.
        if not recipe.checksum:
            raise FetchError(
                f"Refusing to fetch {recipe.name} v{recipe.version}: the recipe "
                f"carries no checksum, so there is nothing to verify the "
                f"download against."
            )

        archive_path = self._download(recipe)
        if recipe.checksum:
            try:
                self._verify_checksum(archive_path, recipe.checksum)
            except FetchError:
                # A mismatching archive is worthless, and _download()
                # short-circuits on existence — leaving it in the cache made
                # every later build fail with the same error until someone
                # deleted it by hand. Drop it so a retry re-downloads.
                archive_path.unlink(missing_ok=True)
                raise
        extract_path = Path(extract_to)
        self._extract(archive_path, extract_path)
        return extract_path

    def _download(self, recipe: PackageRecipe) -> Path:
        """Download the source archive if not already cached."""
        if not recipe.url:
            raise FetchError(f"No URL specified for package {recipe.name}")
        if not recipe.url.startswith("https://"):
            raise FetchError(
                f"Invalid URL scheme for {recipe.name}: {recipe.url} "
                f"(only https:// is allowed)"
            )

        archive_path = self._archive_path(recipe)
        if archive_path is None:
            raise FetchError(f"Could not derive filename from URL: {recipe.url}")

        if archive_path.exists():
            return archive_path

        archive_path.parent.mkdir(parents=True, exist_ok=True)

        # Stream to a .part sibling and rename only once complete. A download
        # that dies halfway must not leave a truncated file at archive_path:
        # _download() short-circuits on existence, so a partial archive would
        # be served by every later fetch as if it were the real thing.
        partial_path = archive_path.with_name(archive_path.name + ".part")
        try:
            try:
                request = urllib.request.Request(
                    recipe.url,
                    headers={"User-Agent": "ebuild-package-manager/3.0"},
                )
                with urllib.request.urlopen(
                    request, timeout=self.timeout
                ) as response:
                    received = 0
                    with open(partial_path, "wb") as f:
                        while True:
                            chunk = response.read(DOWNLOAD_CHUNK_SIZE_BYTES)
                            if not chunk:
                                break
                            received += len(chunk)
                            if received > MAX_ARCHIVE_SIZE_BYTES:
                                raise FetchError(
                                    f"Archive from {recipe.url} exceeds the "
                                    f"maximum size of {MAX_ARCHIVE_SIZE_BYTES} bytes"
                                )
                            f.write(chunk)
                os.replace(partial_path, archive_path)
            except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError) as e:
                raise FetchError(
                    f"Failed to download {recipe.name} v{recipe.version} "
                    f"from {recipe.url}: {e}"
                ) from e
        finally:
            partial_path.unlink(missing_ok=True)

        return archive_path

    def _verify_checksum(self, archive_path: Path, checksum: str) -> None:
        """Verify SHA-256 checksum of a downloaded archive."""
        expected = checksum
        if expected.startswith("sha256:"):
            expected = expected[7:]
        # PackageRecipe.validate() accepts either case; hexdigest() is
        # lower-case, so compare in that case.
        expected = expected.lower()

        actual = sha256_file(archive_path)
        if actual != expected:
            raise FetchError(
                f"Checksum mismatch for {archive_path.name}:\n"
                f"  expected: {expected}\n"
                f"  actual:   {actual}"
            )

    def _extract(self, archive_path: Path, extract_to: Path) -> None:
        """Extract a tar.gz, tar.bz2, tar.xz, or .zip archive."""
        extract_to.mkdir(parents=True, exist_ok=True)

        name = archive_path.name.lower()
        try:
            if name.endswith((".tar.gz", ".tgz")):
                with tarfile.open(archive_path, "r:gz") as tar:
                    self._extract_tar(tar, extract_to)
            elif name.endswith((".tar.bz2", ".tbz2")):
                with tarfile.open(archive_path, "r:bz2") as tar:
                    self._extract_tar(tar, extract_to)
            elif name.endswith((".tar.xz", ".txz")):
                with tarfile.open(archive_path, "r:xz") as tar:
                    self._extract_tar(tar, extract_to)
            elif name.endswith(".zip"):
                with zipfile.ZipFile(archive_path, "r") as zf:
                    self._extract_zip(zf, extract_to)
            else:
                raise FetchError(f"Unsupported archive format: {archive_path.name}")
        except FetchError:
            raise
        except (tarfile.TarError, zipfile.BadZipFile, OSError) as e:
            raise FetchError(f"Failed to extract {archive_path.name}: {e}")

    @staticmethod
    def _path_is_within(base: Path, target: Path) -> bool:
        """Return True if *target* resolves strictly inside *base*.

        Uses Path.relative_to rather than a string prefix check so that
        ``/tmp/extract-evil`` is not treated as inside ``/tmp/extract``.
        """
        try:
            target.resolve().relative_to(base.resolve())
            return True
        except ValueError:
            return False

    def _extract_tar(self, tar: tarfile.TarFile, extract_to: Path) -> None:
        """Extract a tar archive, compatible with Python 3.8–3.11 and 3.12+.

        ``filter='data'`` (CVE-2007-4559 mitigation) was added in Python 3.12.
        README and pyproject.toml claim support for Python 3.8+, so older
        interpreters must extract without that keyword and with an explicit
        member-path check instead.
        """
        if hasattr(tarfile, "data_filter"):
            try:
                tar.extractall(extract_to, filter="data")
            except Exception as e:
                # 3.12+ raises FilterError / OutsideDestinationError for
                # members that would extract outside extract_to.
                err_name = type(e).__name__
                if "Filter" in err_name or "Outside" in err_name or "Absolute" in err_name:
                    raise FetchError(f"Tar path traversal detected: {e}") from e
                raise
            return

        extract_root = extract_to.resolve()
        for member in tar.getmembers():
            dest = extract_to / member.name
            if not self._path_is_within(extract_root, dest):
                raise FetchError(f"Tar path traversal detected: {member.name}")
            if member.issym() or member.islnk():
                link_dest = dest.parent / member.linkname
                if Path(member.linkname).is_absolute():
                    link_dest = Path(member.linkname)
                if not self._path_is_within(extract_root, link_dest):
                    raise FetchError(
                        f"Tar link path traversal detected: {member.name} -> {member.linkname}"
                    )
        tar.extractall(extract_to)

    def _extract_zip(self, zf: zipfile.ZipFile, extract_to: Path) -> None:
        """Extract a zip archive after rejecting path-traversal members."""
        extract_root = extract_to.resolve()
        for member in zf.namelist():
            if not self._path_is_within(extract_root, extract_to / member):
                raise FetchError(f"Zip path traversal detected: {member}")
        zf.extractall(extract_to)

    #: Suffixes _extract() can open. Longest-first so ".tar.gz" is not read
    #: as ".gz".
    ARCHIVE_SUFFIXES = (
        ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz", ".zip",
    )

    #: A name safe to join onto download_dir. Excludes "/", "\\", ".." and
    #: the characters Windows rejects in a filename.
    _SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9._+-]+$")

    @classmethod
    def _archive_suffix(cls, name: str) -> str:
        """The supported archive suffix of *name*, or "" if it has none."""
        lowered = name.lower()
        for suffix in cls.ARCHIVE_SUFFIXES:
            if lowered.endswith(suffix):
                return suffix
        return ""

    @classmethod
    def _safe_name(cls, name: str) -> str:
        """*name* if it is usable as a single path component, else ""."""
        if name in (".", "..") or not cls._SAFE_NAME_RE.match(name):
            return ""
        return name

    def _archive_filename(self, recipe: PackageRecipe) -> str:
        """Derive archive filename from recipe URL.

        Only the URL path names the file: a ``?query`` or ``#fragment`` left
        on hid the archive extension from _extract() and put '?' in a file
        name, which Windows rejects. The download still uses the full URL.

        A URL whose path names no archive but whose query does -- the
        ``/download?file=foo.tar.gz`` form -- is named from the query, so
        _extract() still sees a format it supports instead of rejecting
        "download" as an unsupported one.

        Returns "" when nothing usable can be derived, including when the
        URL does not parse: urlsplit() raises ValueError on an unmatched
        '[' in the authority, and that ran ahead of _download()'s handler
        and inside is_downloaded(), which has none, so fetch() raised
        ValueError instead of the FetchError it documents. _archive_path()
        turns "" into None and the callers raise FetchError.
        """
        try:
            parts = urllib.parse.urlsplit(recipe.url)
        except ValueError:
            return ""

        name = self._safe_name(parts.path.rstrip("/").split("/")[-1])
        if self._archive_suffix(name):
            return name

        for _key, value in urllib.parse.parse_qsl(parts.query):
            candidate = self._safe_name(value.rstrip("/").split("/")[-1])
            if self._archive_suffix(candidate):
                return candidate

        return name

    def _archive_path(self, recipe: PackageRecipe) -> Optional[Path]:
        """Cache path for *recipe*'s archive, namespaced by package slug.

        The URL basename alone does not identify a package. GitHub tag
        archives — ``.../archive/refs/tags/v2.9.3.tar.gz``, the form used by
        ``recipes/littlefs.yaml`` — reduce to ``v2.9.3.tar.gz`` and carry no
        package name, so two recipes sharing a tag would map to the same file
        in the flat download directory. Namespacing by ``recipe.slug``
        (name-version) keeps each package separate and matches the layout
        PackageCache already uses.

        Two URLs that differ only after the '?' now reduce to the same
        filename, so the query and fragment have to reach the cache key as
        well: _download() short-circuits on existence, and without this the
        archive fetched for one query variant would be served for the next,
        failing its checksum instead of being downloaded. Only URLs that
        carry a query or fragment get the extra level, so the cache layout
        for every ordinary URL is unchanged.

        Returns None when no filename can be derived from the URL.
        """
        filename = self._archive_filename(recipe)
        if not filename:
            return None

        parent = self.download_dir / recipe.slug
        try:
            parts = urllib.parse.urlsplit(recipe.url)
        except ValueError:
            return None
        if parts.query or parts.fragment:
            digest = hashlib.sha256(recipe.url.encode("utf-8")).hexdigest()
            parent = parent / digest[:12]
        return parent / filename

    def is_downloaded(self, recipe: PackageRecipe) -> bool:
        """Check if the archive is already downloaded."""
        archive_path = self._archive_path(recipe)
        return archive_path is not None and archive_path.exists()
