# vibemix — Requirements

**Milestone:** v6.0 "The Memory Turn" — vibemix becomes an AI copilot via session memory
**Started:** 2026-05-22
**Mode:** `gsd-autonomous fully` (recommended grey-area answers + defer blockers to KAAN-ACTION; only privacy rule + destructive risk pause)

## Goal

Shift vibemix from a *reactive* co-host to a *forward-leaning* **copilot**. The mechanism is memory: every session feeds an embedding store; the coach prompt grounds in **past** sessions, not just the current moment. Personalization is an **emergent property of the retrieval seam** — not a configured feature, not an LLM-extraction layer.

The product's hard line holds: **grounded, never hallucinating, no AI slop.** The new headline hallucination class is **retrieval poisoning** (an irrelevant past moment injected into the live prompt → the AI references something that didn't happen) — so RETRIEVAL is the anti-slop release gate, and retrieved moments are made **citable-by-construction** (a fabricated `[recall:…]` strips the whole turn, exactly like the Phase 59 `key:` source).

Research-confirmed foundation (`.planning/research/SUMMARY.md`, 4 convergent agents): this is a **WIRING / REUSE milestone with ZERO net-new dependencies**. `sqlite-vec>=0.1.9` is already declared; the embed→`cosine_topk`→cited-evidence machine already ships in `src/vibemix/library/` (`index_sqlite_vec.py`, `embed.py`, `_cosine.py`, `store.py`, `grounding.py`). The memory layer is a second `memory.db` + a ~50-line wrapper + an off-hot-path ingest job + one gated evidence line + a new existence-only `recall` evidence source (zero new linter code). The unanimous dependency-correct spine: **STORE → INGEST → RETRIEVE → COPILOT MOVE.**

Acid test for any embedded artifact: *"does retrieving this close a hallucination class OR unlock a copilot move?"* — if neither, don't embed it.

---

## v6.0 Requirements

### Memory Store (STORE) — Phase 63

- [x] **STORE-01**: A local, per-install `memory.db` (sqlite-vec) stores embedded session "moments" + metadata, **reusing the shipped** `SqliteVecStore` + the storage-only `vec0` + the deterministic `cosine_topk` chokepoint + the content-hash embed cache — **no new dependency** (`sqlite-vec>=0.1.9` already declared). Falls back to the existing NumpyStore when the extension can't load (Mac/Win parity-tested, `pytest -m parity`). _(contract pinned RED-first by Plan 63-01; implementation lands in Plans 63-02/03)_
- [x] **STORE-02**: A ~50-line `MemoryStore` wrapper exposes `add_record` + `query_topk`; each record carries `session_id` + timestamp + the raw text signature + its embedding — **never** an LLM-extracted "insight" (raw-in, raw-out). _(contract pinned RED-first by Plan 63-01; implementation lands in Plans 63-02/03)_
- [x] **STORE-03**: Retention + privacy: deleting a session's recordings **cascades** to its memory embeddings (no orphaned vectors); a per-install size/retention budget caps growth; everything is local-only and user-deletable (extends the shipped `recordings_index` retention/delete machinery + path-traversal defense). _(impl landed Plan 63-03: path-traversal-defended atomic `delete_session` + `reconcile_orphans` + `run_memory_retention_sweep` oldest-session-first whole-session eviction; all 19 `tests/memory/` GREEN. Call-site wiring deferred — see 63-03-SUMMARY KAAN-ACTION.)_
- [x] **STORE-04**: The embedding model is resolved via `model_router.resolve("embedding")` (**never** hardcode `gemini-embedding-001` — the multimodal intent maps to `gemini-embedding-2`; the router already probes the right one); embed calls route through the Bravoh proxy on the `ServiceTier.FLEX` cost lane. _(contract pinned RED-first by Plan 63-01; implementation lands in Plans 63-02/03)_

### Session Ingest (INGEST) — Phase 64

- [x] **INGEST-01**: A post-session ingest job turns each session's existing artifacts (`events.jsonl` + the cited evidence + the `ai_text` it produced) into typed **"reaction moment"** records as **deterministic TEXT signatures** — **NO audio embedding (v1), NO LLM-extraction** between session and embedding (a CI guard asserts the ingest path only calls `embed_content`).
- [x] **INGEST-02**: Ingest runs **off the hot path** — at session-close in batch (FLEX tier) plus a boot-time sweep for crashed sessions (mirrors the recorder sweep), via `run_in_executor`; it never touches `MusicState`, never holds `state._lock`, and is never a live tap.
- [x] **INGEST-03**: The moment taxonomy ("which artifacts ground best") is research-resolved in-phase and held to the acid test — only records that close a hallucination class or unlock a copilot move are embedded; everything is `session_id`/timestamp-tagged for later exclusion + deletion.

### Memory Retrieval Seam (RECALL) — Phase 65 (anti-slop release gate)

