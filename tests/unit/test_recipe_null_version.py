# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""A recipe whose ``version`` is YAML null has no version.

``parse_recipe`` used ``str(raw.get("version", ""))``, which turns an
explicit null into the four-character string ``"None"``. That string is
truthy, so ``PackageRecipe.validate()`` accepted the recipe as version
"None" instead of rejecting it for having no version.
"""

from __future__ import annotations

import pytest

from ebuild.packages.recipe import RecipeError, load_recipe_from_string, parse_recipe

_SHA = "0" * 64


def test_blank_version_in_recipe_yaml_is_rejected() -> None:
    content = (
        "package: zlib\n"
        "version:\n"
        "url: https://example.com/zlib.tar.gz\n"
        f"checksum: sha256:{_SHA}\n"
    )
    with pytest.raises(RecipeError, match="must have a 'version' field"):
        load_recipe_from_string(content)


def test_null_version_in_raw_mapping_is_rejected() -> None:
    raw = {
        "package": "zlib",
        "version": None,
        "url": "https://example.com/zlib.tar.gz",
    }
    with pytest.raises(RecipeError, match="must have a 'version' field"):
        parse_recipe(raw)


def test_numeric_version_is_still_stringified() -> None:
    recipe = parse_recipe(
        {"package": "zlib", "version": 2, "url": "https://example.com/z.tgz"}
    )
    assert recipe.version == "2"
