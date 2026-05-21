# Phase 55 — Research: Feedback Mode Live + Citation Integrity

**Researched:** 2026-05-21
**Verified against HEAD:** `20466bb`
**Requirements:** LIVE-02 (coach-mode grounded reactions ≥2 genres) + LIVE-04 (citation integrity)
**Mode:** Orchestrator-grounded inline research (autonomous `fully`). Findings verified against live source this session.

> **One-line thesis:** The coach + evidence + linter machinery is ALL SHIPPED and load-bearing-tested. Phase 55 does NOT rebuild it. The automatable work is (1) extend Phase 54's anti-slop/trace-replay spine to COACH_* prompts (LIVE-02), and (2) close TWO real telemetry-leak gaps so the `ipc.session.citation` strip Kaan sees reflects *real* stripped/verified counts and the *real* stripped text (LIVE-04). One genuine integrity defect exists and is closable; the core grounding contract (linter strips orphans) is already airtight.

---

## Q0. Is the citation-integrity contract already airtight, or is there a real orphan/leak path?

**Verdict: the GROUNDING contract is airtight; the TELEMETRY-SURFACE has two real leaks.**

### What is already airtight (do NOT touch)

- `EvidenceRegistry.has()` / `snapshot()` / `parse_citations()` (`src/vibemix/state/evidence_registry.py`) — append-only, lock-guarded, frozen-snapshot. `has()` returns False on missing source/key (no KeyError). Pinned by `tests/state/test_evidence_registry.py` + `test_evidence_registry_library.py`.
- `CitationLinter.check(text, snapshot, mode)` (`src/vibemix/coach/citation_linter.py`) — response-level binary strip. Decision ladder: `no_citations` → `malformed_atom` → `invalid_atoms` → `valid`. A single orphan atom strips the WHOLE reply. `LintResult.missing` surfaces every orphan; `reason` is a first-class tag. Pinned by `tests/coach/test_citation_linter.py`.
- The strip CHOKEPOINT in `DJCoHostAgent.llm_node` (`src/vibemix/agent/dj_cohost.py:968-1059`) — runs the linter against the snapshot taken once per turn (line ~216, REUSED, never re-snapshotted), records `stripped_rate_tracker.record(True/False)`, logs `citation_strip` / `citation_bypass` with `raw_text=full_text + missing payload`. Pinned by `tests/agent/test_dj_cohost_linter.py` + `test_citation_strip_emit.py`.
- The debrief leg (`src/vibemix/debrief/stripper.py`, `drills.py`, `tldr.py`) — sentence-level cited-critique filter reusing the SAME `EVIDENCE_CITATION_RE` grammar; drill citations resolve against the registry snapshot at ±2.0s (`mode="debrief"`). Pinned by `tests/debrief/test_drill_citations_resolve.py`, `test_no_uncited_critique_in_debrief.py`, `test_stripper_integration_with_*`.

**Conclusion:** an orphaned/hallucinated citation that reaches the user's EAR is already prevented at HEAD — the linter strips it (silence > slop). LIVE-04's "zero orphaned/hallucinated citations" is satisfied at the *emission* boundary today.

### The TWO real leaks (this phase's automatable engineering target)

The CONTEXT.md decision (c) requires: *"the UI citation strip payload reflects the real stripped/verified counts."* It does NOT today. `_citation_telemetry()` in `src/vibemix/__main__.py:706-752` builds the `ipc.session.citation` payload and has two self-documented placeholders:

1. **`slop_ratio` is a COUNT-derived placeholder, not the real stripped/total ratio.**
   `src/vibemix/__main__.py:738`: `slop_ratio = 1.0 / (1.0 + mean) if mean > 0 else 1.0` — derived from the rolling-50-turn citation-COUNT mean (`evidence_registry.citation_telemetry()["mean"]`). This is "how many citations per turn", NOT "what fraction of turns got stripped". The docstring (lines 714-719) explicitly calls it a "placeholder … The true slop metric (slop-vs-clean turn ratio) is a v2.x refinement". **Effect:** the diagnostics drawer's `slop_ratio` does NOT move when the linter strips an orphan — exactly the metric LIVE-04 SC2 wants to be true.

