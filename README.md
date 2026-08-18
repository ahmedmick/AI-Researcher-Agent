# AI Researcher Agent

A command-line AI research agent that searches the web, reads full articles, and answers questions with real, verifiable citations — built from scratch as a hands-on learning project for understanding how AI agents actually work under the hood.

Instead of using a framework (LangChain, etc.), this project implements the core agentic tool-calling loop manually, across **two different LLM provider APIs** (Groq and Gemini), to understand exactly what's happening at each step: how the model requests a tool, how results get fed back, and how a multi-round research conversation is assembled turn by turn.

---

## Overview
<video src="https://github.com/user-attachments/assets/f1e6074d-512b-4dfb-ba25-e1ed2c826694" width="80%" controls muted></video>

---

## Features

- 🔎 **Web search** via the [Tavily](https://tavily.com) API
- 📄 **Full-page reading** — fetches and extracts clean article text (not just search snippets) using `trafilatura`
- 🔁 **Multi-round tool-calling loop** — the agent can search, read, and search again as many times as it needs (within a configurable cap) before answering
- 📚 **Verified citations** — every `[1]`, `[2]`, etc. in the final answer is checked against real search results in code (not trusted from the model's own text), so citations can't be fabricated or mistyped
- 🧹 **Broken-link filtering** — search results with malformed/relative URLs are automatically filtered out before reaching the model
- 🔄 **Retry with exponential backoff** — handles rate limits and transient API errors gracefully instead of crashing
- 💬 **Interactive CLI** — ask multiple questions in one running session, with a model-selection menu on startup
- 🎨 **Rich terminal formatting** — Markdown-style output (headers, bold, tables) rendered properly in the terminal via [`rich`](https://github.com/Textualize/rich)
- 🌍 **Arabic language support** — a custom-built Markdown-to-terminal renderer with right-to-left text reshaping, since standard Markdown rendering breaks under Arabic bidi text reordering. Handles headers, bullets, numbered lists, and inline bold text mixed with Arabic, English, and citation markers, with automatic terminal-aware rendering (see [Known Limitations](#known-limitations))

---

## How it works

At its core, the agent runs a loop:

```
User question
    → LLM decides: answer directly, or call a tool?
    → If tool call: run web_search or fetch_page, feed result back to the LLM
    → Repeat until the LLM has enough information
    → Final answer, with citations checked against real search data
```

This project has two parallel implementations of that loop:
- **Groq** (`llama-3.3-70b-versatile` / `openai/gpt-oss-120b`) using the standard OpenAI-style chat completions + `tools` API
- **Gemini** (`gemini-3.6-flash`) using Google's newer **Interactions API**, a session-based API with a different shape (`previous_interaction_id`, `steps`, `function_result` blocks) — built as a second implementation specifically to understand how the same agentic pattern looks across genuinely different API designs

`main.py` is the single entry point — it presents a model-selection menu, then hands off to whichever agent implementation you choose.

---

## Project Structure

```
research-agent/
├── main.py                  # entry point — model selection menu, launches the chosen agent
├── tools.py                 # web_search (Tavily) and fetch_page (trafilatura) tool implementations
├── arabic_parser.py         # ArabicParser — reusable RTL/bidi Markdown-to-terminal renderer
├── Groq_web_search.py       # agent loop using the Groq API (in progress)
├── Gemini_web_search.py     # agent loop using the Gemini Interactions API
├── .env                     # API keys and config (not committed)
└── README.md
```

---

## Setup

### 1. Clone and install dependencies
```bash
git clone https://github.com/<your-username>/AI-Researcher-Agent.git
cd AI-Researcher-Agent
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set up your API keys

Create a `.env` file in the project root:
```env
GROQ_API_KEY=your_groq_key
Gemini_API_KEY=your_gemini_key
TAVILY_API_KEY=your_tavily_key
MODEL=gemini-3.6-flash   # or a Groq model, depending on which agent you run
```

You'll need free accounts with:
- [Groq Cloud](https://console.groq.com) and/or [Google AI Studio](https://ai.google.dev) — for the LLM
- [Tavily](https://tavily.com) — for web search

### 3. Run it
```bash
python main.py
```
Choose your preferred model:
```
Welcome to AI Researcher Agent

- Enter '1' for Gemini Model
- Enter '2' for Groq/OpenAI Model (in progress)
Choose your preferred AI Model:
```
### $\color{#FF0000}{Note:}$ Gemini Model is the only model available right now

You'll be dropped into an interactive prompt:
```
Ask a question (or type 'exit' to quit):
```
Type `exit` at any time to quit. Questions can be asked in English or Arabic — the agent detects the language automatically and renders the response accordingly.

---

## Example

```
Ask a question (or type 'exit' to quit): What are the latest developments in solid-state battery technology?

→ Calling web_search({'query': 'solid state battery breakthroughs 2025'})
→ Calling fetch_page({'url': 'https://...'})

FINAL RESPONSE

Solid-state battery (SSB) technology has moved from lab research into
pilot production and real-world vehicle testing [1, 2, 5]...

Sources
┌─────┬──────────────────────────────┬───────────────────────────┐
│  #  │ Title                        │ URL                       │
├─────┼──────────────────────────────┼───────────────────────────┤
│ [1] │ Solid-State Battery ...      │ https://...                │
└─────┴──────────────────────────────┴───────────────────────────┘
```

---

## Known Limitations

**Arabic rendering depends on which terminal you use, due to an unresolved upstream Windows bug.**

Both the legacy Windows Console Host (`conhost.exe`) and modern Windows Terminal currently implement Arabic *letter shaping* but not full *bidi reordering* — this is an acknowledged, open issue in Microsoft's own `microsoft/terminal` repository, not something fixable from application code. As a workaround:

- `ArabicParser` detects this and manually reshapes + reorders Arabic text (via `arabic-reshaper` + `python-bidi`) before printing, so **standard PowerShell / Windows Terminal display Arabic correctly** — with one remaining cosmetic quirk: since these terminals have no native concept of RTL paragraph alignment, output is right-aligned manually (`rich.align.Align.right`) to compensate.
- **mintty-based terminals** (Git Bash, MSYS2) already implement full native bidi support. `ArabicParser` detects this environment (via the `MSYSTEM` environment variable) and skips its own reshaping/reordering step entirely — applying it on top of mintty's own correct handling would double-process the text and produce garbled output.
- If you want to run genuine PowerShell commands inside a terminal with native bidi support (avoiding the manual reshaping path entirely), you can launch PowerShell through `winpty`:
  ```bash
  winpty powershell
  ```
  from a Git Bash prompt — this gives you a real PowerShell session, just hosted by mintty's renderer.

This was diagnosed by testing terminal output programmatically (not just visually) after discovering the terminal itself was misrepresenting already-correct string data — see the Lessons Learned section below.

**Some cited source links may occasionally return 404 or "page not found," even though the citation itself is accurate.**

Every URL in the sources table is the real, unmodified URL returned by Tavily's search API at the time of the query — the agent never fabricates or mistypes a link (see the citation-verification approach above). However, search indexes crawl and cache snapshots of the web, and the underlying pages can be moved, restructured, or taken down by their owners *after* being indexed. When this happens, the citation is still correctly attributed to the source the model actually used, but the live link may no longer resolve. This was confirmed directly (fetching a reported broken link independently returned the same 404), ruling out a numbering or storage bug in the agent itself. There is currently no automatic link-validation step; this is treated as an inherent, unavoidable characteristic of live web search rather than something to engineer around.

---

## Lessons Learned

This project was built step by step, debugging real issues as they came up rather than following a tutorial. Some of the more interesting problems along the way:

**The tool-calling loop has more moving parts than it looks like.** Getting a basic "model asks for a tool, code runs it, result goes back" exchange working is one thing — but making that work *reliably across multiple rounds* required carefully tracking which messages/responses needed to be appended back into the conversation history, and in what order. Missing the model's own "I want to call this tool" message from the history (before appending the tool's result) causes API errors that are non-obvious to debug.

**Switching from Groq to Gemini wasn't a small tweak — it was a different API paradigm.** Groq follows the now-common OpenAI-style `messages` + `tools` + `tool_calls` shape. Gemini's newer Interactions API is session-based (`previous_interaction_id` instead of a growing message list) and uses different field names throughout (`steps`, `function_call`, `function_result`, `call_id`). Porting the same *concept* across both was a good way to see which parts of "tool calling" are universal versus API-specific.

**Trusting the model to write its own citations is risky.** Early versions let the model type out full `Sources:` lists itself — which led to fabricated-looking citation markers and, once fixed, broken relative URLs (`/goto?url=...`) that Tavily itself returned. The fix was to never let the model be the source of truth for URLs: the agent tracks every real search result in code and cross-checks citations against that list using a regex that also handles combined citation groups like `[1, 2]`.

**Rate limits are a normal part of working with any LLM API, not an edge case.** Free-tier limits on both Groq and Gemini were hit multiple times during development. Building retry-with-backoff logic — and specifically learning to catch broadly (`except Exception`) while still re-raising non-retryable errors — turned out to be a more important lesson than any single feature.

**Nested loops need explicit exit signals, not just `break`.** A recurring bug pattern: `break` only exits the *innermost* loop, which caused several rounds of confusing behavior once a retry loop was nested inside the main research loop. Using boolean flags (`is_completed`, `failed`) checked *after* the inner loop, instead of relying on `break` alone, fixed this cleanly — a pattern worth remembering for any future nested-loop control flow.

**Right-to-left language support exposed a genuine conflict between two libraries.** Arabic responses initially rendered with visibly broken letter shaping in the terminal. Fixing that (via `arabic_reshaper` + `python-bidi`) then broke `rich`'s Markdown parser, because bidi text reordering happens *after* Markdown syntax markers (`##`, `**`) need to be read in their original position. This led to building a small custom Markdown-to-terminal renderer specifically for Arabic output.

**Reshaping and bidi-reordering text in isolated fragments breaks both operations.** An early version of the Arabic renderer split each line into bold/non-bold segments and reshaped each piece separately, to preserve inline `**bold**` styling. This caused two distinct symptoms: broken letter joining at segment boundaries (since `arabic_reshaper` needs full word context to pick correct letter forms) and incorrect overall word order (since `get_display()` needs the *whole* line to reorder correctly). The fix was to reshape/reorder the **entire line at once**, using uniquely numbered invisible-ish sentinel markers (`@@B0@@`/`@@E0@@`, `@@B1@@`/`@@E1@@`, ...) inserted before processing to mark bold spans, then located and converted to `rich` markup *after* processing — since a naive single generic marker pair broke under bidi reordering with multiple bold segments in one line (the reordering could separate a "begin" marker from its own segment and pair it with a different segment's "end" marker).

**A terminal can lie to you, even about your own correct output.** While debugging the sentinel-marker approach, a `print()`-based visual check suggested markers were being scrambled in an unexpected way. Verifying the actual string content programmatically (`string.index(...)` comparisons) instead of trusting the terminal's rendering revealed the string was already correct — the terminal itself was misrepresenting it. This became a recurring theme: several "bugs" turned out to be terminal-rendering artifacts, not code defects, and were only resolved by testing data directly rather than trusting how it looked on screen.

---

## Roadmap

- [ ] Finish the Groq agent's model-selection integration into `main.py`
- [ ] Add response caching to avoid re-fetching the same pages across sessions
- [ ] Explore streaming output for the final answer

---

## Tech Stack

- Python
- [Groq API](https://console.groq.com) / [Gemini API](https://ai.google.dev)
- [Tavily](https://tavily.com) — web search
- [`trafilatura`](https://github.com/adbar/trafilatura) — article text extraction
- [`rich`](https://github.com/Textualize/rich) — terminal formatting
- [`arabic-reshaper`](https://github.com/mpcabd/python-arabic-reshaper) + [`python-bidi`](https://github.com/MeirKriheli/python-bidi) — RTL text rendering
