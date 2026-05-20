---
phase: 54
slug: hype-mode-live
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-21
---

# Phase 54 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Verified against HEAD `9137a91`. The reaction machinery (EventDetector +
> cooldowns + HYPE_* matrix + coach_loop + EvidenceRegistry + CitationLinter)
> is ALREADY SHIPPED — this phase HARDENS grounding + TUNES timing with
> test-pinned real-trace regressions. It does NOT re-implement any of it.
> A real captured trace (`recordings/20260515-112139/events.jsonl`) proves
> 52 events → 52 spoken reactions → 0 suppressions: firing is reliable at
> HEAD; the "32s-silent-on-drop" bug is historical/closed.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (`[tool.pytest.ini_options]`, `--strict-markers`) + vitest (`tauri/ui/`) for the indicator |
| **Config file** | `pyproject.toml` (Python); `tauri/ui/package.json` + `vitest.config` (frontend) |
| **Quick run command** | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q <file>` |
| **Full suite command** | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` |
| **Estimated runtime** | ~60-120 seconds (default suite); frontend `npm test` ~10-20s; +real-hw live drive is `macos_audio`, Kaan-action |

---

## Sampling Rate

- **After every task commit:** Run the task's quick command (single test file).
- **After every plan wave:** Run the full default suite.
- **Before `/gsd:verify-work`:** Full default suite must be green. The `macos_audio` live drive (≥2-genre Kaan-ear sign-off) is Kaan-action and recorded as deferred — not a default-suite gate.
- **Max feedback latency:** ~120 seconds (full suite).

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 54-01-01 | 01 | 1 | LIVE-01 | — | Real captured ground-truth trace fixture checked in (drop/build events with timestamps + types); loads cleanly | unit | `pytest -q tests/state/test_hype_trace_replay.py` | ❌ W0 | ⬜ pending |
| 54-01-02 | 01 | 1 | LIVE-01 | — | Genre-1 trace: each ground-truth PHASE/LAYER_ARRIVAL drives an EventDetector that emits the matching Event within the in-bar tolerance | unit (clock-patched) | `pytest -q tests/state/test_hype_trace_replay.py` | ❌ W0 | ⬜ pending |
| 54-01-03 | 01 | 1 | LIVE-01 | — | Genre-2 synthetic house/techno build→drop sequence fires the drop Event (→ ≥2 genres covered in the automated suite) | unit | `pytest -q tests/state/test_hype_trace_replay.py` | ❌ W0 | ⬜ pending |
| 54-02-01 | 02 | 1 | LIVE-03 | — | Consecutive same-type events inside `MIN_EVENT_GAP_PER_TYPE` do NOT double-fire (cooldown respected on the real-trace replay) | unit | `pytest -q tests/state/test_hype_cooldown_grounding.py` | ❌ W0 | ⬜ pending |
| 54-02-02 | 02 | 1 | LIVE-03 | — | `IN_BAR_TOLERANCE_S` constant exists, is one-line editable in `vibemix/audio/constants.py`, and is pinned by a test that reads it | unit | `pytest -q tests/state/test_hype_cooldown_grounding.py` | ❌ W0 | ⬜ pending |
| 54-02-03 | 02 | 1 | LIVE-03 | — | `--print-cooldowns` harness runs over the captured-trace fixture and reports per-type measured-vs-locked deltas (tuning instrument); existing cooldown-report tests stay green | unit/cli | `pytest -q tests/eval/test_replay_harness_cooldowns.py` | ✅ (extends existing) | ⬜ pending |
| 54-03-01 | 03 | 1 | LIVE-01 | — | Anti-slop floor: empty/silent/weak-evidence MusicState → `EventDetector.detect(..., manual=False)` returns None (no Event → no fire) | unit | `pytest -q tests/state/test_hype_anti_slop.py` | ❌ W0 | ⬜ pending |
| 54-03-02 | 03 | 1 | LIVE-01 | — | Anti-slop spine: a reaction citing an event NOT in an empty EvidenceRegistry snapshot → `CitationLinter.check(...).valid is False` (→ strip → no voice) using REAL primitives, no network | unit | `pytest -q tests/state/test_hype_anti_slop.py` | ❌ W0 | ⬜ pending |
| 54-03-03 | 03 | 1 | LIVE-01 | — | HYPE persona cell selected for (hype, intermediate/beginner/pro); the per-event prompt is built from `evidence_line` (grounded real state) | unit | `pytest -q tests/agent/test_hype_prompt_grounding.py` | ❌ W0 | ⬜ pending |
| 54-04-01 | 04 | 2 | LIVE-01 | — | Hype-mode indicator renders "HYPE · LIVE" when interaction mode is hype; uses amber/charcoal tokens (no AI-slop palette) | unit (vitest) | `cd tauri/ui && npm test -- hype-mode-indicator` | ❌ W0 | ⬜ pending |
| 54-04-02 | 04 | 2 | LIVE-01 | — | Reaction-cadence pulse fires on each `SessionCohostReaction` arrival (the "cadence feels alive" visible heartbeat — SC4 surface) | unit (vitest) | `cd tauri/ui && npm test -- hype-mode-indicator` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/fixtures/hype_trace_genre1.jsonl` — checked-in copy of the real captured ground-truth trace (drop/build events, timestamps + types) so the suite does not reach into the mutable `recordings/` dir
- [ ] `tests/state/test_hype_trace_replay.py` — new, LIVE-01 trace-replay (genre 1 real + genre 2 synthetic)
- [ ] `tests/state/test_hype_cooldown_grounding.py` — new, LIVE-03 cooldown respect + in-bar tolerance constant
- [ ] `tests/state/test_hype_anti_slop.py` — new, LIVE-01 anti-slop floor (detector) + spine (linter)
- [ ] `tests/agent/test_hype_prompt_grounding.py` — new, LIVE-01 HYPE persona + grounded evidence_line
- [ ] `src/vibemix/audio/constants.py` — add `IN_BAR_TOLERANCE_S` constant (data, not test; one-line editable)
- [ ] `tauri/ui/src/session/hype-mode-indicator.ts` (+ `.spec.ts`) — new, LIVE-01 SC4 indicator + cadence pulse

*Existing infrastructure (`tests/state/test_event_detector.py` clock-patch pattern, `scripts/eval/replay_harness.py` + its `--print-cooldowns` mode, REAL `EvidenceRegistry` + `CitationLinter` primitives, `tauri/ui` vitest harness) covers fixtures — no new framework install.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Hype mode feels alive across ≥2 genres, in-bar, no slop — reactions land on real drops like a friend, not a script; cadence present at the right density | LIVE-01 (SC2/SC4) | needs his library + his ear (hard quality gate per CLAUDE.md + `project_phase_16_kaan_dj_testing`) | `VIBEMIX_MODE=hype uv run python -m vibemix`; play ≥2 genres into BlackHole 2ch; listen — drops land in-bar, across genres, no scripted/late/fake/hallucinated lines. |
| Final cooldown/latency tuning pass after the live drive | LIVE-03 | needs his ear on real cadence | `python -m scripts.eval.replay_harness --corpus recordings --print-cooldowns` → read measured-vs-locked per-type deltas; if a drop lands late, edit the one constant in `vibemix/audio/constants.py` + restart (`feedback_no_gsd_orchestra_for_trivial_tweaks`). |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-21
