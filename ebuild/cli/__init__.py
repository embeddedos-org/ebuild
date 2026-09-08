# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""ebuild.cli — Command-line interface modules."""
from importlib.metadata import version, PackageNotFoundError

try:
    # Dynamically pull the version from pyproject.toml package metadata
    __version__ = version("ebuild")
except PackageNotFoundError:
    # Fallback if the package is run directly without being installed
    __version__ = "unknown"
