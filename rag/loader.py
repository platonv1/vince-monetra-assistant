"""Loads knowledge/*.md into structured documents.

See RAG_DESIGN.md "Knowledge file format" for the on-disk contract this
parses: YAML frontmatter (category/title/keywords) followed by a markdown
body. No retrieval logic lives here.
"""

import re
from pathlib import Path

CATEGORY_ORDER = ["experience", "ai", "rpa", "banking"]
KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"

_FRONTMATTER_RE = re.compile(r"^---\n(?P<meta>.*?)\n---\n(?P<body>.*)$", re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError("knowledge file is missing YAML frontmatter")

    meta: dict = {}
    for line in match.group("meta").splitlines():
        if not line.strip():
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            meta[key] = [item.strip() for item in value[1:-1].split(",") if item.strip()]
        else:
            meta[key] = value

    return meta, match.group("body").strip()


def load_documents(knowledge_dir: Path = KNOWLEDGE_DIR) -> list[dict]:
    """Load knowledge/*.md in the fixed category order.

    That order (experience, ai, rpa, banking) is what rag/retriever.py's
    tie-break relies on — see ARCHITECTURE.md "Determinism rules".
    """
    documents = []
    for category in CATEGORY_ORDER:
        path = knowledge_dir / f"{category}.md"
        meta, content = _parse_frontmatter(path.read_text(encoding="utf-8"))

        if meta.get("category") != category:
            raise ValueError(
                f"{path.name}: frontmatter category '{meta.get('category')}' "
                f"does not match filename '{category}'"
            )

        documents.append(
            {
                "category": meta["category"],
                "title": meta["title"],
                "keywords": meta["keywords"],
                "content": content,
            }
        )

    return documents
