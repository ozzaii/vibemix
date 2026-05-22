# Phase 64: Session Ingest - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning
**Mode:** Smart-discuss (autonomous `fully` — grey areas auto-resolved with recommended answers; no human pause). The moment-taxonomy grey area is intentionally LEFT OPEN for in-phase research per the ROADMAP flag (`/gsd:plan-phase --research-phase 64`).

<domain>
## Phase Boundary

A post-session **ingest job** that turns each finished session's already-existing artifacts (`events.jsonl` + the cited evidence + the `ai_text` reactions it produced) into typed **"reaction moment"** records — **deterministic TEXT signatures only** — and writes them to the Phase 63 `MemoryStore` (`memory.db`). Runs **strictly off the hot path** (session-close batch on the FLEX tier + a boot-time sweep for crashed/missed sessions, both via `run_in_executor`). This phase is fully decoupled from the live reaction path: it operates on dead session data and could land with the co-host never running.

**Hard out-of-scope for this phase** (downstream / deferred):
- NO retrieval seam / `recall` evidence source / coach-prompt grounding (Phase 65 reads what this writes).
- NO copilot move (Phase 66).
- **NO LLM-extraction of any kind** between session and embedding — the moment signature is a *deterministic* assembly of raw artifact fields (no "summarize this set", no "infer the DJ's tendencies"). A CI guard asserts the ingest path calls only `embed_content` (never a chat/generation model). Extraction = confabulation = anti-slop violation.
- **NO audio embedding (v1)** — text-signature-only. Multimodal moment-audio (gemini-embedding-2 audio path) is a future-milestone deferral, gated on text-retrieval proving insufficient.
- **NO live-path touch:** ingest never reads/writes `MusicState`, never holds `state._lock`, never imports the coach loop / `ws_bus` / agent — it is never a live tap. (Same import-boundary gate discipline as Phase 63; extend it to the ingest module.)

</domain>

<decisions>
## Implementation Decisions

### Area 1 — What gets ingested (taxonomy) — PARTIALLY DEFERRED TO RESEARCH
- **v1 default is text-only and conservative:** the candidate moment kinds are `coach_line` (a reaction the AI produced + the cited evidence that grounded it) and `moment` (a notable session event from `events.jsonl`, e.g. a track-change / phase / layer-arrival with its evidence). `audio_moment` is explicitly DEFERRED to a future milestone.
- **The exact taxonomy ("which artifacts ground best") is the phase's research question** (ROADMAP flag) — resolve it in-phase via `gsd-phase-researcher`, held to the **acid test**: *only* embed a record if retrieving it later closes a hallucination class OR unlocks a copilot move. If a candidate artifact does neither, don't embed it. Start text-only; do not expand kinds without the acid test clearing.
- **Signature = deterministic text template**, assembled from raw fields (e.g. `kind | track/context | evidence tokens | the ai_text it produced`) — stable, human-readable, reproducible byte-for-byte from the same artifacts (so the content-hash embed cache makes re-ingest free). NO model in the assembly path.

### Area 2 — When/how ingest runs (off the hot path)
- **Trigger 1 — session-close batch:** when a session ends, enqueue a single batch ingest of that session's artifacts on the FLEX cost lane, dispatched via `loop.run_in_executor(None, ...)` (the established off-hot-path idiom). Never inline in the reaction loop.
- **Trigger 2 — boot-time sweep:** on startup, scan for sessions whose recordings exist but were never ingested (crashed/missed) and ingest them — mirroring the recorder/`recordings_index` crash-sweep pattern. Also `run_in_executor`.
- **Idempotency:** re-ingesting an already-ingested session costs **0 API calls** and is a no-op write — guarded by (a) the content-hash embed cache (reused from `library/embed.py`) and (b) a per-session `memory_ingested` marker (e.g. a row/flag keyed by `session_id`). Reading an already-marked session short-circuits before any embed call.
- **Tagging:** every record is `session_id` + timestamp + `kind` tagged (already the `MemoryStore` record shape from Phase 63) so it can later be (a) excluded from its own session's retrieval (Phase 65) and (b) cascade-deleted with its recordings (Phase 63 `delete_session`).

