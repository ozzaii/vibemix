# vibemix — Roadmap

**Project:** vibemix — AI DJ Co-Host
**Last shipped:** v5.0 "The Useful Cut" — 2026-05-22 (tech_debt accepted; KAAN-ACTION live-confirm items ride forward)
**Current milestone:** v6.0 "The Memory Turn" — ACTIVE (planning) — Phases 63–66
**Open alongside:** v4.0 "SHIP" — engineering-complete (8/8), publish gated on the external signature clock (NOT archived)

---

## Milestones

- ✅ **v0.1.0 MVP Foundation** — Phases 1–14 (shipped 2026-05-13) — see `.planning/milestones/v0.1.0/`
- ✅ **v2.0 Research-Driven Ship** — Phases 15–26 (shipped 2026-05-14, tech_debt accepted) — see `.planning/milestones/v2.0-ROADMAP.md`
- ✅ **v2.1 The Unified Cut** — Phases 27–39 (shipped 2026-05-16, tech_debt accepted) — see `.planning/milestones/v2.1-ROADMAP.md`
- ✅ **v3.0 Clean OSS Ship** — Phases 40–45 (shipped 2026-05-17, tech_debt accepted) — see `.planning/milestones/v3.0-ROADMAP.md`
- ✅ **v3.1 Distribution-Ready Pass** — Phases 46–50 (shipped 2026-05-18, tech_debt accepted) — see `.planning/milestones/v3.1-ROADMAP.md`
- 🟡 **v4.0 SHIP** — Phases 51–58 (engineering-complete 8/8, publish on signature clock — NOT archived) — see "v4.0 SHIP" section below
- ✅ **v5.0 The Useful Cut** — Phases 59–62 (shipped 2026-05-22, tech_debt accepted) — see `.planning/milestones/v5.0-ROADMAP.md`
- 🔵 **v6.0 The Memory Turn** — Phases 63–66 (ACTIVE — planning) — see "v6.0 The Memory Turn" section below

---

# v6.0 "The Memory Turn" — ACTIVE (planning)

> **Status:** Active milestone. vibemix shifts from a *reactive* co-host to a *forward-leaning* **copilot** — every finished session feeds a local embedding store, and live coach prompts ground in *past* sessions, not just the current moment. Personalization is **emergent from the retrieval seam**, not a settings screen and not an LLM-summarized profile. This is a **WIRING / REUSE milestone with ZERO net-new dependencies** — `sqlite-vec>=0.1.9` is already declared/installed/signed-in-sidecar, and the entire embed → `cosine_topk` → cited-evidence machine already ships under `src/vibemix/library/`. The memory layer is a second `memory.db` + a ~50-line wrapper + an off-hot-path ingest job + one gated evidence line + one new existence-only `recall` citation source.

## Overview (v6.0)

The decisive research finding (4 convergent agents, HIGH confidence — `.planning/research/SUMMARY.md` + `ARCHITECTURE.md`): this is **not a greenfield build**. vibemix already shipped the working sqlite-vec store (`library/index_sqlite_vec.py`), the Gemini-Embedding-2 client with content-hash cache (`library/embed.py`), the single-chokepoint top-K math (`library/_cosine.py::cosine_topk`), and — crucially — the **event-gated embed→cosine→cited-evidence pattern** end-to-end (`library/grounding.py` → `[track:<id>]`). The retrieval seam is that exact shape generalized from `track` to `recall`.

The product's hard line holds: **grounded, never hallucinating, no AI slop.** The new headline hallucination class is **retrieval poisoning** — an irrelevant past moment injected into the live prompt so the AI references something that didn't happen. For a product whose entire thesis is "no AI slop," a poisoned memory footer is an existential, release-blocking failure. The mitigation is **structural, not a prompt plea**: a hard ~0.7 similarity floor (below → inject *nothing*; empty retrieval is the correct, frequent state), a small top-k cap (2–3 — one good callback beats ten weak ones), event-gating (only track-aware events, never HEARTBEAT), a PAST-tense "FROM A PAST SESSION" fence, current-session exclusion, and a new `recall` citation source that makes a fabricated `[recall:<id>]` **uncitable-by-construction** (the existing `CitationLinter` strips the whole turn, exactly like the Phase 59 `key:` source). **RETRIEVE (Phase 65) is therefore the anti-slop release-gate phase.**

The build-order spine is **dependency-correct and unanimous across all four researchers: STORE → INGEST → RETRIEVE → COPILOT MOVE.** Each phase is independently testable and the live reaction path is untouched until RETRIEVE. STORE + INGEST land with *zero* changes to the reaction path (a grep-gate enforces that ingest never imports the coach loop); the live path only changes in RETRIEVE, behind a gate that preserves byte-identity when memory is cold/empty. All **four cardinal invariants** (single-writer, citation-grounding, trust-the-audio, one-socket) are *preserved by reuse* — memory never writes `MusicState`, never opens a new port, never overrides the live ears.

This is a memory-layer graft on an already-mature grounded co-host. No new AI providers, no CLAP/MERT/OpenL3/torch, no managed memory framework (Mem0/Letta/Zep/Cognee all rejected), no LLM-extraction layer, no new ws port, no next-track recommendation. The v4.0 external signature clock is unchanged.

## Phases (v6.0)

**Phase Numbering:** Continues from v5.0 (closed at Phase 62). v6.0 starts at **Phase 63** and runs through **Phase 66**. Integer phases (63, 64, …) = planned milestone work; decimal phases (e.g. 65.1) = urgent insertions if needed.

- [x] **Phase 63: Memory Store** - A local per-install `memory.db` (sqlite-vec) + a ~50-line `MemoryStore` wrapper, cloned from the shipped `library/` store/cosine/embed-cache primitives (zero new dependency), with Mac/Win bit-identical `cosine_topk` parity + numpy fallback, retention + delete-cascade, and embedding routed via `model_router.resolve("embedding")` on the FLEX cost lane. No live-path touch. (3 plans, 3 waves.) **COMPLETE 2026-05-22 — STORE-01..04 GREEN, 19/19 tests/memory/ pass.**
- [ ] **Phase 64: Session Ingest** - An off-hot-path post-session batch job (+ boot-time sweep) that turns each session's existing artifacts (`events.jsonl` + cited evidence + `ai_text`) into deterministic TEXT "reaction moment" records — NO audio embedding, NO LLM-extraction (CI-guarded) — every record `session_id`/timestamp-tagged. Depends on 63.
- [ ] **Phase 65: Memory Retrieval Seam (ANTI-SLOP RELEASE GATE)** - A new existence-only `recall` evidence source (zero new linter code, à la Phase 59 `key`) + a gated `recall[…]` block in `coach.py::evidence_line` (copy the Phase 59 `decks[…]` gate → cold-memory golden byte-identical), top-k 2–3 cap, ~0.7 similarity floor, PAST-tense fence, current-session excluded, cosine-vs-time-weight blend tuned in-phase on Kaan's real corpus. **Kaan-ear veto.** Depends on 63 + 64.
- [ ] **Phase 66: Visible Copilot Move** - A linter-grounded transition-shape callback + a vocabulary/register callback — cited, warm, non-nagging — that prove retrieval is firing, with NO anti-features (no next-track rec, no LLM-extracted "tendencies", no settings-screen personalization, no continuous audio embedding). Depends on 65.

