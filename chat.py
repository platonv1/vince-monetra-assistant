"""Chat controller: wires normalization -> retrieval -> prompt -> LLM into
a single answer() call. Owns last_category derivation and the
no-confidence fallback. `answer(question, history) -> str` is the only
interface app.py is allowed to call — see ARCHITECTURE.md's boundary
contract. Retrieval internals (scores, matched keywords,
resolution_method) never cross into the returned string.
"""

import logging

from llm.provider import generate_response
from rag.loader import load_documents
from rag.prompt import build_prompt
from rag.retriever import retrieve

logger = logging.getLogger(__name__)

FALLBACK_MESSAGE = (
    "I don't have enough information in Vince's professional profile to answer that question."
)

LLM_ERROR_MESSAGE = "Something went wrong while generating a response. Please try again in a moment."

HISTORY_TURNS_FOR_PROMPT = 5

_DOCUMENTS = load_documents()


def _recover_last_category(history: list[tuple[str, str]]) -> str | None:
    """Re-derive last_category from the conversation so far.

    Gradio's chat function signature is (question, history) with no
    separate session-state parameter, and history is already
    session-scoped. Storing last_category in a module-level variable
    instead would leak one user's conversation topic into a concurrent
    user's follow-up resolution, so it's recomputed by replaying each
    prior turn through retrieve() in order, carrying last_category
    forward exactly as a live conversation would have.
    """
    last_category = None
    for user_turn, _ in history:
        result = retrieve(user_turn, _DOCUMENTS, last_category=last_category)
        last_category = result["last_category"]
    return last_category


def answer(question: str, history: list[tuple[str, str]]) -> str:
    last_category = _recover_last_category(history)
    result = retrieve(question, _DOCUMENTS, last_category=last_category)

    if not result["results"]:
        return FALLBACK_MESSAGE

    recent_history = history[-HISTORY_TURNS_FOR_PROMPT:]
    prompt = build_prompt(question, result["results"], recent_history)

    try:
        return generate_response(prompt)
    except Exception:
        # Broad catch is deliberate: this is the external-API boundary
        # (network errors, rate limits, auth failures, provider outages).
        # answer()'s contract is to always return a string, and the raw
        # exception could contain provider-internal detail that shouldn't
        # reach a user-facing response — so it's logged server-side only.
        logger.exception("LLM provider call failed")
        return LLM_ERROR_MESSAGE
