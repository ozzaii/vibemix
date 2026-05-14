# KAAN-ACTION — Phase 23 Plan-01 DDJ-FLX4 Sync sniff

**Status:** open — blocks `verdict:` line in `FLX4-SNIFF.md`.
**Blocks:** nothing in v2.0 critical path (Plan 23-02 ships defensive both-bindings fallback). Verdict gates v2.0-rc1 cut: FLX4 `sync_*` JSON entries must flip `verified: false` → `verified: true` on the winning binding(s) before release.
**Owner:** Kaan (DJ ear-test session + DDJ-FLX4 hardware on his desk).

## What's deferred

The 5-minute live mido sniff of the Pioneer DDJ-FLX4 Sync button to
resolve Pitfall 25: cohost_v4 captured `note 0x60`, Mixxx canonical
docs `note 0x58`. The infrastructure (CLI + tests + verdict template)
is shipped — only the hardware session itself requires a human.

## What Claude shipped

- `scripts/sniff_controller.py` — standalone mido sniff CLI:
  `--port <substring> --seconds N [--list]`, JSONL stdout, summary on
  Ctrl-C. 17/17 unit tests green; mido stubbed via `sys.modules` so the
  test suite runs hardware-free on macOS CI.
- `tests/midi/test_sniff_controller.py` — 17 tests covering match_port,
  format_frame (incl. T-23-02 minimal-fields mitigation), summarize,
  and CLI exit codes for missing/ambiguous/unknown ports.
- `.planning/phases/23-.../FLX4-SNIFF.md` — verdict report template
  with `status: pending_kaan_measurement` frontmatter and three
  possible outcomes pre-documented (0x60 ONLY / 0x58 ONLY / BOTH).

## What Kaan does

1. Plug in the DDJ-FLX4 over USB. Open `Audio MIDI Setup → MIDI Studio`
   and confirm the device appears. Read the firmware version off
   djay Pro's device info panel (record it in the SNIFF.md metadata).
2. Enumerate ports:
   `cd /Users/ozai/projects/dj-set-ai && .venv/bin/python scripts/sniff_controller.py --list`
   Note the exact "DDJ-FLX4" port name.
3. Run the 5-min sniff and tee to disk:
   `.venv/bin/python scripts/sniff_controller.py --port FLX4 --seconds 300 | tee .planning/phases/23-10-sku-midi-controller-library-midimaploader/FLX4-SNIFF.raw.jsonl`
4. While it runs, exercise both Sync gestures on both decks:
   - 3x plain Sync Deck A (channel 0).
   - 3x plain Sync Deck B (channel 1).
   - 2x Shift+Sync Deck A.
   - 2x Shift+Sync Deck B.
   - Then EQ knobs, faders, jog, play, cue (incidental coverage — Plan 23-02 cross-references).
5. Ctrl-C. Grep the raw JSONL:
   `grep -E '"type": "note_on".*"channel": 0' .planning/phases/23-10-sku-midi-controller-library-midimaploader/FLX4-SNIFF.raw.jsonl | grep -E '"data1": (88|96)' | head -20`
   Repeat for channel 1 (Deck B).
6. Update `FLX4-SNIFF.md`:
   - Fill Session Metadata (date, firmware, port name).
   - Replace the "PENDING" Verdict block with the chosen outcome row's
     "Action for FLX4 JSON" line (verbatim).
   - Paste 5-10 JSONL lines around each Sync gesture into "Evidence".
   - Flip frontmatter: `status: pending_kaan_measurement` → `status: measured`.
7. Optionally: re-run Plan 23-02's FLX4 JSON write step (or hand-edit
   `src/vibemix/midi/controllers/ddj-flx4.json`) to flip
   `verified: false` → `verified: true` and remove the `status: "pending-verdict"`
   marker on the winning binding(s); the loser binding(s) should be
   removed entirely if the verdict is single-note, retained if BOTH.
8. Commit the raw JSONL + updated SNIFF.md + (optionally) the FLX4 JSON
   alongside in one commit: `docs(23-01): FLX4 hardware sniff verdict + raw evidence`.

## Why deferred

The DDJ-FLX4 is on Kaan's desk; the sniff requires a human pressing
real buttons in real time. Per memory `feedback_autonomous_no_grey_area_pause`
this is surfaced as a Kaan-action-required item — Plans 23-02 (10-SKU
JSONs + MidiMapLoader) are unblocked and ship now with the defensive
both-bindings fallback documented in FLX4-SNIFF.md's "Action for Plan 02"
section. Verdict tightens the FLX4 JSON before v2.0-rc1 cut.
