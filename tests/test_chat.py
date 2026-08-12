from unittest.mock import patch

import chat


def test_confident_match_calls_llm_and_returns_its_output_verbatim():
    llm_output = "He used UiPath and Automation Anywhere."
    with patch("chat.generate_response", return_value=llm_output) as mock_generate:
        result = chat.answer("Tell me about his RPA experience.", [])

    assert result == llm_output
    mock_generate.assert_called_once()


def test_llm_failure_returns_generic_error_message_not_raw_exception():
    with patch("chat.generate_response", side_effect=RuntimeError("provider secret detail")):
        result = chat.answer("Tell me about his RPA experience.", [])

    assert result == chat.LLM_ERROR_MESSAGE
    assert "provider secret detail" not in result


def test_unrelated_question_returns_fallback_without_calling_llm():
    with patch("chat.generate_response") as mock_generate:
        result = chat.answer("What's the weather like today?", [])

    assert result == chat.FALLBACK_MESSAGE
    mock_generate.assert_not_called()


def test_followup_without_prior_context_falls_back_without_calling_llm():
    with patch("chat.generate_response") as mock_generate:
        result = chat.answer("Which tools did he use?", [])

    assert result == chat.FALLBACK_MESSAGE
    mock_generate.assert_not_called()


def test_followup_resolves_using_prior_turn_category():
    history = [("Tell me about his RPA experience.", "He has 8-10 years of RPA experience.")]
    with patch("chat.generate_response", return_value="UiPath and Automation Anywhere.") as mock_generate:
        result = chat.answer("Which tools did he use?", history)

    assert result == "UiPath and Automation Anywhere."
    prompt = mock_generate.call_args[0][0]
    assert "[RPA]" in prompt["messages"][-1]["content"]


def test_multi_turn_followup_chain_keeps_resolving_same_category():
    history = [
        ("Tell me about his RPA experience.", "He has 8-10 years of RPA experience."),
        ("Which tools did he use?", "UiPath and Automation Anywhere."),
    ]
    with patch("chat.generate_response", return_value="Yes, at Fullerton and ANZ.") as mock_generate:
        result = chat.answer("Did he use them recently?", history)

    assert result == "Yes, at Fullerton and ANZ."
    prompt = mock_generate.call_args[0][0]
    assert "[RPA]" in prompt["messages"][-1]["content"]


def test_history_included_in_prompt_as_prior_messages():
    history = [("Tell me about his RPA experience.", "He has RPA experience.")]
    with patch("chat.generate_response", return_value="ok") as mock_generate:
        chat.answer("Which tools did he use?", history)

    prompt = mock_generate.call_args[0][0]
    assert prompt["messages"][0] == {"role": "user", "content": "Tell me about his RPA experience."}
    assert prompt["messages"][1] == {"role": "assistant", "content": "He has RPA experience."}


def test_history_truncated_to_last_n_turns_in_prompt():
    history = [
        (f"Tell me about his RPA experience. (turn {i})", "He has RPA experience.")
        for i in range(chat.HISTORY_TURNS_FOR_PROMPT + 3)
    ]
    with patch("chat.generate_response", return_value="ok") as mock_generate:
        chat.answer("Which tools did he use?", history)

    prompt = mock_generate.call_args[0][0]
    assert len(prompt["messages"]) == chat.HISTORY_TURNS_FOR_PROMPT * 2 + 1


def test_answer_return_value_has_no_retrieval_debug_fields():
    llm_output = "He used UiPath and Automation Anywhere at Fullerton and ANZ."
    with patch("chat.generate_response", return_value=llm_output):
        result = chat.answer("Tell me about his RPA experience.", [])

    assert isinstance(result, str)
    for leaked_term in ("resolution_method", "score", "matched_keywords", "category_match"):
        assert leaked_term not in result
