# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Unit tests for remote package index sync and offline caching."""

import json
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from ebuild.cli.commands import cli
from ebuild.packages.index_sync import (
    MAX_INDEX_SIZE_BYTES,
    IndexSyncError,
    IndexSyncManager,
    get_default_index_dir,
    is_offline,
    sanitize_package_name,
)


def test_sanitize_package_name():
    assert sanitize_package_name("cjson") == "cjson"
    assert sanitize_package_name("my_pkg-123") == "my_pkg-123"

    with pytest.raises(ValueError, match="Invalid package name"):
        sanitize_package_name("../../etc/passwd")

    with pytest.raises(ValueError, match="Invalid package name"):
        sanitize_package_name("pkg with spaces")

    with pytest.raises(ValueError, match="Invalid package name"):
        sanitize_package_name("")


def test_is_offline(monkeypatch):
    assert not is_offline(False)
    assert is_offline(True)

    monkeypatch.setenv("EBUILD_OFFLINE", "1")
    assert is_offline(False)

    monkeypatch.setenv("EBUILD_OFFLINE", "true")
    assert is_offline(False)

    monkeypatch.setenv("EBUILD_OFFLINE", "0")
    assert not is_offline(False)


def test_get_default_index_dir(monkeypatch, tmp_path):
    custom_dir = tmp_path / "custom_index"
    monkeypatch.setenv("EBUILD_INDEX_PATH", str(custom_dir))
    assert get_default_index_dir() == custom_dir


def test_index_sync_missing_url(tmp_path):
    """Verify Finding 3: Empty default URL raises IndexSyncError when no URL is given."""
    mgr = IndexSyncManager(index_dir=tmp_path)
    with pytest.raises(IndexSyncError, match="No remote package index URL configured"):
        mgr.sync()


def test_index_sync_insecure_url(tmp_path):
    mgr = IndexSyncManager(index_dir=tmp_path)
    with pytest.raises(IndexSyncError, match="Insecure index URL"):
        mgr.sync(url="http://insecure.example.com/index.json")


def test_index_sync_success(tmp_path):
    mgr = IndexSyncManager(index_dir=tmp_path)

    sample_index = [
        {
            "name": "mock-pkg",
            "version": "1.0.0",
            "description": "A mock package for testing",
            "license": "MIT",
            "url": "https://example.com/mock-pkg-1.0.0.tar.gz",
            "checksum": "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "build_system": "cmake",
            "configure_args": ["-DMOCK=ON"],
        }
    ]
    raw_json = json.dumps(sample_index).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.read.return_value = raw_json
    mock_resp.headers = {"Content-Length": str(len(raw_json))}
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = mgr.sync(url="https://example.com/index.json", force=True)

    assert res.package_count == 1
    assert not res.is_fallback
    assert "Successfully synchronized 1 packages" in res.message
    assert mgr.packages_json.is_file()
    assert mgr.packages_json.with_name(mgr.packages_json.name + ".sha256").is_file()
    assert mgr.meta_json.is_file()

    # Check that recipe YAML was cached
    recipe_file = mgr.recipes_dir / "mock-pkg.yaml"
    assert recipe_file.is_file()
    content = recipe_file.read_text(encoding="utf-8")
    assert "mock-pkg" in content
    assert "1.0.0" in content


def test_index_sync_corrupted_json(tmp_path):
    mgr = IndexSyncManager(index_dir=tmp_path)

    mock_resp = MagicMock()
    mock_resp.read.return_value = b"{ invalid json"
    mock_resp.headers = {}
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        with pytest.raises(IndexSyncError, match="Corrupted or invalid JSON"):
            mgr.sync(url="https://example.com/index.json")


def test_index_sync_network_error_fallback(tmp_path):
    mgr = IndexSyncManager(index_dir=tmp_path)
    mgr.ensure_directories()

    # Seed cache
    cached_data = [{"name": "cached-lib", "version": "2.0.0"}]
    mgr.packages_json.write_text(json.dumps(cached_data), encoding="utf-8")

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("No connection")):
        res = mgr.sync(url="https://example.com/index.json", force=True)

    assert res.package_count == 1
    assert res.is_fallback
    assert "fell back to cached index" in res.message


def test_index_sync_offline_mode(tmp_path):
    mgr = IndexSyncManager(index_dir=tmp_path)
    mgr.ensure_directories()

    cached_data = [{"name": "offline-lib", "version": "1.0.0"}]
    mgr.packages_json.write_text(json.dumps(cached_data), encoding="utf-8")

    res = mgr.sync(offline=True)
    assert res.package_count == 1
    assert not res.is_fallback
    assert "Offline mode" in res.message


