---
phase: 77-wire-connect-the-islands
plan: 01
subsystem: test-scaffolding
tags: [wire, grounding, persona-seam, memory-ingest, env-override, regression-pins, tdd-red]
requires:
  - "src/vibemix/library/grounding.py (Grounding contract — read-only)"
  - "src/vibemix/agent/dj_cohost.py (DJCoHostAgent constructor + set_next_event)"
  - "src/vibemix/prompts/matrix.py (MOOD_PERSONAS + block headers)"
  - "src/vibemix/library/agent.py + codex_curate.py (curator system prompts)"
  - "src/vibemix/__main__.py (_load_env_robust + _session_ipc)"
  - "src/vibemix/state/coach.py (task_for_event + evidence_line — shipped WIRE-02/03)"
provides:
  - "tests/agent/test_dj_cohost_grounding.py (WIRE-01 failing scaffold + green citation-gate)"
  - "tests/memory/test_ingest_wiring.py::WIRE-05 main()-path ingest scaffold (extension)"
  - "tests/library/test_curator_persona_seam.py (WIRE-04 failing scaffold + green RULES pin)"
  - "tests/runtime/test_load_env_override.py (WIRE-06 failing scaffold + green security pin)"
  - "tests/repo/test_wire_regression_pins.py (WIRE-02/03 green regression pins)"
affects:
  - "Plans 77-02 (WIRE-04 build_curator_instruction), 77-03 (WIRE-06 override flip), 77-04 (WIRE-01/05 dispatch)"
tech-stack:
  added: []
  patterns:
    - "xfail(strict=True) RED scaffold — flips to hard failure if implemented wrong"
    - "two-tier wiring test (source-text gate + behavioural fakes), off-loop thread-id proof"
    - "honest green — no genai.Client, no GEMINI_API_KEY"
key-files:
  created:
    - tests/agent/test_dj_cohost_grounding.py
    - tests/library/test_curator_persona_seam.py
    - tests/runtime/test_load_env_override.py
    - tests/repo/test_wire_regression_pins.py
  modified:
    - tests/memory/test_ingest_wiring.py
decisions:
  - "WIRE-03 pin asserts the SHIPPED format genre=<name> (not genre=<name>(conf) as the plan text suggested) — the live coach.py emits genre=<name> with the confidence used only as the >=0.5 gate, so the pin matches reality."
  - "WIRE-02 EvidenceRegistry coupling: genre-chain measurements are narrate-only (NOT registry-citable per coach.py:594), so the pin asserts the measured payload reaches the task string rather than a registry round-trip."
  - "Cold-path test uses getattr(agent, '_grounding', None) is None so it stays green BOTH pre- and post-Plan-04 (the attribute does not exist yet)."
metrics:
  duration: "~7 min (incl. 4 min full-suite run)"
  completed: "2026-05-26"
  tasks: 3
  files: 5
---

# Phase 77 Plan 01: WIRE Test Scaffolds Summary

Wave-0 RED scaffolds — every unimplemented wire (WIRE-01/04/05/06) now has an `xfail(strict=True)` automated proof that flips to a real pass the moment its implementation plan lands, plus GREEN regression pins locking the already-shipped WIRE-02/03 behavior and the cold-path / security invariants. Honest green: zero Gemini API dependency, no `genai.Client` constructed anywhere.

## What Was Built

| Task | File | Tier breakdown |
|------|------|----------------|
| 1 | `tests/agent/test_dj_cohost_grounding.py` (new) | WIRE-01: source-text off-loop gate (xfail), behavioural off-loop dispatch (xfail), cold-path byte-identity (GREEN), citation-gate `[track:<id>]`→`EvidenceRegistry.has` (GREEN) |
| 1 | `tests/memory/test_ingest_wiring.py` (extended) | WIRE-05: main()-path `_fire_ingest` boot+close gated on `recall_enabled` (xfail), anti-double-retention guard `run_boot_sweeps`/`on_session_close` absent (GREEN) |
| 2 | `tests/library/test_curator_persona_seam.py` (new) | WIRE-04: `build_curator_instruction` seam exists + omits co-host blocks (xfail), voice-from-seam swap (xfail), grounding RULES preserved in both backends (GREEN) |
| 2 | `tests/runtime/test_load_env_override.py` (new) | WIRE-06: `.env` overrides ghost shell key (xfail), diagnostic never logs key VALUE (GREEN security pin, V7/T-77-01-02) |
| 3 | `tests/repo/test_wire_regression_pins.py` (new) | WIRE-02: all 8 genre-chain detectors yield real tasks + measured payload (GREEN); WIRE-03: `genre=<name>` above floor / omitted below (GREEN) |

