# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Synthetic contract tests for the eCAD-backed hardware generation gate."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from ebuild.eos_ai.hardware_contract import (
    BUNDLE_SCHEMA_URI,
    CONTRACT_VERSION,
    DOCUMENT_SCHEMA_URIS,
    ECAD_REPOSITORY,
    RECEIPT_SCHEMA_URI,
    SCHEMA_FILES,
    ContractPin,
    GenerationDenied,
    VerificationRequest,
    calculate_schema_set_sha256,
)
from ebuild.eos_ai.hardware_gate import HardwareGenerationGate
from ebuild.eos_ai.hardware_verifier import HardwareReceiptVerifier

SYNTHETIC_PRODUCT_ID = "synthetic:validation-fixture"
SYNTHETIC_COMMIT = "0123456789abcdef0123456789abcdef01234567"

def _write_json(path: Path, value) -> str:
    payload = (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def _artifact(path: str, digest: str = "a" * 64, size: int = 1):
    return {
        "path": path,
        "sha256": digest,
        "media_type": "application/json",
        "size_bytes": size,
    }


def _passing_receipt():
    gates = []
    for gate in ("V0", "V1", "V2", "V3", "V4"):
        gates.append(
            {
                "gate": gate,
                "verdict": "PASS",
                "checks": [
                    {
                        "check_id": f"synthetic.{gate.lower()}.required",
                        "gate": gate,
                        "domain": "data_management",
                        "layer": "validation",
                        "tool_id": "synthetic-validator",
                        "execution_status": "completed",
                        "verdict": "PASS",
                        "reason_code": "SYNTHETIC_PASS",
                        "summary": "Synthetic fixture check passed.",
                        "required": True,
                        "requirement_ids": [f"SYNTHETIC-{gate}"],
                        "metrics": {},
                        "evidence": [
                            {
                                "evidence_id": f"synthetic.{gate.lower()}.evidence",
                                "path": f"synthetic/evidence/{gate.lower()}.txt",
                                "sha256": "b" * 64,
                                "media_type": "text/plain",
                                "size_bytes": 17,
                            }
                        ],
                        "findings": [],
                    }
                ],
            }
        )
    return {
        "$schema": RECEIPT_SCHEMA_URI,
        "contract_version": CONTRACT_VERSION,
        "receipt_id": "synthetic-receipt",
        "product": {
            "id": SYNTHETIC_PRODUCT_ID,
            "path": "synthetic/validation-fixture",
        },
        "source": {
            "repository": ECAD_REPOSITORY,
            "commit": SYNTHETIC_COMMIT,
            "dirty": False,
            "input_sha256": "c" * 64,
        },
        "started_at": "2026-09-19T00:00:00Z",
        "completed_at": "2026-09-19T00:00:01Z",
        "tools": [
            {
                "tool_id": "synthetic-validator",
                "name": "Synthetic Validator",
                "version": "1.0.0-test",
                "invocation": ["synthetic-validator", "--fixture"],
                "settings": {"fixture": True},
            }
        ],
        "gates": gates,
        "overall_verdict": "PASS",
        "execution_complete": True,
        "eligible_for_ebuild": True,
    }


class SyntheticContractFixture:
    """Build a self-contained fixture that is unmistakably non-production."""

    def __init__(self, root: Path) -> None:
        self.root = root / "synthetic-ecad-contract"
        self.schema_path = self.root / "schemas" / "validation-receipt.schema.json"
        self.receipt_path = self.root / "receipt.json"
        self.bundle_path = self.root / "bundle.json"
        self.contract_path = self.root / "product-contract.json"
        self.requirements_path = self.root / "requirements.json"
        self.manifest_path = self.root / "product-manifest.json"
        self.evidence_index_path = self.root / "evidence-index.json"

        for name in SCHEMA_FILES:
            schema: dict[str, object] = {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "$id": (
                    "https://embeddedos.org/schemas/hardware-validation/v1/" + name
                ),
                "title": f"Synthetic {name} fixture",
                "type": "object",
            }
            if name == "validation-receipt.schema.json":
                receipt_keys = tuple(_passing_receipt())
                schema.update(
                    properties={key: {} for key in receipt_keys},
                    required=list(receipt_keys),
                    additionalProperties=False,
                )
            _write_json(self.schema_path.parent / name, schema)
        schema_digest = hashlib.sha256(self.schema_path.read_bytes()).hexdigest()
        schema_set_digest = calculate_schema_set_sha256(self.schema_path.parent)

        source_entries = [
            {
                "path": "synthetic/validation-fixture/design/input.txt",
                "sha256": "c" * 64,
                "size_bytes": 17,
                "media_type": "text/plain",
                "artifact_role": "design_input",
            }
        ]
        input_digest = hashlib.sha256(
            json.dumps(
                [{"path": "design/input.txt", "sha256": "c" * 64}],
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        requirements = {
            "$schema": DOCUMENT_SCHEMA_URIS["requirements"],
            "contract_version": CONTRACT_VERSION,
            "requirements": [
                {"requirement_id": f"SYNTHETIC-{gate}", "gate": gate}
                for gate in ("V0", "V1", "V2", "V3", "V4")
            ]
        }
        requirements_digest = _write_json(self.requirements_path, requirements)
        requirements_reference = _artifact(
            "requirements.json",
            requirements_digest,
            self.requirements_path.stat().st_size,
        )
        contract = {
            "$schema": DOCUMENT_SCHEMA_URIS["product_contract"],
            "contract_version": CONTRACT_VERSION,
            "product": {
                "id": SYNTHETIC_PRODUCT_ID,
                "path": "synthetic/validation-fixture",
            },
            "provenance": {
                "source_commit": SYNTHETIC_COMMIT,
                "source_path": "synthetic/validation-fixture",
            },
            "requirements": {
                "catalog": requirements_reference,
                "requirement_ids": [
                    f"SYNTHETIC-{gate}" for gate in ("V0", "V1", "V2", "V3", "V4")
                ],
            },
            "validation_scope": {"gates": ["V0", "V1", "V2", "V3", "V4"]},
        }
        _write_json(self.contract_path, contract)
        manifest = {
            "$schema": DOCUMENT_SCHEMA_URIS["product_manifest"],
            "contract_version": CONTRACT_VERSION,
            "product": {
                "id": SYNTHETIC_PRODUCT_ID,
                "path": "synthetic/validation-fixture",
            },
            "source": {
                "repository": ECAD_REPOSITORY,
                "commit": SYNTHETIC_COMMIT,
                "dirty": False,
                "input_sha256": input_digest,
            },
            "artifacts": source_entries,
        }
        _write_json(self.manifest_path, manifest)

        receipt = _passing_receipt()
        receipt["source"]["input_sha256"] = input_digest
        evidence_values = []
        for gate in receipt["gates"]:
            check = gate["checks"][0]
            evidence_id = f"synthetic.{gate['gate'].lower()}.evidence"
            evidence_path = self.root / "evidence" / f"{gate['gate'].lower()}.txt"
            evidence_path.parent.mkdir(parents=True, exist_ok=True)
            evidence_path.write_text(f"synthetic {gate['gate']} evidence\n", encoding="utf-8")
            digest = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
            reference = {
                "evidence_id": evidence_id,
                "path": evidence_path.relative_to(self.root).as_posix(),
                "sha256": digest,
                "media_type": "text/plain",
                "size_bytes": evidence_path.stat().st_size,
            }
            check["evidence"] = [reference]
            evidence_values.append(
                {
                    **reference,
                    "check_id": check["check_id"],
                    "requirement_ids": check["requirement_ids"],
                    "producer_tool_id": check["tool_id"],
                }
            )
        receipt_digest = _write_json(self.receipt_path, receipt)
        _write_json(
            self.evidence_index_path,
            {
                "$schema": DOCUMENT_SCHEMA_URIS["evidence_index"],
                "contract_version": CONTRACT_VERSION,
                "product_id": SYNTHETIC_PRODUCT_ID,
                "receipt_sha256": receipt_digest,
                "evidence": evidence_values,
            },
        )
        bundle_digest = self._write_bundle(receipt_digest)
        self.pin = ContractPin(
            repository=ECAD_REPOSITORY,
            commit=SYNTHETIC_COMMIT,
            contract_version=CONTRACT_VERSION,
            schema_uri=RECEIPT_SCHEMA_URI,
            schema_sha256=schema_digest,
            schema_set_sha256=schema_set_digest,
            bundle_sha256=bundle_digest,
            receipt_sha256=receipt_digest,
        )

    @property
    def request(self) -> VerificationRequest:
        return VerificationRequest(
            schema_path=self.schema_path,
            bundle_path=self.bundle_path,
            product_id=SYNTHETIC_PRODUCT_ID,
            pin=self.pin,
        )

    def receipt(self):
        return json.loads(self.receipt_path.read_text(encoding="utf-8"))

    def rewrite_receipt(self, receipt) -> None:
        receipt_digest = _write_json(self.receipt_path, receipt)
        evidence_index = json.loads(self.evidence_index_path.read_text(encoding="utf-8"))
        evidence_index["receipt_sha256"] = receipt_digest
        _write_json(self.evidence_index_path, evidence_index)
        bundle_digest = self._write_bundle(receipt_digest)
        self.pin = replace(
            self.pin,
            receipt_sha256=receipt_digest,
            bundle_sha256=bundle_digest,
        )

    def rewrite_document(self, name: str, document: dict) -> None:
        paths = {
            "product_contract": self.contract_path,
            "requirements": self.requirements_path,
            "product_manifest": self.manifest_path,
            "evidence_index": self.evidence_index_path,
        }
        _write_json(paths[name], document)
        bundle_digest = self._write_bundle(self.pin.receipt_sha256)
        self.pin = replace(self.pin, bundle_sha256=bundle_digest)

    def _document_reference(self, path: Path) -> dict:
        return _artifact(
            path.relative_to(self.root).as_posix(),
            digest=hashlib.sha256(path.read_bytes()).hexdigest(),
            size=path.stat().st_size,
        )

    def _write_bundle(self, receipt_digest: str) -> str:
        receipt_reference = _artifact(
            "receipt.json",
            digest=receipt_digest,
            size=self.receipt_path.stat().st_size,
        )
        bundle = {
            "$schema": BUNDLE_SCHEMA_URI,
            "contract_version": CONTRACT_VERSION,
            "bundle_id": "synthetic-validation-bundle",
            "product_id": SYNTHETIC_PRODUCT_ID,
            "created_at": "2026-09-19T00:00:02Z",
            "created_by": {
                "tool_id": "synthetic-validator",
                "name": "Synthetic Validator",
                "version": "1.0.0-test",
                "invocation": ["synthetic-validator", "--fixture"],
                "settings": {"fixture": True},
            },
            "documents": {
                "product_contract": self._document_reference(self.contract_path),
                "requirements": self._document_reference(self.requirements_path),
                "product_manifest": self._document_reference(self.manifest_path),
                "validation_receipt": receipt_reference,
                "evidence_index": self._document_reference(self.evidence_index_path),
            },
        }
        return _write_json(self.bundle_path, bundle)


@pytest.fixture
def synthetic_contract(tmp_path):
    return SyntheticContractFixture(tmp_path)


def test_pinned_synthetic_v0_v4_receipt_authorizes(synthetic_contract):
    result = HardwareReceiptVerifier().verify(synthetic_contract.request)

    assert result.authorized is True
    assert result.denials == ()
    assert result.source_commit == SYNTHETIC_COMMIT
    assert [evidence.artifact for evidence in result.digests] == [
        "schema",
        "schema_set",
        "bundle",
        "receipt",
        "bundle.product_contract",
        "bundle.requirements",
        "bundle.product_manifest",
        "bundle.evidence_index",
    ]
    assert all(evidence.matches for evidence in result.digests)
    assert [gate.gate for gate in result.gates] == ["V0", "V1", "V2", "V3", "V4"]
    assert all(gate.computed_verdict == "PASS" for gate in result.gates)


@pytest.mark.parametrize(
    "moving_ref",
    ["main", "refs/heads/main", "latest", "v1.0.0", "refs/tags/v1.0.0"],
)
def test_contract_pin_rejects_branches_tags_and_latest(synthetic_contract, moving_ref):
    with pytest.raises(ValueError, match="full 40-character"):
        replace(synthetic_contract.pin, commit=moving_ref)


@pytest.mark.parametrize("artifact", ["schema", "bundle", "receipt"])
def test_tampered_pinned_artifact_denies_authorization(synthetic_contract, artifact):
    path = getattr(synthetic_contract, f"{artifact}_path")
    path.write_bytes(path.read_bytes() + b" ")

    result = HardwareReceiptVerifier().verify(synthetic_contract.request)

    assert result.authorized is False
    assert "DIGEST_MISMATCH" in result.denial_codes
    digest = next(item for item in result.digests if item.artifact == artifact)
    assert digest.matches is False


def test_tampered_bundle_document_denies_authorization(synthetic_contract):
    synthetic_contract.contract_path.write_bytes(
        synthetic_contract.contract_path.read_bytes() + b" "
    )

    result = HardwareReceiptVerifier().verify(synthetic_contract.request)

    assert result.authorized is False
    assert "DIGEST_MISMATCH" in result.denial_codes


def test_tampered_evidence_bytes_deny_authorization(synthetic_contract):
    evidence_path = synthetic_contract.root / "evidence" / "v3.txt"
    evidence_path.write_bytes(evidence_path.read_bytes() + b"tampered")

    result = HardwareReceiptVerifier().verify(synthetic_contract.request)

    assert result.authorized is False
    assert "EVIDENCE_DIGEST_MISMATCH" in result.denial_codes


def test_intermediate_evidence_directory_symlink_denies(synthetic_contract):
    evidence_dir = synthetic_contract.bundle_path.parent / "evidence"
    moved_dir = synthetic_contract.root / "moved-evidence"
    evidence_dir.rename(moved_dir)
    evidence_dir.symlink_to(moved_dir, target_is_directory=True)

    result = HardwareReceiptVerifier().verify(synthetic_contract.request)

    assert result.authorized is False
    assert "EVIDENCE_UNREADABLE" in result.denial_codes


def test_dot_only_bundle_path_returns_denial(synthetic_contract):
    bundle = json.loads(synthetic_contract.bundle_path.read_text(encoding="utf-8"))
    bundle["documents"]["validation_receipt"]["path"] = "."
    bundle_digest = _write_json(synthetic_contract.bundle_path, bundle)
    synthetic_contract.pin = replace(
        synthetic_contract.pin, bundle_sha256=bundle_digest
    )

    result = HardwareReceiptVerifier().verify(synthetic_contract.request)

    assert result.authorized is False
    assert "UNSAFE_RECEIPT_PATH" in result.denial_codes


def test_bundle_cannot_substitute_a_different_receipt_pin(synthetic_contract):
    bundle = json.loads(synthetic_contract.bundle_path.read_text(encoding="utf-8"))
    bundle["documents"]["validation_receipt"]["sha256"] = "d" * 64
    bundle_digest = _write_json(synthetic_contract.bundle_path, bundle)
    synthetic_contract.pin = replace(synthetic_contract.pin, bundle_sha256=bundle_digest)

    result = HardwareReceiptVerifier().verify(synthetic_contract.request)

    assert result.authorized is False
    assert "RECEIPT_PIN_MISMATCH" in result.denial_codes


@pytest.mark.parametrize(
    ("verdict", "execution_status", "aggregate"),
    [
        ("FAIL", "completed", "FAIL"),
        ("WARNING", "completed", "BLOCKED"),
        ("NOT_RUN", "unavailable", "NOT_RUN"),
        ("BLOCKED", "unavailable", "BLOCKED"),
        ("INCONCLUSIVE", "timed_out", "INCONCLUSIVE"),
    ],
)
def test_every_required_non_pass_state_denies(
    synthetic_contract, verdict, execution_status, aggregate
):
    receipt = synthetic_contract.receipt()
    check = receipt["gates"][2]["checks"][0]
    check["verdict"] = verdict
    check["execution_status"] = execution_status
    receipt["gates"][2]["verdict"] = aggregate
    receipt["overall_verdict"] = aggregate
    receipt["execution_complete"] = execution_status == "completed"
    receipt["eligible_for_ebuild"] = False
    synthetic_contract.rewrite_receipt(receipt)

    result = HardwareReceiptVerifier().verify(synthetic_contract.request)

    assert result.authorized is False
    assert "REQUIRED_CHECK_NOT_PASS" in result.denial_codes
    assert next(gate for gate in result.gates if gate.gate == "V2").computed_verdict == aggregate


def test_reported_aggregates_are_not_trusted(synthetic_contract):
    receipt = synthetic_contract.receipt()
    receipt["gates"][3]["checks"][0]["verdict"] = "FAIL"
    synthetic_contract.rewrite_receipt(receipt)

    result = HardwareReceiptVerifier().verify(synthetic_contract.request)

    assert result.authorized is False
    assert "REQUIRED_CHECK_NOT_PASS" in result.denial_codes
    assert "GATE_AGGREGATE_MISMATCH" in result.denial_codes
    assert "OVERALL_AGGREGATE_MISMATCH" in result.denial_codes
    assert next(gate for gate in result.gates if gate.gate == "V3").computed_verdict == "FAIL"


def test_missing_v4_gate_denies(synthetic_contract):
    receipt = synthetic_contract.receipt()
    receipt["gates"] = receipt["gates"][:-1]
    receipt["overall_verdict"] = "BLOCKED"
    receipt["execution_complete"] = False
    receipt["eligible_for_ebuild"] = False
    synthetic_contract.rewrite_receipt(receipt)

    result = HardwareReceiptVerifier().verify(synthetic_contract.request)

    assert result.authorized is False
    assert "MISSING_GATES" in result.denial_codes
    assert [gate.gate for gate in result.gates] == ["V0", "V1", "V2", "V3"]


def test_pass_without_evidence_denies(synthetic_contract):
    receipt = synthetic_contract.receipt()
    receipt["gates"][0]["checks"][0]["evidence"] = []
    synthetic_contract.rewrite_receipt(receipt)

    result = HardwareReceiptVerifier().verify(synthetic_contract.request)

    assert result.authorized is False
    assert "MISSING_EVIDENCE" in result.denial_codes


def test_remote_schema_reference_is_rejected_before_validation(synthetic_contract):
    schema_path = synthetic_contract.schema_path.parent / "bundle.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema["allOf"] = [{"$ref": "https://untrusted.invalid/schema.json"}]
    _write_json(schema_path, schema)
    synthetic_contract.pin = replace(
        synthetic_contract.pin,
        schema_set_sha256=calculate_schema_set_sha256(
            synthetic_contract.schema_path.parent
        ),
    )

    result = HardwareReceiptVerifier().verify(synthetic_contract.request)

    assert result.authorized is False
    assert "INVALID_SCHEMA_SET" in result.denial_codes


def test_schema_invalid_unknown_receipt_field_denies(synthetic_contract):
    receipt = synthetic_contract.receipt()
    receipt["unexpected"] = True
    synthetic_contract.rewrite_receipt(receipt)

    result = HardwareReceiptVerifier().verify(synthetic_contract.request)

    assert result.authorized is False
    assert "SCHEMA_VALIDATION_FAILED" in result.denial_codes


def test_dirty_release_source_denies(synthetic_contract):
    receipt = synthetic_contract.receipt()
    receipt["source"]["dirty"] = True
    synthetic_contract.rewrite_receipt(receipt)

    result = HardwareReceiptVerifier().verify(synthetic_contract.request)

    assert result.authorized is False
    assert "DIRTY_SOURCE" in result.denial_codes


def test_execution_complete_is_recomputed_from_all_child_checks(synthetic_contract):
    receipt = synthetic_contract.receipt()
    optional = dict(receipt["gates"][1]["checks"][0])
    optional.update(
        {
            "check_id": "synthetic.v1.optional-unavailable",
            "execution_status": "unavailable",
            "verdict": "WARNING",
            "reason_code": "SYNTHETIC_UNAVAILABLE",
            "required": False,
            "evidence": [],
        }
    )
    receipt["gates"][1]["checks"].append(optional)
    receipt["execution_complete"] = True
    synthetic_contract.rewrite_receipt(receipt)

    result = HardwareReceiptVerifier().verify(synthetic_contract.request)

    assert result.authorized is False
    assert "EXECUTION_AGGREGATE_MISMATCH" in result.denial_codes
    assert "EXECUTION_INCOMPLETE" in result.denial_codes


def test_repository_artifact_provenance_must_match_pin(synthetic_contract):
    manifest = json.loads(synthetic_contract.manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"][0]["provenance"] = {
        "source_type": "repository",
        "source_path": manifest["artifacts"][0]["path"],
        "source_commit": "f" * 40,
        "recorded_at": "2026-09-19T00:00:00Z",
    }
    synthetic_contract.rewrite_document("product_manifest", manifest)

    result = HardwareReceiptVerifier().verify(synthetic_contract.request)

    assert result.authorized is False
    assert "PROVENANCE_MISMATCH" in result.denial_codes


def test_cross_document_product_path_mismatch_denies(synthetic_contract):
    manifest = json.loads(
        synthetic_contract.manifest_path.read_text(encoding="utf-8")
    )
    manifest["product"]["path"] = "synthetic/different-product"
    synthetic_contract.rewrite_document("product_manifest", manifest)

    result = HardwareReceiptVerifier().verify(synthetic_contract.request)

    assert result.authorized is False
    assert "CROSS_DOCUMENT_PRODUCT_MISMATCH" in result.denial_codes


def test_unknown_requirement_denies_even_when_receipt_is_rehashed(synthetic_contract):
    receipt = synthetic_contract.receipt()
    receipt["gates"][2]["checks"][0]["requirement_ids"] = ["UNKNOWN:REQ"]
    synthetic_contract.rewrite_receipt(receipt)

    result = HardwareReceiptVerifier().verify(synthetic_contract.request)

    assert result.authorized is False
    assert "UNKNOWN_REQUIREMENT" in result.denial_codes


def test_requirement_must_be_checked_at_its_declared_gate(synthetic_contract):
    receipt = synthetic_contract.receipt()
    receipt["gates"][3]["checks"][0]["requirement_ids"] = ["SYNTHETIC-V4"]
    receipt["gates"][4]["checks"][0]["requirement_ids"] = ["SYNTHETIC-V3"]
    synthetic_contract.rewrite_receipt(receipt)
    evidence_index = json.loads(
        synthetic_contract.evidence_index_path.read_text(encoding="utf-8")
    )
    for item in evidence_index["evidence"]:
        if item["check_id"] == "v3.synthetic":
            item["requirement_ids"] = ["SYNTHETIC-V4"]
        elif item["check_id"] == "v4.synthetic":
            item["requirement_ids"] = ["SYNTHETIC-V3"]
    synthetic_contract.rewrite_document("evidence_index", evidence_index)

    result = HardwareReceiptVerifier().verify(synthetic_contract.request)

    assert result.authorized is False
    assert "REQUIREMENT_GATE_MISMATCH" in result.denial_codes


def test_product_requirement_without_required_check_coverage_denies(synthetic_contract):
    receipt = synthetic_contract.receipt()
    receipt["gates"][4]["checks"][0]["requirement_ids"] = ["SYNTHETIC-V3"]
    synthetic_contract.rewrite_receipt(receipt)

    result = HardwareReceiptVerifier().verify(synthetic_contract.request)

    assert result.authorized is False
    assert "REQUIREMENT_COVERAGE_INCOMPLETE" in result.denial_codes


def test_optional_warning_does_not_replace_required_pass(synthetic_contract):
    receipt = synthetic_contract.receipt()
    optional = dict(receipt["gates"][1]["checks"][0])
    optional.update(
        {
            "check_id": "synthetic.v1.optional-warning",
            "verdict": "WARNING",
            "reason_code": "SYNTHETIC_WARNING",
            "required": False,
            "evidence": [],
        }
    )
    receipt["gates"][1]["checks"].append(optional)
    synthetic_contract.rewrite_receipt(receipt)

    result = HardwareReceiptVerifier().verify(synthetic_contract.request)

    assert result.authorized is True
    assert result.denials == ()


def test_denial_does_not_invoke_generation_or_touch_existing_output(
    synthetic_contract, tmp_path
):
    receipt = synthetic_contract.receipt()
    receipt["source"]["dirty"] = True
    synthetic_contract.rewrite_receipt(receipt)
    output = tmp_path / "existing-output.txt"
    output.write_text("preserve me", encoding="utf-8")
    invoked = []

    def generate(_authorization):
        invoked.append(True)
        output.write_text("changed", encoding="utf-8")

    with pytest.raises(GenerationDenied) as raised:
        HardwareGenerationGate().authorize_and_generate(
            synthetic_contract.request, generate
        )

    assert raised.value.result.authorized is False
    assert "DIRTY_SOURCE" in raised.value.result.denial_codes
    assert invoked == []
    assert output.read_text(encoding="utf-8") == "preserve me"


def test_generation_callback_receives_verified_authorization(synthetic_contract):
    seen = []

    def generate(authorization):
        seen.append(authorization)
        return f"generated:{authorization.product_id}"

    output = HardwareGenerationGate().authorize_and_generate(
        synthetic_contract.request, generate
    )

    assert output == f"generated:{SYNTHETIC_PRODUCT_ID}"
    assert len(seen) == 1
    assert seen[0].authorized is True