def test_index_sync_filters_unsafe_and_counts_accurately(tmp_path):
    """Verify Findings 6 & 9a:
    1. Cache filters unsafe package names and does not store them in packages.json.
    2. synced_count only increments for packages where a recipe was actually written.
    """
    mgr = IndexSyncManager(index_dir=tmp_path)

    sample_index = [
        {
            "name": "good-pkg",
            "version": "1.0.0",
            "url": "https://example.com/good.tar.gz",
            "checksum": "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        },
        {
            "name": "bad name!",
            "version": "1.0.0",
            "url": "https://example.com/bad.tar.gz",
        },
        {
            "name": "urlless-pkg",
            "version": "1.0.0",
            "description": "No download URL",
        },
    ]
    raw_json = json.dumps(sample_index).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.read.return_value = raw_json
    mock_resp.headers = {"Content-Length": str(len(raw_json))}
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = mgr.sync(url="https://example.com/index.json", force=True)

    # Only good-pkg had a URL and passed validation -> 1 recipe written
    assert res.package_count == 1
    assert "Successfully synchronized 1 packages" in res.message

    # Verify packages.json does not contain "bad name!"
    cached_entries = json.loads(mgr.packages_json.read_text(encoding="utf-8"))
    entry_names = [e["name"] for e in cached_entries]
    assert "good-pkg" in entry_names
    assert "urlless-pkg" in entry_names
    assert "bad name!" not in entry_names

    # Verify only good-pkg recipe file exists on disk
    assert (mgr.recipes_dir / "good-pkg.yaml").is_file()
    assert not (mgr.recipes_dir / "urlless-pkg.yaml").exists()


def test_index_sync_force_and_staleness(tmp_path):
    """Verify Finding 2 & Finding 7: Cache freshness checks TTL and matches origin URL unless force=True."""
    mgr = IndexSyncManager(index_dir=tmp_path)
    mgr.ensure_directories()

    cached_data = [{"name": "fresh-pkg", "version": "1.0.0", "url": "https://example.com/fresh.tar.gz"}]
    mgr.packages_json.write_text(json.dumps(cached_data), encoding="utf-8")
    # Record metadata for index A
    mgr.meta_json.write_text(json.dumps({"url": "https://a.example/index.json"}), encoding="utf-8")

    with patch("urllib.request.urlopen") as mock_url:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(cached_data).encode("utf-8")
        mock_resp.headers = {}
        mock_resp.__enter__.return_value = mock_resp
        mock_url.return_value = mock_resp

        # 1. Fresh cache (< 24h) from same URL without force -> reuses cache
        res = mgr.sync(url="https://a.example/index.json", force=False)
        assert res.package_count == 1
        assert "Cache is up-to-date" in res.message
        mock_url.assert_not_called()

        # 2. Fresh cache (< 24h) but requested URL is DIFFERENT -> fetches new URL! (Finding 2)
        res_diff_url = mgr.sync(url="https://b.example/index.json", force=False)
        assert mock_url.called
        assert res_diff_url.package_count == 1

        mock_url.reset_mock()

        # 3. With force=True, urlopen must be called even for same URL
        mgr.sync(url="https://b.example/index.json", force=True)
        assert mock_url.called


def test_index_sync_size_cap_and_lying_content_length(tmp_path):
    """Verify max size cap and malformed Content-Length handling."""
    mgr = IndexSyncManager(index_dir=tmp_path)

    # 1. Content-Length header is excessively large
    mock_resp = MagicMock()
    mock_resp.headers = {"Content-Length": str(MAX_INDEX_SIZE_BYTES + 100)}
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        with pytest.raises(IndexSyncError, match="exceeds maximum allowed size"):
            mgr.sync(url="https://example.com/index.json", force=True)

    # 2. Lying Content-Length: header claims small size, but stream exceeds limit
    mock_resp2 = MagicMock()
    mock_resp2.headers = {"Content-Length": "50"}
    mock_resp2.read.return_value = b"x" * (MAX_INDEX_SIZE_BYTES + 2)
    mock_resp2.__enter__.return_value = mock_resp2

    with patch("urllib.request.urlopen", return_value=mock_resp2):
        with pytest.raises(IndexSyncError, match="exceeded maximum size limit"):
            mgr.sync(url="https://example.com/index.json", force=True)

    # 3. Malformed non-numeric Content-Length: does not raise ValueError (Finding 3)
    valid_payload = json.dumps([{"name": "test-pkg", "url": "https://example.com/pkg.tar.gz"}]).encode("utf-8")
    mock_resp3 = MagicMock()
    mock_resp3.headers = {"Content-Length": "not-a-number"}
    mock_resp3.read.return_value = valid_payload
    mock_resp3.__enter__.return_value = mock_resp3

    with patch("urllib.request.urlopen", return_value=mock_resp3):
        res = mgr.sync(url="https://example.com/index.json", force=True)
        assert res.package_count == 1


def test_index_sync_deduplicates_duplicate_names(tmp_path):
    """Verify Finding 6: Duplicate names in an index are deduplicated to avoid overwrites and over-reporting."""
    mgr = IndexSyncManager(index_dir=tmp_path)

    duplicate_index = [
        {"name": "dup", "version": "1.0.0", "url": "https://example.com/dup1.tar.gz"},
        {"name": "dup", "version": "9.9.9", "url": "https://example.com/dup9.tar.gz"},
    ]
    raw_json = json.dumps(duplicate_index).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.read.return_value = raw_json
    mock_resp.headers = {"Content-Length": str(len(raw_json))}
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = mgr.sync(url="https://example.com/index.json", force=True)

    assert res.package_count == 1
    assert "Successfully synchronized 1 packages" in res.message
    # Verify recipes dir has only 1 file
    recipe_files = list(mgr.recipes_dir.glob("*.yaml"))
    assert len(recipe_files) == 1
    assert recipe_files[0].name == "dup.yaml"

    # Verify packages.json has only 1 entry
    cached_entries = json.loads(mgr.packages_json.read_text(encoding="utf-8"))
    assert len(cached_entries) == 1


def test_cli_update_index_fallback_exits_nonzero(tmp_path, monkeypatch):
    """Verify Finding 8: CLI update-index logs warning and exits 1 on fallback."""
    custom_dir = tmp_path / "index_cache"
    custom_dir.mkdir()
    packages_json = custom_dir / "packages.json"
    packages_json.write_text(json.dumps([{"name": "stale-pkg", "version": "1.0.0"}]), encoding="utf-8")
    monkeypatch.setenv("EBUILD_INDEX_PATH", str(custom_dir))

    runner = CliRunner()
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Network down")):
        # Without offline flag, network failure falling back to cache must exit non-zero
        result = runner.invoke(cli, ["update-index", "--url", "https://example.com/index.json", "--force"])
        assert result.exit_code == 1
        assert "fell back to cached index" in result.output


def test_index_sync_prunes_stale_cached_recipes(tmp_path):
    """Verify Finding 5: Cached recipe YAMLs not present in new index are pruned."""
    mgr = IndexSyncManager(index_dir=tmp_path)

    # First sync: index containing 'alpha'
    index_a = [
        {"name": "alpha", "version": "1.0.0", "url": "https://example.com/alpha.tar.gz"},
    ]
    raw_a = json.dumps(index_a).encode("utf-8")
    mock_resp_a = MagicMock()
    mock_resp_a.read.return_value = raw_a
    mock_resp_a.headers = {"Content-Length": str(len(raw_a))}
    mock_resp_a.__enter__.return_value = mock_resp_a

    with patch("urllib.request.urlopen", return_value=mock_resp_a):
        res_a = mgr.sync(url="https://example.com/index-a.json", force=True)
        assert res_a.package_count == 1
        assert res_a.pruned == 0

    recipe_files_a = sorted([f.name for f in mgr.recipes_dir.glob("*.yaml")])
    assert recipe_files_a == ["alpha.yaml"]

    # Also add a stale .yml file (Finding 3: stale .yml must not survive sync)
    (mgr.recipes_dir / "stale.yml").write_text("package: stale\nversion: 1.0.0", encoding="utf-8")

    # Second sync: index containing 'beta' (alpha withdrawn/absent)
    index_b = [
        {"name": "beta", "version": "2.0.0", "url": "https://example.com/beta.tar.gz"},
    ]
    raw_b = json.dumps(index_b).encode("utf-8")
    mock_resp_b = MagicMock()
    mock_resp_b.read.return_value = raw_b
    mock_resp_b.headers = {"Content-Length": str(len(raw_b))}
    mock_resp_b.__enter__.return_value = mock_resp_b

    with patch("urllib.request.urlopen", return_value=mock_resp_b):
        res_b = mgr.sync(url="https://example.com/index-b.json", force=True)
        assert res_b.package_count == 1
        # Both alpha.yaml and stale.yml must be counted as pruned
        assert res_b.pruned == 2

    recipe_files_b = sorted([f.name for f in mgr.recipes_dir.iterdir() if f.is_file()])
    # alpha.yaml and stale.yml must be pruned; only beta.yaml must remain!
    assert recipe_files_b == ["beta.yaml"]


def test_index_sync_preserves_cached_recipe_if_index_entry_lacks_url(tmp_path):
    """Verify Finding 1: An index entry that loses URL still preserves cached recipe file."""
    mgr = IndexSyncManager(index_dir=tmp_path)
    mgr.ensure_directories()
    (mgr.recipes_dir / "preserved.yaml").write_text(
        "package: preserved\nversion: 1.0.0\nurl: https://example.com/preserved.tar.gz\nbuild: cmake\n",
        encoding="utf-8",
    )

    index_data = [
        {"name": "preserved", "version": "1.0.0", "description": "Entry without download URL"},
    ]
    raw_json = json.dumps(index_data).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.read.return_value = raw_json
    mock_resp.headers = {"Content-Length": str(len(raw_json))}
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = mgr.sync(url="https://example.com/index.json", force=True)
        assert res.pruned == 0
        assert (mgr.recipes_dir / "preserved.yaml").is_file()


def test_cli_update_index_reports_sha256_digest(tmp_path, monkeypatch):
    """Verify Finding 6: CLI update-index surfaces the SHA-256 digest and updates."""
    custom_dir = tmp_path / "index_cache"
    monkeypatch.setenv("EBUILD_INDEX_PATH", str(custom_dir))

    index_data = [
        {"name": "gamma", "version": "1.0.0", "url": "https://example.com/gamma.tar.gz"},
    ]
    raw_json = json.dumps(index_data).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.read.return_value = raw_json
    mock_resp.headers = {"Content-Length": str(len(raw_json))}
    mock_resp.__enter__.return_value = mock_resp

    runner = CliRunner()
    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = runner.invoke(cli, ["update-index", "--url", "https://example.com/index.json", "--force"])
        assert result.exit_code == 0
        assert "Index SHA-256 digest:" in result.output


def test_cli_update_index_reports_pruned_count(tmp_path, monkeypatch):
    """Verify Finding 2: CLI update-index surfaces count of pruned stale recipes."""
    custom_dir = tmp_path / "index_cache"
    recipes_dir = custom_dir / "recipes"
    recipes_dir.mkdir(parents=True)
    (recipes_dir / "old.yaml").write_text("package: old\nversion: 1.0.0\n", encoding="utf-8")
    monkeypatch.setenv("EBUILD_INDEX_PATH", str(custom_dir))

    index_data = [
        {"name": "newpkg", "version": "1.0.0", "url": "https://example.com/newpkg.tar.gz"},
    ]
    raw_json = json.dumps(index_data).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.read.return_value = raw_json
    mock_resp.headers = {"Content-Length": str(len(raw_json))}
    mock_resp.__enter__.return_value = mock_resp

    runner = CliRunner()
    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = runner.invoke(cli, ["update-index", "--url", "https://example.com/index.json", "--force"])
        assert result.exit_code == 0
        assert "Pruned 1 stale cached recipe(s)" in result.output


def test_index_sync_empty_index_preserves_cache_and_warns(tmp_path):
    """Verify Finding 1 & Finding 2: An empty index payload refuses to prune cached recipes, does not overwrite metadata, and reports fallback."""
    mgr = IndexSyncManager(index_dir=tmp_path)
    mgr.ensure_directories()

    # Seed recipes
    (mgr.recipes_dir / "alpha.yaml").write_text("package: alpha\nversion: 1.0.0\n", encoding="utf-8")
    (mgr.recipes_dir / "bravo.yaml").write_text("package: bravo\nversion: 1.0.0\n", encoding="utf-8")
    # Seed packages.json
    seed_json = [{"name": "alpha", "version": "1.0.0"}, {"name": "bravo", "version": "1.0.0"}]
    mgr.packages_json.write_text(json.dumps(seed_json), encoding="utf-8")

    # Seed index-meta.json and sha256 sidecar
    initial_meta = {
        "url": "https://example.com/index.json",
        "sha256": "initial_sha_12345",
        "synced_at": 1000.0,
    }
    mgr.meta_json.write_text(json.dumps(initial_meta), encoding="utf-8")
    sha_file = mgr.packages_json.with_name(mgr.packages_json.name + ".sha256")
    sha_file.write_text("initial_sha_12345  packages.json\n", encoding="utf-8")

    raw_json = json.dumps([]).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.read.return_value = raw_json
    mock_resp.headers = {"Content-Length": str(len(raw_json))}
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = mgr.sync(url="https://example.com/index.json", force=True)
        assert res.pruned == 0
        assert res.package_count == 2
        assert res.is_fallback is True

    assert (mgr.recipes_dir / "alpha.yaml").is_file()
    assert (mgr.recipes_dir / "bravo.yaml").is_file()
    # packages.json must NOT be overwritten with []
    cached = json.loads(mgr.packages_json.read_text(encoding="utf-8"))
    assert len(cached) == 2

    # index-meta.json and packages.json.sha256 must NOT be overwritten with [] metadata
    meta_after = json.loads(mgr.meta_json.read_text(encoding="utf-8"))
    assert meta_after["sha256"] == "initial_sha_12345"
    assert meta_after["synced_at"] == 1000.0
    assert sha_file.read_text(encoding="utf-8") == "initial_sha_12345  packages.json\n"

    # Subsequent non-forced sync must retry via network (not short-circuited by 24h TTL)
    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_retry:
        res_retry = mgr.sync(url="https://example.com/index.json", force=False)
        assert mock_retry.called
        assert res_retry.is_fallback is True


def test_index_sync_unparseable_entries_preserves_cache(tmp_path):
    """Verify Finding 1: An index with no usable entries refuses to prune cached recipes and reports fallback."""
    mgr = IndexSyncManager(index_dir=tmp_path)
    mgr.ensure_directories()

    (mgr.recipes_dir / "alpha.yaml").write_text("package: alpha\nversion: 1.0.0\n", encoding="utf-8")
    (mgr.recipes_dir / "bravo.yaml").write_text("package: bravo\nversion: 1.0.0\n", encoding="utf-8")

    raw_json = json.dumps([{"nope": 1}, "str", 5]).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.read.return_value = raw_json
    mock_resp.headers = {"Content-Length": str(len(raw_json))}
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = mgr.sync(url="https://example.com/index.json", force=True)
        assert res.pruned == 0
        assert res.package_count == 0
        assert res.is_fallback is True

    assert (mgr.recipes_dir / "alpha.yaml").is_file()
    assert (mgr.recipes_dir / "bravo.yaml").is_file()


def test_index_sync_preserves_yml_if_not_superseded_and_prunes_if_superseded(tmp_path):
    """Verify Finding 5: Cached .yml is kept when index names entry without URL, and pruned when superseded by .yaml."""
    mgr = IndexSyncManager(index_dir=tmp_path)
    mgr.ensure_directories()

    # Pre-existing .yml recipes in cache
    (mgr.recipes_dir / "eps.yml").write_text("package: eps\nversion: 1.0.0\n", encoding="utf-8")
    (mgr.recipes_dir / "delta.yml").write_text("package: delta\nversion: 9.9.9\n", encoding="utf-8")

    # Index lists eps (no url -> no .yaml written) and delta (with url -> delta.yaml written)
    index_data = [
        {"name": "eps", "version": "1.0.0", "description": "Entry without download URL"},
        {"name": "delta", "version": "2.0.0", "url": "https://example.com/delta.tar.gz"},
    ]
    raw_json = json.dumps(index_data).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.read.return_value = raw_json
    mock_resp.headers = {"Content-Length": str(len(raw_json))}
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = mgr.sync(url="https://example.com/index.json", force=True)
        # delta.yml is pruned because delta.yaml superseded it; eps.yml is NOT pruned
        assert res.pruned == 1

    # eps.yml survived
    assert (mgr.recipes_dir / "eps.yml").is_file()
    # delta.yml was pruned and replaced by delta.yaml
    assert not (mgr.recipes_dir / "delta.yml").exists()
    assert (mgr.recipes_dir / "delta.yaml").is_file()


def test_changelog_trailing_newline():
    """Verify Finding 2 & Finding 6: CHANGELOG.md ends with a trailing newline."""
    changelog_path = Path(__file__).resolve().parents[2] / "CHANGELOG.md"
    assert changelog_path.is_file()
    content = changelog_path.read_bytes()
    assert content.endswith(b"\n")

