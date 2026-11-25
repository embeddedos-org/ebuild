# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""A damaged ``index-meta.json`` must not crash ``ebuild update-index``.

``IndexSyncManager.sync`` already treats an unreadable or unparseable
metadata file as absent. Metadata that parses but has the wrong shape --
a JSON value that is not an object, or a ``synced_at`` that is not a
number -- escaped that handling: ``cached_meta.get`` raised AttributeError
and ``float(synced_at)`` raised ValueError/TypeError, so the sync aborted
with a traceback instead of re-downloading the index and rewriting the
metadata.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from ebuild.packages.index_sync import IndexSyncManager

URL = "https://a.example/index.json"
INDEX = [{"name": "zlib", "version": "1.3.1", "url": "https://example.com/zlib.tar.gz"}]


@pytest.mark.parametrize(
    "meta_text",
    [
        "[]",
        "null",
        '"oops"',
        json.dumps({"url": URL, "synced_at": "yesterday"}),
        json.dumps({"url": URL, "synced_at": [1]}),
    ],
    ids=["list", "null", "string", "synced_at-text", "synced_at-list"],
)
def test_sync_refetches_when_meta_has_wrong_shape(tmp_path, meta_text):
    mgr = IndexSyncManager(index_dir=tmp_path)
    mgr.ensure_directories()
    mgr.packages_json.write_text(json.dumps(INDEX), encoding="utf-8")
    mgr.meta_json.write_text(meta_text, encoding="utf-8")

    with patch("urllib.request.urlopen") as mock_url:
        resp = MagicMock()
        resp.read.return_value = json.dumps(INDEX).encode("utf-8")
        resp.headers = {}
        resp.__enter__.return_value = resp
        mock_url.return_value = resp

        result = mgr.sync(url=URL)

    assert mock_url.called
    assert result.is_fallback is False
    assert result.package_count == 1
    meta = json.loads(mgr.meta_json.read_text(encoding="utf-8"))
    assert meta["url"] == URL
    assert isinstance(meta["synced_at"], float)
