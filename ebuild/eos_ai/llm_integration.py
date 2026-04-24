# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""LLM Integration — automated calls to local/cloud LLMs for deep hardware analysis.

Supports:
- Ollama (local, default — no API key needed)
- OpenAI-compatible APIs (OpenAI, Anthropic, Groq, Together, etc.)
- Direct HTTP for any OpenAI-compatible endpoint

No dependencies beyond Python stdlib (uses urllib).

Usage:
    from ebuild.eos_ai.llm_integration import LLMClient

    # Auto-detect: tries Ollama first, then env vars
    client = LLMClient.auto()

    # Or explicit:
    client = LLMClient(provider="ollama", model="llama3")
    client = LLMClient(provider="openai", model="gpt-4o")  # uses OPENAI_API_KEY env var

    response = client.analyze(prompt)
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMResponse:
    """Response from an LLM call."""
    text: str
    model: str
    provider: str
    tokens_used: int = 0
    success: bool = True
    error: str = ""


class LLMClient:
    """Unified LLM client for hardware analysis.

    Tries providers in order:
    1. Ollama (local, http://localhost:11434)
    2. OpenAI-compatible API (via OPENAI_API_KEY or EOS_LLM_API_KEY env var)

    All calls are optional — the analyzer works without any LLM.
    """

    OLLAMA_URL = "http://localhost:11434"
    OPENAI_URL = "https://api.openai.com"

    def __init__(
        self,
        provider: str = "ollama",
        model: str = "llama3",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 120,
    ):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout

        if provider == "ollama":
            self.base_url = base_url or self.OLLAMA_URL
        elif provider == "openai":
            self.base_url = base_url or self.OPENAI_URL
            self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        elif provider == "custom":
            self.base_url = base_url or ""
            self.api_key = api_key or os.environ.get("EOS_LLM_API_KEY", "")

    @classmethod
    def auto(cls) -> "LLMClient":
        """Auto-detect available LLM provider.

        Priority:
        1. Ollama running locally
        2. OpenAI API key in environment
        3. EOS_LLM_API_KEY + EOS_LLM_URL in environment
        4. None (returns a client that will fail gracefully)
        """
        # Try Ollama
        if cls._check_ollama():
            return cls(provider="ollama", model="llama3")

        # Try OpenAI
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        if openai_key:
            return cls(provider="openai", model="gpt-4o-mini", api_key=openai_key)

        # Try custom
        custom_key = os.environ.get("EOS_LLM_API_KEY", "")
        custom_url = os.environ.get("EOS_LLM_URL", "")
        if custom_key and custom_url:
            model = os.environ.get("EOS_LLM_MODEL", "default")
            return cls(provider="custom", model=model,
                       api_key=custom_key, base_url=custom_url)

        # No provider available
        return cls(provider="none", model="none")

    @staticmethod
    def _check_ollama() -> bool:
        """Check if Ollama is running locally."""
        try:
            req = urllib.request.Request(
                f"{LLMClient.OLLAMA_URL}/api/tags",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except (urllib.error.URLError, OSError, TimeoutError):
            return False

    def is_available(self) -> bool:
        """Check if this LLM client can make requests."""
        if self.provider == "none":
            return False
        if self.provider == "ollama":
            return self._check_ollama()
        if self.provider in ("openai", "custom"):
            return bool(self.api_key and self.base_url)
        return False

    def analyze(self, prompt: str, system: str = "") -> LLMResponse:
        """Send a prompt to the LLM and return the response.

        Args:
            prompt: The user prompt (hardware analysis request).
            system: Optional system prompt for context.

        Returns:
            LLMResponse with the analysis text, or error details.
        """
        if self.provider == "none":
            return LLMResponse(
                text="", model="none", provider="none",
                success=False,
                error="No LLM provider available. Install Ollama or set OPENAI_API_KEY.",
            )

        if not system:
            system = (
                "You are an embedded systems hardware expert. "
                "Analyze the hardware description and provide structured "
                "recommendations for EoS (Embedded Operating System) configuration. "
                "Output as YAML when possible."
            )

        try:
            if self.provider == "ollama":
                return self._call_ollama(prompt, system)
            else:
                return self._call_openai_compat(prompt, system)
        except Exception as e:
            return LLMResponse(
                text="", model=self.model, provider=self.provider,
                success=False, error=str(e),
            )

    def _call_ollama(self, prompt: str, system: str) -> LLMResponse:
        """Call Ollama local API."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        return LLMResponse(
            text=body.get("response", ""),
            model=body.get("model", self.model),
            provider="ollama",
            tokens_used=body.get("eval_count", 0),
            success=True,
        )

    def _call_openai_compat(self, prompt: str, system: str) -> LLMResponse:
        """Call OpenAI-compatible chat completions API."""
        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 4096,
        }

        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        choice = body.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage = body.get("usage", {})

        return LLMResponse(
            text=message.get("content", ""),
            model=body.get("model", self.model),
            provider=self.provider,
            tokens_used=usage.get("total_tokens", 0),
            success=True,
        )

    def get_provider_info(self) -> str:
        """Return human-readable provider information."""
        if self.provider == "none":
            return "No LLM provider configured"
        if self.provider == "ollama":
            return f"Ollama (local) — model: {self.model} — {self.base_url}"
        if self.provider == "openai":
            return f"OpenAI — model: {self.model}"
        return f"{self.provider} — model: {self.model} — {self.base_url}"
