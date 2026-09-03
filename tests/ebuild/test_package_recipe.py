# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Tests for ebuild.packages.recipe."""

import pytest

from ebuild.packages.recipe import RecipeError, load_recipe_from_string


BASE_RECIPE = """
package: demo
version: 1.0.0
url: https://example.com/demo.tar.gz
checksum: sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
"""


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