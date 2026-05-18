---
title: Copilot memory layer
date: 2026-05-18
planted_date: 2026-05-18
trigger_condition: When next milestone scoping kicks off via /gsd-new-milestone after v3.1.
context: Seeded from gsd-explore session, post-v3.1 brainstorm with Kaan.
---

# Seed: Copilot memory layer

## Trigger condition

When `/gsd-new-milestone` runs to scope the post-v3.1 milestone. Surface this seed BEFORE the requirements conversation so the thesis is on the table.

## What's locked

- **Direction:** The Memory Turn — vibemix becomes a copilot via embedding memory.
- **Model:** Gemini Embedding 002 (multimodal, native text+image+video+audio+docs).
- **Storage:** sqlite-vec + 50-line Python wrapper. Embedded. No server.
- **Rejected:** Mem0, Letta, Zep, Cognee — see `.planning/notes/mem0-rejected-2026-05-18.md`.
- **No LLM-extraction layer.** Raw artifacts only.

## What's open

See `.planning/research/questions.md § Memory layer` — 6 open research questions including: which artifacts to embed first, retrieval shape, retention & sizing, cold-start UX, multimodal cost/quality tradeoffs, Phase 32 profile interaction.

## Source documents

- Thesis: `.planning/notes/v-next-memory-turn.md`
- Mem0 verdict: `.planning/notes/mem0-rejected-2026-05-18.md`
- Open questions: `.planning/research/questions.md`

## Don't forget

- **Per memory `project_v2_planning_active`:** Kaan drives milestone scoping. Don't auto-kick.
- **Per memory `project_v2_open_candidates`:** Parking lot has Mixxx OSC, pyrekordbox, library vibe search, debrief arc. These are NOT the spine of v.next — but some get cheaper once memory ships. Re-evaluate AFTER the memory thesis is locked into a phase plan.
- **Per memory `feedback_no_scope_creep_clean_utility`:** Ship the spine + 1-2 visible copilot moves. Not 10 features built on memory.
