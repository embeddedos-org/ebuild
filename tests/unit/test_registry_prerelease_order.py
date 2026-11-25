# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Pre-release tags with a numeric tail must order numerically.

version_sort_key compared a pre-release component such as ``rc10`` as plain
text, so ``3.6.0-rc10`` sorted below ``3.6.0-rc2`` and ``beta10`` below
``beta2``. With only pre-releases published, ``PackageRegistry.get(name)``
then selected rc2 as the latest instead of rc10.
"""

import pytest

from ebuild.packages.recipe import PackageRecipe
from ebuild.packages.registry import PackageRegistry, version_sort_key


def _recipe(version: str) -> PackageRecipe:
    return PackageRecipe(
        name="demo",
        version=version,
        url="https://example.com/demo.tar.gz",
        checksum="sha256:" + "a" * 64,
    )


@pytest.mark.parametrize("lower, higher", [
    ("3.6.0-rc2", "3.6.0-rc10"),
    ("3.6.0-beta9", "3.6.0-beta10"),
    ("3.6.0-beta10", "3.6.0-rc1"),      # tag name still ranks first
    ("3.6.0-rc10", "3.6.0"),            # any pre-release below the release
    ("3.6.0-rc", "3.6.0-rc1"),
])
def test_prerelease_ordering(lower, higher):
    assert version_sort_key(lower) < version_sort_key(higher)


def test_latest_prerelease_is_selected():
    registry = PackageRegistry()
    for version in ("3.6.0-rc2", "3.6.0-rc10", "3.6.0-rc9"):
        registry._register(_recipe(version))

    assert registry.get("demo").version == "3.6.0-rc10"
    assert [r.version for r in registry.list_all_versions("demo")] == [
        "3.6.0-rc2", "3.6.0-rc9", "3.6.0-rc10",
    ]
