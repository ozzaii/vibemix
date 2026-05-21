# Project Research Summary

**Project:** vibemix — v6.0 "The Memory Turn" (session-memory / embedding-retrieval copilot layer)
**Domain:** Local embedded vector memory grafted onto a grounded, anti-slop, real-time DJ co-host
**Researched:** 2026-05-22
**Confidence:** HIGH

## Executive Summary

v6.0 turns vibemix from a reactive **co-host** into a forward-leaning **copilot**: every finished session feeds an embedding store, and live coach prompts ground in *past* sessions, not just the current moment. Personalization is emergent from the retrieval seam — not a settings screen, not an LLM-summarized profile. The decisive finding, on which all four researchers independently converged, is that **this is a WIRING/REUSE milestone, not a greenfield build, with ZERO net-new dependencies.** vibemix already shipped the entire embed → cosine-top-k → cited-evidence machine in v2.1/v3.0 under `src/vibemix/library/` (`index_sqlite_vec.py`, `embed.py`, `_cosine.py`, `store.py`, `grounding.py`). `sqlite-vec>=0.1.9` is already in `pyproject.toml:118`, already installed, and already bundled inside the signed Apple/SignPath sidecar. The memory layer is a second store file (`memory.db`), a ~50-line wrapper, a deterministic ingest job, and one extra evidence line — all built on the proven primitives.

The recommended approach is the build-order spine all four agents agreed on: **STORE → INGEST → RETRIEVE → COPILOT MOVE.** STORE clones `SqliteVecStore`/`open_store` and reuses `cosine_topk` verbatim (Mac/Win bit-identical parity, free numpy fallback). INGEST runs **off the hot path** (post-session executor + boot sweep, mirroring the crash-sweep), joining each `event` + `llm_invoke` + `ai_text` triple from `events.jsonl` into a deterministic **text signature** — NO audio embedding in v1, NO LLM-extraction ever. RETRIEVE adds a new existence-only `recall` evidence source that flows through the EXISTING `CitationLinter` with **zero new linter code** (exactly how Phase 59 added `key`), injected as a gated `recall[…]` block in `coach.py:evidence_line` (copying the Phase 59 `decks[…]` gate), with a ~0.7 similarity floor, top-k 2–3 cap, and a PAST-tense / "FROM A PAST SESSION" fence. The COPILOT MOVE — a linter-grounded transition-shape callback, then a vocabulary callback — is the visible proof built last.

The key risk is **retrieval poisoning** — irrelevant past moments injected into the live prompt, producing confidently-wrong "you usually..." callbacks. For a product whose entire thesis is "no AI slop, no hallucination," a poisoned memory footer is an existential, release-blocking failure. The mitigation is structural, not a prompt plea: a hard similarity floor (below ~0.7 → inject nothing; empty retrieval is the correct, frequent state), small-k cap (one good callback beats ten weak ones), event-gating (only TRACK_AWARE_EVENTS, never HEARTBEAT), and the `recall` citation linter that makes a fabricated callback uncitable-by-construction. **RETRIEVE is therefore the anti-slop release-gate phase.** A second, parallel risk lives on the external clock: signing the `vec0.dylib`/`vec0.dll` native binaries and proving a clean-VM memory round-trip — flag this early because it rides Apple notarization + SignPath. Critically, all **four cardinal invariants** (single-writer, citation-grounding, trust-the-audio, one-socket) are *preserved by reuse* — memory never writes `MusicState`, never opens a new port, and never overrides the live ears.

## Key Findings

### Recommended Stack

The memory layer introduces **no new third-party packages**. `sqlite-vec>=0.1.9`, `google-genai>=2.0.1`, `numpy>=2.4.4`, `scipy>=1.17.1` are all already core deps. The entire layer is a pure-Python wrapper + a new data file on top of the already-shipped `library/` subsystem. sqlite-vec ships a tiny (~160 KB) prebuilt per-OS extension binary with no compiler dependency, and the one platform gap (Windows ARM64 has no wheel) is *already handled* by the existing `open_store()` numpy-fallback probe. One-click install is GREEN — the only new artifact is a data file, which has zero signing surface (the *binary* `vec0.*` was already signed in shipping builds). See `STACK.md`.

