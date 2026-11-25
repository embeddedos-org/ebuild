# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Tests for the shared digest helpers.

``sha256_file`` replaced three private copies (model registry, receipt
verifier, package fetcher) and ``canonical_json_sha256`` replaced three
inline canonical-JSON digests in the eCAD contract and verifier. Pinned
digests and receipts depend on these bytes staying exactly the same.
"""

import hashlib
import math

import pytest

from ebuild.eos_ai.hardware_contract import canonical_json_sha256
from ebuild.hashing import sha256_file


class TestSha256File:
    def test_matches_hashlib_across_chunk_boundaries(self, tmp_path):
        # 2.5 MiB spans two full 1 MiB chunks and a partial third.
        data = bytes(range(256)) * (10 * 1024)
        path = tmp_path / "blob.bin"
        path.write_bytes(data)
        assert sha256_file(path) == hashlib.sha256(data).hexdigest()

    def test_empty_file(self, tmp_path):
        path = tmp_path / "empty"
        path.write_bytes(b"")
        assert sha256_file(path) == hashlib.sha256(b"").hexdigest()

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            sha256_file(tmp_path / "absent")


class TestCanonicalJsonSha256:
    def test_compact_sorted_serialization(self):
        value = [{"sha256": "ab", "path": "a.json"}]
        expected = hashlib.sha256(b'[{"path":"a.json","sha256":"ab"}]').hexdigest()
        assert canonical_json_sha256(value) == expected

    def test_key_order_does_not_change_digest(self):
        assert canonical_json_sha256({"a": 1, "b": 2}) == canonical_json_sha256(
            {"b": 2, "a": 1}
        )

    def test_non_ascii_is_utf8_not_escaped(self):
        expected = hashlib.sha256('{"k":"é"}'.encode("utf-8")).hexdigest()
        assert canonical_json_sha256({"k": "é"}) == expected

    def test_nan_is_rejected(self):
        with pytest.raises(ValueError):
            canonical_json_sha256({"k": math.nan})
