# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Content hashing shared across ebuild packages.

Kept as a stdlib-only leaf module so ``cli``, ``packages`` and
``validation`` can share one file digest without importing each other.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK_SIZE = 1 << 20


def sha256_file(path: Path) -> str:
    """Return the hex SHA-256 of a file's contents, read in 1 MiB chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()
