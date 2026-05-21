---
phase: 59-full-deck-awareness-grounding
plan: 01
subsystem: state
tags: [deck-state, harmonics, camelot, music-state, grounding]
requires: []
provides:
  - "state/harmonics.py::to_camelot — pure Rekordbox-tag → Camelot normalizer (load-bearing dependency of every key: citation)"
  - "state/deck_state.py::DeckTrack + DeckState — honest-default per-deck model"
  - "state/music_state.py::MusicState.deck_state — additive default-empty field"
affects:
  - "Plan 59-02+ (deck poller writes DeckTrack snapshots)"
  - "Plan 59-04 (_tick_once populates DeckTrack.camelot via to_camelot; evidence_line gains the deck block)"
  - "Phase 60 (consumes is_clash/compatible ON TOP of to_camelot; reasons on DeckTrack.camelot)"
tech-stack:
  added: []  # zero new deps — pure stdlib (re + dataclasses)
  patterns:
    - "honest-unknown degradation (mirror track_resolver): to_camelot → None, never raises"
    - "additive default-empty field for golden-equivalence (mirror Phase 52 detected_genre)"
    - "typed-empties-on-absence dataclass (mirror library.rekordbox.TrackEntry)"
key-files:
  created:
    - src/vibemix/state/harmonics.py
    - src/vibemix/state/deck_state.py
    - tests/state/test_harmonics.py
    - tests/state/test_deck_state.py
    - tests/state/test_coach_prompt_grounding.py
  modified:
    - src/vibemix/state/music_state.py
decisions:
  - "Open-key form ('Nm'/'Nd') derived programmatically from the canonical rotation (1m==8A anchor) rather than hand-typed — eliminates transcription error across 24 entries"
  - "Golden-equivalence regression test created at tests/state/test_coach_prompt_grounding.py (plan frontmatter file) — the existing tests/agent/ grounding test left untouched; new test pins evidence_line byte-identity for BOTH empty AND populated deck_state (Phase 59 does not read the field)"
  - "DeckTrack/DeckState left as plain (non-frozen) dataclasses — _tick_once mutates dt.camelot in place inside the lock batch (RESEARCH §_tick_once wiring), so frozen would break the writer"
metrics:
  duration: "~12 min"
  completed: "2026-05-21"
  tasks: 2
  files: 6
---

# Phase 59 Plan 01: Deck-State + Harmonics Foundation Summary

The two zero-dependency foundations Phase 59 builds on, landed bottom-up via TDD: the pure `harmonics.to_camelot()` normalizer (Rekordbox `Tonality` is musical notation `Am`/`F#m`, NOT Camelot — every `key:` citation depends on this conversion existing) and the additive `DeckState`/`DeckTrack` model embedded in `MusicState` as a default-empty field that preserves snapshot/prompt golden-equivalence until a later plan populates it.

## What Was Built

**Task 1 — `harmonics.to_camelot` (the load-bearing pure function):**
- `src/vibemix/state/harmonics.py` (NEW, pure, zero-dep): the 24-entry `_MUSICAL_TO_CAMELOT` wheel verbatim from RESEARCH (both enharmonic spellings: `G#m`==`Abm`==`1A`), a programmatically-derived `_OPEN_KEY_TO_CAMELOT` rotation table (anchored at `1m`==`8A`), and `to_camelot(raw)` accepting all three input forms (musical / Camelot passthrough / open-key) and degrading to `None` on empty/garbage/out-of-range — **never raises** (honest-unknown discipline mirroring `track_resolver`).
- `is_clash`/`compatible` deliberately NOT defined (Phase 60 owns them) — grep-gated to 0.

**Task 2 — `DeckState`/`DeckTrack` + additive `MusicState.deck_state`:**
- `src/vibemix/state/deck_state.py` (NEW): `DeckTrack` (honest defaults — `source="unknown"`, every harmonic field `None`/`0.0`; no false-confident key by construction) + `DeckState` (`decks={}` via `default_factory`), verbatim field set from RESEARCH §Pattern 1.
- `src/vibemix/state/music_state.py` (MODIFIED): additive `deck_state: DeckState = field(default_factory=DeckState)` with single-writer + golden-equivalence documentation matching the Phase-52 `detected_genre` comment density. `evidence_line` untouched (deck block is Plan 59-04).

