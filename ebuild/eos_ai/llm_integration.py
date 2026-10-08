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
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

# Same ceiling the package-index fetcher uses. An LLM analysis is a YAML
# recommendation, not a stream; a response larger than this is a fault, not
# a useful answer, and urllib would otherwise read it into memory unbounded.
MAX_LLM_RESPONSE_BYTES = 10 * 1024 * 1024

_ALLOWED_SCHEMES = {"http", "https"}
_BEARER_RE = re.compile(r"Bearer \S+", re.IGNORECASE)
_KEY_QUERY_RE = re.compile(
    r"(api[_-]?key|token|secret)=([^&\s]+)", re.IGNORECASE
)


def _http_url(url: str) -> str:
    """Return *url* if it names an HTTP(S) endpoint.

    ``urllib.request.urlopen`` opens ``file://`` and other schemes. An LLM
    endpoint is an HTTP service; anything else is either a programming error
    or SSRF. Unlike the package index, HTTP (not only HTTPS) is allowed:
    Ollama's default listener is ``http://localhost:11434``.
    """
    parsed = urlparse(url)
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES or not parsed.netloc:
        scheme = parsed.scheme or "empty"
        raise ValueError(f"LLM endpoint must be an http(s) URL (got {scheme})")
    return url


def _ensure_scheme(url: str) -> str:
    """Prefix ``http://`` to a schemeless host such as ``OLLAMA_HOST``.

    Ollama documents ``OLLAMA_HOST`` as ``host:port`` (``0.0.0.0:11434``),
    which ``urlparse`` reads as scheme ``0.0.0.0`` and ``_http_url`` refuses.
    A value that already names a scheme is returned unchanged.
    """
    url = url.strip()
    return url if "://" in url else f"http://{url}"


def _openai_chat_url(base_url: str) -> str:
    """Join *base_url* to the chat-completions path without doubling ``/v1``.

    OpenAI-compatible servers document the base as either the origin
    (``https://api.openai.com``) or the v1 root (``https://api.openai.com/v1``).
    Always appending ``/v1/chat/completions`` made the second form 404. A URL
    that already ends in ``/chat/completions`` is returned as it is.
    """
    base = _http_url(base_url).rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


_normalize_openai_url = _openai_chat_url


def _error_text(exc: BaseException) -> str:
    """Render *exc* for the caller without echoing credentials."""
    text = str(exc)
    text = _BEARER_RE.sub("Bearer [redacted]", text)
    text = _KEY_QUERY_RE.sub(r"\1=[redacted]", text)
    return text


def _read_limited(resp, limit: int = MAX_LLM_RESPONSE_BYTES) -> bytes:
    data = resp.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"LLM response exceeded {limit} bytes")
    return data


