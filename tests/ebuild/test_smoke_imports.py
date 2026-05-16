"""Smoke tests: import every public ebuild module.

This catches AttributeErrors, circular-import bugs, and refactor breakages
before they reach production. Each import is independently tested so a
single broken module does not mask the others.
"""
import importlib
import pkgutil

import pytest


PACKAGE = "ebuild"


def _all_submodules(package_name: str):
    pkg = importlib.import_module(package_name)
    for m in pkgutil.walk_packages(pkg.__path__, prefix=f"{package_name}."):
        # Skip private + test packages
        if "._" in m.name or ".tests" in m.name:
            continue
        yield m.name


@pytest.mark.parametrize("modname", list(_all_submodules(PACKAGE)))
def test_import(modname):
    """Every public ebuild module must import cleanly."""
    importlib.import_module(modname)