**Model-ID correction to surface to Kaan:** the locked literal "`gemini-embedding-001`" is the **text-only GA** model (no audio Parts). The milestone's stated multimodal/audio intent maps to **`gemini-embedding-2`**. **Never hardcode either** — call `model_router.resolve("embedding")` (the codebase already probes the live GA id via `EMBEDDING_GA_CANDIDATES` + a CI grep gate forbids literals). Since v1 ingest is text-signature-only, the cheaper text-001 path is even viable as a one-line config choice; default stays the multimodal model per milestone intent.

**Core technologies:**
- **sqlite-vec `0.1.9`** (already pinned): `vec0` vector store for `memory.db` — REUSE the shipped `SqliteVecStore` pattern; storage-only, rank in Python.
- **google-genai + `gemini-embedding-2`** (via Bravoh proxy): `embed_content` for deterministic text-signature embeds — REUSE `LibraryEmbedder` verbatim (768-dim MRL, content-hash cache).
- **numpy `cosine_topk` / `_cosine.py`** (already core): the single ranking chokepoint — REUSE verbatim for Mac/Win bit-identical parity.
- **stdlib `sqlite3`** (bundled, 3.12): DB + extension host — no new dep.

### Expected Features

The acid test gates every candidate: *"Does retrieving this close a hallucination class OR unlock a copilot move?"* If neither, it is an anti-feature. See `FEATURES.md`.

**Must have (table stakes):**
- **Session-close ingest of reaction-moment records** — the `event`+`llm_invoke`+`ai_text` triple as a deterministic text signature; batch (FLEX tier), off the hot path. No memory without ingest.
- **Second sqlite-vec store (`memory.db`) per-install, retention-capped** — the storage spine; mirror `open_store()`.
- **Retrieval seam (top-k 2–3, cosine × recency, ~0.7 relevance floor, event-gated)** — the mechanism IS the product.
- **`recall` evidence source + linter coverage** — the anti-slop contract must extend to memory (HARD GATE; ship this before retrieval injection).
- **Graceful empty-memory behavior** — first/below-threshold session behaves byte-identically to v5.0; no "I don't remember anything" filler.

**Should have (competitive — where "copilot, not co-host" is won):**
- **Move 1 (headline): transition-shape callback** — "you've run this A→B blend a bunch — last time you killed the bass two bars earlier." Linter-grounded to a real `[recall:<id>]`, rare and earned.
- **Move 2 (texture): vocabulary/register callback** — the AI reuses the DJ's own phrasing across sessions; the *felt* "it remembers me" proof. Cheap, low-risk, keep subtle.

**Defer (v6.x / v7+):**
- **Session-summary-card ingest + cross-session arc priors** — "your last 3 sets peaked then sagged at ~40min"; depends on coarse session-card store, deferrable behind Moves 1–2.
- **Multimodal moment-audio embedding** — only if text-signature retrieval proves insufficient (audio is the 32× cost path).
- **Next-track / "play this next" recommendation** — explicitly FORBIDDEN for v6.0 (prediction, not retrieval — re-opens the core hallucination class; PROJECT.md defers to v1.1).

### Architecture Approach

A new sibling package `src/vibemix/memory/` (NOT inside `library/`) that *imports from* `library/` (`embed.py`, `_cosine.py`, `index_sqlite_vec.py`) rather than forking — so the cosine-parity and embed-cache guarantees are shared. The hot reaction path keeps its shape: the only live-path change is one gated evidence line in `AICoach.evidence_line` and one new existence-only citation source. Ingest is the sole writer to `memory.db`, runs post-session in an executor + a boot sweep, and never touches `MusicState` or the coach loop. See `ARCHITECTURE.md`.

**Major components:**
1. **MemoryStore** (`memory/store.py`) — vec0-backed store, clone of `LibraryStore`; `search()` calls the shared `cosine_topk`; free numpy fallback via `open_store()`.
2. **SessionIngestor + sweep** (`memory/ingest.py`) — reads a session dir's artifacts → typed `MemoryRecord[]` → embed → `add_batch`; idempotent via a `memory_ingested` marker + content-hash cache.
3. **MemoryRetriever** (`memory/retriever.py`) — clone of `library/grounding.py::Grounding`; event-gated, executor-offloaded, deadline-bounded recall; returns a frozen snapshot read in `llm_node`.
4. **`recall` evidence source + gated `recall[…]` line** — additive entries in `EVIDENCE_SOURCES` + `CITATION_GRAMMAR_BLOCK` + `coach.py:evidence_line`; the `CitationLinter` is UNCHANGED.

