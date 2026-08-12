"""Gradio ChatInterface presentation layer.

Only calls chat.answer() — no RAG logic, no direct rag.* imports. See
CLAUDE.md / ARCHITECTURE.md's boundary contract.
"""

import os

import gradio as gr
import spaces
from dotenv import load_dotenv

load_dotenv()

import chat


@spaces.GPU
def _zero_gpu_startup_probe() -> None:
    # This app does no GPU work — the Space's hardware was auto-assigned
    # ZeroGPU with no CPU-basic option at creation, and ZeroGPU refuses to
    # start without at least one @spaces.GPU function present. Never called.
    pass

TITLE = "Vic AI Assistant"

DESCRIPTION = "Ask my AI Assistant about my career, experience, skills, and projects..."

SUGGESTED_QUESTIONS = [
    "What is Vince's experience?",
    "Does Vince have experience with AI?",
    "Tell me about his RPA experience.",
    "What banking projects has he worked on?",
]

UNEXPECTED_ERROR_MESSAGE = (
    "Sorry, something went wrong on this end. Please try asking again."
)


def _extract_text(content) -> str | None:
    """Pull plain text out of a Gradio message's `content` field.

    Gradio has shipped two shapes for this field: a plain string, and (as
    of Gradio 6) a list of content-part dicts like
    [{"type": "text", "text": "..."}]. Accept both so history parsing
    doesn't silently break on a Gradio version bump.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            part["text"]
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ]
        if parts:
            return "".join(parts)
    return None


def _history_to_turn_pairs(history: list[dict]) -> list[tuple[str, str]]:
    """Adapt Gradio's ChatInterface history — a list of {"role", "content"}
    dicts — into the (user, assistant) string pairs chat.answer() expects.
    Pure UI data-format plumbing, not RAG logic.
    """
    pairs = []
    pending_user = None
    for message in history:
        role = message.get("role")
        content = _extract_text(message.get("content"))
        if content is None:
            continue  # ignore non-text content; this chatbot is text-only
        if role == "user":
            pending_user = content
        elif role == "assistant" and pending_user is not None:
            pairs.append((pending_user, content))
            pending_user = None
    return pairs


def respond(message: str, history: list[dict]) -> str:
    try:
        return chat.answer(message, _history_to_turn_pairs(history))
    except Exception:
        # Defense in depth: chat.answer() already handles expected LLM
        # failures internally (see chat.py's LLM_ERROR_MESSAGE). This is
        # the last line of defense against anything unanticipated, so the
        # UI never shows a raw traceback to a visitor.
        return UNEXPECTED_ERROR_MESSAGE


demo = gr.ChatInterface(
    fn=respond,
    description=DESCRIPTION,
    examples=SUGGESTED_QUESTIONS,
    show_progress="full",
)
# Sets only the browser tab <title> — omitting title= above avoids Gradio
# also rendering it as a visible heading, which duplicated the embedding
# widget's own header on the website.
demo.title = TITLE

if __name__ == "__main__":
    # server_name/PORT binding is required on Render (and harmless on HF
    # Spaces, which doesn't set PORT and expects the 7860 default anyway).
    demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))
