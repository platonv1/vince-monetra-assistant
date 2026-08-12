from rag.normalizer import normalize_query


def test_ai_synonym_expansion():
    for query in [
        "Has Vince worked with artificial intelligence?",
        "Does Vince have LLM experience?",
        "What large language model work has he done?",
    ]:
        assert "ai" in normalize_query(query)["terms"]


def test_rpa_synonym_expansion():
    for query in [
        "What robotic process automation experience does Vince have?",
        "What automation tools has Vince used?",
    ]:
        assert "rpa" in normalize_query(query)["terms"]


def test_banking_synonym_expansion():
    for query in [
        "What financial services experience does Vince have?",
        "Tell me about his finance background.",
    ]:
        assert "banking" in normalize_query(query)["terms"]


def test_experience_synonym_expansion():
    for query in [
        "Can you summarize Vince's professional background?",
        "What is Vince's career background?",
    ]:
        assert "experience" in normalize_query(query)["terms"]


def test_followup_pronoun_detection():
    for query in [
        "Which tools did he use?",
        "What did she build?",
        "Tell me about it.",
        "What did they deliver?",
        "Was that difficult?",
    ]:
        assert normalize_query(query)["has_followup_reference"] is True


def test_no_followup_reference_without_pronoun():
    assert normalize_query("What is Vince's experience?")["has_followup_reference"] is False


def test_disjoint_synonym_groups_do_not_cross_categories():
    result = normalize_query("Tell me about his career in banking.")
    assert result["terms"] >= {"experience", "banking"}
    assert "ai" not in result["terms"]
    assert "rpa" not in result["terms"]


def test_stopwords_excluded_from_scoring_terms():
    terms = normalize_query("What is the experience with AI?")["terms"]
    assert "what" not in terms
    assert "is" not in terms
    assert "the" not in terms
    assert "with" not in terms
