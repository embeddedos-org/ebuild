# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Unit tests for package discovery and search across repository sources."""

import json
from click.testing import CliRunner

from ebuild.cli.commands import cli
from ebuild.packages.index_sync import IndexSyncManager
from ebuild.packages.repository import PackageRepository


def test_package_repository_search(tmp_path):
    repo = PackageRepository()

    # Create dummy local recipe directory
    recipe_dir = tmp_path / "recipes"
    recipe_dir.mkdir()
    (recipe_dir / "my_crypto.yaml").write_text(
        """package: my_crypto
version: "1.0.0"
description: "Embedded cryptography primitives"
license: Apache-2.0
url: https://example.com/crypto.tar.gz
checksum: sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
build: cmake
""",
        encoding="utf-8",
    )

    repo.add_recipe_directory(recipe_dir)
    assert repo.package_count == 1

    # Search by keyword
    results = repo.search("crypto")
    assert len(results) == 1
    assert results[0].name == "my_crypto"

    # Search by license filter
    assert len(repo.search("", license_filter="Apache")) == 1
    assert len(repo.search("", license_filter="GPL")) == 0

    # Search by build system
    assert len(repo.search("", build_system="cmake")) == 1
    assert len(repo.search("", build_system="meson")) == 0


def test_package_source_precedence_project_wins(tmp_path):
    """Verify Finding 1: Project-local recipe takes precedence over shipped and cached remote recipes."""
    # 1. Create project-local recipe
    proj_dir = tmp_path / "project"
    proj_recipes = proj_dir / "recipes"
    proj_recipes.mkdir(parents=True)
    (proj_recipes / "cjson.yaml").write_text(
        """package: cjson
version: "1.7.18"
description: "Project pinned cjson"
url: "https://custom-project.org/cjson-PROJECT.tar.gz"
checksum: "sha256:1111111111111111111111111111111111111111111111111111111111111111"
build: cmake
""",
        encoding="utf-8",
    )

    # 2. Create remote cached index with a higher version (9.9.9) for cjson
    remote_index_dir = tmp_path / "remote_index"
    remote_recipes = remote_index_dir / "recipes"
    remote_recipes.mkdir(parents=True)
    (remote_recipes / "cjson.yaml").write_text(
        """package: cjson
version: "9.9.9"
description: "Remote cjson"
url: "https://remote-registry.org/cjson-REMOTE.tar.gz"
checksum: "sha256:2222222222222222222222222222222222222222222222222222222222222222"
build: cmake
""",
        encoding="utf-8",
    )
    # Also in packages.json
    packages_json = remote_index_dir / "packages.json"
    packages_json.write_text(
        json.dumps([
            {
                "name": "cjson",
                "version": "9.9.9",
                "url": "https://remote-registry.org/cjson-REMOTE.tar.gz",
                "checksum": "sha256:2222222222222222222222222222222222222222222222222222222222222222",
            }
        ]),
        encoding="utf-8",
    )

    # 1. Search path verification (PackageRepository)
    sync_mgr = IndexSyncManager(index_dir=remote_index_dir)
    repo = PackageRepository(sync_manager=sync_mgr)
    repo.load_all_sources(project_dir=proj_dir)

    pkg = repo.info("cjson")
    assert pkg is not None
    # Must resolve to the PROJECT-local version, url, and checksum!
    assert pkg.version == "1.7.18"
    assert pkg.url == "https://custom-project.org/cjson-PROJECT.tar.gz"
    assert pkg.checksum == "sha256:1111111111111111111111111111111111111111111111111111111111111111"
    assert pkg.description == "Project pinned cjson"

    # 2. Build path verification (_find_recipe_dirs + create_registry)
    from ebuild.cli.commands import _find_recipe_dirs
    from ebuild.packages.registry import create_registry

    recipe_dirs = _find_recipe_dirs(proj_dir, remote_index_dir=remote_index_dir)
    registry = create_registry(*recipe_dirs)

    # Explicit version lookup
    build_recipe = registry.get("cjson", "1.7.18")
    assert build_recipe is not None
    assert build_recipe.url == "https://custom-project.org/cjson-PROJECT.tar.gz"
    assert build_recipe.checksum == "sha256:1111111111111111111111111111111111111111111111111111111111111111"

    # Unpinned version lookup: project-local recipe must win over higher remote version!
    unpinned_recipe = registry.get("cjson")
    assert unpinned_recipe is not None
    assert unpinned_recipe.version == "1.7.18"
    assert unpinned_recipe.url == "https://custom-project.org/cjson-PROJECT.tar.gz"
    assert unpinned_recipe.checksum == "sha256:1111111111111111111111111111111111111111111111111111111111111111"