2. **`last_unverified_response` is hardcoded `None`.**
   `src/vibemix/__main__.py:750`: `"last_unverified_response": None,  # v2.x follow-up`. The docstring (lines 722-725) says "no simple existing source. v2.x adds a 5-entry ring buffer". **Effect:** Kaan can never SEE the stripped/bypassed text in the Settings → Diagnostics drawer — yet the text IS captured at strip time (`citation_strip`/`citation_bypass` log events carry `raw_text=full_text`). The schema field (`SessionCitationPayload.last_unverified_response: str | None`) exists and is wired end-to-end; only the *source* is stubbed.

**Both are closable with a small, append-only mechanism** (the StrippedRateTracker already holds the stripped/total signal needed for a real slop_ratio; the strip path already has the text for a last-unverified ring). This is the deepest LIVE-04 engineering win and the recommended scope.

---

## Q1. LIVE-02 (coach grounding) — reuse Phase 54's spine for COACH_* prompts

Phase 54 shipped the anti-slop + trace-replay spine for HYPE mode. Phase 55 EXTENDS it to coach mode — same primitives, same patterns, NO duplication.

**Reusable Phase 54 assets (verified present):**
- `tests/fixtures/hype_trace_genre1.jsonl` — the real captured ground-truth trace (copied from `recordings/20260515-112139/events.jsonl`: PHASE 21, MIX_MOVE 20, HEARTBEAT 8, LAYER_ARRIVAL 2, TRACK_CHANGE 1). **REUSE this fixture for the coach trace-replay** — it is mode-agnostic ground truth (events fire the same regardless of hype/coach persona). Do NOT check in a second copy.
- `tests/state/test_hype_anti_slop.py` — the FLOOR (detector refuses to fire on empty/weak evidence) + SPINE (linter strips unbacked citation, passes grounded one) pattern. **EXTEND for coach** with coach-relevant event tasks (PHASE / MIX_MOVE / HEARTBEAT) and the COACH persona path — do NOT re-prove the detector FLOOR (it is persona-independent; already pinned).
- `tests/state/test_hype_trace_replay.py` — drives the REAL `EventDetector` over the fixture, asserts events fire within in-bar tolerance, silence does not fire. The firing path is persona-independent, so coach mode's "fires grounded on real events, in-bar" is largely covered by the existing replay; Phase 55 adds the COACH-specific prompt-grounding leg (the prompt built for a coach event uses `evidence_line` + COACH persona, and empty evidence → no hallucinated coaching).
- `scripts/eval/replay_harness.py` + `tests/eval/test_replay_harness_cooldowns.py` — the cooldown/tuning instrument carries over; no coach-specific change needed (cooldowns are per-event-type, persona-independent).

**What is genuinely NEW for LIVE-02 (the coach leg):**
- A coach-mode anti-slop spine test: empty/weak evidence MusicState → the per-event coach prompt is built from `evidence_line` (grounded real state), and a coach reaction citing an event NOT in the registry → `CitationLinter.check(...).valid is False` → strip. ≥2 genres: genre-1 (real fixture) + genre-2 (synthetic build→drop, BPM ~125-135) — both driven through the real detector + real linter.
- A coach-prompt-grounding test: `build_system_instruction("intermediate", "coach")` selects a COACH_* cell carrying the citation grammar + anti-slop footer; `AICoach.build_prompt(coach_event, registry_snapshot=...)` emits the grounded evidence line + the coach task tail. Pin that the COACH path is grounded the same way HYPE is.

