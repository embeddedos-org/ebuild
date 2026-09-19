# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Fail-closed verification for pinned eCAD validation receipts."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from jsonschema import Draft7Validator, FormatChecker, RefResolver

from ebuild.eos_ai.hardware_contract import (
    BUNDLE_SCHEMA_URI,
    DOCUMENT_SCHEMA_URIS,
    ECAD_REPOSITORY,
    REQUIRED_GATES,
    RECEIPT_SCHEMA_URI,
    SCHEMA_FILES,
    ContractPin,
    DenialEvidence,
    DigestEvidence,
    ExecutionStatus,
    GateEvidence,
    Verdict,
    VerificationRequest,
    VerificationResult,
)

_DENYING_VERDICTS = {
    Verdict.FAIL.value,
    Verdict.WARNING.value,
    Verdict.NOT_RUN.value,
    Verdict.BLOCKED.value,
    Verdict.INCONCLUSIVE.value,
}
_KNOWN_VERDICTS = {verdict.value for verdict in Verdict}
_KNOWN_EXECUTION_STATUSES = {status.value for status in ExecutionStatus}
_DIGEST_RE = frozenset("0123456789abcdef")


class HardwareReceiptVerifier:
    """Verify a pinned eCAD bundle and recompute authorization from child checks."""

    def verify(self, request: VerificationRequest) -> VerificationResult:
        """Verify pinned artifacts and return structured allow-or-deny evidence.

        Args:
            request: Paths, selected product, and immutable upstream pins.

        Returns:
            A result whose ``authorized`` property is true only when every pin and
            every required V0-V4 check passes.

        Example:
            ``HardwareReceiptVerifier().verify(request).authorized``
        """
        denials: List[DenialEvidence] = []
        digests: List[DigestEvidence] = []

        schema_digest, schema_set_digest, schemas = self._read_pinned_schema_set(
            request.schema_path.parent,
            request.pin.schema_sha256,
            request.pin.schema_set_sha256,
            denials,
        )
        digests.extend((schema_digest, schema_set_digest))
        bundle_digest, bundle, _bundle_size = self._read_pinned_object(
            "bundle", request.bundle_path, request.pin.bundle_sha256, denials
        )
        digests.append(bundle_digest)
        if (
            not schema_digest.matches
            or not schema_set_digest.matches
            or not bundle_digest.matches
            or schemas is None
            or bundle is None
        ):
            return self._result(request.product_id, None, digests, (), denials)

        schema = schemas["validation-receipt.schema.json"]

        self._validate_schema(schema, request.pin, denials)
        if not self._validate_instance(
            schemas,
            "bundle.schema.json",
            bundle,
            "bundle",
            denials,
        ):
            return self._result(request.product_id, None, digests, (), denials)
        receipt_relative = self._validate_bundle(bundle, request, denials)
        if receipt_relative is None:
            return self._result(request.product_id, None, digests, (), denials)

        receipt_digest, receipt, receipt_size = self._read_pinned_relative_object(
            "receipt",
            request.bundle_path.parent,
            receipt_relative,
            request.pin.receipt_sha256,
            denials,
        )
        digests.append(receipt_digest)
        self._validate_receipt_reference(
            bundle,
            receipt_digest,
            receipt_size,
            denials,
        )
        if not receipt_digest.matches or receipt is None:
            return self._result(request.product_id, None, digests, (), denials)

        if not self._validate_instance(
            schemas,
            "validation-receipt.schema.json",
            receipt,
            "receipt",
            denials,
        ):
            return self._result(request.product_id, None, digests, (), denials)
        documents = self._load_supporting_documents(
            bundle,
            request.bundle_path.parent,
            digests,
            denials,
        )
        source_commit, gates = self._validate_receipt(receipt, request, denials)
        if documents is not None:
            documents_schema_valid = True
            for name, document in documents.items():
                documents_schema_valid = self._validate_instance(
                    schemas,
                    {
                        "product_contract": "product-contract.schema.json",
                        "requirements": "requirements.schema.json",
                        "product_manifest": "product-manifest.schema.json",
                        "evidence_index": "evidence-index.schema.json",
                    }[name],
                    document,
                    name,
                    denials,
                ) and documents_schema_valid
            if not documents_schema_valid:
                return self._result(
                    request.product_id,
                    source_commit,
                    digests,
                    gates,
                    denials,
                )
            self._validate_cross_documents(
                bundle,
                receipt,
                receipt_digest,
                documents,
                request,
                denials,
            )
        return self._result(request.product_id, source_commit, digests, gates, denials)

    @staticmethod
    def _result(
        product_id: str,
        source_commit: Optional[str],
        digests: Sequence[DigestEvidence],
        gates: Sequence[GateEvidence],
        denials: Sequence[DenialEvidence],
    ) -> VerificationResult:
        return VerificationResult(
            product_id=product_id,
            source_commit=source_commit,
            digests=tuple(digests),
            gates=tuple(gates),
            denials=tuple(denials),
        )

    @staticmethod
    def _deny(
        denials: List[DenialEvidence], code: str, location: str, message: str
    ) -> None:
        denials.append(DenialEvidence(code=code, location=location, message=message))

    def _read_pinned_schema_set(
        self,
        directory: Path,
        expected_receipt: str,
        expected_set: str,
        denials: List[DenialEvidence],
    ) -> Tuple[DigestEvidence, DigestEvidence, Optional[Dict[str, Dict[str, Any]]]]:
        schemas: Dict[str, Dict[str, Any]] = {}
        entries = []
        receipt_actual: Optional[str] = None
        try:
            for name in SCHEMA_FILES:
                path = directory / name
                if path.is_symlink() or not path.is_file():
                    raise OSError(f"schema is missing or is a symbolic link: {name}")
                payload = _read_file_snapshot(path)
                digest = hashlib.sha256(payload).hexdigest()
                entries.append({"path": name, "sha256": digest})
                if name == "validation-receipt.schema.json":
                    receipt_actual = digest
                value = json.loads(payload.decode("utf-8"))
                if not isinstance(value, dict):
                    raise ValueError(f"{name} must contain a JSON object")
                expected_id = (
                    "https://embeddedos.org/schemas/hardware-validation/v1/" + name
                )
                if value.get("$id") != expected_id:
                    raise ValueError(f"{name} has unexpected $id")
                Draft7Validator.check_schema(value)
                schemas[name] = value
            allowed_schema_ids = {schema["$id"] for schema in schemas.values()}
            for schema_name, schema in schemas.items():
                for reference in _schema_references(schema):
                    base = reference.split("#", 1)[0]
                    if base and base not in SCHEMA_FILES and base not in allowed_schema_ids:
                        raise ValueError(
                            f"{schema_name} contains non-local $ref {reference!r}"
                        )
            set_payload = json.dumps(
                entries,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            set_actual: Optional[str] = hashlib.sha256(set_payload).hexdigest()
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            set_actual = None
            schemas = {}
            self._deny(
                denials,
                "INVALID_SCHEMA_SET",
                "schema_set",
                f"cannot load pinned v1 schemas: {exc}",
            )
        receipt_evidence = DigestEvidence(
            artifact="schema",
            path=str(directory / "validation-receipt.schema.json"),
            expected_sha256=expected_receipt,
            actual_sha256=receipt_actual,
        )
        set_evidence = DigestEvidence(
            artifact="schema_set",
            path=str(directory),
            expected_sha256=expected_set,
            actual_sha256=set_actual,
        )
        if not receipt_evidence.matches:
            self._deny(
                denials,
                "DIGEST_MISMATCH",
                "schema",
                "receipt schema SHA-256 does not match its pin",
            )
        if not set_evidence.matches:
            self._deny(
                denials,
                "SCHEMA_SET_DIGEST_MISMATCH",
                "schema_set",
                "schema set SHA-256 does not match its pin",
            )
        return receipt_evidence, set_evidence, schemas or None

    def _validate_instance(
        self,
        schemas: Mapping[str, Mapping[str, Any]],
        schema_name: str,
        value: Mapping[str, Any],
        location: str,
        denials: List[DenialEvidence],
    ) -> bool:
        store = {
            schema["$id"]: schema
            for schema in schemas.values()
            if isinstance(schema.get("$id"), str)
        }
        validator = Draft7Validator(
            schemas[schema_name],
            resolver=RefResolver.from_schema(schemas[schema_name], store=store),
            format_checker=FormatChecker(),
        )
        try:
            errors = sorted(validator.iter_errors(value), key=lambda error: list(error.path))
        except Exception as exc:  # jsonschema exposes backend-specific resolution errors.
            self._deny(
                denials,
                "SCHEMA_VALIDATION_FAILED",
                location,
                f"could not validate document against pinned schema: {exc}",
            )
            return False
        if errors:
            error = errors[0]
            child = ".".join(str(item) for item in error.path)
            self._deny(
                denials,
                "SCHEMA_VALIDATION_FAILED",
                f"{location}{'.' + child if child else ''}",
                error.message,
            )
            return False
        return True

    def _read_pinned_object(
        self,
        artifact: str,
        path: Path,
        expected: str,
        denials: List[DenialEvidence],
    ) -> Tuple[DigestEvidence, Optional[Dict[str, Any]], Optional[int]]:
        try:
            if path.is_symlink():
                raise OSError("symbolic links are not accepted for pinned documents")
            payload = _read_file_snapshot(path)
        except OSError as exc:
            evidence = DigestEvidence(artifact, str(path), expected, None)
            self._deny(
                denials,
                "ARTIFACT_UNREADABLE",
                artifact,
                f"cannot read pinned {artifact}: {exc}",
            )
            return evidence, None, None
        actual = hashlib.sha256(payload).hexdigest()
        evidence = DigestEvidence(artifact, str(path), expected, actual)
        if not evidence.matches:
            self._deny(
                denials,
                "DIGEST_MISMATCH",
                artifact,
                f"{artifact} SHA-256 does not match its pin",
            )
            return evidence, None, len(payload)
        try:
            value = json.loads(payload.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            self._deny(
                denials,
                "INVALID_JSON",
                artifact,
                f"cannot parse {artifact} as UTF-8 JSON: {exc}",
            )
            return evidence, None, len(payload)
        if not isinstance(value, dict):
            self._deny(
                denials,
                "INVALID_DOCUMENT",
                artifact,
                f"{artifact} must be a JSON object",
            )
            return evidence, None, len(payload)
        return evidence, value, len(payload)

    def _read_pinned_relative_object(
        self,
        artifact: str,
        root: Path,
        relative: str,
        expected: str,
        denials: List[DenialEvidence],
    ) -> Tuple[DigestEvidence, Optional[Dict[str, Any]], Optional[int]]:
        path = root / Path(*PurePosixPath(relative).parts)
        try:
            payload = _read_contained_snapshot(root, relative)
        except OSError as exc:
            evidence = DigestEvidence(artifact, str(path), expected, None)
            self._deny(
                denials,
                "ARTIFACT_UNREADABLE",
                artifact,
                f"cannot read pinned {artifact}: {exc}",
            )
            return evidence, None, None
        actual = hashlib.sha256(payload).hexdigest()
        evidence = DigestEvidence(artifact, str(path), expected, actual)
        if not evidence.matches:
            self._deny(
                denials,
                "DIGEST_MISMATCH",
                artifact,
                f"{artifact} SHA-256 does not match its pin",
            )
            return evidence, None, len(payload)
        try:
            value = json.loads(payload.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            self._deny(
                denials,
                "INVALID_JSON",
                artifact,
                f"cannot parse {artifact} as UTF-8 JSON: {exc}",
            )
            return evidence, None, len(payload)
        if not isinstance(value, dict):
            self._deny(
                denials,
                "INVALID_DOCUMENT",
                artifact,
                f"{artifact} must be a JSON object",
            )
            return evidence, None, len(payload)
        return evidence, value, len(payload)

    def _validate_schema(
        self,
        schema: Mapping[str, Any],
        pin: ContractPin,
        denials: List[DenialEvidence],
    ) -> None:
        if schema.get("$id") != pin.schema_uri:
            self._deny(
                denials,
                "SCHEMA_ID_MISMATCH",
                "schema.$id",
                "the pinned schema does not identify the receipt schema",
            )

    def _validate_bundle(
        self,
        bundle: Mapping[str, Any],
        request: VerificationRequest,
        denials: List[DenialEvidence],
    ) -> Optional[str]:
        if bundle.get("$schema") != BUNDLE_SCHEMA_URI:
            self._deny(
                denials,
                "BUNDLE_SCHEMA_MISMATCH",
                "bundle.$schema",
                "bundle does not use the canonical v1 bundle schema",
            )
        if bundle.get("contract_version") != request.pin.contract_version:
            self._deny(
                denials,
                "CONTRACT_VERSION_MISMATCH",
                "bundle.contract_version",
                "bundle contract version does not match its pin",
            )
        if bundle.get("product_id") != request.product_id:
            self._deny(
                denials,
                "PRODUCT_MISMATCH",
                "bundle.product_id",
                "bundle product does not match the selected product",
            )

        documents = bundle.get("documents")
        receipt_reference = (
            documents.get("validation_receipt")
            if isinstance(documents, dict)
            else None
        )
        if not isinstance(receipt_reference, dict):
            self._deny(
                denials,
                "MISSING_RECEIPT",
                "bundle.documents.validation_receipt",
                "bundle has no validation receipt reference",
            )
            return None
        relative = receipt_reference.get("path")
        if not isinstance(relative, str) or not _is_safe_relative_path(relative):
            self._deny(
                denials,
                "UNSAFE_RECEIPT_PATH",
                "bundle.documents.validation_receipt.path",
                "receipt path must be a normalized relative POSIX path",
            )
            return None
        return relative

    def _validate_receipt_reference(
        self,
        bundle: Mapping[str, Any],
        digest: DigestEvidence,
        actual_size: Optional[int],
        denials: List[DenialEvidence],
    ) -> None:
        reference = bundle["documents"]["validation_receipt"]
        if reference.get("sha256") != digest.expected_sha256:
            self._deny(
                denials,
                "RECEIPT_PIN_MISMATCH",
                "bundle.documents.validation_receipt.sha256",
                "bundle receipt digest does not match the external receipt pin",
            )
        size = reference.get("size_bytes")
        if not isinstance(size, int) or isinstance(size, bool) or size != actual_size:
            self._deny(
                denials,
                "RECEIPT_SIZE_MISMATCH",
                "bundle.documents.validation_receipt.size_bytes",
                "bundle receipt size does not match the pinned receipt",
            )

    def _load_supporting_documents(
        self,
        bundle: Mapping[str, Any],
        bundle_root: Path,
        digests: List[DigestEvidence],
        denials: List[DenialEvidence],
    ) -> Optional[Dict[str, Dict[str, Any]]]:
        documents = bundle.get("documents")
        if not isinstance(documents, dict):
            self._deny(
                denials,
                "MISSING_BUNDLE_DOCUMENTS",
                "bundle.documents",
                "product bundle must contain its complete contract document set",
            )
            return None
        loaded: Dict[str, Dict[str, Any]] = {}
        valid = True
        for name in (
            "product_contract",
            "requirements",
            "product_manifest",
            "evidence_index",
        ):
            reference = documents.get(name)
            location = f"bundle.documents.{name}"
            if not isinstance(reference, dict):
                self._deny(
                    denials,
                    "MISSING_BUNDLE_DOCUMENT",
                    location,
                    f"bundle is missing {name}",
                )
                valid = False
                continue
            relative = reference.get("path")
            expected = reference.get("sha256")
            size = reference.get("size_bytes")
            if (
                not isinstance(relative, str)
                or not _is_safe_relative_path(relative)
                or not _is_sha256(expected)
                or not isinstance(size, int)
                or isinstance(size, bool)
                or size < 0
            ):
                self._deny(
                    denials,
                    "INVALID_BUNDLE_REFERENCE",
                    location,
                    f"bundle reference for {name} is malformed",
                )
                valid = False
                continue
            digest, value, actual_size = self._read_pinned_relative_object(
                f"bundle.{name}", bundle_root, relative, expected, denials
            )
            digests.append(digest)
            if not digest.matches or value is None:
                valid = False
                continue
            if actual_size != size:
                self._deny(
                    denials,
                    "DOCUMENT_SIZE_MISMATCH",
                    location,
                    f"{name} size does not match its bundle reference",
                )
                valid = False
                continue
            loaded[name] = value
        return loaded if valid and len(loaded) == 4 else None

    def _validate_cross_documents(
        self,
        bundle: Mapping[str, Any],
        receipt: Mapping[str, Any],
        receipt_digest: DigestEvidence,
        documents: Mapping[str, Mapping[str, Any]],
        request: VerificationRequest,
        denials: List[DenialEvidence],
    ) -> None:
        contract = documents["product_contract"]
        requirements = documents["requirements"]
        manifest = documents["product_manifest"]
        evidence_index = documents["evidence_index"]
        product_id = request.product_id

        for name, document in documents.items():
            if document.get("$schema") != DOCUMENT_SCHEMA_URIS[name]:
                self._deny(
                    denials,
                    "SCHEMA_ID_MISMATCH",
                    f"{name}.$schema",
                    f"{name} does not identify the canonical v1 schema",
                )
            if document.get("contract_version") != request.pin.contract_version:
                self._deny(
                    denials,
                    "CONTRACT_VERSION_MISMATCH",
                    f"{name}.contract_version",
                    f"{name} contract version does not match its pin",
                )

        identities = {
            "contract.product.id": contract.get("product", {}).get("id")
            if isinstance(contract.get("product"), dict)
            else None,
            "manifest.product.id": manifest.get("product", {}).get("id")
            if isinstance(manifest.get("product"), dict)
            else None,
            "evidence_index.product_id": evidence_index.get("product_id"),
        }
        for location, value in identities.items():
            if value != product_id:
                self._deny(
                    denials,
                    "CROSS_DOCUMENT_PRODUCT_MISMATCH",
                    location,
                    "product identity disagrees with the selected product",
                )
        receipt_product = receipt.get("product")
        contract_product = contract.get("product")
        manifest_product = manifest.get("product")
        product_paths = {
            value.get("path")
            for value in (receipt_product, contract_product, manifest_product)
            if isinstance(value, dict)
        }
        if len(product_paths) != 1 or not all(
            isinstance(value, dict) and isinstance(value.get("path"), str)
            for value in (receipt_product, contract_product, manifest_product)
        ):
            self._deny(
                denials,
                "CROSS_DOCUMENT_PRODUCT_MISMATCH",
                "product.path",
                "receipt, contract, and manifest product paths must agree",
            )

        source = receipt.get("source") if isinstance(receipt.get("source"), dict) else {}
        manifest_source = (
            manifest.get("source") if isinstance(manifest.get("source"), dict) else {}
        )
        if (
            manifest_source.get("repository") != ECAD_REPOSITORY
            or manifest_source.get("repository") != source.get("repository")
        ):
            self._deny(
                denials,
                "SOURCE_REPOSITORY_MISMATCH",
                "manifest.source.repository",
                "manifest and receipt must identify the canonical eCAD repository",
            )
        if manifest_source.get("commit") != request.pin.commit:
            self._deny(
                denials,
                "CROSS_DOCUMENT_SOURCE_MISMATCH",
                "manifest.source.commit",
                "manifest source commit does not match the immutable pin",
            )
        if manifest_source.get("dirty") is not False:
            self._deny(
                denials,
                "DIRTY_SOURCE",
                "manifest.source.dirty",
                "dirty eCAD manifests cannot authorize generation",
            )
        if manifest_source.get("input_sha256") != source.get("input_sha256"):
            self._deny(
                denials,
                "CROSS_DOCUMENT_INPUT_MISMATCH",
                "manifest.source.input_sha256",
                "manifest and receipt input digests disagree",
            )
        contract_provenance = (
            contract.get("provenance")
            if isinstance(contract.get("provenance"), dict)
            else {}
        )
        expected_product_path = next(iter(product_paths)) if len(product_paths) == 1 else None
        if contract_provenance.get("source_path") != expected_product_path:
            self._deny(
                denials,
                "CROSS_DOCUMENT_SOURCE_MISMATCH",
                "contract.provenance.source_path",
                "contract provenance path disagrees with the product documents",
            )
        if contract_provenance.get("source_commit") != request.pin.commit:
            self._deny(
                denials,
                "CROSS_DOCUMENT_SOURCE_MISMATCH",
                "contract.provenance",
                "contract provenance disagrees with the pinned receipt and manifest",
            )
        declared_tool_ids = {
            tool.get("tool_id")
            for tool in receipt.get("tools", [])
            if isinstance(tool, dict)
        }
        manifest_artifacts = {
            artifact.get("path"): artifact
            for artifact in manifest.get("artifacts", [])
            if isinstance(artifact, dict)
        }
        for artifact_path, artifact in manifest_artifacts.items():
            provenance = artifact.get("provenance", {})
            if provenance.get("source_type") == "repository" and (
                provenance.get("source_commit") != request.pin.commit
                or provenance.get("source_path") != artifact_path
            ):
                self._deny(
                    denials,
                    "PROVENANCE_MISMATCH",
                    f"manifest.artifacts.{artifact_path}.provenance",
                    "repository artifact provenance must match its path and pinned commit",
                )
            if (
                provenance.get("source_type") == "generated"
                and provenance.get("generator_tool_id") not in declared_tool_ids
            ):
                self._deny(
                    denials,
                    "MISSING_TOOL_PROVENANCE",
                    f"manifest.artifacts.{artifact_path}.provenance",
                    "generated artifact provenance must identify a declared tool",
                )
        calculated_input = _manifest_input_digest(manifest)
        if calculated_input != source.get("input_sha256"):
            self._deny(
                denials,
                "INPUT_DIGEST_MISMATCH",
                "manifest.sources",
                "receipt input digest does not match the manifest source entries",
            )

        requirements_values = requirements.get("requirements")
        requirement_ids = []
        if isinstance(requirements_values, list):
            requirement_ids = [
                item.get("requirement_id")
                for item in requirements_values
                if isinstance(item, dict)
            ]
        if not requirement_ids or len(requirement_ids) != len(set(requirement_ids)):
            self._deny(
                denials,
                "INVALID_REQUIREMENTS",
                "requirements.requirements",
                "requirement identifiers must be present and unique",
            )
        known_requirements = frozenset(requirement_ids)
        requirement_gates = {
            item.get("requirement_id"): item.get("gate")
            for item in requirements_values or []
            if isinstance(item, dict)
        }
        validation_scope = (
            contract.get("validation_scope")
            if isinstance(contract.get("validation_scope"), dict)
            else {}
        )
        if tuple(validation_scope.get("gates", ())) != REQUIRED_GATES:
            self._deny(
                denials,
                "CONTRACT_GATE_SCOPE_MISMATCH",
                "contract.validation_scope.gates",
                "product contract must require exact ordered V0-V4 validation",
            )
        contract_requirements = (
            contract.get("requirements")
            if isinstance(contract.get("requirements"), dict)
            else {}
        )
        if contract_requirements.get("catalog") != bundle.get("documents", {}).get(
            "requirements"
        ):
            self._deny(
                denials,
                "REQUIREMENT_CATALOG_MISMATCH",
                "contract.requirements.catalog",
                "contract does not bind the bundled requirements catalog",
            )
        declared = contract_requirements.get("requirement_ids")
        declared_requirement_ids = (
            frozenset(declared) if isinstance(declared, list) else frozenset()
        )
        if (
            not declared_requirement_ids
            or len(declared_requirement_ids) != len(declared or [])
            or not declared_requirement_ids.issubset(known_requirements)
        ):
            self._deny(
                denials,
                "UNKNOWN_REQUIREMENT",
                "contract.requirements.requirement_ids",
                "contract references missing or unknown requirements",
            )

        if evidence_index.get("receipt_sha256") != receipt_digest.actual_sha256:
            self._deny(
                denials,
                "EVIDENCE_RECEIPT_MISMATCH",
                "evidence_index.receipt_sha256",
                "evidence index does not bind the pinned receipt",
            )
        evidence_values = evidence_index.get("evidence")
        if not isinstance(evidence_values, list):
            self._deny(
                denials,
                "INVALID_EVIDENCE_INDEX",
                "evidence_index.evidence",
                "evidence index must contain an evidence list",
            )
            evidence_values = []
        evidence_ids = [
            item.get("evidence_id") for item in evidence_values if isinstance(item, dict)
        ]
        if len(evidence_ids) != len(evidence_values) or len(evidence_ids) != len(
            set(evidence_ids)
        ):
            self._deny(
                denials,
                "DUPLICATE_EVIDENCE",
                "evidence_index.evidence",
                "evidence identifiers must be present and unique",
            )
        indexed = {
            (
                item.get("evidence_id"),
                item.get("sha256"),
                item.get("path"),
                item.get("media_type"),
                item.get("size_bytes"),
                tuple(item.get("requirement_ids", []))
                if isinstance(item.get("requirement_ids"), list)
                else (),
                item.get("check_id"),
            )
            for item in evidence_values
            if isinstance(item, dict)
        }
        bundle_root = request.bundle_path.parent
        for item in evidence_values:
            if not isinstance(item, dict):
                continue
            if item.get("producer_tool_id") not in declared_tool_ids:
                self._deny(
                    denials,
                    "MISSING_TOOL_PROVENANCE",
                    "evidence_index.evidence.producer_tool_id",
                    "evidence producer is not declared in the receipt",
                )
            provenance = item.get("provenance", {})
            if provenance.get("source_type") == "repository":
                source_path = provenance.get("source_path")
                source_artifact = manifest_artifacts.get(source_path)
                if (
                    provenance.get("source_commit") != request.pin.commit
                    or source_artifact is None
                    or source_artifact.get("sha256") != item.get("sha256")
                ):
                    self._deny(
                        denials,
                        "PROVENANCE_MISMATCH",
                        "evidence_index.evidence.provenance",
                        "repository evidence must bind a matching pinned manifest artifact",
                    )
            if (
                provenance.get("source_type") == "generated"
                and provenance.get("generator_tool_id") not in declared_tool_ids
            ):
                self._deny(
                    denials,
                    "MISSING_TOOL_PROVENANCE",
                    "evidence_index.evidence.provenance",
                    "generated evidence provenance must identify a declared tool",
                )
            indexed_requirements = item.get("requirement_ids")
            if (
                not isinstance(indexed_requirements, list)
                or not indexed_requirements
                or not set(indexed_requirements).issubset(declared_requirement_ids)
            ):
                self._deny(
                    denials,
                    "UNKNOWN_REQUIREMENT",
                    "evidence_index.evidence.requirement_ids",
                    "evidence references unknown requirements",
                )
            relative = item.get("path")
            if not isinstance(relative, str) or not _is_safe_relative_path(relative):
                self._deny(
                    denials,
                    "INVALID_EVIDENCE",
                    "evidence_index.evidence.path",
                    "evidence path is not a safe product-relative path",
                )
                continue
            expected = item.get("sha256")
            if not _is_sha256(expected):
                self._deny(
                    denials,
                    "INVALID_EVIDENCE",
                    "evidence_index.evidence.sha256",
                    "evidence digest is malformed",
                )
                continue
            try:
                payload = _read_contained_snapshot(bundle_root, relative)
            except OSError as exc:
                self._deny(
                    denials,
                    "EVIDENCE_UNREADABLE",
                    relative,
                    f"cannot read evidence: {exc}",
                )
                continue
            actual_digest = hashlib.sha256(payload).hexdigest()
            if actual_digest != expected or len(payload) != item.get("size_bytes"):
                self._deny(
                    denials,
                    "EVIDENCE_DIGEST_MISMATCH",
                    relative,
                    "evidence bytes do not match their index entry",
                )

        covered_requirement_ids = set()
        for gate in receipt.get("gates", []):
            if not isinstance(gate, dict):
                continue
            for check in gate.get("checks", []):
                if not isinstance(check, dict):
                    continue
                requirement_values = check.get("requirement_ids")
                if (
                    not isinstance(requirement_values, list)
                    or not requirement_values
                    or not set(requirement_values).issubset(declared_requirement_ids)
                ):
                    self._deny(
                        denials,
                        "UNKNOWN_REQUIREMENT",
                        f"receipt.checks.{check.get('check_id')}.requirement_ids",
                        "check references missing or unknown requirements",
                    )
                if isinstance(requirement_values, list) and any(
                    requirement_gates.get(requirement_id) != gate.get("gate")
                    for requirement_id in requirement_values
                ):
                    self._deny(
                        denials,
                        "REQUIREMENT_GATE_MISMATCH",
                        f"receipt.checks.{check.get('check_id')}.requirement_ids",
                        "check references a requirement assigned to a different gate",
                    )
                if check.get("required") is True and isinstance(requirement_values, list):
                    covered_requirement_ids.update(requirement_values)
                for reference in check.get("evidence", []):
                    key = (
                        reference.get("evidence_id"),
                        reference.get("sha256"),
                        reference.get("path"),
                        reference.get("media_type"),
                        reference.get("size_bytes"),
                        tuple(check.get("requirement_ids", []))
                        if isinstance(check.get("requirement_ids"), list)
                        else (),
                        check.get("check_id"),
                    ) if isinstance(reference, dict) else None
                    if key not in indexed:
                        self._deny(
                            denials,
                            "UNINDEXED_EVIDENCE",
                            f"receipt.checks.{check.get('check_id')}.evidence",
                            "receipt evidence is missing from the bundled evidence index",
                        )
        missing_requirements = declared_requirement_ids - covered_requirement_ids
        if missing_requirements:
            self._deny(
                denials,
                "REQUIREMENT_COVERAGE_INCOMPLETE",
                "receipt.gates",
                "required checks do not cover product requirements: "
                + ", ".join(sorted(missing_requirements)),
            )

    def _validate_receipt(
        self,
        receipt: Mapping[str, Any],
        request: VerificationRequest,
        denials: List[DenialEvidence],
    ) -> Tuple[Optional[str], Tuple[GateEvidence, ...]]:
        if receipt.get("$schema") != RECEIPT_SCHEMA_URI:
            self._deny(
                denials,
                "SCHEMA_ID_MISMATCH",
                "receipt.$schema",
                "receipt does not identify the pinned schema",
            )
        if receipt.get("contract_version") != request.pin.contract_version:
            self._deny(
                denials,
                "CONTRACT_VERSION_MISMATCH",
                "receipt.contract_version",
                "receipt contract version does not match its pin",
            )

        product = receipt.get("product")
        if not isinstance(product, dict) or product.get("id") != request.product_id:
            self._deny(
                denials,
                "PRODUCT_MISMATCH",
                "receipt.product.id",
                "receipt product does not match the selected product",
            )

        source = receipt.get("source")
        source_commit: Optional[str] = None
        if not isinstance(source, dict):
            self._deny(
                denials,
                "INVALID_SOURCE",
                "receipt.source",
                "receipt source provenance must be an object",
            )
        else:
            source_commit = source.get("commit")
            if source.get("repository") != ECAD_REPOSITORY:
                self._deny(
                    denials,
                    "SOURCE_REPOSITORY_MISMATCH",
                    "receipt.source.repository",
                    "receipt was not produced from the canonical eCAD repository",
                )
            if source_commit != request.pin.commit:
                self._deny(
                    denials,
                    "SOURCE_COMMIT_MISMATCH",
                    "receipt.source.commit",
                    "receipt source commit does not match its pin",
                )
            if source.get("dirty") is not False:
                self._deny(
                    denials,
                    "DIRTY_SOURCE",
                    "receipt.source.dirty",
                    "dirty eCAD sources cannot authorize generation",
                )
            if not _is_sha256(source.get("input_sha256")):
                self._deny(
                    denials,
                    "INVALID_SOURCE",
                    "receipt.source.input_sha256",
                    "receipt input digest must be a lowercase SHA-256",
                )

        tool_ids = self._tool_ids(receipt.get("tools"), denials)
        gates = self._recompute_gates(receipt.get("gates"), tool_ids, denials)
        computed_overall = _aggregate_gate_verdicts(
            [gate.computed_verdict for gate in gates]
        )
        reported_overall = receipt.get("overall_verdict")
        if reported_overall != computed_overall:
            self._deny(
                denials,
                "OVERALL_AGGREGATE_MISMATCH",
                "receipt.overall_verdict",
                f"reported {reported_overall!r}, recomputed {computed_overall}",
            )
        gate_values = receipt.get("gates")
        calculated_execution_complete = (
            isinstance(gate_values, list)
            and len(gate_values) == len(REQUIRED_GATES)
            and all(
                isinstance(gate, dict)
                and isinstance(gate.get("checks"), list)
                and bool(gate["checks"])
                and all(
                    isinstance(check, dict)
                    and check.get("execution_status") == ExecutionStatus.COMPLETED.value
                    for check in gate["checks"]
                )
                for gate in gate_values
            )
        )
        if receipt.get("execution_complete") is not calculated_execution_complete:
            self._deny(
                denials,
                "EXECUTION_AGGREGATE_MISMATCH",
                "receipt.execution_complete",
                "reported execution completeness disagrees with child checks",
            )
        if not calculated_execution_complete:
            self._deny(
                denials,
                "EXECUTION_INCOMPLETE",
                "receipt.gates",
                "authorization requires every V0-V4 child check to complete",
            )
        expected_eligibility = computed_overall == Verdict.PASS.value
        if receipt.get("eligible_for_ebuild") is not expected_eligibility:
            self._deny(
                denials,
                "ELIGIBILITY_MISMATCH",
                "receipt.eligible_for_ebuild",
                "reported eligibility disagrees with recomputed gates",
            )
        if not expected_eligibility:
            self._deny(
                denials,
                "VALIDATION_NOT_PASSING",
                "receipt.gates",
                "all required V0-V4 checks must pass",
            )
        return source_commit, gates

    def _tool_ids(
        self, tools: Any, denials: List[DenialEvidence]
    ) -> frozenset:
        if not isinstance(tools, list) or not tools:
            self._deny(
                denials,
                "MISSING_TOOL_PROVENANCE",
                "receipt.tools",
                "receipt must identify at least one validation tool",
            )
            return frozenset()
        values = []
        for index, tool in enumerate(tools):
            tool_id = tool.get("tool_id") if isinstance(tool, dict) else None
            if not isinstance(tool_id, str) or not tool_id:
                self._deny(
                    denials,
                    "MISSING_TOOL_PROVENANCE",
                    f"receipt.tools[{index}].tool_id",
                    "validation tool is missing its identifier",
                )
            else:
                values.append(tool_id)
        if len(set(values)) != len(values):
            self._deny(
                denials,
                "DUPLICATE_TOOL",
                "receipt.tools",
                "validation tool identifiers must be unique",
            )
        return frozenset(values)

    def _recompute_gates(
        self,
        value: Any,
        tool_ids: frozenset,
        denials: List[DenialEvidence],
    ) -> Tuple[GateEvidence, ...]:
        if not isinstance(value, list):
            self._deny(
                denials,
                "MISSING_GATES",
                "receipt.gates",
                "receipt must contain exact V0-V4 gate results",
            )
            return ()
        by_gate: Dict[str, Mapping[str, Any]] = {}
        for index, gate in enumerate(value):
            name = gate.get("gate") if isinstance(gate, dict) else None
            if name not in REQUIRED_GATES:
                self._deny(
                    denials,
                    "INVALID_GATE",
                    f"receipt.gates[{index}]",
                    f"unknown gate {name!r}",
                )
                continue
            if name in by_gate:
                self._deny(
                    denials,
                    "DUPLICATE_GATE",
                    f"receipt.gates[{index}].gate",
                    f"gate {name} occurs more than once",
                )
                continue
            by_gate[name] = gate
        missing = [gate for gate in REQUIRED_GATES if gate not in by_gate]
        if missing:
            self._deny(
                denials,
                "MISSING_GATES",
                "receipt.gates",
                f"receipt is missing required gates: {', '.join(missing)}",
            )

        evidence: List[GateEvidence] = []
        for name in REQUIRED_GATES:
            gate = by_gate.get(name)
            if gate is None:
                continue
            checks = gate.get("checks")
            required_verdicts: List[str] = []
            if not isinstance(checks, list) or not checks:
                self._deny(
                    denials,
                    "MISSING_REQUIRED_CHECKS",
                    f"receipt.gates.{name}.checks",
                    f"gate {name} must contain a required check",
                )
            else:
                for index, check in enumerate(checks):
                    self._validate_check(
                        name,
                        index,
                        check,
                        tool_ids,
                        required_verdicts,
                        denials,
                    )
            computed = _aggregate_check_verdicts(required_verdicts)
            reported = gate.get("verdict")
            if reported != computed:
                self._deny(
                    denials,
                    "GATE_AGGREGATE_MISMATCH",
                    f"receipt.gates.{name}.verdict",
                    f"reported {reported!r}, recomputed {computed}",
                )
            evidence.append(
                GateEvidence(
                    gate=name,
                    reported_verdict=str(reported),
                    computed_verdict=computed,
                    required_checks=len(required_verdicts),
                )
            )
        return tuple(evidence)

    def _validate_check(
        self,
        gate_name: str,
        index: int,
        check: Any,
        tool_ids: frozenset,
        required_verdicts: List[str],
        denials: List[DenialEvidence],
    ) -> None:
        location = f"receipt.gates.{gate_name}.checks[{index}]"
        if not isinstance(check, dict):
            self._deny(
                denials,
                "INVALID_CHECK",
                location,
                "check result must be an object",
            )
            required_verdicts.append(Verdict.INCONCLUSIVE.value)
            return
        required = check.get("required")
        if not isinstance(required, bool):
            self._deny(
                denials,
                "INVALID_CHECK",
                f"{location}.required",
                "required must be a boolean",
            )
            required = True
        if check.get("gate") != gate_name:
            self._deny(
                denials,
                "CHECK_GATE_MISMATCH",
                f"{location}.gate",
                "child check gate does not match its parent aggregate",
            )
        verdict = check.get("verdict")
        status = check.get("execution_status")
        if verdict not in _KNOWN_VERDICTS:
            self._deny(
                denials,
                "INVALID_CHECK",
                f"{location}.verdict",
                f"unknown check verdict {verdict!r}",
            )
            verdict = Verdict.INCONCLUSIVE.value
        if status not in _KNOWN_EXECUTION_STATUSES:
            self._deny(
                denials,
                "INVALID_CHECK",
                f"{location}.execution_status",
                f"unknown execution status {status!r}",
            )
        if check.get("tool_id") not in tool_ids:
            self._deny(
                denials,
                "MISSING_TOOL_PROVENANCE",
                f"{location}.tool_id",
                "check references an undeclared validation tool",
            )
        if verdict == Verdict.PASS.value:
            if status != ExecutionStatus.COMPLETED.value:
                self._deny(
                    denials,
                    "INVALID_PASS_STATE",
                    f"{location}.execution_status",
                    "PASS requires execution_status=completed",
                )
            evidence = check.get("evidence")
            if not isinstance(evidence, list) or not evidence:
                self._deny(
                    denials,
                    "MISSING_EVIDENCE",
                    f"{location}.evidence",
                    "PASS requires at least one evidence reference",
                )
            elif not all(_valid_evidence_reference(item) for item in evidence):
                self._deny(
                    denials,
                    "INVALID_EVIDENCE",
                    f"{location}.evidence",
                    "evidence references require path, digest, media type, and size",
                )
        if required:
            required_verdicts.append(verdict)
            if verdict in _DENYING_VERDICTS:
                self._deny(
                    denials,
                    "REQUIRED_CHECK_NOT_PASS",
                    f"{location}.verdict",
                    f"required check reported {verdict}",
                )


def _manifest_input_digest(manifest: Mapping[str, Any]) -> Optional[str]:
    artifacts = manifest.get("artifacts")
    product = manifest.get("product")
    if (
        not isinstance(artifacts, list)
        or not artifacts
        or not isinstance(product, dict)
        or not isinstance(product.get("path"), str)
    ):
        return None
    product_path = PurePosixPath(product["path"])
    entries = []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            return None
        repository_path = artifact.get("path")
        digest = artifact.get("sha256")
        if (
            not isinstance(repository_path, str)
            or not _is_safe_relative_path(repository_path)
            or not _is_sha256(digest)
        ):
            return None
        try:
            relative = PurePosixPath(repository_path).relative_to(product_path).as_posix()
        except ValueError:
            return None
        entries.append({"path": relative, "sha256": digest})
    if len({entry["path"] for entry in entries}) != len(entries):
        return None
    entries.sort(key=lambda item: item["path"])
    payload = json.dumps(
        entries,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _schema_references(value: Any) -> Sequence[str]:
    references = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "$ref" and isinstance(child, str):
                references.append(child)
            else:
                references.extend(_schema_references(child))
    elif isinstance(value, list):
        for child in value:
            references.extend(_schema_references(child))
    return references


def _read_contained_snapshot(root: Path, relative: str) -> bytes:
    """Open a product-bundle file without following path-component symlinks."""
    if not _is_safe_relative_path(relative):
        raise OSError(f"unsafe relative path: {relative!r}")
    parts = PurePosixPath(relative).parts
    if os.name == "nt" or not hasattr(os, "O_DIRECTORY"):
        resolved_root = root.resolve()
        candidate = (root / Path(*parts)).resolve()
        try:
            candidate.relative_to(resolved_root)
        except ValueError as exc:
            raise OSError(f"path escapes bundle root: {relative}") from exc
        cursor = root
        for part in parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise OSError(f"path traverses a symbolic link: {relative}")
        return _read_file_snapshot(candidate)

    descriptors = []
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptors.append(
            os.open(str(root), os.O_RDONLY | os.O_DIRECTORY | nofollow)
        )
        for part in parts[:-1]:
            descriptors.append(
                os.open(
                    part,
                    os.O_RDONLY | os.O_DIRECTORY | nofollow,
                    dir_fd=descriptors[-1],
                )
            )
        file_descriptor = os.open(
            parts[-1],
            os.O_RDONLY | getattr(os, "O_BINARY", 0) | nofollow,
            dir_fd=descriptors[-1],
        )
        descriptors.append(file_descriptor)
        metadata = os.fstat(file_descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise OSError(f"not a regular file: {relative}")
        chunks = []
        while True:
            chunk = os.read(file_descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _read_file_snapshot(path: Path) -> bytes:
    """Read one regular file through one descriptor, refusing final symlinks."""
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(str(path), flags)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise OSError(f"not a regular file: {path}")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            return handle.read()
    finally:
        os.close(descriptor)


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and not (set(value) - _DIGEST_RE)
    )


def _is_safe_relative_path(value: str) -> bool:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        return False
    if value.startswith("/"):
        return False
    parts = value.split("/")
    return bool(parts) and all(part not in ("", ".", "..") for part in parts)


def _valid_evidence_reference(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    size = value.get("size_bytes")
    return (
        isinstance(value.get("path"), str)
        and _is_safe_relative_path(value["path"])
        and _is_sha256(value.get("sha256"))
        and isinstance(value.get("media_type"), str)
        and bool(value["media_type"].strip())
        and isinstance(size, int)
        and not isinstance(size, bool)
        and size >= 0
    )


def _aggregate_check_verdicts(verdicts: Sequence[str]) -> str:
    if not verdicts:
        return Verdict.BLOCKED.value
    if Verdict.FAIL.value in verdicts:
        return Verdict.FAIL.value
    if Verdict.BLOCKED.value in verdicts or Verdict.WARNING.value in verdicts:
        return Verdict.BLOCKED.value
    if Verdict.INCONCLUSIVE.value in verdicts:
        return Verdict.INCONCLUSIVE.value
    if Verdict.NOT_RUN.value in verdicts:
        return Verdict.NOT_RUN.value
    if all(verdict == Verdict.PASS.value for verdict in verdicts):
        return Verdict.PASS.value
    return Verdict.INCONCLUSIVE.value


def _aggregate_gate_verdicts(verdicts: Sequence[str]) -> str:
    if len(verdicts) != len(REQUIRED_GATES):
        return Verdict.BLOCKED.value
    return _aggregate_check_verdicts(verdicts)