## Phase Details (v6.0)

### Phase 63: Memory Store
**Goal**: A local, per-install vector store for embedded session "moments" exists and is proven correct — built entirely on the shipped `library/` primitives with zero new dependency, single-writer-disciplined, retention-bounded, and Mac/Win rank-identical. This is the storage spine everything downstream reads and writes; it has no dependency on ingest or retrieval and is unit-testable in isolation.
**Depends on**: Nothing (first v6.0 phase — INGEST writes to it, RETRIEVE reads it)
**Requirements**: STORE-01, STORE-02, STORE-03, STORE-04
**Success Criteria** (what must be TRUE):
  1. A per-install `memory.db` sqlite-vec store accepts an embedded record (`session_id` + timestamp + raw text signature + embedding) via a ~50-line `MemoryStore` wrapper exposing `add_record` + `query_topk`, and returns the correct top-k on query — reusing the shipped `SqliteVecStore` + the deterministic `cosine_topk` chokepoint (no forked KNN).
  2. On a host where the sqlite-vec extension can't load, the store falls back to the existing NumpyStore and produces bit-identical top-k rank order to the sqlite-vec path (Mac/Win parity, `pytest -m parity` green).
  3. Deleting a session's recordings cascades to its memory embeddings — no orphaned vectors remain — and a per-install size/retention budget caps growth; everything is local-only, user-deletable, and confined to the app cache dir (path-traversal defended).
  4. Every embed call resolves the model via `model_router.resolve("embedding")` (no hardcoded `gemini-embedding-001` literal — CI grep gate green) and routes through the Bravoh proxy on the `ServiceTier.FLEX` cost lane; a record carries the raw text signature only — never an LLM-extracted "insight" (raw-in, raw-out).
**Plans**: 3 plans
- [x] 63-01-PLAN.md — Wave 0: scaffold the full tests/memory/ contract suite (parity, round-trip, fallback, cascade, path-traversal, no-live-import, no-extraction, retention)
- [x] 63-02-PLAN.md — Wave 1: SqliteVecMemoryStore (vec_memory + moments table) + MemoryStore facade + open_memory_store probe (STORE-01/02/04)
- [x] 63-03-PLAN.md — Wave 2: hardened delete-cascade + path-traversal gate + oldest-session-first retention sweep + orphan reconciliation (STORE-03)
**Research/KAAN-ACTION flag**: sqlite-vec one-click-install fragility — the `vec0.dylib`/`vec0.dll` native binaries must be signed/notarized and a clean-VM (incl. Windows ARM64) memory round-trip proven in the e2e matrix. This rides the Apple notarization + SignPath external clock already on the critical path — surface it early so it parallelizes against the in-flight approvals. (The *binary* was already signed in shipping builds; the new artifact is only a data file with zero new signing surface, but the clean-VM round-trip is the proof item.)

### Phase 64: Session Ingest
**Goal**: Each finished session's existing artifacts become typed, embeddable "reaction moment" records — deterministic TEXT signatures only, embedded off the hot path, with NO LLM-extraction between session and embedding. This is fully decoupled from the live reaction path: it runs on dead session data in an executor and can land before any prompt touch.
**Depends on**: Phase 63 (writes to `memory.db`)
**Requirements**: INGEST-01, INGEST-02, INGEST-03
**Success Criteria** (what must be TRUE):
  1. After a session closes, an ingest job reads that session's `events.jsonl` + cited evidence + `ai_text` and writes typed "reaction moment" records (deterministic text signatures) to `memory.db` — no audio embedding in v1, and a CI guard asserts the ingest path calls only `embed_content` (never any chat/generation model — extraction is structurally impossible).
  2. Ingest runs strictly off the hot path: at session-close in a batch (FLEX tier) via `run_in_executor`, plus a boot-time sweep that re-ingests crashed/missed sessions (mirroring the recorder crash-sweep) — it never touches `MusicState`, never holds `state._lock`, never imports the coach loop (grep gate green).
  3. Re-ingesting an already-ingested session is idempotent and costs 0 API calls (signature-keyed content-hash embed cache + a `memory_ingested` marker reconciled against `moments` existence), and every record is `session_id`/timestamp-tagged so it can later be excluded from its own session's retrieval and cascade-deleted.
  4. The embedded moment taxonomy ("which artifacts ground best") is RESOLVED in-phase against the acid test (64-RESEARCH §Taxonomy Decision) to exactly ONE v1 kind — **`coach_line`** (an emitted `ai_text` reaction + its preceding-event context + inline citation tokens): the only artifact that closes a hallucination class AND unlocks a Phase-66 copilot move. `moment` (a bare structural event, re-derivable live) is **CUT**; `audio_moment` (multimodal) is **DEFERRED** to a future milestone. Silenced `citation_strip` lines are NOT ingested (embedding a never-heard line is confabulation).
**Plans**: 3 plans (3 waves)
- [x] 64-01-PLAN.md — Wave 0: RED-first tests/memory/test_ingest.py contract (signature determinism, coach_line emission + citation_strip skip, idempotent re-ingest, tagging, embed-cache hit, sweep path-defense) + synthetic events.jsonl fixture + the ingest no-live-path subprocess dormancy assertion
- [x] 64-02-PLAN.md — Wave 1: src/vibemix/memory/ingest.py — build_coach_line_signature + _read_events mirror + signature-keyed embed cache + memory_ingested marker + ingest_session + run_ingest_sweep (path-traversal-defended) — flips the contract GREEN (INGEST-01/02/03)
- [x] 64-03-PLAN.md — Wave 2: runtime wiring — session-close (on_session_close) + boot (run_boot_sweeps) ingest enqueue via run_in_executor, one-way runtime→ingest, best-effort/never-raise (INGEST-02)
**Research flag (RESOLVED)**: the "which artifacts ground best" taxonomy question is closed by 64-RESEARCH §Taxonomy Decision — ONE kind (`coach_line`), text-signature only, no audio, no LLM-extraction. Re-expansion to `moment`/`audio_moment` is gated on Phase-65 retrieval proving `coach_line` insufficient against Kaan's real corpus, never by default.