**Coach machinery confirmed v4-byte-identical / load-bearing (do NOT modify):**
- `src/vibemix/state/coach.py` — `evidence_line` (track-name floor at confidence 0.3, NO `phase=` field — the anti-hallucination invariant), `_evidence_line_compact` (diet path), evidence-corpus footer, `task_for_event` (per-event coach IP), `build_prompt`. Golden-string-pinned by `tests/state/test_coach.py`.
- `src/vibemix/prompts/matrix.py` — `COACH_BEGINNER` / `COACH_INTERMEDIATE` / `COACH_PRO` each carry `{mood_persona}` + the shared `_ANTI_SLOP_FOOTER` + `CITATION_GRAMMAR_BLOCK` (the 7 source forms in lock-step with `EVIDENCE_SOURCES`). `build_system_instruction(skill, mode)` dispatches. Pinned by `tests/prompts/test_matrix.py`.
- `src/vibemix/runtime/coach.py` — `coach_loop` (10Hz poll, single-in-flight, mic gating, periodic `ipc.session.citation` publish at 0.5Hz). Pinned by `tests/runtime/test_coach.py` + `test_coach_citation_publish.py`.

---

## Q2. LIVE-04 (citation integrity) — make it airtight, close the leaks

Three automatable regressions per CONTEXT.md §specifics, plus the two leak fixes from Q0.

**(a) Zero-orphan replay regression.** Replay the real session trace; for every `[track:<id>]` / `[ev:...]` / evidence citation the coach grammar produces, assert it resolves to a real `EvidenceRegistry` entry → assert orphan count == 0. The real registry path: `register_library()` registers `track:<id>` keys (wired in `__main__.py:801`); `EventDetector._fire` + `state_refresh_loop` write `ev`/`aud`/`mix` keys. Build a registry from the fixture's real events, then assert every citation the linter would accept resolves and no fabricated id slips through.

**(b) Hallucination-strip + slop-metrics regression.** Inject a model response citing a non-existent evidence id → assert `CitationLinter.check` strips it (`valid=False`, `reason="invalid_atoms"`, the orphan in `missing`), AND — after the leak fix — the real `slop_ratio` rises and the stripped text surfaces in `last_unverified_response`. Today the strip half is pinned (`test_hype_anti_slop.py::test_spine_unbacked_citation_is_stripped`); the slop-metrics half is NEW (it does not move at HEAD because of the placeholder).

**(c) IPC payload reflects real stripped/verified counts.** After the leak fix, `_citation_telemetry()` must return a `slop_ratio` sourced from a real stripped/total counter and a `last_unverified_response` sourced from the strip path's `raw_text`. Pin via a unit test on the new telemetry source + extend `tests/runtime/test_coach_citation_publish.py` to assert the payload carries real values (not mock zeros).

**Recommended fix shape (smallest correct, append-only):**
- Add a thin **slop counter** primitive (or extend `StrippedRateTracker`) exposing cumulative `(stripped, total)` so `slop_ratio = stripped / total`. The StrippedRateTracker already records every decision (`record(True/False)`); a cumulative pair is a 2-field addition. The rolling 15s `rate()` already exists and is correct — keep it for `stripped_rate_15s`.
- Add a **last-unverified ring** (1-entry is sufficient for the schema; CONTEXT mentions a small ring) populated from the strip/bypass path. Source: the `full_text` already captured at `dj_cohost.py:1050` (`raw_text=full_text`). Wire it through a callback or a shared holder read by `_citation_telemetry()`.
- Rewrite `_citation_telemetry()` (`__main__.py:706-752`) to read the real slop_ratio + last-unverified from those primitives. Keep `bypass_active` (already a real read) + `stripped_rate_15s` (already real).

**Debrief consistency (LIVE-04 SC3 / CONTEXT §code_context):** confirm the citation strip is consistent live vs the debrief path. The debrief leg already resolves citations against the registry at ±2.0s (`mode="debrief"`); a regression should assert the SAME orphan would be stripped in BOTH live (`mode="live"`, ±1.0s) and debrief (`mode="debrief"`, ±2.0s) — one grammar, one registry, two tolerance bands. This is a consistency assertion, not a rebuild.

