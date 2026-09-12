# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Unit tests for LLMClient (ebuild.eos_ai.llm_integration).

All tests are pure Python with zero network calls — every outbound request
is intercepted by unittest.mock so the suite runs fully offline and is safe
to run in CI without credentials.

Coverage targets:
- URL normalisation (_normalize_openai_url, _ensure_scheme)
- Environment variable priority (OLLAMA_HOST, OPENAI_BASE_URL, OPENAI_MODEL, …)
- Authorization header behaviour (present ↔ absent)
- Response parsing (_parse_openai_response, including empty-choices guard)
- Provider auto-detection (LLMClient.auto())
- is_available() for every provider branch
- get_provider_info() formatting
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from ebuild.eos_ai.llm_integration import (
    LLMClient,
    _ensure_scheme,
    _normalize_openai_url,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Strip every LLM-related env var before each test for full isolation."""
    for var in (
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "OPENAI_MODEL",
        "OLLAMA_HOST",
        "OLLAMA_MODEL",
        "EOS_LLM_API_KEY",
        "EOS_LLM_URL",
        "EOS_LLM_MODEL",
    ):
        monkeypatch.delenv(var, raising=False)


# ── _normalize_openai_url ─────────────────────────────────────────────────────


class TestNormalizeOpenAIUrl:
    """_normalize_openai_url must produce exactly one /v1/chat/completions."""

    def test_base_domain_appends_full_path(self):
        assert _normalize_openai_url("https://api.openai.com") == (
            "https://api.openai.com/v1/chat/completions"
        )

    def test_versioned_base_no_double_v1(self):
        result = _normalize_openai_url("http://localhost:8000/v1")
        assert result == "http://localhost:8000/v1/chat/completions"
        assert "/v1/v1/" not in result

    def test_trailing_slash_stripped_then_path_appended(self):
        result = _normalize_openai_url("http://localhost:8000/v1/")
        assert result == "http://localhost:8000/v1/chat/completions"

    def test_full_url_is_idempotent(self):
        full = "http://localhost:8000/v1/chat/completions"
        assert _normalize_openai_url(full) == full

    def test_no_slash_domain(self):
        result = _normalize_openai_url("http://myproxy.internal")
        assert result.endswith("/v1/chat/completions")


# ── _ensure_scheme ────────────────────────────────────────────────────────────


class TestEnsureScheme:
    """_ensure_scheme must prepend http:// to schemeless hosts only."""

    def test_bare_host_port_gets_http(self):
        assert _ensure_scheme("192.168.1.50:11434") == "http://192.168.1.50:11434"

    def test_bare_hostname_gets_http(self):
        assert _ensure_scheme("myserver") == "http://myserver"

    def test_existing_http_preserved(self):
        assert _ensure_scheme("http://localhost:11434") == "http://localhost:11434"

    def test_existing_https_preserved(self):
        assert _ensure_scheme("https://secure-host:11434") == "https://secure-host:11434"


# ── LLMClient.__init__ — env var support ──────────────────────────────────────


class TestEnvVarSupport:
    """Constructor must read the documented environment variables."""

    def test_ollama_host_env_var(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_HOST", "http://remote-box:11434")
        client = LLMClient(provider="ollama")
        assert "remote-box" in client.base_url

    def test_ollama_host_bare_gets_scheme(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_HOST", "192.168.1.10:11434")
        client = LLMClient(provider="ollama")
        assert client.base_url.startswith("http://")

    def test_ollama_model_env_var(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_MODEL", "mistral")
        client = LLMClient(provider="ollama")
        assert client.model == "mistral"

    def test_openai_base_url_env_var(self, monkeypatch):
        monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:8000/v1")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        client = LLMClient(provider="openai")
        assert "localhost:8000" in (client.base_url or "")

    def test_openai_model_env_var(self, monkeypatch):
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4-turbo")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        client = LLMClient(provider="openai")
        assert client.model == "gpt-4-turbo"

    def test_eos_custom_env_vars(self, monkeypatch):
        monkeypatch.setenv("EOS_LLM_URL", "http://custom:9000")
        monkeypatch.setenv("EOS_LLM_API_KEY", "mykey")
        monkeypatch.setenv("EOS_LLM_MODEL", "phi3")
        client = LLMClient(provider="custom")
        assert client.base_url == "http://custom:9000"
        assert client.api_key == "mykey"
        assert client.model == "phi3"


# ── _build_headers — Authorization guard ──────────────────────────────────────


class TestBuildHeaders:
    """Authorization header must be absent when the API key is empty."""

    def test_empty_api_key_no_auth_header(self):
        """Local servers (vLLM, llama.cpp) must not receive an Authorization header."""
        client = LLMClient(provider="custom", base_url="http://localhost:8000", api_key="")
        headers = client._build_headers()
        assert "Authorization" not in headers

    def test_non_empty_api_key_sends_bearer(self):
        client = LLMClient(provider="openai", api_key="sk-abc123")
        headers = client._build_headers()
        assert headers.get("Authorization") == "Bearer sk-abc123"

    def test_content_type_always_present(self):
        client = LLMClient(provider="ollama")
        assert client._build_headers()["Content-Type"] == "application/json"


# ── _parse_openai_response ────────────────────────────────────────────────────


class TestParseOpenAIResponse:
    """_parse_openai_response must guard against empty/missing choices."""

    def _make_client(self) -> LLMClient:
        return LLMClient(provider="openai", api_key="sk-test")

    def test_empty_choices_returns_failure(self):
        """An empty choices list must not raise IndexError and must be success=False."""
        client = self._make_client()
        body = {"choices": [], "model": "gpt-4o", "usage": {"total_tokens": 0}}
        resp = client._parse_openai_response(body)
        assert resp.success is False
        assert "no completion" in resp.error.lower()

    def test_empty_content_returns_failure(self):
        client = self._make_client()
        body = {
            "choices": [{"message": {"content": ""}}],
            "model": "gpt-4o",
            "usage": {},
        }
        resp = client._parse_openai_response(body)
        assert resp.success is False

    def test_valid_response_parsed_correctly(self):
        client = self._make_client()
        body = {
            "choices": [{"message": {"content": "STM32H7 with UART detected"}}],
            "model": "gpt-4o",
            "usage": {"total_tokens": 42},
        }
        resp = client._parse_openai_response(body)
        assert resp.success is True
        assert resp.text == "STM32H7 with UART detected"
        assert resp.tokens_used == 42
        assert resp.model == "gpt-4o"

    def test_missing_choices_key_returns_failure(self):
        client = self._make_client()
        body = {"model": "gpt-4o"}  # no 'choices' key at all
        resp = client._parse_openai_response(body)
        assert resp.success is False


# ── LLMClient.auto() ──────────────────────────────────────────────────────────


class TestAutoDetect:
    """auto() must select providers in documented priority order."""

    def test_auto_prefers_ollama_when_available(self):
        with patch.object(LLMClient, "_check_ollama", return_value=True):
            client = LLMClient.auto()
        assert client.provider == "ollama"

    def test_auto_picks_openai_when_ollama_unavailable(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        with patch.object(LLMClient, "_check_ollama", return_value=False):
            client = LLMClient.auto()
        assert client.provider == "openai"

    def test_auto_picks_custom_when_no_ollama_no_openai(self, monkeypatch):
        monkeypatch.setenv("EOS_LLM_API_KEY", "mykey")
        monkeypatch.setenv("EOS_LLM_URL", "http://custom:9000")
        with patch.object(LLMClient, "_check_ollama", return_value=False):
            client = LLMClient.auto()
        assert client.provider == "custom"

    def test_auto_returns_none_when_nothing_available(self):
        with patch.object(LLMClient, "_check_ollama", return_value=False):
            client = LLMClient.auto()
        assert client.provider == "none"

    def test_auto_respects_ollama_model_env_var(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_MODEL", "phi3")
        with patch.object(LLMClient, "_check_ollama", return_value=True):
            client = LLMClient.auto()
        assert client.model == "phi3"


# ── is_available() ────────────────────────────────────────────────────────────


class TestIsAvailable:

    def test_none_provider_not_available(self):
        client = LLMClient(provider="none")
        assert client.is_available() is False

    def test_openai_with_key_and_url_is_available(self):
        client = LLMClient(provider="openai", api_key="sk-x", base_url="https://api.openai.com")
        assert client.is_available() is True

    def test_openai_without_key_not_available(self):
        client = LLMClient(provider="openai", api_key="", base_url="https://api.openai.com")
        assert client.is_available() is False

    def test_ollama_availability_delegates_to_check(self):
        client = LLMClient(provider="ollama")
        with patch.object(LLMClient, "_check_ollama", return_value=True):
            assert client.is_available() is True
        with patch.object(LLMClient, "_check_ollama", return_value=False):
            assert client.is_available() is False


# ── analyze() — no provider ───────────────────────────────────────────────────


class TestAnalyzeNoProvider:

    def test_none_provider_returns_graceful_failure(self):
        client = LLMClient(provider="none")
        resp = client.analyze("describe this hardware")
        assert resp.success is False
        assert resp.text == ""
        assert "no llm provider" in resp.error.lower()


# ── get_provider_info() ───────────────────────────────────────────────────────


class TestGetProviderInfo:

    def test_none_provider_info(self):
        assert "No LLM" in LLMClient(provider="none").get_provider_info()

    def test_ollama_provider_info_contains_model(self):
        client = LLMClient(provider="ollama", model="llama3")
        info = client.get_provider_info()
        assert "llama3" in info
        assert "Ollama" in info

    def test_openai_provider_info(self):
        client = LLMClient(provider="openai", model="gpt-4o", api_key="sk-x")
        info = client.get_provider_info()
        assert "OpenAI" in info
        assert "gpt-4o" in info