### Critical Pitfalls

See `PITFALLS.md` for all seven plus the "looks done but isn't" checklist.

1. **Retrieval poisoning (the headline, release-blocking)** — low-similarity moments injected as if relevant → confidently-wrong callbacks. Avoid: hard ~0.7 floor (below → inject *nothing*), small-k cap (2–3), event-gating, PAST/citable fence, live audio always wins. Empty retrieval is correct and frequent.
2. **Confabulation via an LLM-extraction step** — summarizing a session into "facts" and embedding those invents load-bearing, self-reinforcing hallucinations (Mem0 #4573: 97.8% junk). Avoid: raw-in/raw-out, deterministic text signatures only, CI guard that fails if ingest calls any chat/generation model (only `embed_content` allowed).
3. **sqlite-vec one-click-install fragility** — `vec0.*` extension fails on clean target machines (missing wheel, unsigned binary, PyInstaller blind spot, "module not found" on Win). Avoid: inherit the `open_store()` probe-and-fallback verbatim; sign+notarize `vec0.dylib`/`vec0.dll`; clean-VM (incl. ARM64 Win) memory round-trip in the e2e matrix. On the external-signing critical path — flag early.
4. **Embedding-everything bloat / hot-path latency** — audio-everything (32× cost) breaks the €50/mo gate; synchronous query-embed blows the 1500ms TTFT budget. Avoid: acid-test scope, structured-text-first, reuse `budget.py` gate + content-hash cache; event-gate + executor-offload + cache + hard deadline on the query embed (late memory is worse than no memory).
5. **Stale / cross-session leakage** — old style calcifies; the current session self-references. Avoid: cosine×recency time-weight (research-decide the half-life), exclude the in-progress session (natural, since ingest is post-session), tag every record with session-id + timestamp. Plus **privacy/retention** (Pitfall 6): delete must cascade to embeddings, reuse `recordings_index.py` retention + path-traversal defense, confine writes to the vibemix cache dir.

## Implications for Roadmap

The build-order spine is **dependency-correct and unanimous across all four researchers: STORE → INGEST → RETRIEVE → COPILOT MOVE.** Each phase is independently testable and the live reaction path is untouched until RETRIEVE.

### Phase 1: STORE — `memory.db` + MemoryStore + records
**Rationale:** No dependency on ingest or retrieval; unit-testable in isolation against an in-memory vec0 table. Foundation for everything downstream.
**Delivers:** `memory/store.py` (clone of `SqliteVecStore`/`open_store`, `vec_memory` table under `app_data_dir()`), `memory/records.py` (`MemoryRecord` + deterministic text-signature builders), retention/size budget scaffolding.
**Uses:** `sqlite-vec` + `_cosine.py::cosine_topk` (REUSE verbatim); `index_sqlite_vec` numpy fallback.
**Implements:** the storage spine; single-writer discipline; delete-cascades-to-embeddings via `recordings_index.py`.
**Avoids:** sqlite-vec install fragility (inherit `open_store()`); privacy/retention (Pitfall 6); cosine-fork parity break (P55).

### Phase 2: INGEST — session artifacts → typed embeddable records
**Rationale:** Depends on STORE (writes to it); fully decoupled from the live path — safe to land before any prompt touch. Runnable end-to-end against real `recordings/` dirs.
**Delivers:** `ingest_session(session_dir)` (session-close executor hook) + `sweep_uningested(recordings_root)` (boot sweep, mirrors crash-sweep); reaction-moment text signatures (event+llm_invoke+ai_text); batch embed (FLEX tier) via reused `LibraryEmbedder`.
**Uses:** `LibraryEmbedder` + content-hash cache (REUSE); `model_router.resolve("embedding")`.
**Implements:** off-hot-path batch ingest; raw-in/raw-out (no LLM-extraction); session-id + timestamp tagging for downstream filtering.
**Avoids:** confabulation/extraction (Pitfall 2 — CI guard: ingest calls only `embed_content`); embedding bloat (Pitfall 3 — acid-test scope, text-first, budget gate); current-session-leakage (tag at ingest).

### Phase 3: RETRIEVE — gated `recall[…]` seam + citation linter coverage (THE ANTI-SLOP GATE)
**Rationale:** Depends on STORE (reads it). This is the hallucination-gate phase and the one place the live path changes. Two sub-steps in order: (3a) add `recall` to `EVIDENCE_SOURCES` + grammar block (pure additive, no behavior change); (3b) build `MemoryRetriever` + wire the gated `recall[…]` line + per-turn registry registration.
**Delivers:** `memory/retriever.py` (clone of `Grounding`, event-gated, executor-offloaded, deadline-bounded); `recall` existence-only evidence source (ZERO new linter code, à la Phase 59 `key`); gated `recall[…]` block in `evidence_line` (copies the Phase 59 `decks[…]` gate); ~0.7 similarity floor; top-k 2–3 cap; cosine×recency blend; PAST-tense / "FROM A PAST SESSION" fence; current-session exclusion.
**Uses:** the event-gated embed→cosine→cited pattern from `grounding.py` (REUSE generalized from `track` to `recall`).
**Avoids:** retrieval poisoning (Pitfall 1 — floor + small-k + fence + linter); hot-path latency (Pitfall 5 — event-gate + executor + cache + deadline); stale leakage (Pitfall 7 — time-weight + exclude current session).
**Success criterion (HARD):** a below-threshold session produces *zero* memory-derived references; a fabricated `[recall:<id>]` strips the whole turn; TTFT p95 unchanged feature-on vs feature-off; v4 byte-identical baseline holds when memory is empty/cold.

### Phase 4: COPILOT MOVE — the visible proof
**Rationale:** Depends on RETRIEVE firing. The proof built last and ear-tested by Kaan (the hard quality gate).
**Delivers:** Move 1 (transition-shape callback) — a `recall` chip on the existing `SessionCohostReaction.citation_strip` + the coach naturally referencing a grounded past moment; then Move 2 (vocabulary callback) as v6.x texture.
**Avoids:** scripted-feeling callbacks (rare-and-earned, strong-match-only); the forbidden prospective "play this next" anti-move.
**Success criterion:** Kaan-ear pass that a recall fires grounded and does not feel scripted.

### Phase Ordering Rationale

- **Dependency-correct:** STORE has no upstream deps; INGEST writes to STORE; RETRIEVE reads STORE; the MOVE needs RETRIEVE firing. This is the order all four research files independently derived.
- **Live path protected until last needed:** STORE + INGEST land with *zero* changes to the reaction path (grep-gate that ingest never imports the coach loop). The live path only changes in RETRIEVE, behind a gate that preserves byte-identity when cold.
- **Anti-slop gate isolated:** retrieval poisoning, confabulation, and latency are all concentrated in INGEST (scope/extraction) and RETRIEVE (floor/fence/linter/latency), so the release-gate work is contained and verifiable.
- **External-clock item flagged early:** sqlite-vec native-binary signing + clean-VM round-trip belongs to STORE/installer work but rides the Apple/SignPath clock — surface it at roadmap time so it parallelizes against the external approvals already on the critical path.

### Research Flags

Phases likely needing deeper research during planning (`/gsd:plan-phase --research-phase`):
- **Phase 2 (INGEST):** the "which artifacts ground best" question is explicitly the first phase's research per the thesis — `coach_line` vs `moment` vs (stretch) `audio_moment` taxonomy. Recommend starting text-only; resolve scope here, not by default.
- **Phase 3 (RETRIEVE):** the **cosine-only vs cosine + time-weight blend and half-life** is an explicit open question — tune the *shape* (two-term, exp-decay-on-sessions, relevance floor) against Kaan's real session corpus. Also tune the exact recall threshold (start at `grounding.py`'s 0.7).

