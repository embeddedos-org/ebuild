# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Tests for ebuild.packages.recipe."""

import pytest
import yaml

from ebuild.packages.recipe import (
    PackageRecipe,
    RecipeError,
    _parse_recipe,
    load_recipe_from_string,
    parse_recipe,
)


BASE_RECIPE = """
package: demo
version: 1.0.0
url: https://example.com/demo.tar.gz
checksum: sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
"""


def test_parse_recipe_public_name_preserves_legacy_alias():
    """The public parser keeps the legacy private alias."""
    assert _parse_recipe is parse_recipe


@pytest.mark.parametrize(
    "field_name",
    [
        "dependencies",
        "patches",
        "configure_args",
        "build_args",
        "install_args",
    ],
)
def test_recipe_list_fields_must_be_lists(field_name):
    """List-valued recipe fields must reject scalar YAML values."""
    content = BASE_RECIPE + f"""
{field_name}: "not-a-list"
"""

    with pytest.raises(RecipeError, match=field_name):
        load_recipe_from_string(content)


@pytest.mark.parametrize(
    "field_name",
    [
        "dependencies",
        "patches",
        "configure_args",
        "build_args",
        "install_args",
    ],
)
def test_recipe_list_fields_must_contain_only_strings(field_name):
    """List-valued recipe fields must reject non-string items."""
    content = BASE_RECIPE + f"""
{field_name}:
  - valid-value
  - 123
"""

    with pytest.raises(RecipeError, match=field_name):
        load_recipe_from_string(content)


def test_recipe_accepts_valid_list_fields():
    """Valid lists of strings should continue to load normally."""
    recipe = load_recipe_from_string(
        BASE_RECIPE
        + """
dependencies:
  - zlib
patches:
  - fix-build.patch
configure_args:
  - -DENABLE_FEATURE=ON
build_args:
  - VERBOSE=1
install_args:
  - DESTDIR=/tmp/install
"""
    )

    assert recipe.dependencies == ["zlib"]
    assert recipe.patches == ["fix-build.patch"]
    assert recipe.configure_args == ["-DENABLE_FEATURE=ON"]
    assert recipe.build_args == ["VERBOSE=1"]
    assert recipe.install_args == ["DESTDIR=/tmp/install"]


def test_depends_alias_accepts_a_list():
    """The legacy 'depends' alias should remain supported."""
    recipe = load_recipe_from_string(
        BASE_RECIPE
        + """
depends:
  - zlib
  - openssl
"""
    )

    assert recipe.dependencies == ["zlib", "openssl"]


def test_depends_alias_must_be_a_list():
    """The legacy 'depends' alias must follow the same list validation."""
    content = BASE_RECIPE + """
depends: zlib
"""

    with pytest.raises(RecipeError, match="dependencies"):
        load_recipe_from_string(content)


def _fully_populated_recipe() -> PackageRecipe:
    """A recipe with every field set, so a round trip has to carry them all."""
    return PackageRecipe(
        name="demo",
        version="1.2.3",
        url="https://example.com/demo-1.2.3.tar.gz",
        checksum="sha256:" + "ab" * 32,
        build_system="autoconf",
        dependencies=["zlib", "openssl"],
        patches=["fix-build.patch"],
        configure_args=["--enable-static"],
        build_args=["VERBOSE=1"],
        install_args=["DESTDIR=/tmp/stage"],
        description="A demo package",
        license="MIT",
    )


def test_to_dict_round_trips_every_field():
    """Dumping to YAML and parsing it back must reproduce the recipe exactly.

    to_dict() predates install_args and never emitted it, so a recipe cached
    by index_sync came back with install_args == [] while every other field
    survived. A field-for-field comparison catches the next one too.
    """
    recipe = _fully_populated_recipe()

    reloaded = parse_recipe(yaml.safe_load(yaml.safe_dump(recipe.to_dict())))

    assert reloaded == recipe
    assert reloaded.install_args == ["DESTDIR=/tmp/stage"]

    # Key order is not a correctness property -- parse_recipe() reads every
    # key by name, as recipe.py says -- but it is a stability property: the
    # cached recipe YAML that index_sync writes is diffed by humans, and this
    # keeps install_args next to build_args, where index_sync's recipe_dict
    # puts it. If this fails after a deliberate reordering, update both
    # emitters together and then this line; it is not a bug in to_dict().
    keys = list(recipe.to_dict())
    assert keys.index("install_args") == keys.index("build_args") + 1


def test_to_dict_returns_copies_not_live_lists():
    """Mutating a list from to_dict() must not reach into the recipe."""
    recipe = _fully_populated_recipe()

    data = recipe.to_dict()
    for field_name in (
        "dependencies",
        "patches",
        "configure_args",
        "build_args",
        "install_args",
    ):
        data[field_name].append("injected")

    assert recipe.dependencies == ["zlib", "openssl"]
    assert recipe.patches == ["fix-build.patch"]
    assert recipe.configure_args == ["--enable-static"]
    assert recipe.build_args == ["VERBOSE=1"]
    assert recipe.install_args == ["DESTDIR=/tmp/stage"]
