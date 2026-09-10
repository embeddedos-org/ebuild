# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Unit tests for ebuild EoS AI LLM integration.

Tests LLMClient initialization, base URL normalization, provider auto-detection,
availability checks, Ollama/OpenAI dispatch payloads, error resilience, and
integration with EosHardwareAnalyzer.
"""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
from unittest.mock import MagicMock, patch

import pytest

from ebuild.eos_ai.eos_hw_analyzer import EosHardwareAnalyzer, HardwareProfile, PeripheralInfo
from ebuild.eos_ai.llm_integration import LLMClient, LLMResponse


class MockHTTPResponse:
    """Mock urllib response object."""

    def __init__(self, data: dict | bytes, status: int = 200):
        self.status = status
        if isinstance(data, dict):
            self._raw = json.dumps(data).encode("utf-8")
        else:
            self._raw = data

    def read(self) -> bytes:
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.mark.ebuild
class TestLLMClientInitAndConfig:
    """Tests for LLMClient initialization and configuration."""

    def test_default_init(self):
        client = LLMClient()
        assert client.provider == "ollama"
        assert client.model == "llama3"
        assert client.base_url == "http://localhost:11434"
        assert client.timeout == 120

    def test_init_strips_trailing_slash_from_base_url(self):
        client_ollama = LLMClient(provider="ollama", base_url="http://localhost:11434/")
        assert client_ollama.base_url == "http://localhost:11434"

        client_openai = LLMClient(
            provider="openai",
            base_url="https://api.openai.com/v1/",
            api_key="sk-test",
        )
        assert client_openai.base_url == "https://api.openai.com/v1"

    def test_custom_provider_init(self):
        client = LLMClient(
            provider="custom",
            model="mistral-7b",
            base_url="http://192.168.1.100:8000/v1/",
            api_key="local-key",
            timeout=30,
        )
        assert client.provider == "custom"
        assert client.model == "mistral-7b"
        assert client.base_url == "http://192.168.1.100:8000/v1"
        assert client.api_key == "local-key"
        assert client.timeout == 30

    def test_get_provider_info(self):
        assert LLMClient(provider="none").get_provider_info() == "No LLM provider configured"

        ollama = LLMClient(provider="ollama", model="llama3", base_url="http://localhost:11434")
        assert "Ollama (local) — model: llama3" in ollama.get_provider_info()

        openai = LLMClient(provider="openai", model="gpt-4o")
        assert openai.get_provider_info() == "OpenAI — model: gpt-4o"

        custom = LLMClient(provider="custom", model="qwen", base_url="http://localhost:8000/v1")
        assert "custom — model: qwen — http://localhost:8000/v1" in custom.get_provider_info()


@pytest.mark.ebuild
class TestURLNormalization:
    """Tests for URL normalization across Ollama and OpenAI-compatible endpoints."""

    def test_normalize_ollama_urls(self):
        expected = "http://localhost:11434/api/generate"
        assert LLMClient._normalize_ollama_url("http://localhost:11434") == expected
        assert LLMClient._normalize_ollama_url("http://localhost:11434/") == expected
        assert LLMClient._normalize_ollama_url("http://localhost:11434/api/generate") == expected

    def test_normalize_openai_urls(self):
        expected = "https://api.openai.com/v1/chat/completions"
        assert LLMClient._normalize_openai_url("https://api.openai.com") == expected
        assert LLMClient._normalize_openai_url("https://api.openai.com/") == expected
        assert LLMClient._normalize_openai_url("https://api.openai.com/v1") == expected
        assert LLMClient._normalize_openai_url("https://api.openai.com/v1/") == expected

        expected_local = "http://localhost:8000/v1/chat/completions"
        assert LLMClient._normalize_openai_url("http://localhost:8000/v1") == expected_local
        assert LLMClient._normalize_openai_url("http://localhost:8000/v1/chat/completions") == expected_local


@pytest.mark.ebuild
class TestAutoDetectionAndAvailability:
    """Tests for provider auto-detection priority and availability checking."""

    def test_auto_detect_prefers_ollama_if_online(self):
        with patch.object(LLMClient, "_check_ollama", return_value=True):
            client = LLMClient.auto()
            assert client.provider == "ollama"
            assert client.model == "llama3"

    def test_auto_detect_falls_back_to_openai_if_ollama_offline(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-12345")
        with patch.object(LLMClient, "_check_ollama", return_value=False):
            client = LLMClient.auto()
            assert client.provider == "openai"
            assert client.model == "gpt-4o-mini"
            assert client.api_key == "sk-test-key-12345"

    def test_auto_detect_falls_back_to_custom_url(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("EOS_LLM_URL", "http://localhost:8000/v1")
        monkeypatch.setenv("EOS_LLM_MODEL", "qwen-coder")
        with patch.object(LLMClient, "_check_ollama", return_value=False):
            client = LLMClient.auto()
            assert client.provider == "custom"
            assert client.model == "qwen-coder"
            assert client.base_url == "http://localhost:8000/v1"

    def test_auto_detect_returns_none_when_no_provider(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("EOS_LLM_URL", raising=False)
        with patch.object(LLMClient, "_check_ollama", return_value=False):
            client = LLMClient.auto()
            assert client.provider == "none"
            assert client.model == "none"
            assert client.is_available() is False

    def test_is_available_logic(self):
        # none provider
        none_client = LLMClient(provider="none")
        assert none_client.is_available() is False

        # ollama provider calls check_ollama with target base_url
        with patch.object(LLMClient, "_check_ollama") as mock_check:
            mock_check.return_value = True
            ollama = LLMClient(provider="ollama", base_url="http://remote-ollama:11434")
            assert ollama.is_available() is True
            mock_check.assert_called_once_with("http://remote-ollama:11434")

        # openai requires key and base_url
        openai_no_key = LLMClient(provider="openai", api_key="")
        assert openai_no_key.is_available() is False
        openai_with_key = LLMClient(provider="openai", api_key="sk-test")
        assert openai_with_key.is_available() is True

        # custom provider works with base_url even without key (local vLLM/Ollama)
        custom_no_key = LLMClient(provider="custom", base_url="http://localhost:8000/v1", api_key="")
        assert custom_no_key.is_available() is True

        custom_empty_url = LLMClient(provider="custom", base_url="", api_key="key")
        assert custom_empty_url.is_available() is False

    def test_check_ollama_handles_tags_endpoint(self):
        # Verify request is made to /api/tags
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = MockHTTPResponse({"models": []}, status=200)
            assert LLMClient._check_ollama("http://localhost:11434/") is True
            req = mock_urlopen.call_args[0][0]
            assert req.full_url == "http://localhost:11434/api/tags"

        # Verify network failure returns False gracefully
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Refused")):
            assert LLMClient._check_ollama("http://localhost:11434") is False


@pytest.mark.ebuild
class TestOllamaDispatch:
    """Tests for Ollama API call construction and response parsing."""

    def test_ollama_successful_call(self):
        client = LLMClient(provider="ollama", model="llama3", base_url="http://localhost:11434/")
        mock_response_body = {
            "model": "llama3",
            "response": "Recommendation: Enable UART and CAN.",
            "eval_count": 84,
            "done": True,
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = MockHTTPResponse(mock_response_body)

            resp = client.analyze(prompt="STM32H7 board", system="Hardware system prompt")

            assert resp.success is True
            assert resp.text == "Recommendation: Enable UART and CAN."
            assert resp.model == "llama3"
            assert resp.provider == "ollama"
            assert resp.tokens_used == 84
            assert resp.error == ""

            # Check outbound request
            req = mock_urlopen.call_args[0][0]
            assert req.full_url == "http://localhost:11434/api/generate"
            assert req.headers["Content-type"] == "application/json"

            payload = json.loads(req.data.decode("utf-8"))
            assert payload["model"] == "llama3"
            assert payload["prompt"] == "STM32H7 board"
            assert payload["system"] == "Hardware system prompt"
            assert payload["stream"] is False


@pytest.mark.ebuild
class TestOpenAICompatDispatch:
    """Tests for OpenAI-compatible API call construction and response parsing."""

    def test_openai_successful_call(self):
        client = LLMClient(
            provider="openai",
            model="gpt-4o",
            api_key="sk-test-secret",
            base_url="https://api.openai.com/v1/",
        )
        mock_response_body = {
            "id": "chatcmpl-123",
            "model": "gpt-4o",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Recommended EOS config: enable Ethernet and I2C.",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 50,
                "completion_tokens": 30,
                "total_tokens": 80,
            },
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = MockHTTPResponse(mock_response_body)

            resp = client.analyze(prompt="Analyze NRF52840", system="System prompt")

            assert resp.success is True
            assert resp.text == "Recommended EOS config: enable Ethernet and I2C."
            assert resp.model == "gpt-4o"
            assert resp.provider == "openai"
            assert resp.tokens_used == 80
            assert resp.error == ""

            # Check outbound request URL & headers
            req = mock_urlopen.call_args[0][0]
            assert req.full_url == "https://api.openai.com/v1/chat/completions"
            assert req.headers["Authorization"] == "Bearer sk-test-secret"
            assert req.headers["Content-type"] == "application/json"

            payload = json.loads(req.data.decode("utf-8"))
            assert payload["model"] == "gpt-4o"
            assert payload["temperature"] == 0.3
            assert payload["max_tokens"] == 4096
            assert payload["messages"] == [
                {"role": "system", "content": "System prompt"},
                {"role": "user", "content": "Analyze NRF52840"},
            ]

    def test_custom_endpoint_omits_bearer_header_when_api_key_empty(self):
        client = LLMClient(
            provider="custom",
            model="local-model",
            base_url="http://localhost:8000/v1",
            api_key="",
        )
        mock_response = {
            "choices": [{"message": {"content": "Local output"}}],
            "usage": {"total_tokens": 10},
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = MockHTTPResponse(mock_response)
            resp = client.analyze("Hardware prompt")

            assert resp.success is True
            assert resp.text == "Local output"

            req = mock_urlopen.call_args[0][0]
            assert req.full_url == "http://localhost:8000/v1/chat/completions"
            assert "Authorization" not in req.headers


@pytest.mark.ebuild
class TestErrorResilienceAndEdgeCases:
    """Tests for edge cases, malformed payloads, and network error handling."""

    def test_analyze_when_provider_none(self):
        client = LLMClient(provider="none")
        resp = client.analyze("Test prompt")
        assert resp.success is False
        assert "No LLM provider available" in resp.error
        assert resp.text == ""

    def test_empty_choices_handled_safely_without_index_error(self):
        client = LLMClient(provider="openai", api_key="sk-test")
        empty_choices_body = {"id": "test", "choices": [], "usage": {}}

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = MockHTTPResponse(empty_choices_body)
            resp = client.analyze("Prompt")

            assert resp.success is True
            assert resp.text == ""

    def test_json_error_payload_in_response(self):
        client = LLMClient(provider="openai", api_key="sk-test")
        error_payload = {
            "error": {
                "message": "The model `gpt-4o-unknown` does not exist",
                "type": "invalid_request_error",
            }
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = MockHTTPResponse(error_payload)
            resp = client.analyze("Prompt")

            assert resp.success is False
            assert "The model `gpt-4o-unknown` does not exist" in resp.error

    def test_http_error_decodes_json_message(self):
        client = LLMClient(provider="openai", api_key="sk-test")
        err_json = json.dumps({"error": {"message": "Incorrect API key provided"}}).encode("utf-8")
        http_err = urllib.error.HTTPError(
            url="https://api.openai.com/v1/chat/completions",
            code=401,
            msg="Unauthorized",
            hdrs={},  # type: ignore[arg-type]
            fp=io.BytesIO(err_json),
        )

        with patch("urllib.request.urlopen", side_effect=http_err):
            resp = client.analyze("Prompt")

            assert resp.success is False
            assert "HTTP 401: Incorrect API key provided" in resp.error

    def test_http_error_fallback_when_plain_text(self):
        client = LLMClient(provider="openai", api_key="sk-test")
        http_err = urllib.error.HTTPError(
            url="https://api.openai.com/v1/chat/completions",
            code=502,
            msg="Bad Gateway",
            hdrs={},  # type: ignore[arg-type]
            fp=io.BytesIO(b"<html>502 Bad Gateway</html>"),
        )

        with patch("urllib.request.urlopen", side_effect=http_err):
            resp = client.analyze("Prompt")

            assert resp.success is False
            assert "HTTP 502: <html>502 Bad Gateway</html>" in resp.error

    def test_network_connection_error(self):
        client = LLMClient(provider="ollama", base_url="http://localhost:11434")
        url_err = urllib.error.URLError(reason="Connection refused")

        with patch("urllib.request.urlopen", side_effect=url_err):
            resp = client.analyze("Prompt")

            assert resp.success is False
            assert "Connection error: Connection refused" in resp.error

    def test_timeout_error_direct(self):
        client = LLMClient(provider="ollama", timeout=45)

        with patch("urllib.request.urlopen", side_effect=TimeoutError()):
            resp = client.analyze("Prompt")

            assert resp.success is False
            assert "Request timed out after 45s" in resp.error

    def test_timeout_error_wrapped_in_urlerror(self):
        client = LLMClient(provider="openai", api_key="sk-test", timeout=60)
        url_err = urllib.error.URLError(reason=TimeoutError())

        with patch("urllib.request.urlopen", side_effect=url_err):
            resp = client.analyze("Prompt")

            assert resp.success is False
            assert "Request timed out after 60s" in resp.error


@pytest.mark.ebuild
class TestHardwareAnalyzerIntegrationWithLLM:
    """Integration test between EosHardwareAnalyzer and LLMClient."""

    def test_analyzer_enriches_profile_when_llm_suggests_peripherals(self):
        analyzer = EosHardwareAnalyzer()
        base_profile = HardwareProfile(
            mcu="STM32F4",
            arch="arm",
            core="cortex-m4",
            confidence=0.8,
        )
        base_profile.peripherals.append(PeripheralInfo(name="UART1", peripheral_type="uart"))

        mock_client = MagicMock(spec=LLMClient)
        mock_client.is_available.return_value = True
        mock_client.provider = "ollama"
        mock_client.analyze.return_value = LLMResponse(
            text="Recommend enabling ethernet and spi for this device.",
            model="llama3",
            provider="ollama",
            success=True,
        )

        analyzer._llm_client = mock_client
        enriched = analyzer.analyze_with_llm(base_profile)

        assert enriched.has_peripheral("uart")
        assert enriched.has_peripheral("ethernet")
        assert enriched.has_peripheral("spi")
        assert "llm_analyzed:ollama" in enriched.features
        assert enriched.confidence == 0.9

    def test_analyzer_unchanged_when_llm_fails(self):
        analyzer = EosHardwareAnalyzer()
        base_profile = HardwareProfile(
            mcu="STM32F4",
            arch="arm",
            core="cortex-m4",
            confidence=0.8,
        )

        mock_client = MagicMock(spec=LLMClient)
        mock_client.is_available.return_value = True
        mock_client.analyze.return_value = LLMResponse(
            text="",
            model="llama3",
            provider="ollama",
            success=False,
            error="Connection refused",
        )

        analyzer._llm_client = mock_client
        result = analyzer.analyze_with_llm(base_profile)

        assert result.confidence == 0.8
        assert "llm_analyzed" not in "".join(result.features)

    def test_analyze_uses_default_system_prompt_when_none_provided(self):
        client = LLMClient(provider="ollama")
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = MockHTTPResponse({"response": "ok"})
            resp = client.analyze("Test prompt")
            assert resp.success is True

            req = mock_urlopen.call_args[0][0]
            payload = json.loads(req.data.decode("utf-8"))
            assert "embedded systems hardware expert" in payload["system"]

    def test_http_error_with_top_level_message_field(self):
        client = LLMClient(provider="openai", api_key="sk-test")
        err_json = json.dumps({"message": "Rate limit exceeded"}).encode("utf-8")
        http_err = urllib.error.HTTPError(
            url="https://api.openai.com/v1/chat/completions",
            code=429,
            msg="Too Many Requests",
            hdrs={},  # type: ignore[arg-type]
            fp=io.BytesIO(err_json),
        )

        with patch("urllib.request.urlopen", side_effect=http_err):
            resp = client.analyze("Prompt")
            assert resp.success is False
            assert "HTTP 429: Rate limit exceeded" in resp.error

    def test_check_ollama_endpoint_variants(self):
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = MockHTTPResponse({"models": []})

            # URL already ending in /api/generate
            assert LLMClient._check_ollama("http://localhost:11434/api/generate") is True
            req = mock_urlopen.call_args[0][0]
            assert req.full_url == "http://localhost:11434/api/tags"

            # URL already ending in /api/tags
            assert LLMClient._check_ollama("http://localhost:11434/api/tags") is True
            req = mock_urlopen.call_args[0][0]
            assert req.full_url == "http://localhost:11434/api/tags"

    def test_analyze_catches_generic_exception(self):
        client = LLMClient(provider="ollama")
        with patch("urllib.request.urlopen", side_effect=ValueError("Unexpected internal failure")):
            resp = client.analyze("Prompt")
            assert resp.success is False
            assert "Unexpected internal failure" in resp.error

    def test_openai_respects_openai_base_url_env_var(self, monkeypatch):
        monkeypatch.setenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1/")
        monkeypatch.setenv("OPENAI_API_KEY", "gsk-test")
        client = LLMClient(provider="openai")
        assert client.base_url == "https://api.groq.com/openai/v1"

        with patch.object(LLMClient, "_check_ollama", return_value=False):
            auto_client = LLMClient.auto()
            assert auto_client.provider == "openai"
            assert auto_client.base_url == "https://api.groq.com/openai/v1"

    def test_ollama_respects_ollama_host_env_var(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_HOST", "192.168.1.50:11434/")
        client = LLMClient(provider="ollama")
        assert client.base_url == "http://192.168.1.50:11434"

    def test_dispatch_non_dict_json_response(self):
        client = LLMClient(provider="ollama")
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = MockHTTPResponse(b'["unexpected", "list"]')
            resp = client.analyze("Prompt")
            assert resp.success is False
            assert "Invalid JSON response: expected object" in resp.error

        openai_client = LLMClient(provider="openai", api_key="sk-test")
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = MockHTTPResponse(b'["unexpected", "list"]')
            resp = openai_client.analyze("Prompt")
            assert resp.success is False
            assert "Invalid JSON response: expected object" in resp.error
