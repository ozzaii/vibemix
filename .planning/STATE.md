---
gsd_state_version: 1.0
milestone: v6.0
milestone_name: The Memory Turn
status: executing
last_updated: "2026-05-22T06:53:40.374Z"
last_activity: 2026-05-22
progress:
  total_phases: 12
  completed_phases: 8
  total_plans: 29
  completed_plans: 28
  percent: 67
---

# vibemix — State

**Last updated:** 2026-05-22 — **v6.0 "The Memory Turn" ROADMAP CREATED (4 phases, 63–66).** Numbering continues from v5.0 (ran 59–62) — NO reset (51–58 = v4.0, 59–62 = v5.0). 14/14 v6.0 REQ-IDs mapped to exactly one phase (100% coverage, no orphans, no duplicates): **P63=STORE-01..04, P64=INGEST-01..03, P65=RECALL-01..04, P66=COPILOT-01..03.** Derived from 4-agent convergent research (`.planning/research/SUMMARY.md` + `ARCHITECTURE.md`) — a **WIRING / REUSE milestone with ZERO net-new dependencies**, not greenfield: `sqlite-vec>=0.1.9` already declared/installed/signed-in-sidecar, and the embed→`cosine_topk`→cited-evidence machine already ships under `src/vibemix/library/`. The memory layer = a second `memory.db` + a ~50-line wrapper + an off-hot-path ingest job + one gated evidence line + one new existence-only `recall` citation source. **Hard, dependency-correct critical path (unanimous across all 4 researchers): STORE (63) → INGEST (64) → RETRIEVE (65) → COPILOT MOVE (66).** Live reaction path is untouched until P65; **P65 is the ANTI-SLOP RELEASE GATE** (retrieval poisoning is the existential failure class). Two flag clusters resolve in plan-time: **P63** install fragility (`vec0.dylib`/`vec0.dll` sign+notarize + clean-VM round-trip — rides the Apple/SignPath external clock) and **P65** Kaan-ear veto + cosine-vs-time-weight blend/half-life tuning on the real corpus (`/gsd:plan-phase --research-phase`). **v4.0 "SHIP" kept OPEN + intact in ROADMAP.md** (engineering-complete 8/8, publish on external signature clock — NOT archived per Kaan directive); v5.0 collapsed block + Phase History + milestone table all preserved verbatim. **Next: `/gsd:plan-phase 63`.**

---

### (prior) v5.0 "The Useful Cut" SHIPPED 2026-05-22 (tech_debt accepted) — 4/4 phases 59–62, 17/17 REQ-IDs, 4/4 integration seams WIRED. Deck-aware + actionable coach + floating pill. P59=DECK-01..05 (deck-state ladder + citable `key:` source), P60=HARMONIC-01..04 (deterministic Camelot clash, default-OFF behind Kaan-ear veto), P61=COACH-01..04 (actionable-not-hype persona, extends `live-tuning-or-brain`), P62=PILL-01..04 (floating pill = primary surface, mascot demoted/opt-in, mascot-audit green). KAAN-ACTION live-confirm items ride forward (harmonic veto flip, vision-eval, coach/pill live-ear passes, FLX4 live). `v5.0` git tag + branch merge deferred to Kaan (`live-tuning-or-brain` unmerged). Full archive: `.planning/milestones/v5.0-*`.

---

### (prior) v4.0 "SHIP" engineering-complete 2026-05-21 (8/8 phases 51–58, 19/19 REQ-IDs) — **kept OPEN, NOT archived per Kaan directive.** Public RC publish gated on the external signature clock (Apple Dev Agreement via Francesco + SignPath OSS cert). `cut_release.sh --dry-run v0.1.0-rc1` exits GREEN — everything-but-the-signature ready; publish hard-guard regression-pinned (never auto-runs). KAAN-ACTION discharge surface: `KAAN-ACTION-LEGAL.md §SHIP-V4` + per-phase `*-HUMAN-UAT.md`. v6.0's P63 sqlite-vec-binary clean-VM round-trip rides this same external clock — surface early to parallelize.

---

## Project Reference

See: .planning/PROJECT.md (Current Milestone: v6.0 "The Memory Turn")