def test_transitive_dependency_source_precedence_project_wins(tmp_path):
    """Verify Finding 1: Transitive dependencies resolve to project-local definitions even when remote has higher version."""
    from ebuild.cli.commands import _find_recipe_dirs
    from ebuild.packages.registry import create_registry
    from ebuild.packages.resolver import PackageResolver

    proj_dir = tmp_path / "project"
    proj_recipes = proj_dir / "recipes"
    proj_recipes.mkdir(parents=True)
    (proj_recipes / "app.yaml").write_text(
        """package: app
version: "1.0.0"
url: "https://custom-project.org/app-1.0.0.tar.gz"
checksum: "sha256:0000000000000000000000000000000000000000000000000000000000000000"
build: cmake
dependencies:
  - mbedtls
""",
        encoding="utf-8",
    )
    (proj_recipes / "mbedtls.yaml").write_text(
        """package: mbedtls
version: "3.6.0"
url: "https://custom-project.org/mbedtls-PROJECT.tar.gz"
checksum: "sha256:1111111111111111111111111111111111111111111111111111111111111111"
build: cmake
""",
        encoding="utf-8",
    )

    remote_index_dir = tmp_path / "remote_index"
    remote_recipes = remote_index_dir / "recipes"
    remote_recipes.mkdir(parents=True)
    (remote_recipes / "mbedtls.yaml").write_text(
        """package: mbedtls
version: "9.9.9"
url: "https://remote-registry.org/mbedtls-REMOTE.tar.gz"
checksum: "sha256:2222222222222222222222222222222222222222222222222222222222222222"
build: cmake
""",
        encoding="utf-8",
    )

    recipe_dirs = _find_recipe_dirs(proj_dir, remote_index_dir=remote_index_dir)
    registry = create_registry(*recipe_dirs)
    resolver = PackageResolver(registry)

    # Resolve top-level app pinned to 1.0.0; mbedtls is resolved transitively (unpinned)
    resolved = resolver.resolve([{"name": "app", "version": "1.0.0"}])
    by_name = {r.name: r for r in resolved}

    assert "mbedtls" in by_name
    mbedtls = by_name["mbedtls"]
    # Must resolve to project recipe 3.6.0, NOT remote 9.9.9!
    assert mbedtls.version == "3.6.0"
    assert mbedtls.url == "https://custom-project.org/mbedtls-PROJECT.tar.gz"
    assert mbedtls.checksum == "sha256:1111111111111111111111111111111111111111111111111111111111111111"


def test_cli_search_command(tmp_path):
    runner = CliRunner()

    result = runner.invoke(cli, ["search", "cjson"])
    assert result.exit_code == 0
    assert "cjson" in result.output

    # JSON output
    json_result = runner.invoke(cli, ["search", "cjson", "--json"])
    assert json_result.exit_code == 0
    data = json.loads(json_result.output)
    assert isinstance(data, list)
    assert any(p["name"] == "cjson" for p in data)


def test_cli_update_index_offline():
    runner = CliRunner()
    result = runner.invoke(cli, ["update-index", "--offline"])
    assert result.exit_code == 0
    assert "Offline mode" in result.output

