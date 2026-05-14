---
phase: 23-10-sku-midi-controller-library-midimaploader
plan: 01
subsystem: midi
tags: [midi, sniff-cli, ddj-flx4, pitfall-25, kaan-action]
requires:
  - mido (already a project dep)
provides:
  - scripts/sniff_controller.py — standalone MIDI capture CLI (no src/vibemix imports)
  - tests/midi/test_sniff_controller.py — 17 unit tests, hardware-free via sys.modules stub
  - FLX4-SNIFF.md verdict template (status: pending_kaan_measurement)
  - KAAN-ACTION.md — deferred hardware sniff manifest
affects:
  - .planning/phases/23-.../FLX4-SNIFF.md (template only; verdict line pending Kaan session)
tech_stack_added: []
key_files_created:
  - scripts/sniff_controller.py
  - tests/midi/test_sniff_controller.py
  - .planning/phases/23-10-sku-midi-controller-library-midimaploader/FLX4-SNIFF.md
  - .planning/phases/23-10-sku-midi-controller-library-midimaploader/KAAN-ACTION.md
key_files_modified: []
decisions:
  - Hardware sniff deferred to Kaan-action — infrastructure shipped, Plan 23-02 unblocked via defensive both-bindings fallback (note 0x60 + 0x58 both verified=false until verdict).
  - JSONL frame schema is intentionally minimal (ts, type, channel, data1, data1_hex, data2) — T-23-02 mitigation pinned by test.
  - mido stubbed via sys.modules in tests so CI runs on macOS without python-rtmidi.
metrics:
  duration_minutes: 12
  completed_date: 2026-05-14
  tests_added: 17
  tests_passing: 1881/1891 (10 pre-existing failures unchanged)
---

# Phase 23 Plan 01: DDJ-FLX4 Sync sniff CLI + verdict template Summary

Day-1 sniff infrastructure for Phase 23: standalone `scripts/sniff_controller.py` MVP that captures MIDI CC + note events as JSONL frames, plus the `FLX4-SNIFF.md` verdict template that gates the FLX4 JSON `sync_*` binding choice. Live hardware sniff itself is deferred to a Kaan-action session — Plan 23-02 unblocks via the defensive both-bindings fallback documented in the template.

## Tasks Completed

### Task 1 (TDD) — `scripts/sniff_controller.py` MVP

- **RED commit:** `9e291db` — `test(23-01): add failing tests for sniff_controller CLI helpers`
- **GREEN commit:** `a68c810` — `feat(23-01): implement standalone sniff_controller CLI`
- 17 new unit tests in `tests/midi/test_sniff_controller.py`. mido stubbed via `sys.modules` so the suite runs hardware-free on macOS.
- CLI surface: `--port <substring>` (case-insensitive match, `AmbiguousPortError` on multi-match), `--seconds N` (default 300 = 5 min, matches Pitfall 25 window), `--list` enumerates `mido.get_input_names()` and exits 0.
- Output: one JSONL frame per CC/note_on/note_off event — `{ts, type, channel, data1, data1_hex, data2}`. Summary line on Ctrl-C / timeout: `{summary: true, duration_s, frames, unique_cc, unique_notes}` (both lists sorted ascending so diffs stay stable across runs).
- Standalone — no `src/vibemix/` imports (per D-LOCKED community PR path).
- License header points to repo Apache-2.0.

### Task 2 (deferred — Kaan-action) — live FLX4 hardware sniff

Deferred per `feedback_autonomous_no_grey_area_pause` memory. Documented in `KAAN-ACTION.md` with exact CLI invocations, gesture sequence (3x plain Sync Deck A/B, 2x Shift+Sync Deck A/B, incidental EQ/fader/jog cross-reference), and grep verdict commands.

### Task 3 — `FLX4-SNIFF.md` verdict template

- **Commit:** `f817d5a` — `docs(23-01): FLX4-SNIFF.md verdict template + KAAN-ACTION defer`
- Six required sections present and pinned by automated verify: `Session Metadata`, `Verdict` (with all three pre-documented outcomes), `Evidence` (placeholder for raw JSONL excerpts), `Action for Plan 02` (defensive both-bindings instruction), `Other Notable Findings`.
- Frontmatter: `status: pending_kaan_measurement` — flips to `measured` after Kaan's hardware session.

## Deviations from Plan

### [Rule 3 - Blocking issue avoided] Hardware session deferred, not blocked

The plan included a `checkpoint:human-action` between Task 1 and Task 3, with a `deferred — kaan-action` resume signal that explicitly authorizes ship-with-pending-verdict. I executed both Task 1 and Task 3 in the same run (the template fallback IS the kaan-action defer outcome) so Plan 23-02 can start immediately. Per the plan's own Task 3 action spec, when Task 2 is deferred the FLX4-SNIFF.md ships with `Verdict: PENDING` and the Plan 02 action string documents the defensive both-bindings fallback — which is exactly what landed.

### [Rule 2 - Critical functionality] T-23-02 mitigation pinned by test

Threat-model T-23-02 (info disclosure via raw JSONL) was marked `mitigate`. The plan required `format_frame` to emit only ts + type + channel + data1 + data2. Added explicit `test_format_frame_threat_T_23_02_only_minimal_fields` that asserts the exact key set so any future regression that adds env, clipboard, or audio metadata to a captured frame fails CI.

## Authentication Gates

None — the sniff CLI is offline + read-only and uses no API keys.

## Verification Results

| Check | Result |
| --- | --- |
| `pytest tests/midi/test_sniff_controller.py` | 17/17 PASS |
| Full suite delta | +17 added, 0 regressions, 1881 passed / 10 pre-existing failures (same as baseline) |
| `python scripts/sniff_controller.py --help` | exits 0, documents `--port`, `--seconds`, `--list` |
| `python scripts/sniff_controller.py --list` | runs cleanly (returns project's current MIDI inputs) |
| `grep -E "^## Verdict\|^## Action for Plan 02" FLX4-SNIFF.md \| wc -l` | 2 (both sections present) |
| AIza scan delta | 0 matches in new files |

## Known Stubs

- `FLX4-SNIFF.md` Verdict block: `PENDING — Kaan-action required`. This is intentional per CONTEXT D-LOCKED — Plan 23-02 ships the defensive fallback and the verdict tightens the FLX4 JSON before v2.0-rc1 cut. KAAN-ACTION.md tracks the unblock path.

## Threat Flags

None new — sniff CLI captures only MIDI bytes from a local USB device, no network, no env, no clipboard.

## Self-Check: PASSED

- `scripts/sniff_controller.py` FOUND
- `tests/midi/test_sniff_controller.py` FOUND
- `.planning/phases/23-.../FLX4-SNIFF.md` FOUND
- `.planning/phases/23-.../KAAN-ACTION.md` FOUND
- Commit `9e291db` (RED) FOUND in `git log`
- Commit `a68c810` (GREEN) FOUND in `git log`
- Commit `f817d5a` (docs) FOUND in `git log`

## TDD Gate Compliance

- RED gate: `9e291db` `test(23-01): ...` — failing tests committed before implementation.
- GREEN gate: `a68c810` `feat(23-01): ...` — implementation lands tests green.
- REFACTOR: not needed (script was clean on first GREEN).