Phases with standard patterns (lighter research):
- **Phase 1 (STORE):** a near-verbatim clone of the shipped `library/store.py` + `index_sqlite_vec.py`; the pattern is proven. The only research-ish item is the **retention/size budget per install** (reuse `library/budget.py` + `staleness.py` machinery).
- **Phase 4 (COPILOT MOVE):** the surfacing seams (`citation_strip`, `ipc.session.*`) already exist; the real gate is Kaan's ear, not research.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Both core deps already declared + installed + bundled in the signed sidecar; live versions verified against PyPI + official Gemini docs + Context7 + a dev-box probe. |
| Features | HIGH | Acid test applied per-candidate against the locked thesis; copilot moves + anti-features map directly to PROJECT.md scope; corroborated by Stanford Generative Agents + temporal-RAG + RAG-poisoning literature. |
| Architecture | HIGH | Every integration point read from live `src/vibemix/` source (not training data); the four cardinal invariants traced to their current owners; build order is dependency-verified. |
| Pitfalls | HIGH | Most pitfalls map to patterns vibemix already shipped (P55/P56/grounding thresholds); the two load-bearing items (poisoning, confabulation) corroborated by external sources + the Mem0 rejection audit. |

**Overall confidence:** HIGH

### Gaps to Address

- **Artifact taxonomy (which records ground best):** intentionally left open as Phase 2 (INGEST) research. Recommendation: start text-only (`coach_line` + `moment` signatures); audio-moment is a v6.x stretch gated on text proving insufficient.
- **Retrieval blend + half-life:** cosine-only vs cosine×recency, and the decay half-life (in *sessions*, not hours). Recommended shape is two-term exp-decay with a relevance floor; exact weights are Phase 3 tuning on Kaan's corpus. Default cosine-only is acceptable for a first cut.
- **Retention / size budget per install:** rows + bytes cap and sweep policy. Reuse `library/budget.py` + `recordings_index.py` retention sweep; decide the cap in STORE.
- **Recall threshold:** start at 0.7 (the shipped `CITATION_THRESHOLD`); tune by Kaan-ear in Phase 3/4.
- **Model-ID decision:** confirm `gemini-embedding-2` (multimodal, default per milestone intent) vs cheaper text-001 with Kaan — but never hardcode either; route via `model_router.resolve("embedding")`.

