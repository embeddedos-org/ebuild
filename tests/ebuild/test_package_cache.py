# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Tests for ebuild.packages.cache.PackageCache."""

import shutil

from ebuild.packages.cache import PackageCache
from ebuild.packages.recipe import PackageRecipe


def make_recipe():
    return PackageRecipe(
        name="demo",
        version="1.0.0",
        url="https://example.com/demo.tar.gz",
        checksum="sha256:" + "a" * 64,
    )


def test_is_built_is_false_when_install_dir_is_missing(tmp_path):
    """Regression: a valid .built marker is not enough if install/ is gone.

    Callers treat is_built() as "the cached install prefix is usable".
    A leftover marker after a deleted install directory must not skip rebuild.
    """
    cache = PackageCache(tmp_path / "packages")
    recipe = make_recipe()
    cache.ensure_dirs(recipe)
    cache.mark_built(recipe)

    assert cache.is_built(recipe) is True

    shutil.rmtree(cache.install_dir(recipe))

    assert cache.is_built(recipe) is False


def test_the_same_digest_in_another_case_does_not_force_a_rebuild(tmp_path):
    """A digest is a number, not a string.

    Regression (review of #199): a `.built` marker recorded against a
    lower-case digest, with the recipe later edited to the same digest in
    upper case, read as "not built" and rebuilt a package whose install
    tree was already valid.
    """
    cache = PackageCache(tmp_path / "packages")
    recipe = make_recipe()
    cache.ensure_dirs(recipe)
    cache.mark_built(recipe)
    assert cache.is_built(recipe) is True

    # Hand-write the marker in upper case, as one written before digests
    # were canonicalised would be.
    import json

    marker = cache._marker_path(recipe)
    data = json.loads(marker.read_text(encoding="utf-8"))
    data["checksum"] = data["checksum"].upper()
    marker.write_text(json.dumps(data), encoding="utf-8")

    assert cache.is_built(recipe) is True

    # The control: a genuinely different digest still forces a rebuild.
    data["checksum"] = "sha256:" + "b" * 64
    marker.write_text(json.dumps(data), encoding="utf-8")
    assert cache.is_built(recipe) is False


def test_a_recipe_canonicalises_its_checksum(tmp_path):
    """The one place the digest's case is decided."""
    upper = PackageRecipe(
        name="demo",
        version="1.0.0",
        url="https://example.com/demo.tar.gz",
        checksum="SHA256:" + "A" * 64,
    )
    assert upper.checksum == "sha256:" + "a" * 64
    upper.validate()