- [x] **RECALL-01**: A new **`recall` evidence source** (existence-only) is added to `EVIDENCE_SOURCES` and flows through the **existing** `CitationLinter` with **zero new linter code** (à la the Phase 59 `key:` source) — each retrieved `record_id` is registered before the LLM call, and a fabricated `[recall:<id>]` strips the whole turn.
- [ ] **RECALL-02**: The coach prompt is grounded with **top-k (2–3 cap)** past moments via a **gated `recall[…]` block** in `state/coach.py::evidence_line` (copying the Phase 59 `decks[…]` gate verbatim so the cold/empty-memory golden stays **byte-identical**), behind a similarity floor (~0.7, mirroring `CITATION_THRESHOLD`) and event-gated to track-aware events.
- [x] **RECALL-03**: Retrieval is **anti-poisoning by construction**: below-floor → inject **nothing**; retrieved moments are fenced **past-tense** ("FROM A PAST SESSION") so they can never be confused with live evidence; the **current session is excluded** from its own retrieval. The cosine-vs-cosine+time-weight blend + half-life is tuned in-phase on Kaan's real session corpus.
- [x] **RECALL-04**: Retrieval stays off the hot path / within the €50/mo budget gate; the four cardinal invariants hold (single-writer, citation-grounding, trust-the-audio, one-socket); ships behind a **Kaan-ear veto** on retrieval relevance (mirrors the Phase 60 harmonic veto — no callback that references a moment Kaan's ear says didn't matter).

### Visible Copilot Move (COPILOT) — Phase 66

- [ ] **COPILOT-01**: At least one end-user-noticeable copilot move proves retrieval is firing — a **transition-shape callback** ("last time you ran this blend you killed the bass 2 bars earlier"), **linter-grounded** so the comparison must resolve to a real registered past moment (no fabricated callback).
- [ ] **COPILOT-02**: A second **vocabulary/register callback** calls back phrasing/moves the DJ has made before — cited, warm, non-nagging (reuses the v5.0 actionable-not-hype coach persona discipline + cooldown/pacing).
- [ ] **COPILOT-03**: The copilot voice carries **no anti-features** — no next-track recommendation, no LLM-extracted "tendencies"/insights presented as fact, no settings-screen personalization, no continuous audio embedding (explicit anti-slop exclusions, enforced by review).

---

## Future Requirements (deferred — next milestone)

- **Multimodal moment-audio embedding** — v1 is text-signature-only; embedding the actual moment audio (gemini-embedding-2's audio path, ~180s cap, 32× cost) is future, gated on text-retrieval proving insufficient.
- **Cross-session "arc" priors** — longer-horizon narrative memory (a set's emotional arc learned across many sessions) beyond per-moment recall.
- **Memory-driven pre-set prep** — surfacing "you tend to open with X" before a set starts (forward-looking, not just in-set recall).
- **ProDJ Link / live key-detection as primary sources** — unchanged carry-forward from v5.0.

## Out of Scope (this milestone)

- **Next-track recommendation** — prediction, not retrieval; re-opens the core hallucination class (PROJECT.md Out-of-Scope).
- **LLM-extracted insights/tendencies** — the single most dangerous candidate (cites invented tendencies as fact); the no-extraction rule is locked (`mem0-rejected` audit: 97.8% junk).
- **Managed memory frameworks** — Mem0 / Letta / Zep / Cognee all rejected; DIY sqlite-vec + Gemini Embedding only.
- **Settings-screen personalization** — Phase 32's ~2KB DJ profile already covers configured prefs; v6.0 personalization is emergent from retrieval, not configured.
- **Any new AI provider / CLAP / MERT / OpenL3 / torch** — Gemini-only held.
- **Any new ws port / Python delivery change** — one-socket invariant; recall surfaces on existing IPC envelopes + the citation strip.

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| STORE-01 | Phase 63 | ✅ Complete (Plan 63-02 — storage spine, numpy fallback, parity) |
| STORE-02 | Phase 63 | ✅ Complete (Plan 63-02 — MemoryStore add_record/query_topk, raw-in/raw-out) |
| STORE-03 | Phase 63 | ✅ Complete (Plan 63-03 — atomic cascade + path-traversal gate + retention sweep + orphan reconcile) |
| STORE-04 | Phase 63 | ✅ Complete (Plan 63-02 — embedding via model_router.resolve, no literal) |
| INGEST-01 | Phase 64 | Complete |
| INGEST-02 | Phase 64 | Complete |
| INGEST-03 | Phase 64 | Complete |
| RECALL-01 | Phase 65 | Complete |
| RECALL-02 | Phase 65 | Pending |
| RECALL-03 | Phase 65 | Complete |
| RECALL-04 | Phase 65 | Complete |
| COPILOT-01 | Phase 66 | Pending |
| COPILOT-02 | Phase 66 | Pending |
| COPILOT-03 | Phase 66 | Pending |

**Coverage:** 14/14 requirements mapped to exactly one phase each — no orphans, no duplicates (STORE-01..04 → Phase 63 · INGEST-01..03 → Phase 64 · RECALL-01..04 → Phase 65 · COPILOT-01..03 → Phase 66). Mapped by the roadmapper 2026-05-22.