## Verification

- `PYTHONPATH=src python3 -m pytest tests/state/test_harmonics.py tests/state/test_deck_state.py tests/state/test_coach_prompt_grounding.py -x -q` → **67 passed**.
- `to_camelot('Am')=='8A'`, `to_camelot('F#m')=='11A'`, `to_camelot('')` is `None` → inline assert exits 0.
- `grep -c "def is_clash\|def compatible" src/vibemix/state/harmonics.py` → **0** (Phase 60 scope not leaked).
- `MusicState().deck_state.decks=={}` and `.updated_at==0.0` → inline assert exits 0.
- Golden-equivalence (Pitfall 5 / T-59-01-02): empty AND populated `deck_state` both leave `evidence_line` byte-identical to the captured pre-Phase-59 baseline (`hearing[silent] | track=unknown | deck=none | set_time=0:00 | recent_moves[8s]: NONE`).
- Threat T-59-01-01: all malformed `to_camelot` inputs (`''`, `None`, `garbage`, `13A`, `0A`, `8C`, whitespace, `99m`, `XYZ`) → `None`, no raise.

## Deviations from Plan

None — plan executed exactly as written. Two clarifications worth recording (not deviations):

1. **Golden-equivalence test location.** The plan frontmatter lists `tests/state/test_coach_prompt_grounding.py` while the existing grounding test lives at `tests/agent/test_coach_prompt_grounding.py`. Per the authoritative frontmatter file list, the new golden-equivalence regression was created at `tests/state/test_coach_prompt_grounding.py` (the `tests/agent/` file was left untouched). The new test additionally pins byte-identity for a *populated* `deck_state` (stronger than the plan's empty-only requirement, valid because Phase 59 does not read the field).
2. **Open-key table** derived programmatically from the canonical `1m`==`8A` rotation rather than hand-transcribed — same result, zero transcription risk.

## Deferred Issues (out of scope — pre-existing, NOT caused by this plan)

7 full-suite tests fail on the `live-tuning-or-brain` WIP branch independent of this plan — **proven pre-existing** by reverting `music_state.py` to the pre-plan commit `5f375c0` and re-running (all 7 fail identically with deck-state changes absent; none reference `deck_state`/`harmonics`/`DeckTrack`/`DeckState`). They stem from in-flight v4.0 ship/branch work (`__main__.py` orchestrator wiring, README feature-matrix not regenerated for phases 55–58, `cut_release.sh` regex churn). Logged in detail at `.planning/phases/59-full-deck-awareness-grounding/deferred-items.md`. **Action:** none in this plan — they belong to the branch-finalization work, not deck-state.

## TDD Gate Compliance

Both tasks followed RED → GREEN cleanly (no refactor needed):
- Task 1: `test(59-01)` `eaf9992` (RED, module missing) → `feat(59-01)` `d962611` (GREEN).
- Task 2: `test(59-01)` `0d0110f` (RED, module/field missing) → `feat(59-01)` `e0fecf1` (GREEN).
RED was a genuine failure each time (ModuleNotFoundError) — no test passed unexpectedly before implementation.

## Known Stubs

None. `harmonics.to_camelot` is fully implemented (all three input forms + degradation). The numpy KS estimator and the vision leg are explicitly OUT of this plan's scope (later plans / RESEARCH Open-Q2); `DeckTrack.source="numpy_key"` is a documented slot value, not a stub.

## Self-Check: PASSED

- FOUND: src/vibemix/state/harmonics.py
- FOUND: src/vibemix/state/deck_state.py
- FOUND: src/vibemix/state/music_state.py (deck_state field at line 69)
- FOUND: tests/state/test_harmonics.py
- FOUND: tests/state/test_deck_state.py
- FOUND: tests/state/test_coach_prompt_grounding.py
- FOUND commit eaf9992 (test 59-01 harmonics RED)
- FOUND commit d962611 (feat 59-01 harmonics GREEN)
- FOUND commit 0d0110f (test 59-01 deck_state RED)
- FOUND commit e0fecf1 (feat 59-01 deck_state GREEN)
