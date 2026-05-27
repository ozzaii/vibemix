---
title: Mem0 evaluated and rejected for vibemix memory layer
date: 2026-05-18
context: gsd-explore research pass during post-v3.1 brainstorm
verdict: REJECTED — do not relitigate
---

# Mem0 (and Letta / Zep / Cognee) — Rejected

## Verdict

For vibemix's constraints (Gemini-only, one-click install, anti-slop), Mem0 is **dead-on-arrival**. So is every other managed memory framework in this class. Use `sqlite-vec` + Gemini Embedding 002 + a 50-line wrapper instead.

## Dispositive evidence

| # | Mem0 finding | Constraint violated |
|---|---|---|
| 1 | Hard `openai` Python dep in core, even when configured Gemini-only. | Gemini-only |
| 2 | No documented switch to disable LLM extraction on `add()`. Extraction is core architecture. | Anti-slop (LLM-extraction is a hallucination class) |
| 3 | GitHub issue #4573 — audit of 10,134 entries found **97.8% junk**, including 808 amplified hallucinations from a single seed ("User prefers Vim") via recall→re-extract feedback loop. | Anti-slop (this IS the class anti-slop closes) |
| 4 | GitHub issue #4099 — ghost memories on empty payloads, Gemini-specific. | Gemini-only |
| 5 | GitHub issue #4540 — silent fact loss with non-OpenAI LLMs (malformed JSON). | Gemini-only |

Sources:
- [GitHub #4573 — 97.8% mem0 entries were junk](https://github.com/mem0ai/mem0/issues/4573)
- [GitHub #4099 — Hallucinated memories on empty payloads (Gemini)](https://github.com/mem0ai/mem0/issues/4099)
- [GitHub #4540 — Silent fact loss with non-OpenAI LLMs](https://github.com/mem0ai/mem0/issues/4540)
- [Mem0 Gemini config docs](https://docs.mem0.ai/components/llms/models/gemini)

## Other managed frameworks (one-line verdict)

- **Letta** (formerly MemGPT) — agent-driven self-editing memory. Agent-shaped, not embedding-shaped. Heavier than needed. **Red.**
- **Zep** — temporal knowledge graph. Requires server (Graphiti + graph store). **Red on one-click install.**
- **Cognee** — poly-store (graph + vector + relational). **Red on one-click install.**

## The replacement

`sqlite-vec` (SQLite extension, embedded, pure-C) + direct `google-genai` calls to `gemini-embedding-001` + a thin Python wrapper. Zero new deps that touch one-click install hard req. Full control over what enters the embedding space. No LLM-extraction layer = no confabulation surface.

## Do not relitigate

If anyone in a future session proposes Mem0 or category-equivalent: point them at this file. The 97.8% audit is dispositive on its own; the Gemini-only constraint independently kills the option.
