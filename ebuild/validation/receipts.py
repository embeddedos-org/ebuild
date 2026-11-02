# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Pinned eCAD validation-receipt verification (issue #156, first slice).

The eCAD contract (eCAD-Hardware-Products `validation/contract.md`)
emits a receipt per product claiming gate results V0..V4. This module
is the consumer-side verifier ebuild will gate generation on: given a
receipt, the bundle directory it covers, and a pin, it decides —
fail-closed — whether the receipt authorizes anything at all.

SCOPE (first slice): the verifier and its CLI exist and are tested,
but generation does NOT call them yet. As of 2026-10-14 no product in
eCAD has a genuine all-PASS V0..V4 receipt (the migrated corpus is
UNVERIFIED) and the contract is still DRAFT pre-1.0, so wiring this
into `generate` today would deny every real product. Wiring lands
when the first genuine receipt exists; see #156.

Trust model: nothing in the receipt is believed. The pin (eCAD commit,
contract version, schema digest, bundle digest) comes from the
consumer's own configuration, never from the receipt; bundle file
digests are recomputed from disk; gate results are recomputed from
the child checks, so a receipt that merely *claims* PASS is denied.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

__all__ = [
    "GATES",
    "ReceiptPin",
    "ReceiptVerdict",
    "validate_receipts",
]

#: The contract's gate ladder, in order. All five must pass.
GATES: Tuple[str, ...] = ("V0", "V1", "V2", "V3", "V4")

_PASS = "PASS"
_DENY_STATUSES = frozenset({"FAIL", "WARNING", "NOT_RUN", "BLOCKED", "INCONCLUSIVE"})

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ReceiptPin:
    """The consumer-side expectation a receipt is verified against.

    ``ecad_commit`` must be a full 40-hex commit SHA — branches, tags
    and ``latest``-style aliases are moving refs and never valid pins.
    Digests are bare lowercase hex SHA-256 (no ``sha256:`` prefix).
    """

    ecad_commit: str
    contract_version: str
    schema_digest: str
    bundle_digest: str


@dataclass(frozen=True)
class ReceiptVerdict:
    """Outcome of :func:`validate_receipts`. ``authorized`` is the
    only field a caller may act on; ``reasons`` explains every denial
    (empty when authorized)."""

    authorized: bool
    reasons: Tuple[str, ...] = ()
    product_id: Optional[str] = None
    gate_statuses: Dict[str, str] = field(default_factory=dict)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bundle_digest(entries: List[Tuple[str, str]]) -> str:
    """Canonical bundle digest over (path, sha256) pairs, path-sorted.

    The canonical form is one ``path\\0sha256\\n`` line per file, so
    the digest binds both the file set and every file's content.
    """
    digest = hashlib.sha256()
    for rel, hex_digest in sorted(entries):
        digest.update(f"{rel}\0{hex_digest}\n".encode("utf-8"))
    return digest.hexdigest()