## Sources

### Primary (HIGH confidence)
- `src/vibemix/library/{store,index_sqlite_vec,embed,_cosine,grounding,budget}.py` — the shipped sqlite-vec + Gemini Embedding 2 + cosine_topk + event-gated grounding subsystem (the reuse target)
- `src/vibemix/state/{coach,evidence_registry}.py` + `coach/citation_linter.py` + `prompts/matrix.py` — the retrieval injection seam, citation grammar/linter, PAST-tense + lookahead framing fences
- `src/vibemix/audio/recorder.py` — `events.jsonl` schema + crash-sweep pattern (ingest source + mirror)
- `src/vibemix/runtime/{config_store,recordings_index,ws_bus}.py` — `app_data_dir()`, delete/retention/path-traversal defense, the one socket
- `pyproject.toml:118` — `sqlite-vec>=0.1.9` already committed
- `.planning/notes/v-next-memory-turn.md` + `.planning/notes/mem0-rejected-2026-05-18.md` + PROJECT.md — locked thesis, acid test, anti-feature list, Mem0 confabulation audit
- Dev-box probe (executed 2026-05-22): `sqlite_vec 0.1.9`, `vec0.dylib` Mach-O arm64 162 KB, `google-genai 2.0.1`, `sqlite3 3.50.4`
- Gemini API docs (Embeddings / Pricing / Rate limits), Context7 `/asg017/sqlite-vec`, PyPI `sqlite-vec` + `google-genai`

### Secondary (MEDIUM confidence)
- [Park et al., Generative Agents (2304.03442)](https://ar5iv.labs.arxiv.org/html/2304.03442) — relevance+recency+importance retrieval score, exp decay
- [RAG poisoning / distractor literature (arXiv 2412.16708, 2512.14313)](https://arxiv.org/pdf/2412.16708) — irrelevant retrieved context degrades generation; precision collapse with large k (the small-k + floor guards)
- Temporal-RAG sources (Towards Data Science, arXiv 2509.19376) — cosine-only surfaces stale; recency reranking
- [sqlite-vec issues #13, #45](https://github.com/asg017/sqlite-vec/issues/45) + Alex Garcia Python notes — Windows extension-load fragility, default-SQLite-lacks-extensions

### Tertiary (LOW confidence)
- Gemini preview pricing/rate-limit specifics (single-vendor doc + aggregators; preview values may shift — bind the proxy key, not end-users)
- Single-source RAG hallucination-threshold blogs (corroborative only)

---
*Research completed: 2026-05-22*
*Ready for roadmap: yes*
