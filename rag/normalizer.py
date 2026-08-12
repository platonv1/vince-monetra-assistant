"""Query normalization: builds the normalized term set and detects
follow-up pronoun references. See RAG_DESIGN.md "Query normalization".
"""

import re

SYNONYM_GROUPS = {
    "experience": ["background", "career", "professional experience"],
    "ai": ["artificial intelligence", "llm", "large language model"],
    "rpa": ["robotic process automation", "automation"],
    "banking": ["financial services", "finance"],
}

FOLLOWUP_PRONOUNS = {
    "he", "him", "his", "she", "her", "hers",
    "it", "its", "they", "them", "their", "theirs",
    "this", "that", "these", "those",
}

# Function words excluded from the scoring term set: left in an unfiltered
# query they'd match nearly every document's prose (e.g. "the", "with"),
# collapsing the confidence threshold's ability to reject irrelevant
# queries. Pronouns are stopwords for scoring but are still read for
# has_followup_reference below, from the token set before this filter runs.
STOPWORDS = {
    "a", "an", "the",
    "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "doing",
    "have", "has", "had", "having",
    "what", "which", "who", "whom", "whose", "when", "where", "why", "how",
    "with", "about", "of", "in", "on", "at", "to", "for", "from", "by", "as",
    "and", "or", "but", "if", "so", "than", "then",
    "i", "me", "my", "we", "us", "our", "you", "your", "yours",
} | FOLLOWUP_PRONOUNS

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def phrase_present(phrase: str, text: str) -> bool:
    """Whole-word/phrase, case-insensitive presence check."""
    return re.search(rf"\b{re.escape(phrase.lower())}\b", text.lower()) is not None


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def normalize_query(query: str) -> dict:
    """Returns {"terms": set[str], "has_followup_reference": bool}.

    `terms` is the normalized term set used for scoring: lowercase query
    tokens, minus stopwords and single-character noise, plus the
    canonical category name for every recognized synonym phrase found in
    the raw query. Synonym groups are disjoint (one canonical category per
    group), so a synonym can only ever add its own category's name.

    `has_followup_reference` is computed from the unfiltered token set,
    independent of stopword removal, since pronouns are stopwords for
    scoring but signal-bearing for follow-up detection.
    """
    lowered = query.lower()
    raw_tokens = set(_tokenize(lowered))

    has_followup_reference = bool(raw_tokens & FOLLOWUP_PRONOUNS)

    terms = {token for token in raw_tokens if token not in STOPWORDS and len(token) > 1}

    for category, synonyms in SYNONYM_GROUPS.items():
        for synonym in synonyms:
            if phrase_present(synonym, lowered):
                terms.add(category)

    return {"terms": terms, "has_followup_reference": has_followup_reference}