### Phase 65: Memory Retrieval Seam (ANTI-SLOP RELEASE GATE)
**Goal**: At reaction time, the coach prompt is grounded with top-k *past* moments — citable-by-construction, fenced past-tense, subordinate to the live audio, and structurally anti-poisoning — so the AI can call back a real past moment while a fabricated recall strips the whole turn. This is the one phase that touches the live reaction path, and the hallucination-gate phase: retrieval poisoning, latency, and staleness are all concentrated and verified here. **This is the milestone's anti-slop release gate.**
**Depends on**: Phase 63 (reads `memory.db`) + Phase 64 (needs ingested records to retrieve)
**Requirements**: RECALL-01, RECALL-02, RECALL-03, RECALL-04
**Success Criteria** (what must be TRUE):
  1. A new existence-only `recall` evidence source is added to `EVIDENCE_SOURCES` and flows through the **existing** `CitationLinter` with zero new linter code (à la Phase 59 `key`) — each retrieved `record_id` is registered before the LLM call, and a fabricated `[recall:<id>]` the registry never saw strips the whole turn.
  2. The coach prompt is grounded via a gated `recall[…]` block in `state/coach.py::evidence_line` (copying the Phase 59 `decks[…]` gate verbatim) — top-k 2–3 cap, ~0.7 similarity floor, event-gated to track-aware events — and when memory is cold/empty/below-floor the prompt is **byte-identical** to the v5.0 baseline (golden test green; no "I don't remember anything" filler).
  3. Retrieval is anti-poisoning by construction: below-floor injects nothing; retrieved moments are fenced PAST-tense ("FROM A PAST SESSION") so they can never be read as live evidence; and the current in-progress session is excluded from its own retrieval.
  4. Retrieval stays off the hot path and within the €50/mo budget gate (event-gate + executor-offload + content-hash cache + hard deadline — late memory is worse than no memory), TTFT p95 is unchanged feature-on vs feature-off, and all four cardinal invariants hold (single-writer, citation-grounding, trust-the-audio, one-socket).
**Plans**: 4 plans
- [x] 65-01-PLAN.md — Wave 0 RED-first test scaffold (poisoning RED, byte-identical cold golden, lockstep 8→9 count updates)
- [x] 65-02-PLAN.md — `recall` vocabulary across schema-mirror sites 1-3 (sites 1+2 lockstep — silent-poisoning-hole guard); zero new linter code
- [x] 65-03-PLAN.md — `MemoryRecall` service (Grounding clone): event-gate, 0.7 floor, current-session-excluded, cosine-only, no live-path import
- [x] 65-04-PLAN.md — live-path wiring: gated `recall[…]` block + off-loop pre-dispatch/deadline + register survivors + clear (behind `recall_enabled`)
**Research/KAAN-ACTION flag**: (1) the cosine-only vs cosine+time-weight blend and the decay half-life (in *sessions*, not hours) is an explicit open question — tune the shape (two-term exp-decay + relevance floor) and the exact recall threshold (start at 0.7) against Kaan's real session corpus in-phase (`/gsd:plan-phase --research-phase`). (2) Ships behind a **Kaan-ear veto** on retrieval relevance (mirrors the Phase 60 harmonic veto) — no callback that references a moment Kaan's ear says didn't matter; this is the hard quality gate.

### Phase 66: Visible Copilot Move
**Goal**: At least one — ideally two — end-user-noticeable copilot moves prove retrieval is firing: the AI calls back a transition shape it has seen the DJ make, and reuses the DJ's own phrasing across sessions. Each is linter-grounded (must resolve to a real registered past moment), rare-and-earned, warm, and non-nagging — the felt "it remembers me" proof, built last and gated on Kaan's ear.
**Depends on**: Phase 65 (retrieval must be firing for a copilot move to ground in)
**Requirements**: COPILOT-01, COPILOT-02, COPILOT-03
**Success Criteria** (what must be TRUE):
  1. A transition-shape callback ("last time you ran this blend you killed the bass two bars earlier") fires as an end-user-noticeable copilot move — linter-grounded so the comparison must resolve to a real registered `[recall:<id>]` past moment (a fabricated callback strips the turn), surfaced on the existing `SessionCohostReaction.citation_strip` (no new socket/port).
  2. A second vocabulary/register callback reuses phrasing/moves the DJ has made before — cited, warm, and non-nagging — reusing the v5.0 actionable-not-hype coach persona discipline + cooldown/pacing.
  3. The copilot voice carries no anti-features — no next-track recommendation, no LLM-extracted "tendencies"/insights presented as fact, no settings-screen personalization, no continuous audio embedding (enforced by review).
  4. Kaan's ear confirms a recall actually fires grounded on real session data and does not feel scripted (the hard quality gate).
