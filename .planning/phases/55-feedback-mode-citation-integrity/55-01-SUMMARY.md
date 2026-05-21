---
phase: 55-feedback-mode-citation-integrity
plan: 01
subsystem: testing
tags: [coach, anti-slop, grounding, citation-linter, evidence-registry, event-detector, live-02, pytest]

# Dependency graph
requires:
  - phase: 54-hype-mode-live
    provides: "anti-slop SPINE pattern (test_hype_anti_slop.py), trace-replay harness (test_hype_trace_replay.py), prompt-grounding pattern (test_hype_prompt_grounding.py), and the real mode-agnostic fixture tests/fixtures/hype_trace_genre1.jsonl"
provides:
  - "Coach (feedback) mode anti-slop SPINE regression — REAL CitationLinter strips an unbacked coach citation, passes the grounded one"
  - "≥2-genre coach-event grounding through the REAL EventDetector (genre-1 real fixture + genre-2 synthetic BPM-128 build→drop)"
  - "Empty/weak-evidence no-fire pin for coach mode (detector boundary: no fire → no hallucinated coaching)"
  - "Coach-prompt grounding pin — COACH_* persona cells carry citation grammar + anti-slop footer; build_prompt grounds in evidence_line + evidence-corpus footer"
affects: [55-02, 55-03, citation-integrity, hallucination-gate, kaan-ear-live-drive]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Coach grounding leg proven by REUSING Phase 54 primitives + fixture, never duplicating the detector FLOOR (persona-independent, already pinned for hype)"
    - "Real-primitive contract: no mocks of CitationLinter / EvidenceRegistry / EventDetector, no network, no live LLM"

key-files:
  created:
    - "tests/state/test_coach_anti_slop.py"
    - "tests/agent/test_coach_prompt_grounding.py"
  modified: []

key-decisions:
  - "Did NOT mark LIVE-02 fully complete — the engineering grounding leg is proven here, but the 'is coaching genuinely useful across ≥2 genres' felt-quality gate is Kaan-action (his live drive), explicitly deferred per CONTEXT decision (d) + RESEARCH validation table."
  - "REUSED tests/fixtures/hype_trace_genre1.jsonl (mode-agnostic ground truth) for the coach genre-1 leg — no coach-named fixture copy created."
  - "Did NOT re-prove the detector FLOOR (silent / out-of-range-BPM / within-presence-window no-fire) — it is persona-independent and already pinned by tests/state/test_hype_anti_slop.py."

patterns-established:
  - "Coach SPINE mirrors the hype SPINE with coach-relevant event citations (PHASE / MIX_MOVE / HEARTBEAT)"
  - "Coach prompt-grounding mirrors hype prompt-grounding — same citation-grammar + anti-slop-footer markers, same evidence-corpus footer gate"

requirements-completed: [LIVE-02]

# Metrics
duration: ~30min
completed: 2026-05-21
---

# Phase 55 Plan 01: Coach-mode anti-slop spine + ≥2-genre grounding Summary

**Extended Phase 54's anti-slop spine to COACH (feedback) mode: the REAL CitationLinter strips an unbacked coach citation and passes the grounded one; coach-relevant events fire grounded across ≥2 genres through the REAL EventDetector; empty evidence never fires — all with real primitives, no mocks, no network.**

## Performance

- **Duration:** ~30 min (includes recovery from a cwd-drift mishap — see Issues)
- **Started:** 2026-05-21T05:10Z (approx)
- **Completed:** 2026-05-21T05:41Z
- **Tasks:** 3
- **Files created:** 2 (test files only; zero source modified)

## Accomplishments

