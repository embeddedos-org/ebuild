# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""ebuild - EoS Build System & SDK Generator."""
from importlib.metadata import version, PackageNotFoundError

try:
    # Dynamically pull the version from pyproject.toml package metadata
    # Distribution name, not import name: see [project].name in pyproject.toml.
    __version__ = version("embeddedos-ebuild")
except PackageNotFoundError:
    # Fallback if the package is run directly without being installed
    __version__ = "unknown"