### Area 3 — Reuse & boundaries
- **Reader:** reuse / mirror `src/vibemix/debrief/session_loader.py` — it already parses `events.jsonl` + `ai_text` + evidence from a session directory. Do not re-implement session parsing; lift its loader (read-only) or factor a shared helper.
- **Writer:** `MemoryStore.add_record(...)` from Phase 63 (compose, don't re-open the DB ad hoc). Embedding strictly via `library/embed.py` (router-resolved `embedding` model, FLEX, content-hash cache) — NO hardcoded model literal (the shipped `tests/repo/test_model_literal_gate.py` covers the new `ingest`/`memory` files).
- **No-extraction CI guard:** add a static test (clone the Phase 63 `test_no_extraction.py` tokenize-stripper idiom) asserting the ingest path imports/calls only `embed_content` — never `generate_content`/`generate_reply`/`.chats.`/`GenerateContentConfig`.
- **Import-boundary gate:** extend the no-live-path import test to the ingest module (no coach loop / `MusicState` / `ws_bus` / agent / prompts import).

### Claude's Discretion
- Module placement (`src/vibemix/memory/ingest.py` vs a sibling `src/vibemix/ingest/` package), the exact `memory_ingested` marker mechanism (sqlite flag row vs sentinel file), and whether the boot-sweep lives with the recorder sweep or in the ingest module — planner's discretion, guided by `recordings_index`/`debrief` conventions. The session-close enqueue **call-site wiring** into the runtime may be shipped here (it touches only the session-end seam, not the reaction loop) OR surfaced as a scope note — planner decides, but if wired it must not import the live reaction path.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/vibemix/debrief/session_loader.py` — already loads a session's `events.jsonl` + `ai_text` + cited evidence from its directory (the ingest reader analog).
- `src/vibemix/memory/store.py` (Phase 63) — `MemoryStore.add_record()` (write target) + `session_id`/ts/kind tagging + `delete_session` cascade already shipped.
- `src/vibemix/library/embed.py` — `embed_content` via router-resolved `embedding` model, FLEX tier, content-hash cache (the ONLY model call; powers idempotency).
- `src/vibemix/runtime/recordings_index.py` — the crash/boot sweep + `_scandir` + per-install cache-dir + path-traversal idiom (mirror for the boot-time ingest sweep).
- `run_in_executor` precedent: `runtime/session_loop.py`, `library/embed.py`, `library/importer.py`, `state/deck_poller.py` (the off-hot-path dispatch idiom).
- `tests/repo/test_model_literal_gate.py` + the Phase 63 `tests/memory/test_no_extraction.py` / `test_no_live_path_import.py` (clone targets for the ingest gates).

### Established Patterns
- Off-hot-path blocking work → `loop.run_in_executor(None, fn)`.
- Crash-recovery boot sweep → scan artifact dirs, process the un-marked ones.
- Content-hash embed cache → idempotent, budget-safe re-embedding.
- Static tokenize-stripped import/extraction gates (Phase 63 precedent).

### Integration Points
- WRITE: ingest → `MemoryStore.add_record` (Phase 63).
- READ (downstream): Phase 65 retrieval queries the records this writes.
- SESSION-END: a session-close hook enqueues the batch ingest (the only runtime touch — must stay off the reaction loop).
- DELETE: records carry `session_id` → Phase 63 `delete_session` cascade already covers them.

</code_context>

<specifics>
## Specific Ideas

- The milestone acid test is the taxonomy gate: *"does retrieving this moment close a hallucination class or unlock a copilot move?"* — embedded as the in-phase research criterion. Default text-only; expand only if it clears.
- Re-ingest must be free (content-hash cache + `memory_ingested` marker) — load-bearing for the €50/mo budget and the boot-sweep's safety.
- Four cardinal invariants preserved by construction: ingest never writes `MusicState` (single-writer), never opens a socket (one-socket), never overrides live ears (trust-the-audio); citation-grounding is Phase 65's concern (ingest only stores raw signatures).

</specifics>

<deferred>
## Deferred Ideas

- **Retrieval seam / `recall` evidence source / coach grounding** → Phase 65 (anti-slop release gate).
- **Visible copilot moves** → Phase 66.
- **`audio_moment` (multimodal) embedding** → future milestone (text-signature-only in v6.0).
- **Cross-session "arc" priors / pre-set prep** → future milestone.

</deferred>
