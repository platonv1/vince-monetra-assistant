import pytest

from rag.prompt import SYSTEM_PROMPT, build_prompt

SAMPLE_RESULT = {
    "category": "rpa",
    "title": "RPA & Automation Experience",
    "keywords": ["rpa", "uipath"],
    "content": "8-10 years of RPA experience across UiPath and Automation Anywhere.",
}
OTHER_RESULT = {
    "category": "banking",
    "title": "Banking Projects",
    "keywords": ["banking"],
    "content": "Delivered banking automation projects at ANZ.",
}


def test_prompt_contains_system_rules():
    result = build_prompt("What RPA tools has he used?", [SAMPLE_RESULT], [])
    assert result["system"] == SYSTEM_PROMPT


def test_prompt_contains_retrieved_content_labeled_by_category():
    result = build_prompt("What RPA tools has he used?", [SAMPLE_RESULT], [])
    last_message = result["messages"][-1]["content"]
    assert "[RPA]" in last_message
    assert SAMPLE_RESULT["content"] in last_message


def test_prompt_contains_only_retrieved_content_not_other_documents():
    result = build_prompt("What RPA tools has he used?", [SAMPLE_RESULT], [])
    last_message = result["messages"][-1]["content"]
    assert OTHER_RESULT["content"] not in last_message
    assert "[BANKING]" not in last_message


def test_prompt_contains_the_question():
    result = build_prompt("What RPA tools has he used?", [SAMPLE_RESULT], [])
    assert "What RPA tools has he used?" in result["messages"][-1]["content"]


def test_prompt_includes_history_as_prior_messages():
    history = [("What is Vince's RPA experience?", "He has 8-10 years of RPA experience.")]
    result = build_prompt("Which tools did he use?", [SAMPLE_RESULT], history)

    assert result["messages"][0] == {
        "role": "user",
        "content": "What is Vince's RPA experience?",
    }
    assert result["messages"][1] == {
        "role": "assistant",
        "content": "He has 8-10 years of RPA experience.",
    }
    assert result["messages"][-1]["role"] == "user"


def test_multiple_results_each_included_and_labeled():
    result = build_prompt("Tell me about his RPA and banking work.", [SAMPLE_RESULT, OTHER_RESULT], [])
    last_message = result["messages"][-1]["content"]
    assert "[RPA]" in last_message
    assert "[BANKING]" in last_message


def test_empty_results_raises():
    with pytest.raises(ValueError):
        build_prompt("What is Vince's experience?", [], [])
