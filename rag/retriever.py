"""Vectorless retrieval: scores knowledge documents against a normalized
query and applies the confidence threshold. See RAG_DESIGN.md.

Term-matching contract (RAG_DESIGN.md describes this at the "found
anywhere in content" / "found in the doc's keywords list" level; this is
the concrete rule implemented here): a term is "found" in a text if it
appears as a whole word/phrase, case-insensitively — not a raw substring
(so the 2-letter term "ai" can't spuriously match inside "maintain"), and
not frequency-weighted (a term repeated 50 times still counts once).
"""

import os

from .normalizer import normalize_query, phrase_present

MIN_RETRIEVAL_SCORE = int(os.environ.get("MIN_RETRIEVAL_SCORE", "3"))
MAX_RESULTS = int(os.environ.get("MAX_RESULTS", "3"))

CONTENT_WEIGHT = 1
METADATA_WEIGHT = 2
CATEGORY_WEIGHT = 3


def _score(doc: dict, terms: set[str]) -> int:
    content = doc["content"].lower()
    keywords = [k.lower() for k in doc["keywords"]]

    unique_content_matches = sum(1 for term in terms if phrase_present(term, content))
    metadata_matches = sum(
        1 for term in terms if any(phrase_present(term, keyword) for keyword in keywords)
    )
    category_match = 1 if doc["category"] in terms else 0

    return (
        unique_content_matches * CONTENT_WEIGHT
        + metadata_matches * METADATA_WEIGHT
        + category_match * CATEGORY_WEIGHT
    )


def retrieve(query: str, documents: list[dict], last_category: str | None = None) -> dict:
    """Retrieve up to MAX_RESULTS documents relevant to `query`.

    `documents` must already be in the fixed category load order
    (experience, ai, rpa, banking — see loader.load_documents()) so that
    the stable sort below preserves that order as the tie-break.

    Returns {"results": list[dict], "resolution_method": str,
    "last_category": str | None}. `last_category` in the return value is
    the value chat.py should persist as session state for the next turn.
    """
    normalized = normalize_query(query)
    terms = normalized["terms"]

    scored = [(doc, _score(doc, terms)) for doc in documents]
    qualifying = [(doc, score) for doc, score in scored if score >= MIN_RETRIEVAL_SCORE]

    if qualifying:
        qualifying.sort(key=lambda pair: pair[1], reverse=True)
        results = [doc for doc, _ in qualifying[:MAX_RESULTS]]

        # "experience" is the generalist/fallback category — every other
        # category's overview also mentions "experience" once, so it can
        # tie for the top score on almost any single-category query. When
        # that happens, prefer the more specific tied category for
        # last_category, so a follow-up ("which tools did he use?")
        # resolves to the domain the user actually asked about rather
        # than the generalist doc that happened to tie it.
        top_score = qualifying[0][1]
        tied_at_top = [doc for doc, score in qualifying if score == top_score]
        specific_tied = [doc for doc in tied_at_top if doc["category"] != "experience"]
        top_category = specific_tied[0]["category"] if specific_tied else tied_at_top[0]["category"]

        return {
            "results": results,
            "resolution_method": "matched",
            "last_category": top_category,
        }

    if normalized["has_followup_reference"] and last_category:
        followup_doc = next((d for d in documents if d["category"] == last_category), None)
        if followup_doc:
            return {
                "results": [followup_doc],
                "resolution_method": "followup_reference",
                "last_category": last_category,
            }

    return {
        "results": [],
        "resolution_method": "none",
        "last_category": last_category,
    }