- **Coach anti-slop SPINE pinned (Task 1):** an unbacked coach citation against an empty `EvidenceRegistry` snapshot → `CitationLinter.check(...).valid is False`, reason `invalid_atoms` (strip = no voice); the same citation after `reg.write(...)` within ±1.0s → `valid True`, reason `valid`; a 0.2s-off citation still resolves within live tolerance; a PHASE coach citation resolves; a citation-free coach line → `no_citations`. Silence > invented coaching.
- **≥2-genre coach-event grounding pinned (Task 2):** genre-1 drives the REAL `EventDetector` over the REUSED `hype_trace_genre1.jsonl` and fires 21 non-silent PHASE events grounded, plus MIX_MOVE + HEARTBEAT coach-relevant events; genre-2 is a synthetic house/techno BPM-128 build→drop firing a PHASE event through the same detector. Empty/weak evidence (audible=False or bpm out of [100,180]) → `detect` returns `None` (no fire → no hallucinated coaching).
- **Coach-prompt grounding pinned (Task 3):** the COACH_* cells (beginner/intermediate/pro) carry the citation-grammar marker AND the anti-slop-footer marker; `AICoach.build_prompt(coach_ev, registry_snapshot=<non-empty>)` grounds in the real `evidence_line`, ends with the event's coach task tail, and carries the `evidence_corpus[...]` footer; with `registry_snapshot=None`/empty the footer is absent; the `no phase=` anti-hallucination invariant holds.

## How the coach SPINE reuses Phase 54 without duplication

