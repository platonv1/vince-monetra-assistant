from app import _extract_text, _history_to_turn_pairs


def test_extract_text_from_plain_string_content():
    assert _extract_text("Tell me about his RPA experience.") == "Tell me about his RPA experience."


def test_extract_text_from_content_parts_list():
    # Gradio 6's Chatbot history shape: content is a list of part dicts.
    content = [{"type": "text", "text": "Tell me about his RPA experience."}]
    assert _extract_text(content) == "Tell me about his RPA experience."


def test_extract_text_from_multiple_text_parts_joins_them():
    content = [{"type": "text", "text": "Hello "}, {"type": "text", "text": "world."}]
    assert _extract_text(content) == "Hello world."


def test_extract_text_ignores_non_text_parts():
    content = [{"type": "image", "path": "/tmp/x.png"}]
    assert _extract_text(content) is None


def test_history_to_turn_pairs_handles_content_parts_shape():
    history = [
        {"role": "user", "content": [{"type": "text", "text": "Tell me about his RPA experience."}]},
        {"role": "assistant", "content": [{"type": "text", "text": "He has 8-10 years of RPA experience."}]},
    ]
    assert _history_to_turn_pairs(history) == [
        ("Tell me about his RPA experience.", "He has 8-10 years of RPA experience.")
    ]


def test_history_to_turn_pairs_handles_plain_string_shape():
    history = [
        {"role": "user", "content": "Tell me about his RPA experience."},
        {"role": "assistant", "content": "He has 8-10 years of RPA experience."},
    ]
    assert _history_to_turn_pairs(history) == [
        ("Tell me about his RPA experience.", "He has 8-10 years of RPA experience.")
    ]


def test_history_to_turn_pairs_skips_non_text_content():
    history = [
        {"role": "user", "content": [{"type": "image", "path": "/tmp/x.png"}]},
        {"role": "assistant", "content": "some reply"},
    ]
    assert _history_to_turn_pairs(history) == []
