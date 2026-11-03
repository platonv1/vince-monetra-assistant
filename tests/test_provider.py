from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from llm.provider import generate_response

PROMPT = {"system": "You are helpful.", "messages": [{"role": "user", "content": "Hi"}]}


def _claude_response(stop_reason="end_turn", blocks=None):
    blocks = blocks if blocks is not None else [SimpleNamespace(type="text", text="Hello.")]
    return SimpleNamespace(stop_reason=stop_reason, content=blocks)


def _gemini_response(parts_by_candidate=None):
    if parts_by_candidate is None:
        parts_by_candidate = [["Hello."]]
    candidates = [
        SimpleNamespace(content=SimpleNamespace(parts=[SimpleNamespace(text=t) for t in parts]))
        for parts in parts_by_candidate
    ]
    return SimpleNamespace(candidates=candidates)


def test_unsupported_provider_raises(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "unsupported")
    with pytest.raises(ValueError):
        generate_response(PROMPT)


def test_claude_missing_api_key_raises(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "claude")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        generate_response(PROMPT)


def test_gemini_missing_api_key_raises(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        generate_response(PROMPT)


def test_claude_refusal_returns_canned_message(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "claude")
    monkeypatch.setenv("LLM_API_KEY", "test-key")

    mock_client = MagicMock()
    mock_client.messages.create.return_value = _claude_response(stop_reason="refusal")

    with patch("llm.provider.anthropic.Anthropic", return_value=mock_client):
        result = generate_response(PROMPT)

    assert result == "I'm not able to answer that."


def test_claude_extracts_only_text_blocks(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "claude")
    monkeypatch.setenv("LLM_API_KEY", "test-key")

    blocks = [
        SimpleNamespace(type="thinking", text="internal reasoning"),
        SimpleNamespace(type="text", text="He used UiPath."),
    ]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _claude_response(blocks=blocks)

    with patch("llm.provider.anthropic.Anthropic", return_value=mock_client):
        result = generate_response(PROMPT)

    assert result == "He used UiPath."


def test_gemini_extracts_text_from_parts(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _gemini_response(
        parts_by_candidate=[["Hello ", "world."]]
    )

    with patch("llm.provider.genai.Client", return_value=mock_client):
        result = generate_response(PROMPT)

    assert result == "Hello world."


def test_gemini_empty_response_returns_canned_message(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _gemini_response(parts_by_candidate=[])

    with patch("llm.provider.genai.Client", return_value=mock_client):
        result = generate_response(PROMPT)

    assert result == "I'm not able to answer that."
