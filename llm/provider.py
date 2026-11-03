"""Calls the configured LLM provider with the prompt assembled by
rag/prompt.py. No business logic, no retrieval — see ARCHITECTURE.md.

Swappable via LLM_PROVIDER (env var). "claude" and "gemini" are implemented;
any other value raises so the failure is explicit rather than silent.
"""

import os

import anthropic
from google import genai
from google.genai import types

DEFAULT_MODEL = "claude-opus-5"
DEFAULT_GEMINI_MODEL = "gemini-flash-latest"
MAX_TOKENS = 1024


def generate_response(prompt: dict) -> str:
    provider = os.environ.get("LLM_PROVIDER", "claude").lower()
    if provider == "claude":
        return _generate_with_claude(prompt)
    if provider == "gemini":
        return _generate_with_gemini(prompt)
    raise ValueError(f"Unsupported LLM_PROVIDER: {provider!r} (supported: 'claude', 'gemini')")


def _generate_with_claude(prompt: dict) -> str:
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        raise RuntimeError("LLM_API_KEY is not set")

    client = anthropic.Anthropic(api_key=api_key)
    model = os.environ.get("CLAUDE_MODEL", DEFAULT_MODEL)

    # This is grounded lookup-and-summarize over a handful of short knowledge
    # documents, not multi-step reasoning — low effort keeps cost/latency
    # down. Thinking stays on (adaptive, the Opus 5 default) rather than
    # being disabled, since disabling it can leak reasoning tags or emit
    # tool-call-shaped text into the response.
    response = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=prompt["system"],
        messages=prompt["messages"],
        output_config={"effort": "low"},
    )

    if response.stop_reason == "refusal":
        return "I'm not able to answer that."

    return next(block.text for block in response.content if block.type == "text")


def _generate_with_gemini(prompt: dict) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    client = genai.Client(api_key=api_key)
    model = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)

    # Gemini has no "system" role and calls the assistant turn "model" rather
    # than "assistant" — the provider-agnostic history built by rag/prompt.py
    # needs both translated before it reaches the API.
    contents = [
        types.Content(
            role="model" if message["role"] == "assistant" else "user",
            parts=[types.Part(text=message["content"])],
        )
        for message in prompt["messages"]
    ]

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=prompt["system"],
            max_output_tokens=MAX_TOKENS,
        ),
    )

    # Extract text parts directly rather than relying on the response.text
    # convenience accessor, which can raise if a candidate mixes in
    # non-text parts — mirrors the explicit block-type filtering on the
    # Claude path above.
    text = "".join(
        part.text
        for candidate in (response.candidates or [])
        for part in (candidate.content.parts or [])
        if getattr(part, "text", None)
    )

    if not text:
        return "I'm not able to answer that."

    return text