def _completed(text: str, model: str, provider: str, tokens_used: int) -> LLMResponse:
    if not text.strip():
        return LLMResponse(
            text="",
            model=model,
            provider=provider,
            tokens_used=tokens_used,
            success=False,
            error="LLM returned an empty response",
        )
    return LLMResponse(
        text=text,
        model=model,
        provider=provider,
        tokens_used=tokens_used,
        success=True,
    )


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

    # Per-provider default model, used only when neither the caller nor the
    # provider's environment variable names one. ``model`` defaults to None
    # rather than a real model name: a sentinel such as "llama3" cannot tell
    # "not given" from an explicit model="llama3".
    DEFAULT_MODELS = {
        "ollama": "llama3",
        "openai": "gpt-4o-mini",
        "custom": "default",
    }
    MODEL_ENV = {
        "ollama": "OLLAMA_MODEL",
        "openai": "OPENAI_MODEL",
        "custom": "EOS_LLM_MODEL",
    }

    def __init__(
        self,
        provider: str = "ollama",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 120,
    ):
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout

        env_var = self.MODEL_ENV.get(provider)
        env_model = os.environ.get(env_var, "") if env_var else ""
        self.model = model or env_model or self.DEFAULT_MODELS.get(provider, "none")

        if provider == "ollama":
            self.base_url = base_url or self._ollama_env_url() or self.OLLAMA_URL
        elif provider == "openai":
            self.base_url = base_url or os.environ.get("OPENAI_BASE_URL", "") or self.OPENAI_URL
            self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        elif provider == "custom":
            self.base_url = base_url or os.environ.get("EOS_LLM_URL", "")
            self.api_key = api_key or os.environ.get("EOS_LLM_API_KEY", "")

    @staticmethod
    def _ollama_env_url() -> str:
        """``OLLAMA_HOST`` as a URL, or "" when it is unset."""
        host = os.environ.get("OLLAMA_HOST", "").strip()
        return _ensure_scheme(host) if host else ""

    @classmethod
    def auto(cls) -> "LLMClient":
        """Auto-detect available LLM provider.

        Priority:
        1. Ollama running locally
        2. OpenAI API key in environment
        3. EOS_LLM_API_KEY + EOS_LLM_URL in environment
        4. None (returns a client that will fail gracefully)
        """
        # Try Ollama, where OLLAMA_HOST says it is (localhost by default)
        if cls._check_ollama(cls._ollama_env_url() or None):
            return cls(provider="ollama")

        # Try OpenAI
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        if openai_key:
            return cls(provider="openai", api_key=openai_key)

        # Try custom. The key is optional: local OpenAI-compatible servers
        # (vLLM, llama.cpp, LM Studio) usually run without one.
        if os.environ.get("EOS_LLM_URL", ""):
            return cls(provider="custom")

        # No provider available
        return cls(provider="none", model="none")

    @staticmethod
    def _check_ollama(base_url: Optional[str] = None) -> bool:
        """Return True if an Ollama server answers at *base_url*.

        Availability must probe the URL the client will actually call. The
        previous probe always hit ``OLLAMA_URL`` (localhost:11434), so a
        client constructed with ``base_url=http://gpu-box:11434`` reported
        itself available whenever a *different* Ollama was running locally,
        and unavailable when only the configured host was up.
        """
        url = (base_url or LLMClient.OLLAMA_URL).rstrip("/")
        try:
            _http_url(url)
        except ValueError:
            return False
        try:
            req = urllib.request.Request(f"{url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except (urllib.error.URLError, OSError, TimeoutError, ValueError):
            return False

    def is_available(self) -> bool:
        """Check if this LLM client can make requests."""
        if self.provider == "none":
            return False
        if self.provider == "ollama":
            return self._check_ollama(self.base_url)
        if self.provider in ("openai", "custom"):
            # openai needs a key; a custom endpoint may be a keyless local
            # server, so only its URL is required.
            if not self.base_url or (self.provider == "openai" and not self.api_key):
                return False
            try:
                _http_url(self.base_url)
            except ValueError:
                return False
            return True
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
            return self._call_openai_compat(prompt, system)
        except Exception as e:
            return LLMResponse(
                text="", model=self.model, provider=self.provider,
                success=False, error=_error_text(e),
            )

    def _call_ollama(self, prompt: str, system: str) -> LLMResponse:
        """Call Ollama local API."""
        base = _http_url(self.base_url or "").rstrip("/")
        url = f"{base}/api/generate"
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
            body = json.loads(_read_limited(resp).decode("utf-8"))

        return _completed(
            text=body.get("response") or "",
            model=body.get("model", self.model),
            provider="ollama",
            tokens_used=int(body.get("eval_count") or 0),
        )

    def _call_openai_compat(self, prompt: str, system: str) -> LLMResponse:
        """Call OpenAI-compatible chat completions API."""
        url = _openai_chat_url(self.base_url or "")
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
        req = urllib.request.Request(
            url, data=data, headers=self._build_headers(), method="POST"
        )

        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.loads(_read_limited(resp).decode("utf-8"))

        return self._parse_openai_response(body)

    def _build_headers(self) -> dict:
        """Request headers; Authorization only when there is a key.

        A bare ``Authorization: Bearer `` (empty key) is rejected by some
        keyless local servers and says nothing to the rest.
        """
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _parse_openai_response(self, body: dict) -> LLMResponse:
        """Turn a chat-completions body into an LLMResponse.

        No choices is a failure with its own message, not an empty success.
        """
        choices = body.get("choices") or []
        model = body.get("model", self.model)
        usage = body.get("usage") or {}
        tokens = int(usage.get("total_tokens") or 0)
        if not choices:
            return LLMResponse(
                text="", model=model, provider=self.provider,
                tokens_used=tokens, success=False,
                error="LLM returned no completion choices",
            )
        message = (choices[0] or {}).get("message") or {}
        return _completed(
            text=message.get("content") or "",
            model=model,
            provider=self.provider,
            tokens_used=tokens,
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
