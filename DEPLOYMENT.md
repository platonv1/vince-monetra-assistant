# DEPLOYMENT — Vince AI Career Assistant

## Local development (macOS)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Gradio serves a local URL, typically `http://127.0.0.1:7860`.

## Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `LLM_PROVIDER` | Selects which LLM backend `llm/provider.py` calls — `claude` (production default) or `gemini` (dev-time alternative only, see note below) | `claude` |
| `LLM_API_KEY` | Anthropic API key. Only read on the `claude` path — ignored entirely when `LLM_PROVIDER=gemini` | (none — must be set when using `claude`, never committed) |
| `CLAUDE_MODEL` | Claude model ID `llm/provider.py` calls | `claude-opus-5` |
| `GEMINI_API_KEY` | Google AI Studio API key. Only read on the `gemini` path — a separate variable from `LLM_API_KEY`, not a fallback for it | (none — must be set when using `gemini`, never committed) |
| `GEMINI_MODEL` | Gemini model ID `llm/provider.py` calls | `gemini-flash-latest` |
| `MIN_RETRIEVAL_SCORE` | Confidence threshold for retrieval | `3` (tuned, see RAG_DESIGN.md) |
| `MAX_RESULTS` | Max documents returned per query | `3` (tuned, see RAG_DESIGN.md) |

Keep `.env` out of source control; `.env.example` documents the variables above with empty values.

**Claude vs. Gemini:** Claude is the primary, production provider — deployments (HF Spaces, Render) should use `LLM_PROVIDER=claude`. Gemini exists only to keep `llm/provider.py` genuinely swappable per CLAUDE.md's architecture rule and is intended for local development, not production use.

## Hugging Face Spaces

**Note (2026):** Hugging Face now requires a **Pro subscription** to create a Gradio or Docker Space on a free account — a policy change that landed mid-2026. Free accounts are limited to a Space auto-assigned **ZeroGPU** hardware (if they can create a compute Space at all; this has been observed to vary/tighten per-account). `app.py` includes a no-op `@spaces.GPU`-decorated function (`_zero_gpu_startup_probe`) purely so the app can boot on ZeroGPU hardware, which otherwise refuses to start without one — the app does no actual GPU work. If Space creation is blocked entirely on a given account, use **Render** below instead.

- SDK: **Gradio**.
- Python version matched to local development (3.12).
- On Space → Settings → **Variables and secrets**:
  - Secret: `LLM_API_KEY` — the production deployment uses Claude. API keys always go in Secrets, never Variables.
  - Variable: `LLM_PROVIDER` set to `claude` — not sensitive, so Variables (not Secrets) is the right place for it. (`gemini` is a valid value too, but is for local development only — see the env-var table above.)
  - Never placed in source code either way.
- `requirements.txt` pins exact versions of: `gradio`, `python-dotenv`, `pytest` (for running the test suite, not production runtime), `anthropic`, `google-genai`, `spaces` (the last only matters on HF's ZeroGPU runtime — it no-ops everywhere else, including Render).
- No local filesystem assumptions beyond reading `knowledge/*.md`, which ships with the repo — no writes to disk at runtime.

## Render (alternative deployment)

Render has a genuine free tier (no credit card required) for hosting a small always-Python web service, unlike HF Spaces' 2026 Pro requirement above. Trade-off: the free instance spins down after ~15 minutes of inactivity and takes 30–50 seconds to wake on the next request — comparable to HF's own free-tier cold-start behavior.

### Prerequisites

- This repo pushed to a GitHub repository Render can read (e.g. `github.com/YOUR_USERNAME/vince-monetra-assistant`) — Render deploys by connecting to a Git repo, not by direct CLI push.
- A Render account (render.com) — sign-up isn't something to automate; do this yourself.

### Setup

1. On Render: **New** → **Web Service** → connect the GitHub repo above.
2. **Runtime**: Python 3. Set the `PYTHON_VERSION` environment variable to `3.12.x` to match local development if Render's auto-detected default differs.
3. **Build Command**: `pip install -r requirements.txt`
4. **Start Command**: `python app.py` — `app.py` binds to `0.0.0.0` and reads Render's `PORT` env var automatically (falls back to `7860` when `PORT` isn't set, e.g. local dev or HF Spaces).
5. **Instance Type**: Free.
6. Under **Environment** → add the same variables as the HF Secrets table above (`LLM_PROVIDER`, and `LLM_API_KEY` or `GEMINI_API_KEY` depending on provider) — Render's environment variables are private to the service by default, equivalent to HF's Secrets.
7. Deploy. Render assigns a public URL like `https://vince-monetra-assistant.onrender.com`.

