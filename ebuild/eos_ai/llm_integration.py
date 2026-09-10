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
            default_url = os.environ.get("OLLAMA_HOST") or self.OLLAMA_URL
            if default_url and not default_url.startswith(("http://", "https://")):
                default_url = f"http://{default_url}"
            self.base_url = (base_url or default_url).rstrip("/")
        elif provider == "openai":
            default_url = os.environ.get("OPENAI_BASE_URL") or self.OPENAI_URL
            self.base_url = (base_url or default_url).rstrip("/")
            self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        elif provider == "custom":
            self.base_url = (base_url or "").rstrip("/")
            self.api_key = api_key or os.environ.get("EOS_LLM_API_KEY", "")

    @staticmethod
    def _normalize_ollama_url(base_url: str) -> str:
        """Normalize Ollama base URL to generation endpoint."""
        url = (base_url or "").rstrip("/")
        if url.endswith("/api/generate"):
            return url
        return f"{url}/api/generate"

    @staticmethod
    def _normalize_openai_url(base_url: str) -> str:
        """Normalize OpenAI-compatible base URL to chat completions endpoint.

        Handles:
        - "https://api.openai.com" -> "https://api.openai.com/v1/chat/completions"
        - "https://api.openai.com/" -> "https://api.openai.com/v1/chat/completions"
        - "https://api.openai.com/v1" -> "https://api.openai.com/v1/chat/completions"
        - "https://api.openai.com/v1/" -> "https://api.openai.com/v1/chat/completions"
        - "http://localhost:8000/v1/chat/completions" -> unchanged
        """
        url = (base_url or "").rstrip("/")
        if url.endswith("/chat/completions"):
            return url
        if url.endswith("/v1"):
            return f"{url}/chat/completions"
        return f"{url}/v1/chat/completions"

    @classmethod
    def auto(cls) -> "LLMClient":
        """Auto-detect available LLM provider.

        Priority:
        1. Ollama running locally or at OLLAMA_HOST
        2. OpenAI API key in environment (respecting OPENAI_BASE_URL)
        3. EOS_LLM_URL in environment (EOS_LLM_API_KEY optional)
        4. None (returns a client that will fail gracefully)
        """
        # Try Ollama
        ollama_url = os.environ.get("OLLAMA_HOST") or cls.OLLAMA_URL
        if ollama_url and not ollama_url.startswith(("http://", "https://")):
            ollama_url = f"http://{ollama_url}"
        if cls._check_ollama(ollama_url):
            model = os.environ.get("OLLAMA_MODEL", "llama3")
            return cls(provider="ollama", model=model, base_url=ollama_url)

        # Try OpenAI
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        if openai_key:
            openai_base = os.environ.get("OPENAI_BASE_URL")
            model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
            return cls(provider="openai", model=model, api_key=openai_key, base_url=openai_base)

        # Try custom
        custom_url = os.environ.get("EOS_LLM_URL", "")
        if custom_url:
            custom_key = os.environ.get("EOS_LLM_API_KEY", "")
            model = os.environ.get("EOS_LLM_MODEL", "default")
            return cls(provider="custom", model=model,
                       api_key=custom_key, base_url=custom_url)

        # No provider available
        return cls(provider="none", model="none")

    @classmethod
    def _check_ollama(cls, base_url: Optional[str] = None) -> bool:
        """Check if Ollama is running at target base_url or localhost default."""
        target_url = (base_url or cls.OLLAMA_URL).rstrip("/")
        if target_url.endswith("/api/generate"):
            tags_url = target_url.rsplit("/", 1)[0] + "/tags"
        elif target_url.endswith("/api/tags"):
            tags_url = target_url
        else:
            tags_url = f"{target_url}/api/tags"

        try:
            req = urllib.request.Request(tags_url, method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except (urllib.error.URLError, OSError, TimeoutError):
            return False

    def is_available(self) -> bool:
        """Check if this LLM client can make requests."""
        if self.provider == "none":
            return False
        if self.provider == "ollama":
            return self._check_ollama(self.base_url)
        if self.provider == "openai":
            return bool(self.api_key and self.base_url)
        if self.provider == "custom":
            return bool(self.base_url)
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
        except urllib.error.HTTPError as e:
            err_details = ""
            try:
                raw_err = e.read().decode("utf-8")
                try:
                    err_json = json.loads(raw_err)
                    if isinstance(err_json, dict):
                        if "error" in err_json:
                            inner = err_json["error"]
                            err_details = inner.get("message", str(inner)) if isinstance(inner, dict) else str(inner)
                        elif "message" in err_json:
                            err_details = str(err_json["message"])
                except (json.JSONDecodeError, ValueError):
                    pass
                if not err_details and raw_err.strip():
                    err_details = raw_err.strip()[:200]
            except Exception:
                pass
            msg = f"HTTP {e.code}: {err_details}" if err_details else f"HTTP {e.code}: {e.reason}"
            return LLMResponse(
                text="", model=self.model, provider=self.provider,
                success=False, error=msg,
            )
        except urllib.error.URLError as e:
            if isinstance(e.reason, TimeoutError):
                error_msg = f"Request timed out after {self.timeout}s"
            else:
                error_msg = f"Connection error: {e.reason}"
            return LLMResponse(
                text="", model=self.model, provider=self.provider,
                success=False, error=error_msg,
            )
        except TimeoutError:
            return LLMResponse(
                text="", model=self.model, provider=self.provider,
                success=False, error=f"Request timed out after {self.timeout}s",
            )
        except Exception as e:
            return LLMResponse(
                text="", model=self.model, provider=self.provider,
                success=False, error=str(e),
            )

    def _call_ollama(self, prompt: str, system: str) -> LLMResponse:
        """Call Ollama local API."""
        url = self._normalize_ollama_url(self.base_url or self.OLLAMA_URL)
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

        if not isinstance(body, dict):
            return LLMResponse(
                text="", model=self.model, provider="ollama",
                success=False, error="Invalid JSON response: expected object",
            )

        return LLMResponse(
            text=body.get("response", ""),
            model=body.get("model", self.model),
            provider="ollama",
            tokens_used=body.get("eval_count", 0),
            success=True,
        )

    def _call_openai_compat(self, prompt: str, system: str) -> LLMResponse:
        """Call OpenAI-compatible chat completions API."""
        url = self._normalize_openai_url(self.base_url or self.OPENAI_URL)
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
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        if not isinstance(body, dict):
            return LLMResponse(
                text="", model=self.model, provider=self.provider,
                success=False, error="Invalid JSON response: expected object",
            )

        if isinstance(body, dict) and "error" in body and not body.get("choices"):
            err_data = body["error"]
            err_msg = err_data.get("message", str(err_data)) if isinstance(err_data, dict) else str(err_data)
            return LLMResponse(
                text="",
                model=self.model,
                provider=self.provider,
                success=False,
                error=err_msg,
            )

        choices = body.get("choices") or []
        first_choice = choices[0] if choices else {}
        message = first_choice.get("message", {}) if isinstance(first_choice, dict) else {}
        content = message.get("content", "") if isinstance(message, dict) else ""
        usage = body.get("usage", {}) if isinstance(body.get("usage"), dict) else {}

        return LLMResponse(
            text=content or "",
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