- **Project:** vibemix — open-source AI DJ co-host (Bravoh's first OSS release)
- **Core value:** "Real DJ friend in your ear" — never hallucinating, never breaking flow, never AI slop.
- **v6.0 thesis:** reactive co-host → forward-leaning **copilot**. Mechanism = memory: every session feeds an embedding store; coach prompts ground in *past* sessions. Personalization is **emergent from the retrieval seam**, NOT a settings screen and NOT an LLM-extraction layer. Acid test for any embedded artifact: *"does retrieving this close a hallucination class OR unlock a copilot move?"* — if neither, don't embed it.
- **New headline hallucination class:** **retrieval poisoning** (an irrelevant past moment injected into the live prompt → AI references something that didn't happen). Mitigation is structural, not a prompt plea: ~0.7 floor (below → inject nothing), top-k 2–3 cap, event-gating, PAST-tense fence, current-session exclusion, `recall` citation source (fabricated `[recall:<id>]` strips the whole turn). **P65 RETRIEVE = anti-slop release gate.**
- **Current focus:** Phase 63 — memory-store
- **Last shipped:** v5.0 "The Useful Cut" — 2026-05-22 (tech_debt accepted).
- **Open alongside:** v4.0 "SHIP" — engineering-complete (8/8), publish gated on Apple Dev Agreement + SignPath OSS cert (external clock). NOT archived.
- **Project mode:** standard. **Granularity:** fine. **Model profile:** quality (all agents on Opus, all checkpoints on).
- **Autonomy mode:** `gsd-autonomous fully` — every blocker + human-needed item discharged autonomously; only privacy rule + destructive risk + legal-capacity carveouts (Apple Dev + SignPath) still pause. Soft Kaan-discharge gates surface to KAAN-ACTION but do NOT pause work.

---

## Current Position

Phase: 63 (memory-store) — EXECUTING
Plan: 3 of 3
Status: Ready to execute 63-03 (Wave 2 — session_id path-traversal guard + retention sweep + orphan reconcile). 63-02 done: storage spine GREEN (Wave-1 subset).
Last activity: 2026-05-22 — Phase 63 Plan 02 complete: `src/vibemix/memory/` package (SqliteVecMemoryStore + MemoryStore + open_memory_store + Record), STORE-01/02/04 contract subset GREEN (10/19 tests/memory/ green; path-traversal + retention correctly RED, deferred to 63-03).

## v6.0 Phase Map

| Phase | Goal | Requirements (count) | Depends on | UI |
|-------|------|----------------------|-----------|----|
| 63 — Memory Store | Local per-install `memory.db` + ~50-line `MemoryStore` cloned from shipped `library/` primitives (zero new dep); Mac/Win `cosine_topk` parity + numpy fallback; retention + delete-cascade; `model_router.resolve("embedding")` on FLEX. Storage spine; no live-path touch. | STORE-01..04 (4) | — (first v6.0 phase) | — |
| 64 — Session Ingest | Off-hot-path post-session batch (+ boot sweep) turning `events.jsonl`+evidence+`ai_text` into deterministic TEXT "reaction moment" records; NO audio, NO LLM-extraction (CI-guarded); session-id/timestamp-tagged. | INGEST-01..03 (3) | P63 | — |
| 65 — Memory Retrieval Seam | **ANTI-SLOP RELEASE GATE.** New existence-only `recall` source (zero new linter code, à la P59 `key`); gated `recall[…]` block (copy P59 `decks[…]` gate → cold-memory byte-identical); top-k 2–3, ~0.7 floor, PAST-tense fence, current-session excluded; blend tuned in-phase. **Kaan-ear veto.** | RECALL-01..04 (4) | P63 + P64 | — |
| 66 — Visible Copilot Move | Linter-grounded transition-shape callback + vocabulary callback — cited/warm/non-nagging; recall chip on existing `citation_strip`. NO anti-features (no next-track rec, no LLM-tendencies, no settings personalization, no continuous audio embed). | COPILOT-01..03 (3) | P65 | yes (recall chip on Tier-1 surface) |

**Build-order rationale (dependency-correct, unanimous across 4 researchers):** STORE has no upstream deps; INGEST writes to STORE; RETRIEVE reads STORE; the MOVE needs RETRIEVE firing. Live path protected until last needed — STORE + INGEST land with zero reaction-path changes (grep-gate: ingest never imports the coach loop); the live path only changes in RETRIEVE behind a gate that preserves byte-identity when cold. The four cardinal invariants (single-writer / citation-grounding / trust-the-audio / one-socket) are preserved by reuse — memory never writes `MusicState`, never opens a new port, never overrides the live ears.

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases complete (v0.1.0) | 14 / 14 |
| Phases complete (v2.0) | 10 / 12 code-shipped (2 deferred to Kaan-action) |
| Phases complete (v2.1) | 13 / 13 engineering-green |
| Phases complete (v3.0) | 6 / 6 engineering-green (22 carveouts → KAAN-ACTION-LEGAL) |
| Phases complete (v3.1) | 5 / 5 engineering-green (7 carveouts on external clock) |
| Phases complete (v4.0) | 8 / 8 engineering-green (publish on external signature clock; NOT archived) |
| Phases complete (v5.0) | 4 / 4 engineering-green (KAAN-ACTION live-confirm items ride forward) |
| v6.0 phase count | 4 (Phases 63–66) |
| v6.0 REQ-IDs mapped | 14 / 14 ✓ (100% coverage, no orphans, no duplicates) |
| v6.0 per-phase REQ counts | P63=4 (STORE) · P64=3 (INGEST) · P65=4 (RECALL) · P66=3 (COPILOT) |
| v6.0 net-new dependencies | 0 (WIRING/REUSE milestone — `sqlite-vec>=0.1.9` already declared) |
| P63-01 (Wave 0) | 2 tasks, 6 files, ~18 min — RED-first test contract (dde3c0f, 5635390) |
| P63-02 (Wave 1) | 2 tasks, 3 files, ~32 min — storage spine GREEN; STORE-01/02/04 (610c374, d36d924) |
| v4.0 git tag | local artifacts on `live-tuning-or-brain`; unsigned `v0.1.0-rc1` .dmg built |
| v3.0/v3.1/v4.0 carveouts | external clock (Apple Dev + SignPath) — unchanged by v6.0 |

---

## Accumulated Context

### v6.0 Roadmap Decisions Locked (2026-05-22)

v6.0 "The Memory Turn" roadmapped into **4 phases (63–66)** continuing numbering from v5.0 (ran 59–62) — NO reset. 14/14 REQ-IDs mapped to exactly one phase (100% coverage, no orphans, no duplicates). Shaped by 4-agent convergent research that independently produced the same four-phase spine. This is a **WIRING/REUSE milestone with ZERO net-new dependencies** on the mature grounded co-host — not greenfield.

**Reuse map (the load-bearing finding):** the entire memory layer is built on already-shipped `src/vibemix/library/` primitives:

- `index_sqlite_vec.py::SqliteVecStore` + `store.py::open_store` (numpy fallback) → cloned by `memory/store.py` (NEW sibling pkg `src/vibemix/memory/`, imports from `library/`, does NOT fork).
- `_cosine.py::cosine_topk` → reused verbatim (single chokepoint; Mac/Win bit-identical parity, P55 rule).
- `embed.py::LibraryEmbedder` + content-hash cache (`embeddings.db`) → reused for ingest + query embeds.
- `grounding.py::Grounding` (event-gated embed→cosine→`[track:<id>]`) → the exact pattern `memory/retriever.py` clones, generalized `track`→`recall`.
- `evidence_registry.py` + `coach/citation_linter.py` existence-only branch (`track`, `key`) → `recall` joins it with ZERO new linter code (à la P59 `key`).
- `coach.py::evidence_line` P59 `decks[…]` gate → copied verbatim for the gated `recall[…]` block (cold-memory golden byte-identical).
- `audio/recorder.py` `events.jsonl` schema + crash-sweep → ingest source + boot-sweep mirror.
- `runtime/config_store.py::app_data_dir()` → `memory.db` placement (durable user-data tier, not `~/.cache`).

**Model-ID correction (surface to Kaan):** locked literal `gemini-embedding-001` is the TEXT-ONLY GA model; the milestone's multimodal intent maps to `gemini-embedding-2`. **Never hardcode either** — route via `model_router.resolve("embedding")` (CI grep gate forbids literals). v1 ingest is text-signature-only, so cheaper text-001 is even a viable one-line config choice; default stays the multimodal model per milestone intent. Decision to confirm with Kaan in-phase.

### P63-01 Execution Decisions (2026-05-22)

- **Wave-0 RED-first contract is the deliverable, not green tests.** 6 `tests/memory/` files pin the `MemoryStore` interface (`add_record` / `query_topk(.., *, exclude_session=None)` / `delete_session` / `run_retention_sweep(max_moments=)` → `result.deleted`; `Record.{record_id,session_id,ts,kind,signature,score}`; `MemoryStore(db_path, prefer_sqlite_vec=True)`) BEFORE `src/vibemix/memory/` exists. Acceptance = collection `ModuleNotFoundError: No module named 'vibemix.memory'` (verified under `.venv`/Python 3.12, the authoritative runner — system Python 3.14 masks it with a `ServiceTier` import gap, so always verify under `.venv`). Plans 63-02/03 flip these GREEN.
- **`cosine_topk` reused verbatim** from `vibemix.library._cosine` in the memory parity gate (`@pytest.mark.parity`); never forked, no native-KNN ranking anywhere in the tests. Synthetic 768-dim vectors generated in-test (`np.random.default_rng`) — no new fixture file.
- **STORE-04 literal gate delegated, not duplicated:** the shipped `tests/repo/test_model_literal_gate.py` already scans all of `src/vibemix/` (incl. the new `memory/`); a module comment records the delegation.
- **STORE-01..04 traceability = "Contract pinned (63-01); impl pending (63-02/03)"** — NOT marked Complete, because the `MemoryStore` source does not exist yet. (Reverted an auto-mark that the plan-frontmatter `requirements` field triggered — requirements complete when the implementing plan lands.)
- T-63-01 (no-live-path import) + T-63-02 (no-extraction) mitigations are now regression-pinned from the first commit (static AST + subprocess dormancy; tokenize-stripped generation-surface scan w/ positive control).

### P63-02 Execution Decisions (2026-05-22)

- **Storage spine shipped, contract subset GREEN.** `src/vibemix/memory/` (3 files): `SqliteVecMemoryStore` (vec0 backend cloned from `library/index_sqlite_vec.py` — `vec_library`→`vec_memory` + `moments` sibling table on one connection), `MemoryStore` facade (compose-not-subclass: backend + owned `moments` connection; `add_record`/`query_topk(*, exclude_session=None)`/`delete_session`), `open_memory_store()` (clone of `library/store.py::open_store` pointed at `app_data_dir()/memory.db`). 10/19 `tests/memory/` GREEN: roundtrip, numpy_fallback, delete_cascade, parity (sqlite-vec↔numpy bit-identical + tie-break + float32 round-trip), no_live_path (CLEAN), no_extraction, + `tests/repo/test_model_literal_gate.py`.
- **`cosine_topk` IMPORTED VERBATIM** from `vibemix.library._cosine` — sole ranking path in `query_topk`; no native vec0 KNN / `MATCH` / `ORDER BY distance` / `vec_distance_cosine` anywhere in `memory/`. `NumpyStore` reused as-is (no `index_numpy_memory.py`). Embedding seam = reused `LibraryEmbedder` (no hardcoded model literal — `model_literal_gate` green).
- **Lazy `app_data_dir` import (the one auto-fix, Rule 3 blocking).** Module-level `from vibemix.runtime.config_store import app_data_dir` triggers `vibemix.runtime.__init__`, which eagerly imports the live reaction path (`coach`, `ws_bus`, `session_loop`, `state.refresh`) → leaked into `sys.modules`, failing `test_no_live_path_import.py`. Fixed by deferring the import into `_memory_db_path()` + `db_path=None` sentinel defaults resolved lazily. Behavior/public surface unchanged; only import timing. (Library never hit this — it uses `~/.cache` defaults, never `config_store`.) **Note for 63-03/64:** any new `memory/` module must keep `config_store`/runtime imports function-local or the dormancy gate fails.
- **add_record vector-first then moments-row then commit** (crash → at worst a reconcilable orphan vector, never metadata→missing-vector). `moments` reuses the sqlite-vec backend's single `self.db` (atomic); numpy path opens sibling `memory_moments.db`.
- **Path-traversal + retention correctly RED (deferred to 63-03).** 9/19 `tests/memory/` red by design: 6× `test_session_id_path_traversal` (session_id guard — regex shape + `is_relative_to`, mirroring `recordings_index`) + 3× `test_retention` (`run_retention_sweep(max_moments=)`). `delete_session` is the documented Wave-2 extension point. 4 pre-existing `tests/repo/` failures (README matrix ×2, gate-42 STATE annotation, cut-release tag-regex) confirmed failing identically at parent `b45b419` — unrelated to `memory/`, no new failures introduced.
- **STORE-01/02/04 marked complete in REQUIREMENTS** (impl landed). STORE-03 (cascade + retention + path-traversal) stays open for 63-03.

### v6.0 KAAN-ACTION / Research Flags (carry into planning)

- **P63 — sqlite-vec install fragility (KAAN-ACTION, external clock):** `vec0.dylib`/`vec0.dll` native binaries must be signed/notarized + a clean-VM (incl. Windows ARM64) `memory.db` round-trip proven in the e2e matrix. Rides the Apple notarization + SignPath external clock already on the critical path — surfaced EARLY so it parallelizes against the in-flight v4.0 approvals. (The binary was already signed in shipping builds; the new artifact is only a data file with zero new signing surface — the clean-VM round-trip is the proof item.)
- **P64 — moment taxonomy (research flag):** "which artifacts ground best" (`coach_line` vs `moment` vs stretch `audio_moment`) is explicitly the first phase's research per the milestone thesis. `/gsd:plan-phase --research-phase`. Start text-only; resolve scope here, not by default.
- **P65 — blend/half-life tuning (research flag) + Kaan-ear veto (KAAN-ACTION):** cosine-only vs cosine+time-weight and the decay half-life (in *sessions*, not hours) is an open question — tune the shape (two-term exp-decay + relevance floor) + exact recall threshold (start at 0.7) against Kaan's real session corpus in-phase. Ships behind a **Kaan-ear veto** on retrieval relevance (mirrors P60 harmonic veto) — the hard quality gate.
- **P66 — Kaan-ear quality gate (KAAN-ACTION):** the visible copilot move's real gate is Kaan's ear (recall fires grounded + doesn't feel scripted), not a test.

### Anti-slop invariants baked into v6.0 success criteria

- **Retrieval-poisoning suppression:** ~0.7 floor (below → inject nothing; empty retrieval is correct + frequent), top-k 2–3 cap, event-gated to track-aware events (never HEARTBEAT). [P65]
- **Citable-by-construction recall:** fabricated `[recall:<id>]` the registry never saw strips the whole turn (existing `CitationLinter`, zero new code). [P65 / P66]
- **No-extraction:** raw-in/raw-out deterministic text signatures only; CI guard asserts ingest calls only `embed_content` (never any chat/generation model). [P64]
- **Current-session exclusion:** the in-progress session is excluded from its own retrieval (natural — ingest is post-session). [P64 tag + P65 exclusion]
- **Four cardinal invariants:** single-writer (memory DB sole writer = ingest, off-loop), citation-grounding (recall through the existing linter), trust-the-audio (recall fenced PAST-tense, subordinate to the live audio Part), one-socket (no new port; recall surfaces on existing `ipc.session.*` / citation strip). [P65 / P66]
- **No anti-features:** no next-track recommendation, no LLM-extracted "tendencies"/insights as fact, no settings-screen personalization, no continuous audio embedding. [P66, enforced by review]

---

## Session Continuity

**Next command:** continue Phase 63 — execute Plan 63-03 (Wave 2: session_id path-traversal guard + `run_retention_sweep(max_moments=)` + orphan reconciliation) to turn the remaining 9 RED `tests/memory/` GREEN.

**What's done:** Phase 63 Plan 02 complete — `src/vibemix/memory/` storage spine: `index_sqlite_vec_memory.py` (SqliteVecMemoryStore — vec0 `vec_memory` + `moments` table), `store.py` (MemoryStore + open_memory_store + Record), `__init__.py` (barrel). Committed `610c374` + `d36d924`. Wave-1 contract GREEN (10/19 `tests/memory/`): roundtrip, numpy_fallback, delete_cascade, parity, no_live_path (CLEAN), no_extraction + model_literal_gate. STORE-01/02/04 marked complete. Earlier: 63-01 RED-first contract (`dde3c0f`, `5635390`); v6.0 roadmap.

**What's next:** Plan 63-03 extends `delete_session` (the documented Wave-2 hook) with the path-traversal guard (regex shape + `is_relative_to`, mirroring `recordings_index`) and adds the retention sweep + orphan reconciliation against the still-RED contract. **Invariant for 63-03/64:** keep any `config_store`/`vibemix.runtime` import function-local — module-level pulls the live path into `sys.modules` and fails the no-live-path dormancy gate (see P63-02 decisions). Then `/gsd:plan-phase --research-phase` for P64 (taxonomy) / P65 (blend/half-life). Surface the P63 sqlite-vec clean-VM/sign item to the v4.0 external-clock surface early.

**Open before execution:** none blocking — the spine is research-locked and dependency-correct. Model-ID (text-001 vs multimodal-2) is a one-line config choice to confirm with Kaan but never hardcode either way.

---

## Deferred Items

(v6.0: none yet — milestone just roadmapped. v3.0 / v3.1 / v4.0 / v5.0 external-clock + Kaan-action carveouts unchanged — see PROJECT.md Active section + KAAN-ACTION-LEGAL.md §SHIP / §SHIP-V4 + v5.0 KAAN-ACTION live-confirm items.)
