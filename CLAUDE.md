# CLAUDE.md — Vince AI Career Assistant

Guidance for Claude Code (or any AI assistant) working in this repository.

## What this project is

A Gradio chatbot that answers questions about Vince's professional CV, using **Vectorless RAG** — keyword, category, and relevance-score based retrieval. No embeddings, no vector database.

## Non-negotiable architecture rules

- No embeddings, FAISS, Chroma, Pinecone, Qdrant, LangChain, or LangGraph — for V1.
- Retrieval must remain deterministic: same query → same result, every run. Ties are broken by a fixed category load order (`experience, ai, rpa, banking`), never left to chance.
- The LLM never selects its own context; the retriever selects it before the LLM is called.
- `app.py` never imports `rag.*` directly — only `chat.answer()`.
- `chat.answer(question, history) -> str` is the only interface `app.py` may call. Retrieval debug data (scores, matched keywords, `resolution_method`) never crosses that boundary into a user-facing response.
- Conversation history lives in Gradio's in-memory session state only — never logged or persisted to disk.

## Development workflow

Follow the docs in this order when building:

```
PRD.md → ARCHITECTURE.md → RAG_DESIGN.md
  → knowledge base
  → retriever + tests (pytest must pass before continuing)
  → LLM provider
  → chat controller
  → Gradio UI
  → TESTING.md checklist
  → DEPLOYMENT.md
```

Do not implement multiple layers in one prompt. Retrieval must be fully tested with `pytest` before the LLM or Gradio layers are touched.

## Reference docs

- `PRD.md` — what the product does and V1 scope
- `ARCHITECTURE.md` — layers, directory structure, component responsibilities, data flow
- `RAG_DESIGN.md` — scoring formula, confidence threshold, follow-up resolution, known open items
- `DEPLOYMENT.md` — local setup, Hugging Face Spaces, website embedding
- `TESTING.md` — required test coverage and manual QA checklist

## Known open items (see RAG_DESIGN.md)

- Scoring weights and confidence threshold are provisional until tuned against real knowledge-base content.
- LLM provider not yet selected; `llm/provider.py` must stay swappable via the `LLM_PROVIDER` env var.
- Streaming vs. synchronous LLM responses not yet decided (deferred to the Gradio implementation step).