**Plans**: 2 plans
- [x] 66-01-PLAN.md — Wave 0 RED-first contract: 9 new tests pin chip allow-list, fragment helper, byte-identity baseline, cooldown gate + new tests/repo/test_no_recall_antifeatures.py static gate (COPILOT-01/02/03)
- [x] 66-02-PLAN.md — Wave 1 GREEN: dj_cohost.py allow-list + recall verb branch + RECALL_CALLBACK_COOLDOWN_S + cooldown gate/arm; coach.py recall_fragment_for_event helper + 2 templates + build_prompt integration; 66-HUMAN-UAT.md + §RECALL-EAR in KAAN-ACTION-LEGAL.md (COPILOT-01/02/03)
**UI hint**: yes — the recall chip surfaces on the existing `SessionCohostReaction.citation_strip` / floating pill (a small additive touch on a Tier-1 live surface; the `frontend-enforcement` skill governs the chip's CDJ-Whisper material/typography). No new socket, no new port — rides the existing `ipc.session.*` envelopes.

## Progress (v6.0)

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 63. Memory Store | v6.0 | 3/3 | Complete    | 2026-05-22 |
| 64. Session Ingest | v6.0 | 3/3 | Complete    | 2026-05-22 |
| 65. Memory Retrieval Seam | v6.0 | 4/4 | Complete    | 2026-05-22 |
| 66. Visible Copilot Move | v6.0 | 2/2 | Complete   | 2026-05-22 |

**Coverage:** 14/14 v6.0 requirements mapped ✓ (no orphans, no duplicates) — STORE-01..04 → P63 · INGEST-01..03 → P64 · RECALL-01..04 → P65 · COPILOT-01..03 → P66

---

# v5.0 "The Useful Cut" — SHIPPED 2026-05-22 (tech_debt accepted)

<details>
<summary>✅ v5.0 The Useful Cut (Phases 59–62) — SHIPPED 2026-05-22 (tech_debt accepted)</summary>

Deck-aware, actionable, unobtrusive. Full session-wide deck-state (pyrekordbox XML → Gemini-vision → numpy ladder) with a citable `key:` evidence source; a deterministic Camelot harmonic key-clash gate the LLM only narrates (ships **default-OFF** behind the Kaan-ear veto); an actionable-not-hype coach persona extending the `live-tuning-or-brain` branch (hype goldens regression-fenced); and a transparent, draggable, non-focus-stealing **floating pill** as the primary live surface (Three.js mascot kept opt-in/secondary, mascot-audit green). 4/4 phases, 17/17 requirements satisfied, 4/4 cross-phase integration seams WIRED. Tests at close: cargo 61/61 · vitest 787/787 · tsc clean · pytest at the 7-WIP `live-tuning-or-brain` branch baseline (zero new failures).

- [x] Phase 59: Full Deck Awareness + Grounding (5/5 plans) — 2026-05-21
- [x] Phase 60: Harmonic-Feedback Confidence Gate (4/4 plans) — 2026-05-21 (detector default-OFF until the Kaan-ear veto flip)
- [x] Phase 61: Actionable-Not-Hype Coach Persona (2/2 plans) — 2026-05-21
- [x] Phase 62: Floating Pill UI (5/5 plans) — 2026-05-22

**KAAN-ACTION (live-confirm, rides forward):** harmonic clash veto flip (`eval/harmonic/run_veto.py` → flip `harmonic_clash_enabled`), Gemini-vision accuracy-floor eval, coach live-ear pass + WR-01 prose-claim check, pill felt drag/focus/transparency/DMG/multi-monitor, live FLX4+djay deck-resolution. None gate the engineering close under `gsd-autonomous fully`.

**Git tag deferred** (consistent with v4.0): the `v5.0` tag + branch merge are Kaan's call on his clock — `live-tuning-or-brain` is unmerged and v4.0 is also untagged/open.

Full archive: `.planning/milestones/v5.0-ROADMAP.md` · Requirements: `.planning/milestones/v5.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v5.0-MILESTONE-AUDIT.md`

</details>


# v4.0 SHIP — OPEN (engineering-complete 8/8, publish on signature clock — NOT archived)

> **Status:** All 8 phases (51–58) are engineering-complete. The milestone is deliberately **left open and unarchived** — its public RC publish stays gated on the external signature clock (Apple Dev Agreement via Francesco + SignPath OSS cert). v5.0 runs as the active milestone alongside it. v4.0's KAAN-ACTION discharge surface lives in `KAAN-ACTION-LEGAL.md §SHIP-V4` + per-phase `*-HUMAN-UAT.md`. Do not delete or archive this section until the v4.0 publish lands.

## Overview (v4.0)

v3.1 left vibemix engineering-complete: a built Tauri app + Python sidecar, one-click installer chain, dependency-audited lockfile, full mascot scaffold, and an e2e harness — all green in CI, none of it yet driven on real hardware in a real DJ session. v4.0 closes that gap. For the first time the actual app runs on Kaan's MacBook with real audio through BlackHole and a real DDJ-FLX4 over USB.

The journey, finer-grained than the prior 4-phase cut so each real-hardware seam is its own validated checkpoint: **boot it and make it stable** (Phase 51) → **prove the audio path live and ground the features it derives** (Phase 52) → **prove the controller path live with clean fallback** (Phase 53) → **make hype mode actually fire grounded in-bar reactions on real audio** (Phase 54) → **make feedback mode coach grounded with clean citations** (Phase 55) → **hit peak performance + make the mascot react live** (Phase 56) → **final visual pass + close carryover bugs + tighten first-run** (Phase 57) → **get every engineering gate green on real artifacts and document the one-button ship** (Phase 58).

Bring-up is split into THREE input seams — boot/stability, audio, controller — because real hardware already surfaced distinct breaks in each (clean startup vs the 48 kHz capture path vs MIDI ingest), and each must be independently green before the modes that consume them can be validated. The two interaction modes get their own phases because hype and feedback have different failure shapes (hype: the AI voice currently does not fire on a detected drop; feedback: citation integrity), and each is its own Kaan-ear pass.

The signed public binary itself is gated on external signatures (Apple Dev Agreement via Francesco; SignPath OSS cert) — those stay KAAN-ACTION; engineering makes the release one-button-after-signatures. No phase depends on signatures landing.

This is bring-up + live validation + polish + ship of an **already-built** app. No new AI providers, no new detectors, no scope creep.

## Phases (v4.0)

**Phase Numbering:** Continues from v3.1 (closed at Phase 50). v4.0 starts at **Phase 51** and runs through **Phase 58**. Integer phases (51, 52, …) = planned milestone work; decimal phases (e.g. 54.1) = urgent insertions if needed.

- [x] **Phase 51: Real-Hardware Bring-Up** - Boot the app + sidecar on Kaan's Mac, reach a stable live "listening" session with clean startup logs, and survive a ≥30-min full-set run with zero unhandled exceptions or unbounded memory. ✅ 2026-05-21 — boot green, ws_bus empty-frame + stale-sidecar dev loop closed, soak harness shipped; review CLEAN; real ≥30-min live soak = KAAN-ACTION.
- [x] **Phase 52: Audio Path + Feature Grounding** - BlackHole 48 kHz capture is live end-to-end and every feature derived from it (levels, BPM, bands) is grounded — out-of-range values like the live BPM=200 read on a ~129 BPM track never reach the bus or UI. ✅ 2026-05-21 — BPM never exceeds 180 on harmonic-leak trace; psytrance profile + grounded DSP genre auto-detector (confidence-gated, `unknown` fallback, hysteresis) + genre on bus; review CLEAN; multi-genre live drive = KAAN-ACTION.
- [x] **Phase 53: Controller Live + Graceful Fallback** - DDJ-FLX4 MIDI is ingested live during a real session and the app degrades cleanly when the controller is unplugged. ✅ 2026-05-21 — closed the real gap: `start_port_watcher` now wired into the live session (was never spawned); `mark_disconnected` clears stale moves; single-state hot-plug callback (no rebuild divergence); review CLEAN; physical FLX4 plug/unplug drive = KAAN-ACTION.
- [x] **Phase 54: Hype Mode Live** - On real audio, hype (party) mode actually fires grounded, in-bar, non-slop reactions — the AI voice lands on real events (drops/builds) across ≥2 genres, cooldowns/latency tuned live so nothing comes late. ✅ 2026-05-21 — trace-replay regression pins the real captured trace's drop/build events fire through the REAL EventDetector (52/52 events→reactions, 0 suppressions) + a synthetic genre-2 build→drop, never on silence; `IN_BAR_TOLERANCE_S` named one-line knob + cooldown-respect pinned (no v4 value changed) + `--print-cooldowns` over the real trace; anti-slop spine pinned with REAL EvidenceRegistry+CitationLinter (empty evidence→no fire, unbacked citation→strip, grounded→emit) + grounded HYPE persona (no `phase=`); thin HYPE·LIVE indicator + reaction-cadence pulse (token-only, 20/80). Full suite 3768 passed; review CLEAN. Live ≥2-genre ear-pass + cooldown-tuning drive = KAAN-ACTION.
- [x] **Phase 55: Feedback Mode Live + Citation Integrity** - On real audio, feedback (coach) mode produces grounded, in-bar, non-slop coaching across ≥2 genres, and the EvidenceRegistry citation strip reflects real session events with zero orphaned or hallucinated citations. ✅ 2026-05-21 — LIVE-04 made airtight provable engineering: zero-orphan replay + hallucination-strip on a real non-empty registry + live/debrief consistency (REAL CitationLinter+EvidenceRegistry, no mocks); two telemetry stubs closed with REAL signals (cumulative stripped/total `slop_ratio` + actual stripped text from `StrippedRateTracker`, the `1/(1+mean)` placeholder gone). LIVE-02 coach grounding pinned across ≥2 genres (REAL EventDetector fixture + synthetic genre-2; empty evidence→no fire). Full suite 3821 passed; review 0 critical (WR-01 live/debrief test now drives the real `drills._citation_resolves` + IN-01 unified tolerance — both fixed). Live ≥2-genre coach ear-pass + live citation-strip drive = KAAN-ACTION (`55-HUMAN-UAT`).
- [x] **Phase 56: Performance + Live Mascot** - TTFT within budget on real HW, no audio dropouts under live load, mascot + UI hold 60fps, and the Neon Rebel mascot reacts correctly to live audio/MIDI events in-session across its **many modes** (idle/groove/build/drop/breakdown/speaking), driven by the rich bus signals — not the loudness ramp it uses today. ✅ 2026-05-21 — KEY CORRECTION: research found the shipped Tauri app loads the **Three.js GLB rig** (`tauri/ui/mascot.html`), not root `mascot.html` (whose sprites don't exist) — retargeted the whole phase to the rig users actually see. LIVE-05/05a: mascot now consumes rich bus signals (`SnapshotSlice` threads `music`/`voice` from the live frame), 6 modes reachable each gated to a real event, music-confirmation anti-slop guard (drop/peak/breakdown), speaking-overrides-music, FSM stays pure. PERF-01 `LIVE_TTFT_BUDGET_MS=1500` + `thinking_gate` MINIMAL pinned; PERF-02 zero soak underruns (reused `SoakCounters`); PERF-03 dispatch p95 ~0.22ms < 50ms. vitest 711 + perf suites green; review 0 critical (WR-01 guard mirrored real `phase.py` semantics — breakdown/peak no longer over-suppressed — + IN-01 realistic fixtures, both fixed). Felt TTFT/60fps/no-dropout + "mascot feels alive across modes" live-drive = KAAN-ACTION (`56-HUMAN-UAT`).
- [x] **Phase 57: Sexify Finish** - Final Tier-1 visual pass (zero HIGH findings), close v0.1.0-rc1 carryover bugs, tighten fresh-account first-run. ✅ 2026-05-21 — POLISH-01: impeccable CDJ-Whisper pass on session view + mascot overlay → formal gsd-ui-auditor **22/24, 0 HIGH** (removed 2 Tier-1 italics, aligned hero box-shadow, fixed `cohost` undefined `--silk-25`→`--silk-22`); Saira+JetBrains Mono held, no Geist/Fraunces; 721 vitest + tsc clean. POLISH-02: the 3 v0.1.0-rc1 carryover bugs were already fixed in `fac4c4a` — regression-PINNED them (drag cap + JS handler, chrome strip display:none, TCC boot-prime path; 7 security pins green) so they can't silently regress. POLISH-03: first-run friction audit = clean walk (no code-fixable friction; absent forewarning/driver-fetch/48k-probe steps resolved as Phase-49 installer-companion, intentionally out of in-app flow) + a continuity smoke. Real-app drag/chrome/TCC confirm + felt "looks peak" sign-off + fresh-account walk = KAAN-ACTION (`57-HUMAN-UAT`). Sidecar binary rebuild deferred to Phase 58.
- [x] **Phase 58: Ship Readiness** - All engineering release gates green on real artifacts, §E2E-50A-WALK discharged by driving the real app, one-button SHIP-CUT sequence documented + pre-verified with external-clock items surfaced as KAAN-ACTION. ✅ 2026-05-21 — REL-01: sidecar rebuilt (AIza-clean) + unsigned `vibemix_0.1.0-rc1_aarch64-unsigned.dmg` (254M) + `v4.0-MILESTONE-AUDIT.md` GENERATED (5/5 WIRED, via integration_audit.py); `cut_release.sh` re-pointed Gate 1→`^v0\.1\.0-rc[0-9]+$` + Gate 4→v4.0 audit. REL-02: `record_50a_walk.sh` OUT_DIR path bug fixed; Gate-6b green on a REAL rendered report (Hallucination honestly PARTIAL). REL-03: §SHIP-V4 consolidated KAAN-ACTION surface in `KAAN-ACTION-LEGAL.md`; **`cut_release.sh --dry-run v0.1.0-rc1` exits GREEN** ("everything but the signature is ready"); publish hard-guard (`gh release create`) regression-pinned to never auto-run. 43/43 phase tests green; verify human_needed 13/13 engineering must-haves. Recorded §E2E walk + Gate-2b ear-pass + external signatures (Apple Dev + SignPath) + Gate-5b freshness + tag-confirm = KAAN-ACTION (`58-HUMAN-UAT`).

## Phase Details (v4.0)

### Phase 51: Real-Hardware Bring-Up
**Goal**: The built app actually runs — boots to a live listening session on Kaan's MacBook, starts up clean, and survives a full-set run with every console/log error triaged and fixed. This is the foundation: nothing downstream can be observed until the app boots and stays up on real hardware.
**Depends on**: Nothing (first phase — everything downstream needs a running app)
**Requirements**: BRINGUP-01, BRINGUP-04, BRINGUP-05
**Success Criteria** (what must be TRUE):
  1. Launching the app on the real Mac reaches a live "listening" session with no boot crash.
  2. The Tauri console + sidecar logs are clean at startup — no unhandled exceptions, and the ws_bus no longer emits intermittent empty `{}` frames between real frames.
  3. Every runtime error observed in the Tauri console + sidecar logs during a real run is triaged and fixed — a full-set run completes with zero unhandled exceptions.
  4. A ≥30-minute continuous real session runs with no dropout, hang, or unbounded memory growth (RSS stays bounded across the run).
**Plans**: TBD
**Known issues to fold in**: ws_bus emits intermittent empty `{}` frames between real frames (bring-up cleanliness — close here).

### Phase 52: Audio Path + Feature Grounding
**Goal**: The live audio path is proven on real hardware — master output reaches the co-host through BlackHole at 48 kHz with levels registering in real time — AND every feature derived from that audio is grounded so the AI (and the UI) never sees a value that did not happen. The live BPM=200 read on a ~129 BPM track is the canonical bug to close: out-of-range values must never reach the bus/UI.
**Depends on**: Phase 51 (needs a stable, running session to route audio into)
**Requirements**: BRINGUP-02, GENRE-01, GENRE-02
**Success Criteria** (what must be TRUE):
  1. Real master output routed through BlackHole reaches the co-host at 48 kHz and live audio levels register on-screen in real time (capture path confirmed live).
  2. Derived BPM tracks the real track tempo — a ~129 BPM track reads ~129, never 200; out-of-range BPM (outside BPM_VALID_MAX) is rejected at the source and never reaches the bus or UI. *(The median-ring stabilizer already landed in `fd25337`; this phase confirms the gate + adds a real-trace regression — it does NOT re-implement it.)*
  3. The other audio-derived features (RMS levels, frequency bands, onset density) stay within valid ranges across a full-set run — no NaN, no out-of-range spikes leaking to the UI.
  4. With a track routed in, the on-screen level meters move in time with the music (visible, grounded feedback that capture is live and correct).
  5. **Genre is auto-detected from the live audio** (Kaan directive): a `psytrance` profile exists, and a grounded DSP detector (BPM band + band-signature + crest-factor) picks the active profile from real features — confidence-gated with `unknown` fallback + hysteresis, env override wins when set. Psytrance no longer misclassifies.
  6. **Detected genre + confidence are on the bus/UI** — surfaced as `unknown` when unsure, never a hallucinated label.
**Plans**: TBD
**UI hint**: yes — genre + confidence join the live snapshot the UI/mascot read

### Phase 53: Controller Live + Graceful Fallback
**Goal**: The DDJ-FLX4 MIDI path is proven on real hardware — controller moves are ingested live during a real session — and the app degrades cleanly to a clear, no-crash state when the controller is unplugged mid-session or absent at boot.
**Depends on**: Phase 51 (running app to ingest into); independent of Phase 52
**Requirements**: BRINGUP-03
**Success Criteria** (what must be TRUE):
  1. The DDJ-FLX4 is ingested live during a session when plugged in — real fader/knob/jog moves register in `ControllerState` and surface to the bus.
  2. Unplugging the controller mid-session degrades gracefully — no crash, no unhandled exception, the app stays in a clear, defined state and keeps running.
  3. Booting with the controller absent runs a full session on audio alone with no MIDI-related errors in the logs (verified graceful fallback).
**Plans** (2 plans, 2 waves):
  - **Wave 1** — 53-01: Controller state hardening + FLX4 decode proof + canonical-binding pin (mark_disconnected clears stale rings; profiles/ vs controllers/ dual-map resolved; FLX4 synthetic-stream decode; unknown-controller graceful path).
  - **Wave 2** *(blocked on Wave 1 completion)* — 53-02: Wire hot-plug watcher into the live session + disconnect/reconnect proof (single-state callback, no rebuild divergence; `__main__` watcher spawn + cleanup; disconnect→reconnect + watcher-callback integration; macos_audio live-drive recipe).
  - **Cross-cutting constraints:** profiles/ is canonical for live binding/decode (controllers/+MidiMapLoader unwired — do not switch/delete); mark_disconnected must clear moves+events rings; real FLX4 plug/move/unplug/replug drive = KAAN-ACTION.

### Phase 54: Hype Mode Live
**Goal**: On real audio, hype (party) mode feels like a real DJ friend in the ear — and, critically, the AI voice **actually fires** on real events. Real hardware surfaced a hard bug: a detected drop produced no voice in a 32s window. Hype mode is not validated until grounded, in-bar reactions reliably land on real drops/builds across ≥2 genres, with cooldowns and latency tuned live so nothing comes late.
**Depends on**: Phase 52 (grounded audio features are what hype reactions react to)
**Requirements**: LIVE-01, LIVE-03
**Success Criteria** (what must be TRUE):
  1. On real audio, when a drop/build is detected the AI voice fires — no more dead windows where a clear event passes with no reaction (the 32s-silent-on-drop bug is closed).
  2. Hype-mode reactions are grounded, in-time, and non-slop across ≥2 genres — no scripted, late, or hallucinated lines (Kaan-ear pass + autonomous proxy clean).
  3. Event cooldowns and reaction latency are tuned live so reactions land in-bar rather than after the moment passes.
  4. Across a full hype-mode set, the cadence feels alive (reactions present at the right density) — not silent stretches, not chatter.
**Plans**: TBD
**UI hint**: yes

### Phase 55: Feedback Mode Live + Citation Integrity
**Goal**: On real audio, feedback (coach) mode coaches like a real DJ mentor — grounded, in-bar, non-slop across ≥2 genres — and every claim it makes is backed by a real event. The EvidenceRegistry citation strip is the visible proof: it must reflect real session events live with zero orphaned or hallucinated citations.
**Depends on**: Phase 52 (grounded audio features back the coaching); benefits from Phase 54 (latency/cooldown tuning carries over)
**Requirements**: LIVE-02, LIVE-04
**Success Criteria** (what must be TRUE):
  1. On real audio, feedback (coach) mode produces grounded, in-time, non-slop coaching across ≥2 genres — observations tie to things that actually happened in the set (Kaan-ear pass + autonomous proxy clean).
  2. The EvidenceRegistry citation strip reflects real session events live — every citation maps to a real event, zero orphaned or hallucinated citations across a full-set run.
  3. Clicking a live citation deep-links to the real event it cites (citation → debrief region highlight works on real session data, not fixtures).
**Plans**: TBD
**UI hint**: yes

### Phase 56: Performance + Live Mascot
**Goal**: On the real machine under live-session load, the co-host hits peak performance — reactions are fast (TTFT within budget), audio never glitches, the UI and mascot hold 60fps — and the Neon Rebel mascot is a live, correct feedback surface that telegraphs back what the system saw from real audio/MIDI events.
**Depends on**: Phase 54 + Phase 55 (perf is measured against real reaction traffic from both modes); Phase 53 (mascot reacts to live MIDI)
**Requirements**: PERF-01, PERF-02, PERF-03, LIVE-05, LIVE-05a
**Success Criteria** (what must be TRUE):
  1. TTFT (trigger → first audio out) measured on the real MacBook meets the live-path latency budget.
  2. No audio glitches/dropouts occur in the playback path under real-session load across a full set.
  3. The mascot + UI hold 60fps on the integrated-GPU MacBook during a live session.
  4. The Neon Rebel mascot reacts correctly to live audio/MIDI events in-session — its state visibly tracks real drops/builds/controller moves (the visual feedback loop is grounded, not decorative).
  5. The mascot consumes the **rich bus signals** (`phase`, `mood`, `reaction_intent`, `bpm`, levels), not just the music-loudness ramp it uses today — `mascot.html` currently reads only `music`+`voice` → 3 tiers; this seam is the gap.
  6. The mascot has **many distinct modes** (Kaan directive 2026-05-21): ≥ idle/dead-air, vibing/groove, building, drop/peak, breakdown/chill, and a speaking/emoting mode while the AI talks — every mode change corresponds to a real musical/session event (anti-slop: no random or purely decorative state changes).
**Plans**: 3 plans (2 waves)
  - [x] 56-01-PLAN.md — LIVE-05/05a anti-slop guard: extend the Three.js rig SnapshotSlice with music/voice + the drop/breakdown music-confirmation defence-in-depth guard + anti-slop fixtures (wave 1)
  - [x] 56-02-PLAN.md — PERF-01 (TTFT telemetry budget + thinking-gate positive/negative pin) + PERF-02 (zero playback underruns under both-mode soak) via Python test extensions (wave 1)
  - [x] 56-03-PLAN.md — LIVE-05/05a six-mode reachability + speaking-overrides-music proof + mood/emotion tint discipline + PERF-03 dispatch-latency mode-transition floor (wave 2, depends on 56-01)
**UI hint**: yes — mascot is a Tier-1 live surface; the many-modes work is design-led (lift `mocks/` + `frontend-enforcement` skill; the bus already carries the signals to drive it).

### Phase 57: Sexify Finish
**Goal**: The surfaces a real user touches are polished to peak — Tier-1 live views get a final CDJ-Whisper visual pass, the v0.1.0-rc1 carryover bugs are closed, and a fresh account reaches first-session with no friction.
**Depends on**: Phase 51 (running app to inspect); benefits from Phases 52–56 live observations
**Requirements**: POLISH-01, POLISH-02, POLISH-03
**Success Criteria** (what must be TRUE):
  1. Tier-1 live surfaces (session view, mascot overlay) pass a final paired ui-checker + ui-auditor visual pass with zero HIGH findings and CDJ Whisper consistency held (20/80 accent rule, textured material feel, no AI-slop typography).
  2. The three v0.1.0-rc1 carryover bugs are closed and verified on the real app: Tauri drag capability works, the mascot chrome strip is gone, and the TCC permissions list populates correctly.
  3. A fresh macOS user account walks first-run → first-session with the friction points identified and tightened (no dead-ends, no confusing steps before audio is live).
**Plans**: 3 plans (2 waves)
- [x] 57-01-PLAN.md — POLISH-02: regression-pin the 3 carryover-bug fixes (drag cap + JS handler, chrome strip display:none, deep-link + TCC prime path) [wave 1, autonomous]
- [x] 57-02-PLAN.md — POLISH-03: fresh-account first-run friction audit + wizard continuity smoke [wave 1, autonomous]
- [x] 57-03-PLAN.md — POLISH-01: impeccable CDJ-Whisper visual pass on session view + mascot overlay → zero HIGH [wave 2, depends 57-01, has Kaan felt-sign-off checkpoint]
**UI hint**: yes — **use the `impeccable` skill for the visual polish pass** (Kaan directive 2026-05-21), not just the default ui-phase/ui-review.

### Phase 58: Ship Readiness
**Goal**: Everything that does not require an external signature is green and proven — release gates pass on real artifacts, the §E2E-50A-WALK is discharged by driving the real app, and the exact one-button ship sequence is documented and pre-verified so the only thing left is the external signatures.
**Depends on**: Phase 54 + Phase 55 (live validation feeds Gate 2b hallucination + Gate 6b e2e report), Phase 57 (polish complete before final artifacts)
**Requirements**: REL-01, REL-02, REL-03
**Success Criteria** (what must be TRUE):
  1. `cut_release.sh` 6-gate pre-flight + Gate 2b (hallucination) + Gate 6b (e2e report) all run green on real artifacts (not simulated fixtures).
  2. §E2E-50A-WALK is discharged by driving the real app end-to-end on the MacBook with real DJ-set audio, and the walk artifact (`docs/e2e/2026-05-walk.webm`) is recorded.
  3. The external-clock items (Apple Dev Agreement, SignPath OSS cert) are surfaced as KAAN-ACTION with the exact one-button SHIP-CUT sequence documented and pre-verified — a dry-run confirms everything-but-the-signature is ready, with no engineering step left to discover after signatures land.
**Plans**: 4 plans
- [x] 58-01-PLAN.md — Real artifacts: sidecar rebuild + unsigned .dmg + generated v4.0 milestone audit (REL-01)
- [x] 58-02-PLAN.md — §E2E walk rig path-bug fix + real Gate-6b report producer (REL-02)
- [x] 58-03-PLAN.md — Consolidated v4.0 KAAN-ACTION ship surface in the canonical cookbook (REL-03)
- [x] 58-04-PLAN.md — Re-point cut_release.sh to v0.1.0-rc/v4.0 + --dry-run signature stub + hard-guard regression + green-now gate run (REL-01/03)

## Progress (v4.0)

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 51. Real-Hardware Bring-Up | v4.0 | 3/3 | Complete | 2026-05-21 |
| 52. Audio Path + Feature Grounding | v4.0 | 4/4 | Complete | 2026-05-21 |
| 53. Controller Live + Graceful Fallback | v4.0 | 2/2 | Complete | 2026-05-21 |
| 54. Hype Mode Live | v4.0 | 4/4 | Complete    | 2026-05-20 |
| 55. Feedback Mode Live + Citation Integrity | v4.0 | 3/3 | Complete   | 2026-05-21 |
| 56. Performance + Live Mascot | v4.0 | 3/3 | Complete   | 2026-05-21 |
| 57. Sexify Finish | v4.0 | 3/3 | Complete   | 2026-05-21 |
| 58. Ship Readiness | v4.0 | 4/4 | Complete   | 2026-05-21 |

**Coverage:** 19/19 v4.0 requirements mapped ✓ (no orphans, no duplicates)

---

## Phase History (Archived)

<details>
<summary>✅ v0.1.0 MVP Foundation (Phases 1–14) — SHIPPED 2026-05-13</summary>

See `.planning/milestones/v0.1.0/` for full archive.

</details>

<details>
<summary>✅ v2.0 Research-Driven Ship (Phases 15–26) — SHIPPED 2026-05-14 (tech_debt accepted)</summary>

12 phases shipped — 10 Claude-side end-to-end + 2 deferred to Kaan-action (Phase 15 Plan 04 UAT + entire Phase 16 ear-test gate). 38 plans, 1961 passing tests, 220 commits since `v0.1.0-rc1`, ~45.7k LOC across `src/vibemix/`, `tauri/`, `scripts/`, `tests/`.

Full archive: `.planning/milestones/v2.0-ROADMAP.md` · Requirements: `.planning/milestones/v2.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v2.0-MILESTONE-AUDIT.md`

</details>

<details>
<summary>✅ v2.1 The Unified Cut (Phases 27–39) — SHIPPED 2026-05-16 (tech_debt accepted)</summary>

13 phases shipped engineering-green under `gsd-autonomous fully` mode. 96 plans, 633 phase-scope tests added, 225 commits since `v2.0` tag, net ~+45k LOC across `src/vibemix/`, `tauri/`, `scripts/`, `tests/`, `docs/`, `eval/`. 105 / 105 v2.1 REQ-IDs engineering-satisfied. All 5 cross-phase integration seams audited WIRED.

Full archive: `.planning/milestones/v2.1-ROADMAP.md` · Requirements: `.planning/milestones/v2.1-REQUIREMENTS.md` · Audit: `.planning/milestones/v2.1-MILESTONE-AUDIT.md`

</details>

<details>
<summary>✅ v3.0 Clean OSS Ship (Phases 40–45) — SHIPPED 2026-05-17 (tech_debt accepted)</summary>

6 phases shipped engineering-green under `gsd-autonomous fully` mode. 41 plans, 250 commits since `v2.1.0` tag, net ~+61k LOC across `src/vibemix/`, `tauri/`, `scripts/`, `tests/`, `docs/`, `eval/`. 57 / 57 v3.0 REQ-IDs engineering-satisfied. All 3 integration seams + 5 flows audited.

- [x] Phase 40: Anti-Slop Audio Port (6/6 plans) — completed 2026-05-16 (AUDIO-01..04 GREEN; AUDIO-05/06/07 = KAAN-ACTION-LEGAL)
- [x] Phase 41: Gemini SKU Upgrade + Latency Stack v2 (7/7 plans) — completed 2026-05-16 (LAT-01..08 GREEN; LAT-09 spike = KAAN-ACTION-PROXY)
- [x] Phase 42: Hallucination Gate v3 — Hybrid (6/6 plans) — completed 2026-05-16 (GATE-05..09 GREEN; GATE-01/02/03/04 corpus = KAAN-ACTION-LEGAL)
- [x] Phase 43: Visual Ship Lock (9/9 plans) — completed 2026-05-16 (VIS-01..09 GREEN; VIS-04 Mixamo retargets = KAAN-ACTION-LEGAL)
- [x] Phase 44: Launch Positioning + Pre-stage (7/7 plans) — completed 2026-05-17 (LAUNCH-01..10 GREEN; LAUNCH-03/04/06/07/08 = KAAN-ACTION-LEGAL)
- [x] Phase 45: External Discharge + Public RC Publish (6/6 plans) — completed 2026-05-17 (SHIP-08/11/13 engineering GREEN; SHIP-01..13 cookbook in KAAN-ACTION-LEGAL)

**Critical path at close:** External clock — Apple Dev Agreement (Francesco, P46) + SignPath OSS Foundation (Kaan, ~1-week SLA, P46) gate the public RC publish. After approvals land, SHIP-CUT v3.0.0-rc1 is one-button via the §SHIP-01..13 discharge cookbook (45-06).

Full archive: `.planning/milestones/v3.0-ROADMAP.md` · Requirements: `.planning/milestones/v3.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v3.0-MILESTONE-AUDIT.md`

</details>

<details>
<summary>✅ v3.1 Distribution-Ready Pass (Phases 46–50) — SHIPPED 2026-05-18 (tech_debt accepted)</summary>

5 phases shipped engineering-green under `gsd-autonomous fully` mode. 32 plans, 61 commits since `v3.0` tag, net ~+57.5k LOC across `installer/`, `tauri/`, `scripts/`, `tests/`, `docs/`, `.github/workflows/`. 44 / 44 v3.1 REQ-IDs engineering-satisfied. All 5 cross-phase integration seams audited WIRED.

- [x] Phase 46: Dependency Audit + Lockfile + AUDIT.md (6/6 plans, 45 tests + 1 xfail; DEPS-01..06 + DEPS-09/10 GREEN; DEPS-07 pinact + DEPS-08 cull-blocked documented in AUDIT.md § Decisions) — completed 2026-05-18
- [x] Phase 47: Mascot Real GLB Land + Full Emotion Coverage (8/8 plans, 63 python + 177 ts tests; MASCOT-01..08 GREEN; §VIS-04 + §VIS-05 Mixamo discharge = KAAN-ACTION) — completed 2026-05-18
- [x] Phase 48: New-Dep + Integration Opportunity Scan (6/6 plans, 19 tests; OPP-01..06 GREEN; 24 candidates rated 1G/8Y/9R-constraint/6R-risk; OBS adopted docs-only) — completed 2026-05-18
- [x] Phase 49: Win + Mac One-Click Installer Chain (6/6 plans, 68 passing + 1 skip; INSTALL-01..10 GREEN; §INSTALL-COMPANION-SIGN + §INSTALL-VM-RUN + §SHIP-CONTACT-VBAUDIO = KAAN-ACTION; median 41,000 ms / 60,000 ms budget) — completed 2026-05-18
- [x] Phase 50: End-to-End MacBook + OS-Matrix Pass (6/6 plans, 16 passing + 5 CI-tolerant skips; E2E-01..10 GREEN; §E2E-50A-WALK + §INSTALL-VM-RUN downstream = KAAN-ACTION; Gate 6b wired into cut_release.sh) — completed 2026-05-18

**Critical path at close:** Same external clock as v3.0 — §INSTALL-COMPANION-SIGN (SignPath OSS Foundation cert) unblocks §INSTALL-VM-RUN (real Tart VM execution) which enables §E2E-50A-WALK full completion. §VIS-04 (28 Mixamo retargets via Adobe walk) is independent and runs in parallel. SHIP-CUT v3.1 ride-along with v3.0 publish.

Full archive: `.planning/milestones/v3.1-ROADMAP.md` · Requirements: `.planning/milestones/v3.1-REQUIREMENTS.md` · Audit: `.planning/milestones/v3.1-MILESTONE-AUDIT.md`

</details>

---

## Milestone-Level Progress

| Milestone | Phases | Status | Shipped |
|-----------|--------|--------|---------|
| v0.1.0 MVP Foundation | 1–14 | ✅ Shipped | 2026-05-13 |
| v2.0 Research-Driven Ship | 15–26 | ✅ Shipped (tech_debt) | 2026-05-14 |
| v2.1 The Unified Cut | 27–39 | ✅ Shipped (tech_debt) | 2026-05-16 |
| v3.0 Clean OSS Ship | 40–45 | ✅ Shipped (tech_debt) | 2026-05-17 |
| v3.1 Distribution-Ready Pass | 46–50 | ✅ Shipped (tech_debt) | 2026-05-18 |
| v4.0 SHIP | 51–58 | 🟡 Engineering-complete (8/8) — publish on signature clock | - |
| v5.0 The Useful Cut | 59–62 | ✅ Shipped (tech_debt) | 2026-05-22 |
| v6.0 The Memory Turn | 63–66 | 🔵 Active (planning) | - |

---

*Roadmap extended 2026-05-21 for v5.0 "The Useful Cut" — **4 phases (59–62)** continuing numbering from v4.0 (which ran 51–58). v4.0 "SHIP" is kept OPEN and intact above (engineering-complete 8/8, publish on the external signature clock — NOT archived per Kaan directive 2026-05-21). v5.0 derives from 17 requirements across 4 categories (DECK / HARMONIC / COACH / PILL), shaped by 4-agent convergent research (`.planning/research/SUMMARY.md`). Hard critical path: P59 (deck-state + citable key source) → P60 (deterministic Camelot clash + conservative gate + Kaan-ear veto) → P61 (actionable coach persona, extends `live-tuning-or-brain`); P62 (floating pill) parallelizes with the spine, only its deck-chip polish soft-depends on P59. Every new capability respects the four cardinal invariants (single-writer / citation grounding / "trust the audio" / one socket) and the anti-slop thesis. No new providers, no CLAP/Essentia, read-only DJ-DB. The v4.0 external signature clock is unchanged.*

*Prior re-split 2026-05-20 for v4.0 "SHIP" — 8 phases (51–58) per Kaan's directive for finer granularity; bring-up split into three input seams; two interaction modes get dedicated phases; real-hardware findings folded in (ws_bus empty-frame 51, BPM=200 grounding 52, AI-voice-must-fire 54).*
