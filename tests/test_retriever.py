import pytest

from rag.loader import load_documents
from rag.retriever import MAX_RESULTS, retrieve

CANONICAL_QUESTIONS = {
    "experience": "What is Vince's experience?",
    "ai": "Does Vince have experience with AI?",
    "rpa": "Tell me about his RPA experience.",
    "banking": "What banking projects has he worked on?",
}

WORDING_VARIANTS = [
    ("experience", "Can you summarize Vince's professional background?"),
    ("experience", "How many years of experience does Vince have?"),
    ("experience", "What is Vince's career background?"),
    ("ai", "Has Vince worked with artificial intelligence?"),
    ("ai", "Does Vince have LLM experience?"),
    ("ai", "What AI technologies has Vince used?"),
    ("rpa", "What robotic process automation experience does Vince have?"),
    ("rpa", "What automation tools has Vince used?"),
    ("banking", "What financial services experience does Vince have?"),
    ("banking", "Tell me about Vince's banking background."),
]


@pytest.fixture(scope="module")
def documents():
    return load_documents()


@pytest.mark.parametrize("category,question", CANONICAL_QUESTIONS.items())
def test_canonical_question_matches_correct_category(documents, category, question):
    result = retrieve(question, documents)
    assert result["resolution_method"] == "matched"
    categories = [doc["category"] for doc in result["results"]]
    assert category in categories


@pytest.mark.parametrize("category,question", WORDING_VARIANTS)
def test_wording_variant_matches_correct_category(documents, category, question):
    result = retrieve(question, documents)
    assert result["resolution_method"] == "matched"
    assert category in [doc["category"] for doc in result["results"]]


def test_unrelated_question_returns_no_results(documents):
    result = retrieve("What's the weather like today?", documents)
    assert result["results"] == []
    assert result["resolution_method"] == "none"


def test_empty_question_returns_no_results(documents):
    result = retrieve("", documents)
    assert result["results"] == []
    assert result["resolution_method"] == "none"


def test_two_category_question_returns_both_docs(documents):
    result = retrieve("AI and RPA experience", documents)
    categories = [doc["category"] for doc in result["results"]]
    assert "ai" in categories
    assert "rpa" in categories


def test_repeated_keyword_does_not_outscore_distinct_single_match():
    keywords = ["rpa", "uipath"]
    repeats_one_keyword = {
        "category": "rpa",
        "title": "Repeats one keyword",
        "keywords": keywords,
        "content": "rpa " * 50,
    }
    matches_two_keywords_once_each = {
        "category": "rpa",
        "title": "Matches two keywords once each",
        "keywords": keywords,
        "content": "rpa uipath",
    }

    result = retrieve("rpa uipath", [repeats_one_keyword, matches_two_keywords_once_each])

    titles = [doc["title"] for doc in result["results"]]
    assert titles.index("Matches two keywords once each") < titles.index("Repeats one keyword")


def test_tie_break_and_truncation_preserve_fixed_category_load_order():
    docs = [
        {"category": "experience", "title": "Experience doc", "keywords": ["experience"], "content": "experience"},
        {"category": "ai", "title": "AI doc", "keywords": ["ai"], "content": "ai"},
        {"category": "rpa", "title": "RPA doc", "keywords": ["rpa"], "content": "rpa"},
        {"category": "banking", "title": "Banking doc", "keywords": ["banking"], "content": "banking"},
    ]

    result = retrieve("experience ai rpa banking", docs)

    expected = ["experience", "ai", "rpa", "banking"][:MAX_RESULTS]
    assert [doc["category"] for doc in result["results"]] == expected


def test_score_one_below_threshold_excluded_score_at_threshold_included():
    below_threshold_doc = {
        "category": "rpa",
        "title": "Below threshold",
        "keywords": ["rpa"],
        "content": "foo bar",
    }
    at_threshold_doc = {
        "category": "rpa",
        "title": "At threshold",
        "keywords": ["rpa"],
        "content": "foo bar baz",
    }

    result = retrieve("foo bar baz", [below_threshold_doc, at_threshold_doc])

    titles = [doc["title"] for doc in result["results"]]
    assert "At threshold" in titles
    assert "Below threshold" not in titles


def test_two_specific_categories_tied_at_top_resolve_by_load_order():
    docs = [
        {"category": "experience", "title": "Experience doc", "keywords": ["experience"], "content": "experience"},
        {"category": "ai", "title": "AI doc", "keywords": ["ai"], "content": "ai"},
        {"category": "rpa", "title": "RPA doc", "keywords": ["rpa"], "content": "rpa"},
        {"category": "banking", "title": "Banking doc", "keywords": ["banking"], "content": "banking"},
    ]

    result = retrieve("ai rpa", docs)

    assert result["resolution_method"] == "matched"
    # ai and rpa qualify with equal scores; load order (ai before rpa) wins last_category.
    assert result["last_category"] == "ai"


def test_followup_after_confident_match(documents):
    first_turn = retrieve("Tell me about his RPA experience.", documents)
    assert first_turn["resolution_method"] == "matched"

    followup = retrieve(
        "Which tools did he use?", documents, last_category=first_turn["last_category"]
    )
    assert followup["resolution_method"] == "followup_reference"
    assert followup["results"][0]["category"] == "rpa"


def test_followup_without_prior_match_falls_back(documents):
    result = retrieve("Which tools did he use?", documents, last_category=None)
    assert result["results"] == []
    assert result["resolution_method"] == "none"


def test_topic_switch_mid_followup_prefers_normal_match(documents):
    result = retrieve("What banking projects has he worked on?", documents, last_category="rpa")
    assert result["resolution_method"] == "matched"
    assert result["last_category"] == "banking"
