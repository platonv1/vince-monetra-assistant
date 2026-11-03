# RAG_DESIGN — Vectorless Retrieval

## Document schema

One structured document per knowledge file:

```json
{
  "category": "rpa",
  "title": "RPA Experience",
  "keywords": ["rpa", "uipath", "power automate", "automation", "bot"],
  "content": "<full markdown body>"
}
```

## Knowledge file format

Each `knowledge/*.md` file is YAML frontmatter followed by a markdown body. `loader.py` reads the frontmatter into `category`, `title`, `keywords`, and takes the entire body (unparsed markdown, headings included) as `content`:

```markdown
---
category: rpa
title: RPA & Automation Experience
keywords: [rpa, robotic process automation, automation, uipath, automation anywhere, power automate]
---

## Overview
...
```

`category` must be one of the four fixed categories (`experience`, `ai`, `rpa`, `banking`) and matches the filename stem. `keywords` should include the category's own synonym-group terms (RAG_DESIGN's normalizer expands queries to canonical category names, but literal keyword-list matches still contribute `metadata_matches` independently) plus domain-specific terms (tool names, employers, acronyms) a recruiter might type verbatim.

## Scoring — presence-based, not frequency-based

```
unique_content_matches = count of DISTINCT terms in the normalized term set found anywhere in content   (0 or 1 per term)
metadata_matches       = count of DISTINCT terms in the normalized term set found in the doc's keywords list
category_match          = 1 if the doc's category's canonical name is present in the normalized term set, else 0

score = (unique_content_matches × 1) + (metadata_matches × 2) + (category_match × 3)
```

Earlier design counted raw keyword *occurrences*, which let long documents win purely by repeating a term. Presence-based scoring (0/1 per distinct keyword) removes document length as a variable entirely — a doc can't inflate its score by saying "banking" fifty times instead of once.

A term is "found" in content or a keyword-list entry if it appears as a whole word/phrase, case-insensitively (`\bterm\b`) — not a raw substring (so the 2-letter term `ai` can't spuriously match inside `maintain`). `metadata_matches` checks each normalized-query term against every entry in the doc's keyword list independently, so a multi-word keyword like `power automate` is still reachable by a query that only says "automate".

`category_match` is evaluated independently per document/category. A single query can trigger it for more than one category at once (e.g. "career in banking" triggers both `experience` and `banking`) — this is intended: a compound question should surface every genuinely relevant category, up to `MAX_RESULTS`. It is not a scoring leak, because synonym groups (below) are disjoint, so a synonym can only ever activate its own category's `category_match`, never another one's.

## Confidence threshold

`MIN_RETRIEVAL_SCORE` (env var, default: `3`). A document must meet or exceed this score to be returned at all. Tuned against the real `knowledge/*.md` content and the retriever test suite (`tests/test_retriever.py`) — see Open Items for what that tuning found.

## Result set

Up to `MAX_RESULTS` (env var, default: `3`) documents are returned, each independently meeting the threshold, ranked by score descending. Ties are broken by the fixed category load order (`experience, ai, rpa, banking`) so truncation stays deterministic.

Raised from an initial default of 2 to 3 during retriever testing: a genuinely compound query (e.g. "AI and RPA experience") can legitimately clear the threshold for 3 of the 4 documents at once (see Open Items), and capping at 2 silently dropped one of the two categories the query actually asked about.

## Follow-up resolution

`resolution_method` is one of: `"matched"`, `"followup_reference"`, `"none"`.

- **`matched`** — normal scoring cleared the threshold for one or more docs. `last_category` is set to the top-scored category, with one refinement found during testing: `experience` is the generalist category (every other category's overview also happens to mention the word "experience" once, and vice versa), so on a single-category query it routinely *ties* the specific category's score exactly. When `experience` ties for the top score with a more specific category, the more specific category wins `last_category` — otherwise a follow-up like "which tools did he use?" after an RPA question would resolve to the generalist doc instead of `rpa`. This does not change which documents are returned this turn (both still appear in `results`), only which category is remembered for the next turn's follow-up resolution.
- **`followup_reference`** — normal scoring returned nothing, but the query contains a follow-up pronoun (static list: `he, his, him, it, that, those, them, ...`) and a `last_category` exists from a prior confidently-matched turn. That category's document is returned directly.
- **`none`** — no match by either path; the chat controller returns the fixed fallback string without calling the LLM.

**Known limitation**: only pronoun-style follow-ups are resolved this way. Generic continuations like "tell me more" are not — out of scope for V1, since `My AI Assistant Chatbot.md` (the original implementation guide at the repo root)'s own test matrix only requires pronoun resolution (e.g., "Which tools did **he** use?").

## Query normalization

Static synonym dictionary in `rag/normalizer.py`, organized as one **disjoint** group per category — no term belongs to more than one group, which is what keeps `category_match` scoped to a single category per synonym:

- `experience` ← `background`, `career`, `professional experience`
- `ai` ← `artificial intelligence`, `llm`, `large language model`
- `rpa` ← `robotic process automation`, `automation`
- `banking` ← `financial services`, `finance`

Normalization builds a **normalized term set** from the raw query: lowercase, tokenize, and for every token/phrase that matches an entry in a synonym group, add that group's canonical category name to the set (the original term is kept too, so literal content/metadata-keyword matching still works unchanged). Downstream scoring reads only from this set — it never re-parses the raw query.

## Open items

Resolved during knowledge-base creation and retriever testing (`tests/test_retriever.py`, 42 tests passing):

- Weights (1 / 2 / 3) and `MIN_RETRIEVAL_SCORE=3` needed no change — they already satisfy every required test case against the real knowledge base.
- `MAX_RESULTS` raised from 2 to 3 (see Result set) — required for the compound-query test to pass.
- `last_category` tie-break refined so `experience` doesn't win ties against a more specific category (see Follow-up resolution) — required for the follow-up-after-a-confident-match test to pass.

Still open:

- Streaming vs. synchronous LLM response — deferred to the Gradio implementation step.

Resolved since:

- LLM provider chosen: Claude (`llm/provider.py`, model `claude-opus-5` by default, overridable via `CLAUDE_MODEL`). Affects `llm/provider.py` only, not retrieval.
