# ARCHITECTURE — Vince AI Career Assistant

## Layers

```
Website (vicsaisanplaton.info)
        |  embed
Gradio Chatbot (app.py)              -- presentation only
        |
Chat Controller (chat.py)            -- orchestration + last_category state
        |
Vectorless Retriever (rag/)          -- deterministic, no LLM
        |
CV Knowledge Base (knowledge/*.md)   -- source of truth

LLM Provider (llm/provider.py)       -- called by chat.py, swappable via env var
```

Retrieval is fully deterministic and testable without any LLM or network call. The LLM only ever sees content the retriever already selected — it never fetches its own context.

## Directory structure

```
vince-monetra-assistant/
├── CLAUDE.md
├── PRD.md
├── ARCHITECTURE.md
├── RAG_DESIGN.md
├── DEPLOYMENT.md
├── TESTING.md
├── app.py
├── chat.py
├── requirements.txt
├── .env.example
├── .gitignore
├── knowledge/
│   ├── experience.md
│   ├── ai.md
│   ├── rpa.md
│   └── banking.md
├── rag/
│   ├── __init__.py
│   ├── loader.py            # parses knowledge/*.md into structured docs
│   ├── normalizer.py        # query normalization / synonym expansion
│   ├── retriever.py         # scoring, ranking, threshold, follow-up resolution
│   └── prompt.py            # builds the grounded system + context prompt
├── llm/
│   ├── __init__.py
│   └── provider.py          # generate_response(prompt: dict)
└── tests/
    ├── test_loader.py
    ├── test_normalizer.py
    ├── test_retriever.py
    ├── test_prompt.py
    ├── test_chat.py
    └── test_app.py
```

`rag/normalizer.py` is a deliberate deviation from the original outline (which folded normalization into `retriever.py`) — kept separate for independent testability of synonym expansion.

## Component responsibilities

| Component | Responsibility | Must NOT do |
|---|---|---|
| `loader.py` | Read `knowledge/*.md`, parse into `{category, title, keywords, content}` | No retrieval logic |
| `normalizer.py` | Build the normalized term set (lowercase, tokenize, expand recognized synonyms into their disjoint group's canonical category name — see RAG_DESIGN.md); detect follow-up pronoun references | No LLM calls |
| `retriever.py` | Score & rank docs against the normalized query; apply confidence threshold; resolve follow-ups via `last_category` | No prompt construction |
| `prompt.py` | Assemble system instructions + retrieved context (labeled by category) + history + question | No retrieval, no LLM call |
| `provider.py` | Call the configured LLM API with the assembled prompt | No business logic, no retrieval |
| `chat.py` | Wire the above into `answer(question, history) -> str`; own `last_category` state; enforce the no-confidence fallback | Never return retrieval internals |
| `app.py` | Gradio `ChatInterface`, suggested questions, error display | No RAG logic, no direct `rag.*` imports |

## Data flow

```
User question
   → normalize (rag/normalizer.py): lowercase, synonym expansion
   → retrieve (rag/retriever.py): score every doc, presence-based (see RAG_DESIGN.md)
        - any doc scores >= threshold → return ranked list (up to MAX_RESULTS),
          update last_category to the TOP-SCORED category of this turn
        - else, if query has a follow-up reference (pronoun) AND last_category is set →
          return last_category's doc directly, resolution_method = "followup_reference"
        - else → no results, resolution_method = "none"
   → chat.py checks results
        - empty → fixed fallback string, skip the LLM entirely
        - non-empty → build prompt (rag/prompt.py): system rules + each result's
          content labeled by category + last N turns + question
   → llm/provider.py: generate_response(prompt)
   → chat.py returns a plain string
   → app.py displays it
```

## Boundary contract (security)

`chat.answer(question, history) -> str` is the only interface `app.py` is allowed to call. Retrieval internals (scores, matched keywords, `resolution_method`) are visible to tests via direct `retriever.retrieve()` calls, but are never returned by `chat.answer()` and never reach the Gradio UI.

## Determinism rules

- Ties in retrieval score are broken by a fixed category order: `experience, ai, rpa, banking` (the order knowledge files are loaded in `loader.py`). This keeps `MAX_RESULTS` truncation reproducible for tests.
- When a turn matches multiple categories, `last_category` is set to the **top-scored** category of that turn (single value, not a list) — keeping follow-up resolution simple and testable.
