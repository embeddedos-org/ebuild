# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Models for pinned eCAD validation authorization."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple

CONTRACT_VERSION = "1.0.0"
ECAD_REPOSITORY = "https://github.com/embeddedos-org/eCAD-Hardware-Products"
RECEIPT_SCHEMA_URI = (
    "https://embeddedos.org/schemas/hardware-validation/v1/"
    "validation-receipt.schema.json"
)
BUNDLE_SCHEMA_URI = (
    "https://embeddedos.org/schemas/hardware-validation/v1/bundle.schema.json"
)
DOCUMENT_SCHEMA_URIS = {
    "product_contract": "https://embeddedos.org/schemas/hardware-validation/v1/product-contract.schema.json",
    "requirements": "https://embeddedos.org/schemas/hardware-validation/v1/requirements.schema.json",
    "product_manifest": "https://embeddedos.org/schemas/hardware-validation/v1/product-manifest.schema.json",
    "evidence_index": "https://embeddedos.org/schemas/hardware-validation/v1/evidence-index.schema.json",
}
REQUIRED_GATES = ("V0", "V1", "V2", "V3", "V4")
SCHEMA_FILES = (
    "common.schema.json",
    "product-contract.schema.json",
    "requirements.schema.json",
    "product-manifest.schema.json",
    "validation-cases.schema.json",
    "validation-receipt.schema.json",
    "evidence-index.schema.json",
    "bundle.schema.json",
    "repository-bundle.schema.json",
)

_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
_COMMIT_RE = re.compile(r"^[a-f0-9]{40}$")


def calculate_schema_set_sha256(directory: Path) -> str:
    """Return the canonical digest used to pin the complete eCAD v1 schema set."""
    entries = []
    for name in SCHEMA_FILES:
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"schema is missing or is a symbolic link: {name}")
        entries.append(
            {"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        )
    payload = json.dumps(
        entries,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class Verdict(str, Enum):
    """A validation check or aggregate verdict."""

    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    NOT_RUN = "NOT_RUN"
    BLOCKED = "BLOCKED"
    INCONCLUSIVE = "INCONCLUSIVE"


class ExecutionStatus(str, Enum):
    """The execution state reported for one validation check."""

    COMPLETED = "completed"
    SKIPPED = "skipped"
    UNAVAILABLE = "unavailable"
    TIMED_OUT = "timed_out"
    CRASHED = "crashed"


@dataclass(frozen=True)
class ContractPin:
    """Immutable identity and digest pins for one trusted eCAD release."""

    repository: str
    commit: str
    contract_version: str
    schema_uri: str
    schema_sha256: str
    schema_set_sha256: str
    bundle_sha256: str
    receipt_sha256: str

    def __post_init__(self) -> None:
        """Reject aliases and malformed pins before any artifact is trusted."""
        if self.repository != ECAD_REPOSITORY:
            raise ValueError("repository must pin the canonical eCAD repository")
        if not _COMMIT_RE.fullmatch(self.commit):
            raise ValueError("commit must be a full 40-character lowercase Git object ID")
        if self.contract_version != CONTRACT_VERSION:
            raise ValueError(
                "unsupported hardware validation contract version: "
                f"{self.contract_version!r}"
            )
        if self.schema_uri != RECEIPT_SCHEMA_URI:
            raise ValueError("schema_uri must identify the pinned v1 receipt schema")
        for name in (
            "schema_sha256",
            "schema_set_sha256",
            "bundle_sha256",
            "receipt_sha256",
        ):
            value = getattr(self, name)
            if not _SHA256_RE.fullmatch(value):
                raise ValueError(f"{name} must be a lowercase SHA-256 digest")


@dataclass(frozen=True)
class VerificationRequest:
    """Inputs required to authorize one product generation request."""

    schema_path: Path
    bundle_path: Path
    product_id: str
    pin: ContractPin

    def __post_init__(self) -> None:
        """Validate the selected product identifier at the API boundary."""
        if not isinstance(self.product_id, str) or not self.product_id.strip():
            raise ValueError("product_id must be a non-empty string")


@dataclass(frozen=True)
class DenialEvidence:
    """A stable denial code with a human-readable location and explanation."""

    code: str
    location: str
    message: str


@dataclass(frozen=True)
class DigestEvidence:
    """Expected and observed digest evidence for one pinned artifact."""

    artifact: str
    path: str
    expected_sha256: str
    actual_sha256: Optional[str]

    @property
    def matches(self) -> bool:
        """Return whether the artifact exactly matches its configured digest."""
        return self.actual_sha256 == self.expected_sha256


@dataclass(frozen=True)
class GateEvidence:
    """Reported and independently recomputed state for one V0-V4 gate."""

    gate: str
    reported_verdict: str
    computed_verdict: str
    required_checks: int


@dataclass(frozen=True)
class VerificationResult:
    """Structured authorization evidence returned for both allow and deny paths."""

    product_id: str
    source_commit: Optional[str]
    digests: Tuple[DigestEvidence, ...]
    gates: Tuple[GateEvidence, ...]
    denials: Tuple[DenialEvidence, ...]

    @property
    def authorized(self) -> bool:
        """Return true only for an exact, denial-free V0-V4 PASS result."""
        return (
            not self.denials
            and tuple(gate.gate for gate in self.gates) == REQUIRED_GATES
            and all(gate.computed_verdict == Verdict.PASS.value for gate in self.gates)
        )

    @property
    def denial_codes(self) -> Tuple[str, ...]:
        """Return stable machine-readable denial codes in discovery order."""
        return tuple(denial.code for denial in self.denials)


class GenerationDenied(RuntimeError):
    """Raised when generation is attempted without verified authorization."""

    def __init__(self, result: VerificationResult) -> None:
        self.result = result
        codes = ", ".join(result.denial_codes) or "authorization incomplete"
        super().__init__(f"hardware generation denied: {codes}")
