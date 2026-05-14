---
phase: 23-10-sku-midi-controller-library-midimaploader
plan: 02
subsystem: midi
tags: [midi, controller-library, midimaploader, jsonschema, pitfall-24]
requires:
  - jsonschema (project dep)
  - mido message duck-typing (no import at load time)
  - 23-01 (defensive both-bindings approach baked into FLX4 JSON)
provides:
  - src/vibemix/midi/schema.json — Draft-07 controller-map shape
  - src/vibemix/midi/controllers/*.json — 10 SKUs (Pioneer DDJ-FLX4/400/200/REV1, Denon MC7000/6000, NI Kontrol S4/S2, Numark Mixtrack Platinum FX / Pro FX)
  - src/vibemix/midi/map_loader.py — MidiMapLoader registry (.load, .all_maps, .lookup)
affects:
  - registry never lies: per-control `status` field honestly flags `verified` / `pending-verdict` / `tentative — needs hardware verification`
tech_stack_added: []
key_files_created:
  - src/vibemix/midi/schema.json
  - src/vibemix/midi/controllers/ddj-flx4.json
  - src/vibemix/midi/controllers/ddj-400.json
  - src/vibemix/midi/controllers/ddj-200.json
  - src/vibemix/midi/controllers/ddj-rev1.json
  - src/vibemix/midi/controllers/mc-7000.json
  - src/vibemix/midi/controllers/mc-6000.json
  - src/vibemix/midi/controllers/kontrol-s4.json
  - src/vibemix/midi/controllers/kontrol-s2.json
  - src/vibemix/midi/controllers/mixtrack-platinum-fx.json
  - src/vibemix/midi/controllers/mixtrack-pro-fx.json
  - src/vibemix/midi/map_loader.py
  - tests/midi/test_map_loader.py
key_files_modified: []
decisions:
  - 10-SKU set per orchestrator spec (overrides earlier 23-CONTEXT 10-SKU list — orchestrator's explicit list won as the v2.0 "10-SKU library" deliverable). The older `src/vibemix/midi/profiles/` directory (Phase 9) is left untouched; the new `controllers/` directory is the v2.0 MidiMapLoader surface.
  - FLX4 ships BOTH sync bindings (note 96 + note 88) flagged pending-verdict — defensive until Kaan's FLX4-SNIFF.md hardware session lands.
  - Lookup index keys collapse note_on + note_off into one "note" kind — semantic events are press-not-release; the EventDetector consumes them at press edges anyway.
  - 4-deck controllers (MC7000, Kontrol S4, Mixtrack Platinum FX) map decks A/B only — semantic vocabulary is 2-deck in v2.0. C/D bindings deferred to v2.1.
metrics:
  duration_minutes: 24
  completed_date: 2026-05-14
  tests_added: 21 (this plan) + 17 (Plan 23-01) = 38 for Phase 23
  tests_passing: 1885 passed / 7 skipped / 10 pre-existing failures unchanged (no regressions)
  schema_validation_pass: 10/10 controller JSONs
---

# Phase 23 Plan 02: 10-SKU MIDI Controller Library + MidiMapLoader Summary

10-SKU schema-validated controller library shipped under `src/vibemix/midi/controllers/`, plus `MidiMapLoader` — the universal grounding spine that turns vendor-specific MIDI bytes into a normalized semantic event vocabulary (`eq_low_a`, `fader_b`, `sync_a`, `cue_b`, `jog_a`, ...). DDJ-FLX4 ports the cohost_v4 POC `_CC_MAP` + `_NOTE_MAP` verbatim; the 9 other SKUs ship convention-grounded but honestly flagged `tentative — needs hardware verification` per Pitfall 24.

## Tasks Completed

### Task 1 — schema + 10 controller JSONs (commit `7589941`)

- `src/vibemix/midi/schema.json` — JSON Draft-07. Required: vendor, model, description, verified (bool), controls (object). Each control: type (cc|note), channel (0-15), value (0-127), semantic (string), status (verified|pending-verdict|tentative). `additionalProperties: false` at both levels.
- 10 JSONs validate against schema.
- `ddj-flx4.json` (27 controls) ports cohost_v4.py `_CC_MAP`/`_NOTE_MAP` (lines 586-602): EQ on CC 7/11/15 per deck, vol on CC 19, tempo on CC 0, filter on channel 6 CC 23/24, xfader on channel 6 CC 31, play/cue/loop verified. **`sync_a` / `sync_b` flagged `pending-verdict`** with note 96 (cohost_v4 capture) + **defensive `sync_a_alt` / `sync_b_alt` with note 88 (Mixxx canonical)** also `pending-verdict` — both ship until FLX4-SNIFF.md verdict from hardware lands.
- 9 other SKUs (DDJ-400, DDJ-200, DDJ-REV1, MC7000, MC6000, Kontrol S4 Mk3, Kontrol S2 Mk3, Mixtrack Platinum FX, Mixtrack Pro FX): `verified: false` top-level, every control `status: "tentative — needs hardware verification"`. Vendor-convention bindings: Pioneer rekordbox (CC 7/11/15 EQ, CC 19 vol, CC 0 tempo), Denon Serato (vol CC 28, tempo CC 9), NI Traktor (EQ CC 2/3/4, vol CC 0), Numark Serato Lite (vol CC 28, tempo CC 9).

### Task 2 — MidiMapLoader (commits `22bd1f7` RED + `1800895` GREEN)

- `MidiMapLoader()` auto-discovers `controllers/*.json`, validates each against schema, builds (kind, channel, value) → semantic index per map for O(1) lookup.
- `.load(id)` returns map dict; missing id raises `KeyError` listing all valid IDs.
- `.all_maps()` returns shallow registry copy.
- `.lookup(cmap, msg)` — duck-typed on mido Message: msg.type / .channel / .control or .note. note_off resolves to same semantic as note_on. Unsupported msg types (program_change, etc.) return None. Unmapped events return None.
- `MapValidationError` raised on schema failure OR JSON syntax error, citing the offending filename (T-23-04 mitigation pinned by 2 tests).

### Task 3 — full-suite regression (no new files)

- Full pytest: **1885 passed, 7 skipped, 10 failed**.
- Baseline before Phase 23: 1864 collected, 10 failed.
- Delta: **+38 new tests** (17 sniff + 21 loader), all green. The 10 failures are the exact same pre-existing failures from baseline (test_persona_02_byte_identical_to_v4, test_phase15_success_criteria.*, test_replay_linter.test_csv_report_has_correct_shape, test_open_voice_output_completes_without_real_audio_device, test_main_smoke.*, test_g5_poc_files_untouched — the last one fails because `_test_multimodal.py` / `_test_tts.py` / `mascot.html` were modified in prior unrelated work, NOT by Phase 23. I did not touch any POC file).
- AIza scan on new files: **0 matches**.

## Deviations from Plan

### [Rule 3 — Blocking issue resolved upstream]

The plan called for 10 SKUs matching the orchestrator's explicit list (DDJ-FLX4, DDJ-400, DDJ-200, DDJ-REV1, MC7000, MC6000, Kontrol S4, Kontrol S2, Mixtrack Platinum FX, Mixtrack Pro FX) — which **differs** from the 23-CONTEXT.md 10-SKU list (DDJ-FLX6, FLX10, SX3, XDJ-RX3, Inpulse 300/500, Numark Party Mix Live, Mixstream Pro+). I followed the orchestrator's explicit instruction since that's the canonical v2.0 deliverable spec. The Phase 9 `profiles/` directory still holds the older 10-SKU set (Inpulse 300/500, Party Mix Live, FLX6, FLX10, SX3, XDJ-RX3, DDJ-1000, DDJ-FLX4, DDJ-400) untouched — Phase 9 ControllerState continues to consume those; the new `controllers/` directory is the v2.0 MidiMapLoader surface. Future plan (Plan 23-03+ per CONTEXT Wave-4) reconciles these.

### [Rule 2 — Threat-model T-23-04 mitigation pinned by test]

T-23-04 (`mitigate` disposition: tampered JSON could reach MIDI ingest layer) is closed: schema validation runs on every JSON at loader construction, and `MapValidationError` is raised citing the filename. Added **two** tests (`test_loader_invalid_json_raises_map_validation_error` + `test_loader_malformed_json_text_raises_map_validation_error`) covering both failure modes (missing required fields + invalid JSON syntax).

## Authentication Gates

None — MidiMapLoader is offline, file-system only.

## Verification Results

| Check | Result |
| --- | --- |
| `pytest tests/midi/test_map_loader.py` | 21/21 PASS |
| `pytest tests/midi/test_sniff_controller.py` (23-01 regression) | 17/17 PASS |
| Full suite | 1885 passed, 7 skipped, 10 pre-existing failed (no regressions) |
| 10 JSONs validate against schema.json | 10/10 PASS |
| AIza scan on new files | 0 matches |
| `MidiMapLoader().all_maps()` returns dict with 10 entries | OK |
| FLX4 sync_a + sync_a_alt round-trip via lookup | OK (both 0x60 → sync_a, 0x58 → sync_a_alt) |

## Known Stubs

- 9 non-FLX4 SKUs ship with every entry flagged `tentative — needs hardware verification`. This is intentional Pitfall 24 honesty — not stubs. Hardware sniff sessions (Plan 23-03+ or community PRs via `scripts/sniff_controller.py`) will flip `verified: false` → `verified: true` on confirmed bindings.
- FLX4 `sync_*` entries flagged `pending-verdict`. Resolved by KAAN-ACTION.md (Plan 23-01).

## TDD Gate Compliance

- Task 2 RED: `22bd1f7` `test(23-02): add failing tests for MidiMapLoader` — 22 failing tests (collection ImportError because module missing).
- Task 2 GREEN: `1800895` `feat(23-02): MidiMapLoader — schema-validated controller registry` — 21/21 green (one test collapsed during refinement; final count 21).
- Task 1 was not TDD-driven (data files only — no behavior); verified by direct schema-validation check before commit.

## Threat Flags

None new — the registry is read-only data + a pure-function index. No new network endpoints, auth paths, file-write, or schema-changing surfaces introduced.

## Self-Check: PASSED

- `src/vibemix/midi/schema.json` FOUND
- `src/vibemix/midi/controllers/` directory FOUND with 10 JSONs
- `src/vibemix/midi/map_loader.py` FOUND
- `tests/midi/test_map_loader.py` FOUND
- Commit `7589941` (Task 1: schema + 10 JSONs) FOUND in git log
- Commit `22bd1f7` (Task 2 RED) FOUND in git log
- Commit `1800895` (Task 2 GREEN) FOUND in git log
