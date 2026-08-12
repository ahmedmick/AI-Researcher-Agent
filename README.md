# AI Researcher Agent

A command-line AI research agent that searches the web, reads full articles, and answers questions with real, verifiable citations — built from scratch as a hands-on learning project for understanding how AI agents actually work under the hood.

Instead of using a framework (LangChain, etc.), this project implements the core agentic tool-calling loop manually, across **two different LLM provider APIs** (Groq and Gemini), to understand exactly what's happening at each step: how the model requests a tool, how results get fed back, and how a multi-round research conversation is assembled turn by turn.

---

## Features

- 🔎 **Web search** via the [Tavily](https://tavily.com) API
- 📄 **Full-page reading** — fetches and extracts clean article text (not just search snippets) using `trafilatura`
- 🔁 **Multi-round tool-calling loop** — the agent can search, read, and search again as many times as it needs (within a configurable cap) before answering
- 📚 **Verified citations** — every `[1]`, `[2]`, etc. in the final answer is checked against real search results in code (not trusted from the model's own text), so citations can't be fabricated or mistyped
- 🧹 **Broken-link filtering** — search results with malformed/relative URLs are automatically filtered out before reaching the model
- 🔄 **Retry with exponential backoff** — handles rate limits and transient API errors gracefully instead of crashing
- 💬 **Interactive CLI** — ask multiple questions in one running session
- 🎨 **Rich terminal formatting** — Markdown-style output (headers, bold, tables) rendered properly in the terminal via [`rich`](https://github.com/Textualize/rich)
- 🌍 **Arabic language support** *(in progress)* — right-to-left text reshaping and a custom Markdown-to-terminal renderer, since standard Markdown rendering breaks under Arabic bidi text reordering

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

---

## Project Structure

```
research-agent/
├── tools.py                 # web_search (Tavily) and fetch_page (trafilatura) tool implementations
├── Groq_web_search.py       # agent loop using the Groq API
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
MODEL=gemini-3.6-flash   # or a Groq model, depending on which script you run
```

You'll need free accounts with:
- [Groq Cloud](https://console.groq.com) and/or [Google AI Studio](https://ai.google.dev) — for the LLM
- [Tavily](https://tavily.com) — for web search

### 3. Run it
```bash
python main.py
```
Choose your perfered model:
```
Welcome to AI Researcher Agent

- Enter '1' for Gemini Model
- Enter '2' for Groq/OpenAI Model(in progress)
Choose your perfered AI Model:
```
### $\color{#FF0000}{Note:}$ Gemini Model is the only model available right now

You'll be dropped into an interactive prompt:
```
Ask a question (or type 'exit' to quit):
```
Type `exit` at any time to quit.

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

## Lessons Learned

This project was built step by step, debugging real issues as they came up rather than following a tutorial. Some of the more interesting problems along the way:

**The tool-calling loop has more moving parts than it looks like.** Getting a basic "model asks for a tool, code runs it, result goes back" exchange working is one thing — but making that work *reliably across multiple rounds* required carefully tracking which messages/responses needed to be appended back into the conversation history, and in what order. Missing the model's own "I want to call this tool" message from the history (before appending the tool's result) causes API errors that are non-obvious to debug.

**Switching from Groq to Gemini wasn't a small tweak — it was a different API paradigm.** Groq follows the now-common OpenAI-style `messages` + `tools` + `tool_calls` shape. Gemini's newer Interactions API is session-based (`previous_interaction_id` instead of a growing message list) and uses different field names throughout (`steps`, `function_call`, `function_result`, `call_id`). Porting the same *concept* across both was a good way to see which parts of "tool calling" are universal versus API-specific.

**Trusting the model to write its own citations is risky.** Early versions let the model type out full `Sources:` lists itself — which led to fabricated-looking citation markers and, once fixed, broken relative URLs (`/goto?url=...`) that Tavily itself returned. The fix was to never let the model be the source of truth for URLs: the agent tracks every real search result in code and cross-checks citations against that list using a regex that also handles combined citation groups like `[1, 2]`.

**Rate limits are a normal part of working with any LLM API, not an edge case.** Free-tier limits on both Groq and Gemini were hit multiple times during development. Building retry-with-backoff logic — and specifically learning to catch broadly (`except Exception`) while still re-raising non-retryable errors — turned out to be a more important lesson than any single feature.

**Nested loops need explicit exit signals, not just `break`.** A recurring bug pattern: `break` only exits the *innermost* loop, which caused several rounds of confusing behavior once a retry loop was nested inside the main research loop. Using boolean flags (`is_completed`, `failed`) checked *after* the inner loop, instead of relying on `break` alone, fixed this cleanly — a pattern worth remembering for any future nested-loop control flow.

**Right-to-left language support exposed a genuine conflict between two libraries.** Arabic responses initially rendered with visibly broken letter shaping in the terminal. Fixing that (via `arabic_reshaper` + `python-bidi`) then broke `rich`'s Markdown parser, because bidi text reordering happens *after* Markdown syntax markers (`##`, `**`) need to be read in their original position. This led to building a small custom Markdown-to-terminal renderer specifically for Arabic output — a good example of how fixing one layer of a problem can surface a conflict in the layer above it.

---

## Roadmap

- [ ] Finish the custom Arabic Markdown renderer (headers, bold, lists, mixed Arabic/English/citation text)
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
