# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Generation entry gate backed by pinned eCAD validation evidence."""

from __future__ import annotations

from typing import Callable, TypeVar

from ebuild.eos_ai.hardware_contract import (
    GenerationDenied,
    VerificationRequest,
    VerificationResult,
)
from ebuild.eos_ai.hardware_verifier import HardwareReceiptVerifier

_Generated = TypeVar("_Generated")


class HardwareGenerationGate:
    """Authorize first and invoke generation only for a verified PASS receipt."""

    def __init__(self, verifier: HardwareReceiptVerifier = None) -> None:
        """Create a gate with the supplied verifier or the strict default verifier."""
        self._verifier = verifier or HardwareReceiptVerifier()

    def authorize(self, request: VerificationRequest) -> VerificationResult:
        """Evaluate a generation request without creating or changing output.

        Args:
            request: The selected product and pinned validation artifacts.

        Returns:
            Structured digest, gate, and denial evidence.

        Example:
            ``HardwareGenerationGate().authorize(request).authorized``
        """
        return self._verifier.verify(request)

    def authorize_and_generate(
        self,
        request: VerificationRequest,
        generate: Callable[[VerificationResult], _Generated],
    ) -> _Generated:
        """Invoke a generation callback only after authorization succeeds.

        Args:
            request: The selected product and pinned validation artifacts.
            generate: Callback that performs generation after authorization.

        Returns:
            The callback's return value.

        Raises:
            GenerationDenied: If any digest, provenance, or required gate check
                fails verification. The exception carries structured evidence.

        Example:
            ``gate.authorize_and_generate(request, lambda evidence: "generated")``
        """
        result = self.authorize(request)
        if not result.authorized:
            raise GenerationDenied(result)
        return generate(result)