## Website embedding

`vicsaisanplaton.info` embeds the deployed backend (Hugging Face Space or Render service — whichever is live) via a floating chat button (bottom-right corner). The website stays a thin shell — no RAG logic is duplicated client-side; all retrieval and generation happens in the hosted backend. This section is about the **website's** codebase (outside this repo), not `app.py` — `app.py` only needs to already be a working, tested deployment (see the checklist above) before you start.

### Prerequisites

- The backend (HF Space or Render service) is deployed and reachable at its public URL.
- It has been manually tested end-to-end (all 4 canonical questions, hallucination probes, prompt injection probes — see `TESTING.md`'s manual QA checklist) so you're not debugging the widget and the backend at the same time.
- If using HF Spaces, the Space is **public** (not gated/private) — a private Space returns an authentication wall inside the iframe instead of the chat UI. Render service URLs are public by default.

### Step 1 — Get the direct embed URL

- **Render**: the service URL Render assigns (e.g. `https://vince-monetra-assistant.onrender.com`) is already the direct app URL — no extra step needed.
- **Hugging Face Spaces**: reachable at two URLs — `https://huggingface.co/spaces/YOUR_USERNAME/vince-monetra-assistant` (the HF-hosted page, with HF's own header/chrome — not what you want to embed) vs. `https://YOUR_USERNAME-vince-monetra-assistant.hf.space` (the **direct** app URL, no HF chrome — this is the one to embed). Find it on the Space page under **Embed this Space** → "Direct URL."

Confirm whichever URL you use loads the chat UI cleanly (no host chrome) by opening it in a plain browser tab first.

### Step 2 — Choose an embedding approach

**Option A — Plain iframe (simplest; good for an initial test embed)**

Paste this directly into the website's HTML, wherever the chatbot should appear on the page:

```html
<iframe
  src="https://YOUR_USERNAME-vince-monetra-assistant.hf.space"
  title="Vince AI Career Assistant"
  style="width: 100%; height: 600px; border: none; border-radius: 12px;"
  loading="lazy"
></iframe>
```

This is a static, inline embed — the chatbot occupies a fixed block on the page, always visible. No JavaScript required. Use this to confirm the embed itself works end-to-end before building the floating widget.

**Option B — Floating chat widget (recommended for the final portfolio experience)**

A fixed-position button in the bottom-right corner that opens/closes a panel containing the same iframe. This is a self-contained snippet — plain HTML/CSS/JS, no build step, no framework dependency — so it drops into any static site, WordPress custom-HTML block, or template partial. Paste it once, near the end of `<body>` (so it renders after the rest of the page):

```html
<!-- Vince AI floating chat widget -->
<button id="vince-ai-toggle" aria-label="Open Vince AI chat" aria-expanded="false">💬</button>

<div id="vince-ai-panel" aria-hidden="true">
  <div id="vince-ai-panel-header">
    <span>Vince AI</span>
    <button id="vince-ai-close" aria-label="Close chat">✕</button>
  </div>
  <iframe
    id="vince-ai-iframe"
    src="about:blank"
    data-src="https://YOUR_USERNAME-vince-monetra-assistant.hf.space"
    title="Vince AI Career Assistant"
    loading="lazy"
  ></iframe>
</div>

<style>
  #vince-ai-toggle {
    position: fixed;
    bottom: 24px;
    right: 24px;
    width: 56px;
    height: 56px;
    border-radius: 50%;
    border: none;
    background: #1a1a2e;
    color: #fff;
    font-size: 24px;
    cursor: pointer;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
    z-index: 9999;
    transition: transform 0.2s ease;
  }
  #vince-ai-toggle:hover {
    transform: scale(1.08);
  }

  #vince-ai-panel {
    position: fixed;
    bottom: 96px;
    right: 24px;
    width: 380px;
    height: 600px;
    max-height: calc(100vh - 120px);
    background: #fff;
    border-radius: 16px;
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
    overflow: hidden;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    opacity: 0;
    transform: translateY(16px) scale(0.98);
    pointer-events: none;
    transition: opacity 0.2s ease, transform 0.2s ease;
  }
  #vince-ai-panel.open {
    opacity: 1;
    transform: translateY(0) scale(1);
    pointer-events: auto;
  }

  #vince-ai-panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    background: #1a1a2e;
    color: #fff;
    font-weight: 600;
    font-family: system-ui, -apple-system, sans-serif;
  }
  #vince-ai-close {
    background: none;
    border: none;
    color: #fff;
    font-size: 18px;
    cursor: pointer;
    line-height: 1;
  }

  #vince-ai-iframe {
    flex: 1;
    width: 100%;
    border: none;
  }

  /* Full-screen on small viewports so the widget doesn't get cramped */
  @media (max-width: 480px) {
    #vince-ai-panel {
      bottom: 0;
      right: 0;
      width: 100%;
      height: 100%;
      max-height: 100%;
      border-radius: 0;
    }
    #vince-ai-toggle {
      bottom: 16px;
      right: 16px;
    }
  }
</style>

<script>
  (function () {
    var toggle = document.getElementById("vince-ai-toggle");
    var panel = document.getElementById("vince-ai-panel");
    var closeBtn = document.getElementById("vince-ai-close");
    var iframe = document.getElementById("vince-ai-iframe");
    var loaded = false;

    function openPanel() {
      // Defer loading the iframe (and therefore the HF Space cold start)
      // until the user actually opens the widget, not on page load.
      if (!loaded) {
        iframe.src = iframe.getAttribute("data-src");
        loaded = true;
      }
      panel.classList.add("open");
      panel.setAttribute("aria-hidden", "false");
      toggle.setAttribute("aria-expanded", "true");
    }

    function closePanel() {
      panel.classList.remove("open");
      panel.setAttribute("aria-hidden", "true");
      toggle.setAttribute("aria-expanded", "false");
    }

    toggle.addEventListener("click", function () {
      panel.classList.contains("open") ? closePanel() : openPanel();
    });
    closeBtn.addEventListener("click", closePanel);
  })();
</script>
```

Customization notes:

- Replace `https://YOUR_USERNAME-vince-monetra-assistant.hf.space` in `data-src` with the real direct URL from Step 1 — the Render URL works exactly the same way, just swap it in.
- Colors (`#1a1a2e`), size (`380px` × `600px`), and position (`bottom: 24px; right: 24px;`) are safe to change freely — they're isolated to this snippet's own IDs (`vince-ai-*`), so they won't collide with the rest of the site's CSS.
- The 💬 emoji button is a placeholder — swap it for an `<img>`/SVG icon if the site has its own iconography.
- The iframe's `src` is intentionally left as `about:blank` until first open (`data-src` holds the real URL) — this avoids waking the Space (and paying its cold-start latency) for every visitor who never opens the widget.

### Step 3 — Verify on the live website

- Load the page and confirm the button appears bottom-right, doesn't overlap existing content (nav bars, cookie banners, other floating widgets), and its `z-index` wins.
- Click to open: confirm the panel animates in smoothly and the chat UI loads (first open will be slower if the backend had gone to sleep — both HF free-tier Spaces and Render's free instance sleep after inactivity).
- Send a real question end-to-end from the website (not just the raw `.hf.space` URL) to confirm the iframe embed itself isn't blocked.
- Resize to a mobile viewport (or test on an actual phone) and confirm the full-screen behavior from the `@media` block kicks in and the chat remains usable.
- Confirm closing the panel and reopening it doesn't reset conversation history mid-session (Gradio keeps it in the iframe's own page state, so it persists as long as the iframe isn't reloaded).

### Troubleshooting

- **Iframe shows blank / refuses to load**: if using HF Spaces, confirm the Space is public, not gated behind HF login, and that you're using the direct `.hf.space` URL (not the `huggingface.co/spaces/...` page URL, which HF's own site does not intend to be iframed).
- **Long first-load delay**: expected on both HF's free CPU tier and Render's free instance — the backend sleeps after inactivity and needs to "wake up" on the first request. A paid tier on either platform removes this if it's a problem for real visitors.
- **Widget appears behind other page elements**: raise `z-index` on `#vince-ai-toggle` / `#vince-ai-panel` above whatever else on the page is competing for stacking order.

## Pre-launch checklist

- All automated tests pass (`pytest`).
- Manual QA checklist in `TESTING.md` completed against the live deployment (HF Space or Render).
- Secrets confirmed present in the platform's own secret/env store (HF Space Settings or Render Environment), absent from git history.
- Website embed tested on both mobile and desktop.