## xfail(strict) assertions to be un-xfailed by downstream plans

| Test | Un-xfailed by |
|------|---------------|
| `test_dj_cohost_grounding.py::test_agent_references_grounding_engine` | Plan 04 (WIRE-01) |
| `test_dj_cohost_grounding.py::test_grounding_dispatch_is_off_loop_run_in_executor` | Plan 04 (WIRE-01) |
| `test_dj_cohost_grounding.py::test_track_change_dispatches_grounding_off_loop` | Plan 04 (WIRE-01) |
| `test_ingest_wiring.py::test_main_fires_boot_and_close_ingest` | Plan 04 (WIRE-05) |
| `test_ingest_wiring.py::test_main_ingest_is_gated_behind_recall_enabled` | Plan 04 (WIRE-05) |
| `test_curator_persona_seam.py::test_build_curator_instruction_is_importable_and_tutor_voiced` | Plan 02 (WIRE-04) |
| `test_curator_persona_seam.py::test_curator_instruction_omits_cohost_only_blocks` | Plan 02 (WIRE-04) |
| `test_curator_persona_seam.py::test_gemini_curator_voice_sourced_from_matrix_seam` | Plan 02 (WIRE-04) |
| `test_curator_persona_seam.py::test_codex_curator_voice_sourced_from_matrix_seam` | Plan 02 (WIRE-04) |
| `test_load_env_override.py::test_dotenv_overrides_ghost_shell_env` | Plan 03 (WIRE-06) |

## Grep findings for the shipped WIRE-02/03 mechanism (the pin targets)

- **WIRE-02** — `src/vibemix/state/coach.py::AICoach.task_for_event` (`:476`). The 8 genre-chain branches live at `:598-694` (`ACID_LINE_ENTRY`, `KICK_SWAP`, `SUB_LAYER_ARRIVAL`, `KICK_DENSITY_SHIFT`, `DISTORTION_CLIMB`, `BREAKDOWN_KICK_KILL`, `REENTRY_KICK_LAND`, `PHRASE_BOUNDARY`); the generic `"React naturally."` fallthrough is `:695`. Each branch interpolates the measured `ev.extra` payload into a narrate-style task. The genre-chain comment at `:586-597` documents that these are NOT registry-citable (no forced `[citation]`), which is why the pin asserts payload-in-task rather than an `EvidenceRegistry` round-trip.
- **WIRE-03** — `src/vibemix/state/coach.py::AICoach.evidence_line` (`:256`). The genre field gate is `:334-335`: `if state.detected_genre != "unknown" and state.genre_confidence >= 0.5: e.append(f"genre={state.detected_genre}")`. Shipped format is `genre=<name>` (the confidence is the gate, not appended in parens) — the pin matches this exactly. Below floor / unset → no append (no `genre=unknown` spam).

## Deviations from Plan

### Auto-fixed Issues
None — plan executed as written, with two documented format-fidelity adjustments (recorded in frontmatter `decisions`):
1. WIRE-03 pin asserts the *actual* shipped `genre=<name>` format (the plan text said `genre=<name>(conf)`; the live code does not append the confidence). Pinning reality is the correct regression-pin behavior.
2. WIRE-02 pin asserts the measured payload reaches the task string (genre-chain measurements are narrate-only, not registry-citable) rather than asserting an `EvidenceRegistry` registration, per the verbatim `coach.py:594` design note.

These are pin-fidelity choices, not behavior changes — no production code was touched.

## Verification

- Plan-scoped: `PYTHONPATH=src pytest -q tests/agent/test_dj_cohost_grounding.py tests/memory/test_ingest_wiring.py tests/library/test_curator_persona_seam.py tests/runtime/test_load_env_override.py tests/repo/test_wire_regression_pins.py` — all green (xfail=pass, pins=pass).
- Full suite: **4441 passed, 26 skipped, 11 xfailed, 4 xpassed, 0 failed** (237s). The 5 new xfails are the WIRE-01/04/05/06 scaffolds; the 4 XPASS are pre-existing live-hardware (`V7-LIVE`) markers unrelated to this plan.
- No `genai.Client` constructed; runs with no `GEMINI_API_KEY`.

## Self-Check: PASSED

- FOUND: tests/agent/test_dj_cohost_grounding.py
- FOUND: tests/library/test_curator_persona_seam.py
- FOUND: tests/runtime/test_load_env_override.py
- FOUND: tests/repo/test_wire_regression_pins.py
- FOUND (modified): tests/memory/test_ingest_wiring.py
- FOUND commit caa4ada (Task 1), a560e29 (Task 2), 07e400e (Task 3)
