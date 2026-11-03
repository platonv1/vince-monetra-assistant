# PRD — Vince AI Career Assistant

## Goal

A production-quality portfolio project: a Gradio chatbot, embedded on `vicsaisanplaton.info`, that answers recruiter questions about Vince's professional background using only his verified CV knowledge base.

## V1 supported questions

1. What is Vince's experience?
2. Does Vince have experience with AI?
3. Tell me about his RPA experience.
4. What banking projects has he worked on?

Plus reasonable wording variants of the above, and simple pronoun-based follow-ups referencing the prior answer (e.g., "Which tools did he use?").

## Success criteria

- Answers the four V1 categories correctly, including reworded variants.
- Never invents information not present in `knowledge/*.md`.
- Refuses gracefully (fixed fallback message) when no relevant knowledge is found.
- Resists prompt injection attempts to override its instructions or reveal system prompts.
- Resolves simple pronoun-based follow-ups against the previous turn's topic.
- Runs locally on macOS and on Hugging Face Spaces with no code changes.

## Non-functional requirements

- **Determinism** — retrieval must be reproducible: same input, same output, every run.
- **Testability** — retrieval, normalization, and prompt construction must be unit-testable without any LLM or network call.
- **Security** — no secrets in source control; no system-prompt leakage; no retrieval debug data in user-facing responses.
- **Privacy** — no persistence of conversation history beyond the active session.

## Out of scope for V1

(see Section 50 of `My AI Assistant Chatbot.md`, the original implementation guide at the repo root, for the full V2+ roadmap)

- Embeddings / hybrid RAG
- Agentic retrieval
- Multi-source knowledge (GitHub, portfolio, technical articles)
- Job-description matching
- Analytics / evaluation dashboards
