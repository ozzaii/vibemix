---
title: v.next direction — The Memory Turn
date: 2026-05-18
context: post-v3.1 brainstorm (gsd-explore)
status: thesis, not yet a milestone
---

# v.next: The Memory Turn

## Thesis

vibemix shifts from **AI co-host** (reactive) to **AI copilot** (forward-leaning). The mechanism is memory: every session feeds an embedding layer; coach prompts ground in past sessions, not just the current moment. Personalization is an emergent property of the retrieval seam, not a configured feature.

## Locked decisions

- **Embedding model:** Gemini Embedding 002 (`gemini-embedding-001` — multimodal, native text+image+video+audio+docs into one space).
- **Storage:** `sqlite-vec` + a 50-line wrapper. Pure-Python access, embedded, no server, single SQLite extension load. Green on one-click install.
- **No managed memory framework.** Mem0 / Letta / Zep / Cognee all rejected — see `.planning/notes/mem0-rejected-2026-05-18.md`.
- **No LLM-extraction layer between session and embedding.** What goes in is what was there. Raw events, raw transcripts, raw track metadata. Extraction = confabulation surface = violates anti-slop thesis.

## Scope spine (not yet phased)

The milestone ships the spine:

1. **Ingest pipeline** — session artifacts (`events.jsonl`, `voice.wav`, `input.wav`, MIDI moves, track metadata) → typed embeddable records.
2. **Storage** — sqlite-vec DB scoped per-install; retention + size budget TBD.
3. **Retrieval seam** — coach prompt is grounded with top-k past moments at every reaction. Hybrid (cosine + time-weight) TBD per research.
4. **Visible copilot moves** — one or two end-user-noticeable proofs that retrieval is firing. E.g., the AI calls back a vocabulary you used last Friday; it anticipates a transition shape it has seen you make 30 times; it cites a past moment in its reaction.

The "which artifacts ground best" question is the FIRST PHASE's research, not a pre-decided answer.

## Acid test for any embedded artifact

> Does retrieving this close a hallucination class, or unlock a copilot move?

If neither — don't embed it.

## What this is NOT

- Not a feature ranking of the parking-lot candidates (Mixxx OSC, pyrekordbox, library vibe search, debrief arc). Some of these get *cheaper* once the memory layer exists. They are not the spine.
- Not a settings-screen personalization. Phase 32's ~2KB DJ profile already covers configured prefs.
- Not a "embed every audio sample" play. Scope hard. Start with structured artifacts that are already typed.
- Not Mem0 or any managed framework.

## Carry-forward from v3.1

- 7 Kaan-action carveouts on external clock — independent, do not block this thesis.
- Mascot stays single VTuber (Neon Rebel). No `/hatch` user-gen.
- Gemini-only AI. No CLAP, no MERT, no OpenL3, no OpenAI/Anthropic.

## Source conversation

Crystallized during a Socratic `/gsd-explore` session on 2026-05-18. Kaan compressed the direction in four phrases: "IT BECOMES YOUR DJ COPILOT" → "it personalizes itself" → "Gemini Embedding 002 simplemem" → "REMEMBER." The mechanism IS the product, per the anti-slop thesis: personalization is just another grounding axis.

## Next steps

- Convert this thesis into a REQUIREMENTS-shaped milestone via `/gsd-new-milestone` when Kaan is ready.
- First phase candidate: "Memory spine v1 — ingest + storage + retrieval seam + 1 visible copilot move."
