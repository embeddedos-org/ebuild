# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Every recipe shipped in recipes/ must be a usable pin.

Four of the five shipped recipes could not be fetched at all:

- littlefs and lwip carried ``checksum: sha256:placeholder``. That parses, so
  nothing rejected it, and then every fetch failed with a checksum mismatch.
- mbedtls carried ``...b1490fcd73`` where the published digest ends
  ``...b1490fcd38`` — the last two hex characters transposed.
- freertos carried a digest matching none of the release's assets.

None of that is visible by reading the file; it only shows up when someone
tries to build the package. These tests make the shape of a recipe checkable
without a network round trip, so a placeholder or a truncated digest cannot be
committed again. They deliberately do not assert the digest *values* — that
needs the network, and pinning a value here would just duplicate the recipe.
"""

import re
from pathlib import Path

import pytest
import yaml

RECIPES_DIR = Path(__file__).resolve().parents[2] / "ebuild" / "recipes"
SHA256_RE = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")

RECIPE_FILES = sorted(RECIPES_DIR.glob("*.yaml"))


def test_there_are_recipes_to_check():
    assert RECIPE_FILES, f"no recipes found under {RECIPES_DIR}"


@pytest.mark.parametrize("recipe_path", RECIPE_FILES, ids=lambda p: p.stem)
def test_recipe_pins_a_real_sha256(recipe_path):
    raw = yaml.safe_load(recipe_path.read_text(encoding="utf-8"))
    checksum = raw.get("checksum", "")

    assert checksum, f"{recipe_path.name}: no checksum, so the download is unverified"
    assert SHA256_RE.match(checksum), (
        f"{recipe_path.name}: checksum {checksum!r} is not a sha256 digest. "
        f"Expected 64 lowercase hex characters, optionally prefixed 'sha256:'."
    )


@pytest.mark.parametrize("recipe_path", RECIPE_FILES, ids=lambda p: p.stem)
def test_recipe_url_is_https(recipe_path):
    raw = yaml.safe_load(recipe_path.read_text(encoding="utf-8"))
    url = raw.get("url", "")

    assert url, f"{recipe_path.name}: no url"
    assert url.startswith("https://"), (
        f"{recipe_path.name}: {url!r} is not https. A pin is worth much less "
        f"over a transport anyone on the path can rewrite."
    )


@pytest.mark.parametrize("recipe_path", RECIPE_FILES, ids=lambda p: p.stem)
def test_recipe_loads_through_the_real_loader(recipe_path):
    """The loader validates too; make sure the shipped files pass it."""
    from ebuild.packages.recipe import load_recipe

    recipe = load_recipe(recipe_path)
    assert recipe.name
    assert recipe.version
