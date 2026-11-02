# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Tests for `ebuild receipts validate` (issue #156, first slice).

The fixture is a SYNTHETIC bundle: no eCAD product has a genuine
all-PASS V0..V4 receipt yet (the migrated corpus is UNVERIFIED), so
these tests build a self-consistent receipt + bundle, prove the
verifier authorizes exactly that, and prove it denies tampering,
stale pins and receipts that merely claim PASS. Generation does not
consult the verifier yet — see ebuild/validation/receipts.py.
"""

import hashlib
import json

import pytest
from click.testing import CliRunner

from ebuild.cli.commands import cli
from ebuild.validation.receipts import GATES, ReceiptPin, validate_receipts

COMMIT = "a" * 40
CONTRACT_VERSION = "0.1.0"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _bundle_digest(entries):
    digest = hashlib.sha256()
    for rel, hex_digest in sorted(entries):
        digest.update(f"{rel}\0{hex_digest}\n".encode("utf-8"))
    return digest.hexdigest()


@pytest.fixture
def bundle(tmp_path):
    """A self-consistent receipt + bundle that must authorize."""
    bundle_dir = tmp_path / "bundle"
    (bundle_dir / "cad").mkdir(parents=True)
    files = {
        "cad/board.kicad_pcb": b"board-bytes",
        "report.json": b"{}",
    }
    for rel, data in files.items():
        (bundle_dir / rel).write_bytes(data)
    entries = [(rel, _sha(data)) for rel, data in files.items()]
    receipt = {
        "product_id": "eos-test-product",
        "ecad_commit": COMMIT,
        "contract_version": CONTRACT_VERSION,
        "schema_digest": _sha(b"schema-bytes"),
        "bundle_digest": _bundle_digest(entries),
        "files": [{"path": rel, "sha256": h} for rel, h in entries],
        "gates": [
            {"gate": g, "status": "PASS", "checks": [{"id": f"{g}-1", "status": "PASS"}]}
            for g in GATES
        ],
        "result": "PASS",
    }
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    pin = ReceiptPin(
        ecad_commit=COMMIT,
        contract_version=CONTRACT_VERSION,
        schema_digest=receipt["schema_digest"],
        bundle_digest=receipt["bundle_digest"],
    )
    return tmp_path, bundle_dir, receipt_path, receipt, pin


def test_valid_receipt_authorizes(bundle):
    _, bundle_dir, receipt_path, _, pin = bundle
    verdict = validate_receipts(receipt_path, bundle_dir, pin)
    assert verdict.authorized, verdict.reasons
    assert verdict.product_id == "eos-test-product"
    assert verdict.gate_statuses == {g: "PASS" for g in GATES}


def test_tampered_bundle_file_is_denied(bundle):
    _, bundle_dir, receipt_path, _, pin = bundle
    (bundle_dir / "cad" / "board.kicad_pcb").write_bytes(b"tampered")
    verdict = validate_receipts(receipt_path, bundle_dir, pin)
    assert not verdict.authorized
    assert any("digest mismatch" in r for r in verdict.reasons)


def test_stale_pin_is_denied(bundle):
    _, bundle_dir, receipt_path, _, pin = bundle
    stale = ReceiptPin("b" * 40, pin.contract_version, pin.schema_digest, pin.bundle_digest)
    verdict = validate_receipts(receipt_path, bundle_dir, stale)
    assert not verdict.authorized
    assert any("does not match the pin" in r for r in verdict.reasons)


def test_moving_ref_pin_is_denied(bundle):
    _, bundle_dir, receipt_path, _, pin = bundle
    moving = ReceiptPin("master", pin.contract_version, pin.schema_digest, pin.bundle_digest)
    verdict = validate_receipts(receipt_path, bundle_dir, moving)
    assert not verdict.authorized
    assert any("moving refs" in r for r in verdict.reasons)


def test_gate_claiming_pass_with_failing_check_is_denied(bundle):
    tmp_path, bundle_dir, receipt_path, receipt, pin = bundle
    receipt["gates"][2]["checks"][0]["status"] = "FAIL"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    verdict = validate_receipts(receipt_path, bundle_dir, pin)
    assert not verdict.authorized
    assert any("recompute" in r for r in verdict.reasons)


@pytest.mark.parametrize("status", ["WARNING", "NOT_RUN", "BLOCKED", "INCONCLUSIVE"])
def test_non_pass_gate_status_is_denied(bundle, status):
    tmp_path, bundle_dir, receipt_path, receipt, pin = bundle
    receipt["gates"][1]["status"] = status
    receipt["gates"][1]["checks"][0]["status"] = status
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    verdict = validate_receipts(receipt_path, bundle_dir, pin)
    assert not verdict.authorized


def test_missing_gate_is_denied(bundle):
    tmp_path, bundle_dir, receipt_path, receipt, pin = bundle
    receipt["gates"] = receipt["gates"][:4]
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    verdict = validate_receipts(receipt_path, bundle_dir, pin)
    assert not verdict.authorized
    assert any("V4" in r and "missing" in r for r in verdict.reasons)


def test_missing_receipt_file_is_denied(bundle, tmp_path):
    _, bundle_dir, _, _, pin = bundle
    verdict = validate_receipts(tmp_path / "nope.json", bundle_dir, pin)
    assert not verdict.authorized


class TestReceiptsCli:
    def _args(self, bundle_dir, receipt_path, pin):
        return [
            "receipts",
            "validate",
            "--receipt",
            str(receipt_path),
            "--bundle-dir",
            str(bundle_dir),
            "--pin-commit",
            pin.ecad_commit,
            "--pin-contract-version",
            pin.contract_version,
            "--pin-schema-digest",
            pin.schema_digest,
            "--pin-bundle-digest",
            pin.bundle_digest,
        ]

    def test_cli_authorizes_valid_receipt(self, bundle):
        _, bundle_dir, receipt_path, _, pin = bundle
        result = CliRunner().invoke(cli, self._args(bundle_dir, receipt_path, pin))
        assert result.exit_code == 0, result.output
        assert "AUTHORIZED eos-test-product" in result.output

    def test_cli_denies_tampered_bundle(self, bundle):
        _, bundle_dir, receipt_path, _, pin = bundle
        (bundle_dir / "report.json").write_bytes(b'{"tampered": true}')
        result = CliRunner().invoke(cli, self._args(bundle_dir, receipt_path, pin))
        assert result.exit_code == 1
