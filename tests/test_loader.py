from rag.loader import CATEGORY_ORDER, load_documents


def test_loads_all_four_categories_in_fixed_order():
    docs = load_documents()
    assert [doc["category"] for doc in docs] == CATEGORY_ORDER


def test_each_document_has_required_fields():
    docs = load_documents()
    for doc in docs:
        assert isinstance(doc["category"], str) and doc["category"]
        assert isinstance(doc["title"], str) and doc["title"]
        assert isinstance(doc["keywords"], list) and doc["keywords"]
        assert isinstance(doc["content"], str) and doc["content"]


def test_content_excludes_frontmatter():
    docs = load_documents()
    for doc in docs:
        assert not doc["content"].startswith("---")
        assert "category:" not in doc["content"]


def test_rpa_document_parsed_correctly():
    docs = load_documents()
    rpa_doc = next(doc for doc in docs if doc["category"] == "rpa")

    assert rpa_doc["title"] == "RPA & Automation Experience"
    assert "uipath" in rpa_doc["keywords"]
    assert "power automate" in rpa_doc["keywords"]
    assert "UiPath" in rpa_doc["content"]


def test_banking_document_parsed_correctly():
    docs = load_documents()
    banking_doc = next(doc for doc in docs if doc["category"] == "banking")

    assert "anz" in banking_doc["keywords"]
    assert "citibank" in banking_doc["keywords"]
    assert "ANZ" in banking_doc["content"]