def validate_receipts(
    receipt_path: Path,
    bundle_dir: Path,
    pin: ReceiptPin,
) -> ReceiptVerdict:
    """Verify a pinned eCAD receipt against its bundle, fail-closed.

    Returns a :class:`ReceiptVerdict`; validation failures are
    reported in ``reasons`` with ``authorized == False``, never raised.
    """
    reasons: List[str] = []

    # --- The pin itself must be a pin (no moving refs). ---
    if not _HEX40.match(pin.ecad_commit or ""):
        reasons.append(
            f"pin ecad_commit {pin.ecad_commit!r} is not a full 40-hex commit SHA "
            "(branches, tags and aliases are moving refs and cannot pin a receipt)"
        )
    for field_name in ("schema_digest", "bundle_digest"):
        value = getattr(pin, field_name)
        if not _HEX64.match(value or ""):
            reasons.append(f"pin {field_name} {value!r} is not a bare SHA-256 hex digest")

    # --- Load the receipt. ---
    try:
        raw = receipt_path.read_text(encoding="utf-8")
    except OSError as exc:
        return ReceiptVerdict(False, (f"receipt {receipt_path} cannot be read: {exc}",))
    try:
        receipt = json.loads(raw)
    except ValueError as exc:
        return ReceiptVerdict(False, (f"receipt {receipt_path} is not valid JSON: {exc}",))
    if not isinstance(receipt, dict):
        return ReceiptVerdict(False, ("receipt is not a JSON object",))

    product_id = receipt.get("product_id")
    if not isinstance(product_id, str) or not product_id:
        reasons.append("receipt has no product_id")

    # --- The receipt must match the pin on every pinned field. ---
    for receipt_key, pin_value in (
        ("ecad_commit", pin.ecad_commit),
        ("contract_version", pin.contract_version),
        ("schema_digest", pin.schema_digest),
        ("bundle_digest", pin.bundle_digest),
    ):
        actual = receipt.get(receipt_key)
        if actual != pin_value:
            reasons.append(
                f"receipt {receipt_key} {actual!r} does not match the pin {pin_value!r}"
            )

    # --- Bundle integrity: recompute every file digest from disk. ---
    files = receipt.get("files")
    computed_entries: List[Tuple[str, str]] = []
    if not isinstance(files, list) or not files:
        reasons.append("receipt declares no bundle files")
        files = []
    seen_paths = set()
    for entry in files:
        if not isinstance(entry, dict) or "path" not in entry or "sha256" not in entry:
            reasons.append(f"bundle file entry is malformed: {entry!r}")
            continue
        rel = entry["path"]
        if not isinstance(rel, str) or rel.startswith("/") or ".." in Path(rel).parts:
            reasons.append(f"bundle file path {rel!r} escapes the bundle directory")
            continue
        if rel in seen_paths:
            reasons.append(f"bundle file {rel!r} is declared twice")
            continue
        seen_paths.add(rel)
        target = bundle_dir / rel
        if not target.is_file():
            reasons.append(f"bundle file {rel!r} is missing from {bundle_dir}")
            continue
        actual_digest = _sha256_file(target)
        if actual_digest != entry["sha256"]:
            reasons.append(
                f"bundle file {rel!r} digest mismatch: receipt declares "
                f"{entry['sha256']}, disk hashes to {actual_digest}"
            )
            continue
        computed_entries.append((rel, actual_digest))
    if computed_entries:
        computed_bundle = _bundle_digest(computed_entries)
        if computed_bundle != pin.bundle_digest:
            reasons.append(
                f"bundle digest recomputed from disk ({computed_bundle}) does not "
                f"match the pin ({pin.bundle_digest})"
            )

    # --- Gates: recompute each aggregate from its child checks. ---
    gate_statuses: Dict[str, str] = {}
    gates = receipt.get("gates")
    if not isinstance(gates, list):
        reasons.append("receipt has no gates list")
        gates = []
    by_gate: Dict[str, Any] = {}
    for gate in gates:
        if isinstance(gate, dict) and isinstance(gate.get("gate"), str):
            by_gate[gate["gate"]] = gate
    for name in GATES:
        gate = by_gate.get(name)
        if gate is None:
            reasons.append(f"gate {name} is missing from the receipt")
            gate_statuses[name] = "NOT_RUN"
            continue
        checks = gate.get("checks")
        if not isinstance(checks, list) or not checks:
            reasons.append(f"gate {name} has no child checks to recompute from")
            gate_statuses[name] = "NOT_RUN"
            continue
        recomputed = _PASS
        for check in checks:
            status = check.get("status") if isinstance(check, dict) else None
            if status != _PASS:
                recomputed = status if status in _DENY_STATUSES else "FAIL"
                break
        declared = gate.get("status")
        if declared != recomputed:
            reasons.append(
                f"gate {name} declares {declared!r} but its child checks "
                f"recompute to {recomputed!r}"
            )
        gate_statuses[name] = recomputed
        if recomputed != _PASS:
            reasons.append(f"gate {name} recomputes to {recomputed}, not PASS")

    # --- The overall claim must agree with the recomputation. ---
    if receipt.get("result") != _PASS:
        reasons.append(f"receipt result is {receipt.get('result')!r}, not PASS")
    elif any(gate_statuses.get(name) != _PASS for name in GATES):
        reasons.append("receipt claims PASS overall but not every gate recomputes to PASS")

    return ReceiptVerdict(
        authorized=not reasons,
        reasons=tuple(reasons),
        product_id=product_id if isinstance(product_id, str) else None,
        gate_statuses=gate_statuses,
    )
