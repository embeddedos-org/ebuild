# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Regression tests for the optional LLM client.

The hardware analyzer works offline. ``ebuild analyze --llm`` is the
opt-in path that actually calls a model, and it had no tests: a failed
call still printed success, availability always probed localhost, and
OpenAI-compatible base URLs that already ended in ``/v1`` 404'd.

Network is mocked at ``urllib.request.urlopen``. These tests must fail
if a future change reintroduces a real request, a ``file://`` fetch, or
a success report for an empty/failed response.
"""

from __future__ import annotations

import json
import urllib.error
from email.message import Message
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from ebuild.cli.commands import cli
from ebuild.eos_ai.eos_hw_analyzer import EosHardwareAnalyzer, HardwareProfile
from ebuild.eos_ai.llm_integration import (
    LLMClient,
    LLMResponse,
    MAX_LLM_RESPONSE_BYTES,
    _openai_chat_url,
)


pytestmark = pytest.mark.ebuild


def _cli_text(result) -> str:
    """Stdout plus stderr — Click 8.2 split them; 8.1 mixed them."""
    parts = [result.output or ""]
    stderr = getattr(result, "stderr", None)
    if stderr:
        parts.append(stderr)
    return "\n".join(parts)


def _response(payload, status=200):
    resp = MagicMock()
    resp.status = status
    if isinstance(payload, bytes):
        body = payload
    else:
        body = json.dumps(payload).encode("utf-8")
    resp.read.return_value = body
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    return resp


def _url_of(req) -> str:
    if isinstance(req, str):
        return req
    return req.full_url if hasattr(req, "full_url") else req.get_full_url()


class TestOllamaAvailability:
    def test_probes_the_configured_host_not_localhost(self):
        seen = []

        def fake_urlopen(req, timeout=None):
            seen.append(_url_of(req))
            return _response({"models": []})

        client = LLMClient(provider="ollama", base_url="http://gpu-box:11434")
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            assert client.is_available() is True

        assert seen == ["http://gpu-box:11434/api/tags"]

    def test_default_still_probes_localhost(self):
        seen = []

        def fake_urlopen(req, timeout=None):
            seen.append(_url_of(req))
            return _response({"models": []})

        client = LLMClient(provider="ollama")
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            assert client.is_available() is True

        assert seen == ["http://localhost:11434/api/tags"]

    def test_unreachable_ollama_is_unavailable(self):
        client = LLMClient(provider="ollama")
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            assert client.is_available() is False

    def test_non_200_ollama_is_unavailable(self):
        client = LLMClient(provider="ollama")
        with patch("urllib.request.urlopen", return_value=_response({}, status=500)):
            assert client.is_available() is False

    def test_file_url_is_not_available_and_does_not_open(self):
        client = LLMClient(provider="ollama", base_url="file:///etc/passwd")
        with patch("urllib.request.urlopen") as urlopen:
            assert client.is_available() is False
            urlopen.assert_not_called()


class TestOpenAIUrlJoin:
    @pytest.mark.parametrize(
        "base, expected",
        [
            ("https://api.openai.com", "https://api.openai.com/v1/chat/completions"),
            ("https://api.openai.com/", "https://api.openai.com/v1/chat/completions"),
            ("https://api.openai.com/v1", "https://api.openai.com/v1/chat/completions"),
            ("https://api.openai.com/v1/", "https://api.openai.com/v1/chat/completions"),
            (
                "https://api.groq.com/openai/v1",
                "https://api.groq.com/openai/v1/chat/completions",
            ),
        ],
    )
    def test_v1_is_not_doubled(self, base, expected):
        assert _openai_chat_url(base) == expected

    def test_analyze_posts_to_the_joined_url(self):
        seen = []

        def fake_urlopen(req, timeout=None):
            seen.append(_url_of(req))
            return _response(
                {
                    "choices": [{"message": {"content": "use FreeRTOS"}}],
                    "model": "gpt-4o-mini",
                    "usage": {"total_tokens": 9},
                }
            )

        client = LLMClient(
            provider="custom",
            model="gpt-4o-mini",
            api_key="sk-test",
            base_url="https://api.example.com/v1",
        )
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = client.analyze("nRF52840 with BLE")

        assert result.success is True
        assert result.text == "use FreeRTOS"
        assert seen == ["https://api.example.com/v1/chat/completions"]


class TestSchemeGuard:
    def test_file_url_does_not_reach_urlopen(self):
        client = LLMClient(
            provider="custom",
            api_key="sk-test",
            base_url="file:///C:/secrets/key.json",
        )
        with patch("urllib.request.urlopen") as urlopen:
            result = client.analyze("anything")
            urlopen.assert_not_called()

        assert result.success is False
        assert "http" in result.error.lower()

    def test_ftp_url_is_rejected(self):
        client = LLMClient(
            provider="custom",
            api_key="sk-test",
            base_url="ftp://files.example.com/model",
        )
        with patch("urllib.request.urlopen") as urlopen:
            result = client.analyze("anything")
            urlopen.assert_not_called()
        assert result.success is False

    def test_custom_file_url_is_not_available(self):
        client = LLMClient(
            provider="custom",
            api_key="sk-test",
            base_url="file:///etc/passwd",
        )
        assert client.is_available() is False


class TestAnalyzeContract:
    def test_provider_none_fails_without_network(self):
        client = LLMClient(provider="none", model="none")
        with patch("urllib.request.urlopen") as urlopen:
            result = client.analyze("hello")
            urlopen.assert_not_called()
        assert result.success is False
        assert result.provider == "none"

    def test_ollama_success(self):
        def fake_urlopen(req, timeout=None):
            return _response(
                {"response": "enable UART", "model": "llama3", "eval_count": 4}
            )

        client = LLMClient(provider="ollama")
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = client.analyze("STM32H7")
        assert result.success is True
        assert result.text == "enable UART"
        assert result.tokens_used == 4

    def test_empty_response_is_a_failure(self):
        client = LLMClient(
            provider="custom",
            api_key="sk-test",
            base_url="https://api.example.com",
        )
        with patch(
            "urllib.request.urlopen",
            return_value=_response({"choices": [{"message": {"content": "   "}}]}),
        ):
            result = client.analyze("STM32H7")
        assert result.success is False
        assert "empty" in result.error.lower()

    def test_http_401_is_a_failure_not_an_exception(self):
        err = urllib.error.HTTPError(
            "https://api.openai.com/v1/chat/completions",
            401,
            "Unauthorized",
            Message(),
            BytesIO(b'{"error":"invalid_api_key"}'),
        )
        client = LLMClient(provider="openai", api_key="sk-test")
        with patch("urllib.request.urlopen", side_effect=err):
            result = client.analyze("STM32H7")
        assert result.success is False
        assert "401" in result.error

    def test_oversized_body_is_rejected(self):
        huge = MagicMock()
        huge.status = 200
        huge.read.return_value = b"x" * (MAX_LLM_RESPONSE_BYTES + 2)
        huge.__enter__.return_value = huge
        huge.__exit__.return_value = False

        client = LLMClient(provider="ollama")
        with patch("urllib.request.urlopen", return_value=huge):
            result = client.analyze("STM32H7")
        assert result.success is False
        assert "exceeded" in result.error.lower()

    def test_error_text_does_not_echo_a_bearer_token(self):
        client = LLMClient(provider="openai", api_key="sk-live-secret")
        with patch(
            "urllib.request.urlopen",
            side_effect=RuntimeError("Authorization: Bearer sk-live-secret"),
        ):
            result = client.analyze("STM32H7")
        assert result.success is False
        assert "sk-live-secret" not in result.error
        assert "[redacted]" in result.error

    def test_openai_without_key_is_unavailable(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        client = LLMClient(provider="openai", api_key="")
        assert client.is_available() is False

    def test_unknown_provider_is_unavailable(self):
        client = LLMClient(provider="azure")
        assert client.is_available() is False

    def test_custom_system_prompt_is_forwarded(self):
        seen = []

        def fake_urlopen(req, timeout=None):
            body = json.loads(req.data.decode("utf-8"))
            seen.append(body["messages"][0]["content"])
            return _response(
                {"choices": [{"message": {"content": "ok"}}], "usage": {}}
            )

        client = LLMClient(
            provider="custom",
            api_key="sk-test",
            base_url="https://api.example.com",
        )
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = client.analyze("board", system="stay terse")
        assert result.success is True
        assert seen == ["stay terse"]

    def test_provider_info_covers_each_kind(self):
        assert "No LLM" in LLMClient(provider="none").get_provider_info()
        ollama = LLMClient(provider="ollama").get_provider_info()
        assert "Ollama" in ollama and "llama3" in ollama
        custom = LLMClient(
            provider="custom", api_key="k", base_url="https://x.example"
        ).get_provider_info()
        assert "custom" in custom and "https://x.example" in custom
        client = LLMClient(provider="openai", api_key="sk-live-secret")
        assert "sk-live-secret" not in client.get_provider_info()


class TestAutoDetect:
    def test_prefers_ollama_when_it_answers(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with patch.object(LLMClient, "_check_ollama", return_value=True):
            client = LLMClient.auto()
        assert client.provider == "ollama"

    def test_openai_when_ollama_is_down(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.delenv("EOS_LLM_API_KEY", raising=False)
        with patch.object(LLMClient, "_check_ollama", return_value=False):
            client = LLMClient.auto()
        assert client.provider == "openai"
        assert client.model == "gpt-4o-mini"

    def test_custom_env(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("EOS_LLM_API_KEY", "tok")
        monkeypatch.setenv("EOS_LLM_URL", "https://llm.internal")
        monkeypatch.setenv("EOS_LLM_MODEL", "local-7b")
        with patch.object(LLMClient, "_check_ollama", return_value=False):
            client = LLMClient.auto()
        assert client.provider == "custom"
        assert client.model == "local-7b"
        assert client.base_url == "https://llm.internal"

    def test_none_when_nothing_is_configured(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("EOS_LLM_API_KEY", raising=False)
        monkeypatch.delenv("EOS_LLM_URL", raising=False)
        with patch.object(LLMClient, "_check_ollama", return_value=False):
            client = LLMClient.auto()
        assert client.provider == "none"
        assert client.is_available() is False


class TestAnalyzeWithLlm:
    def test_failure_is_recorded_and_does_not_claim_analysis(self):
        analyzer = EosHardwareAnalyzer()
        fake = MagicMock()
        fake.is_available.return_value = True
        fake.provider = "openai"
        fake.analyze.return_value = LLMResponse(
            text="", model="x", provider="openai",
            success=False, error="HTTP Error 401: Unauthorized",
        )
        analyzer._llm_client = fake

        profile = HardwareProfile(mcu="STM32H7")
        out = analyzer.analyze_with_llm(profile)

        assert any(f.startswith("llm_failed:") for f in out.features)
        assert not any(f.startswith("llm_analyzed:") for f in out.features)
        fake.analyze.assert_called_once()

    def test_success_records_provider_and_can_add_peripherals(self):
        analyzer = EosHardwareAnalyzer()
        fake = MagicMock()
        fake.is_available.return_value = True
        fake.provider = "ollama"
        fake.analyze.return_value = LLMResponse(
            text="Recommend enabling CAN and USB.",
            model="llama3",
            provider="ollama",
            success=True,
        )
        analyzer._llm_client = fake

        profile = HardwareProfile(mcu="STM32H7")
        out = analyzer.analyze_with_llm(profile)

        assert "llm_analyzed:ollama" in out.features
        assert not any(f.startswith("llm_failed:") for f in out.features)
        types = {p.peripheral_type for p in out.peripherals}
        assert "can" in types
        assert "usb" in types

    def test_unavailable_client_is_a_noop(self):
        analyzer = EosHardwareAnalyzer()
        fake = MagicMock()
        fake.is_available.return_value = False
        analyzer._llm_client = fake

        profile = HardwareProfile(mcu="STM32H7")
        out = analyzer.analyze_with_llm(profile)
        fake.analyze.assert_not_called()
        assert out.features == []


class TestAnalyzeCliHonesty:
    def _run(self, tmp_path, available, features):
        llm_client = MagicMock()
        llm_client.is_available.return_value = available
        llm_client.get_provider_info.return_value = "OpenAI — model: gpt-4o-mini"
        llm_client.provider = "openai"

        def fake_analyze(profile):
            profile.features.extend(features)
            return profile

        argv = [
            "analyze",
            "STM32H7 with UART",
            "--output-dir",
            str(tmp_path),
            "--llm",
        ]
        runner = CliRunner()
        with patch.object(
            EosHardwareAnalyzer, "llm_client", llm_client
        ), patch.object(
            EosHardwareAnalyzer, "analyze_with_llm", side_effect=fake_analyze
        ):
            return runner.invoke(cli, argv)

    def test_failed_llm_does_not_print_success(self, tmp_path):
        result = self._run(tmp_path, available=True, features=["llm_failed:openai"])
        text = _cli_text(result)
        assert result.exit_code == 0, text
        assert "LLM analysis complete" not in text
        assert "did not complete" in text

    def test_successful_llm_still_prints_ok(self, tmp_path):
        result = self._run(tmp_path, available=True, features=["llm_analyzed:openai"])
        text = _cli_text(result)
        assert result.exit_code == 0, text
        assert "LLM analysis complete" in text
        assert "did not complete" not in text