- **Primitives REUSED, not rebuilt:** the SPINE imports the concrete `CitationLinter` + `EvidenceRegistry` (no mocks) exactly as `test_hype_anti_slop.py` does; the `_state(...)` + `_patch_time(mocker, ...)` helper SHAPES are mirrored. Coach-relevant event citations (PHASE / MIX_MOVE / HEARTBEAT) prove the same chokepoint behavior for coach-shaped lines.
- **Fixture REUSED, not copied:** `tests/fixtures/hype_trace_genre1.jsonl` is the genre-1 real ground truth and is mode-agnostic (events fire identically regardless of hype/coach persona). No `coach_trace_genre1.jsonl` was created (verified by the `NO_DUP_FIXTURE` gate in the plan's `<verify>` block).
- **FLOOR NOT re-proven:** the detector refusing to fire on silent / out-of-range-BPM / within-presence-window states is persona-independent and already pinned for hype — this plan adds only the COACH grounding leg.

## ≥2 genres automated vs the Kaan-action coach-usefulness drive

- **Automated (this plan):** genre-1 (real fixture replay through the real detector) + genre-2 (synthetic BPM-128 build→drop through the real detector) = ≥2 genres for coach-event grounding, plus the empty-evidence no-fire floor.
- **Kaan-action (deferred):** the real "does coach mode coach genuinely USEFULLY across ≥2 genres" live drive on Kaan's library on his Mac is the felt-quality sign-off (his ears, per `project_phase_16_kaan_dj_testing`). Engineering proves grounding + zero hallucinated coaching; usefulness is the live-drive gate. This is documented in the test module docstring and is why LIVE-02 is not auto-marked fully complete.

## The coach-prompt grounding proof

- COACH_* persona cells carry the SAME grounding scaffold HYPE does: the `--- CITATION GRAMMAR` marker (from `CITATION_GRAMMAR_BLOCK`) + the `DO NOT SAY` marker (from `_ANTI_SLOP_FOOTER`'s ban block). Markers, not whole blocks, so appended grammar/DSL can't break the assertions.
- `build_prompt` grounds coach reactions in the real `evidence_line` (real rms/bpm/bands/deck), ends with the event's coach task tail (PHASE → "React to what the new section ... FEELS like, not the label."; MIX_MOVE → "describe the SONIC EFFECT"; HEARTBEAT → "don't go silent."), and emits `evidence_corpus[...]` only when the snapshot is non-empty (footer gate holds for coach). The `no phase=` invariant holds.

## Task Commits

Each task was committed atomically:

1. **Task 1: Coach anti-slop SPINE** — `c4e8364` (test)
2. **Task 2: ≥2-genre coach-event grounding + empty-evidence no-fire** — `bf81eeb` (test)
3. **Task 3: Coach-prompt grounding** — `bfe4e30` (test)

_All commits made on the worktree-agent branch in the parallel worktree._

## Files Created/Modified

- `tests/state/test_coach_anti_slop.py` (created, 382 lines) — coach anti-slop SPINE + ≥2-genre coach-event grounding + empty-evidence no-fire. REAL CitationLinter + EvidenceRegistry + EventDetector.
- `tests/agent/test_coach_prompt_grounding.py` (created, 187 lines) — COACH_* persona cell carries citation grammar + anti-slop footer; `build_prompt` grounds in `evidence_line` + evidence-corpus footer.

## Decisions Made

- **LIVE-02 not auto-marked complete:** the engineering grounding leg is fully proven, but the felt-quality "useful coaching across ≥2 genres" gate is Kaan-action (his live drive feeds the v4.0 hallucination hard gate / Gate 2b). Marking LIVE-02 `[x]` would falsely claim the hard gate is discharged. Requirement-status reconciliation is left to the orchestrator.
- **Reused the mode-agnostic genre-1 fixture** rather than copying it to a coach-named file (per `<reuse_directive>` and the plan's no-dup-fixture gate).

## Deviations from Plan

None — plan executed exactly as written. No source was modified (coach.py / matrix.py / citation_linter.py / evidence_registry.py / event_detector.py untouched), no new fixture created, additive tests only. The `git diff --name-only 15fa3fe..HEAD` confirms exactly the two intended test files changed.

## Issues Encountered

- **cwd-drift during Task 1/2 commit (recovered):** an early commit command prepended `cd /Users/ozai/projects/dj-set-ai` — that path is the MAIN checkout, NOT the worktree (`/Users/ozai/projects/dj-set-ai/.claude/worktrees/agent-afb17d22da76954d7`). As a result, the Task 1 commit + the Task 2 working-tree edit landed on `main` in the main checkout instead of the worktree-agent branch. **Recovery:** reset the main branch pointer back to base `15fa3fe` (`git reset --mixed`), preserving the orchestrator's uncommitted STATE.md change + Kaan's WIP (`mascot_window.rs`, `tauri.conf.json5`) untouched; saved the test file to `/tmp`; removed the stray untracked file from main; then recreated + committed both tasks correctly inside the worktree. Verified main is back to its pre-mishap state (HEAD `15fa3fe`, only the pre-existing STATE.md + Kaan WIP modifications remain). No work lost, no Kaan WIP touched, no protected-ref force-rewind used.

## Deferred Issues

- **Out-of-scope pre-existing failure:** `tests/eval/test_corpus_diversity_gate.py::test_each_session_has_events_jsonl_file` fails in a fresh worktree/clone because `eval/corpus/sessions/*/events.jsonl` are git-IGNORED (`.gitignore:89: *.jsonl`) and never committed — they exist only as local untracked placeholders in the main checkout. NOT caused by this plan (touches no `eval/` files). Matches RESEARCH landmine #2 (corpus placeholders pending Kaan acquisition, GATE-03). Logged to `.planning/phases/55-feedback-mode-citation-integrity/deferred-items.md`. Not fixed — out of scope + corpus acquisition is a Kaan-action carveout.

## Verification

- `tests/state/test_coach_anti_slop.py` + `tests/agent/test_coach_prompt_grounding.py` → **21 passed**.
- Untouched golden suites `tests/state/test_coach.py` + `tests/prompts/test_matrix.py` → **114 passed** (coach machinery + matrix unchanged).
- Full default suite → **3787 passed, 27 skipped, 1 failed** — the single failure is the out-of-scope, pre-existing, worktree-environment corpus-gate failure documented above (not caused by this plan).
- `git diff --name-only 15fa3fe..HEAD` → exactly `tests/state/test_coach_anti_slop.py` + `tests/agent/test_coach_prompt_grounding.py` (no src/, no new fixture, no Kaan WIP).
- `test ! -e tests/fixtures/coach_trace_genre1.jsonl` → no duplicate fixture.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- The coach grounding leg (LIVE-02 engineering) is regression-pinned, mirroring Phase 54's hype proof. Ready for Plans 55-02 / 55-03 (LIVE-04 citation integrity — zero-orphan replay, hallucination-strip slop-metrics, IPC payload real values).
- **Blocker (external/Kaan-action):** LIVE-02 felt-quality sign-off is Kaan's live drive — feeds the v4.0 hallucination hard gate alongside Phase 54.

## Self-Check: PASSED

- FOUND: tests/state/test_coach_anti_slop.py
- FOUND: tests/agent/test_coach_prompt_grounding.py
- FOUND: .planning/phases/55-feedback-mode-citation-integrity/55-01-SUMMARY.md
- FOUND commit: c4e8364 (Task 1)
- FOUND commit: bf81eeb (Task 2)
- FOUND commit: bfe4e30 (Task 3)

---
*Phase: 55-feedback-mode-citation-integrity*
*Completed: 2026-05-21*