---

## Q3. UI surface (Phase 55 UI hint: yes)

ROADMAP Success Criterion 3: *"Clicking a live citation deep-links to the real event it cites (citation → debrief region highlight works on real session data, not fixtures)."* The diagnostics drawer + `ipc.session.citation` surface ALREADY EXISTS (`SessionCitationPayload` → `ipc.session.citation` → Tauri Settings → Diagnostics; Phase 24 shipped `ipc.session.overlay_highlight` for `[screen:<id>]` deep-link). The Phase 24 overlay-highlight path (`dj_cohost.py:1088-1115`) already publishes on `screen` citations.

**UI scope is MINIMAL:** the engineering work makes the *existing* citation strip show real values (`slop_ratio` moves, `last_unverified_response` populates). The "click citation → highlight" deep-link is largely shipped (Phase 24). Phase 55 verifies the strip reflects real session data and the deep-link works on real (not fixture) data — both achievable as a vitest assertion against the diagnostics component consuming a real-valued `SessionCitationPayload`, plus a Kaan-action live-drive check. **No new component, no new IPC schema.** See VALIDATION + the UI-SPEC gate note in the orchestrator report — scope is "wire real values into the existing strip + pin the existing component renders them", not net-new UI.

---

## Validation Architecture

| LIVE req | Automatable proof | Kaan-action (deferred) |
|----------|-------------------|------------------------|
| LIVE-02 | Coach anti-slop spine (empty evidence → no hallucinated coaching; grounded citation passes) + ≥2-genre detector replay (genre-1 real fixture + genre-2 synthetic) + COACH-prompt-grounding test | "Does coach mode coach USEFULLY across ≥2 genres" live drive on Kaan's Mac (his ears) |
| LIVE-04 | Zero-orphan replay regression + hallucination-strip-moves-slop-metrics + IPC payload reflects real stripped/verified counts + live/debrief consistency | Watch the diagnostics citation strip during a full-set live drive: slop_ratio low, no orphans, last-unverified populates on a real strip |

**Test infra:** pytest (`source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q`) + vitest (`tauri/ui/`). No new framework. Reuse `tests/fixtures/hype_trace_genre1.jsonl`, the `test_event_detector.py` clock-patch pattern, REAL `EvidenceRegistry`+`CitationLinter` primitives, and the `test_coach_citation_publish.py` async harness.

---

## Landmines

1. **Do NOT re-snapshot the registry inside the linter chokepoint.** `dj_cohost.py` reuses the per-turn snapshot taken at ~line 216; a second snapshot races the writers (commented LOAD-BEARING). The leak-fix telemetry must read cumulative counters, not re-snapshot.
2. **`eval/corpus/sessions/*.events.jsonl` are EMPTY placeholders** (pending Kaan corpus acquisition, per `manifest.json._note`) — use `tests/fixtures/hype_trace_genre1.jsonl` (the real recordings trace), as Phase 54 did.
3. **`coach.py` evidence_line has NO `phase=` field — anti-hallucination invariant (v4:1350-1351).** Any change near it must not reintroduce it (golden-pinned by `test_coach.py`).
4. **Coach machinery is v4-byte-identical and golden-string-pinned.** The leak fix touches `__main__.py` telemetry + a new small primitive + the strip-path source wiring — NOT `coach.py`, NOT `citation_linter.py`, NOT `evidence_registry.py` core, NOT the matrix COACH cells.
5. **`StrippedRateTracker` is NOT thread-safe by design** (single-threaded coach loop). A cumulative slop counter must follow the same single-threaded contract — do not add it to a multi-threaded write path. The `record()` call already happens on the event loop in `llm_node`.
6. **Kaan WIP in working tree:** `tauri/src-tauri/src/mascot_window.rs` + `tauri/src-tauri/tauri.conf.json5` are uncommitted — DO NOT touch/stage them.

## RESEARCH COMPLETE
