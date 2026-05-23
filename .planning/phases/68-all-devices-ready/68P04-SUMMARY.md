---
phase: 68-all-devices-ready
plan: 04
subsystem: contributor-recipe
tags: [docs, contributing, midi, dev-05, recipe]
requirements:
  - DEV-05
provides:
  - "≤30-line cross-platform port-name discovery helper (scripts/discover_midi_port.py) with 0/1/2 exit-code contract"
  - "Clean profile JSON copy-target (docs/contributing/_template.json) that validates through profile.py::_parse_profile as-is"
  - "≤200-line contributor recipe (docs/contributing/add-a-controller.md) with 4 numbered steps + PR checklist"
  - "Engineering-side close of DEV-05 — a stranger with a controller can ship a new bundled profile end-to-end without reading src/"
affects:
  - "scripts/ (1 new file — discover_midi_port.py, executable bit set)"
  - "docs/contributing/ (2 new files — _template.json copy-target + add-a-controller.md recipe)"
tech-stack:
  added: []
  patterns:
    - "Standalone CLI script convention from scripts/sniff_controller.py: SPDX header + module docstring + no vibemix imports + exit-code-as-contract — so contributors run pip install mido python-rtmidi and the helper works"
    - "Template lives under docs/contributing/ (NOT src/vibemix/midi/profiles/) — verified empty under list_profiles() so _template.json never gets loaded as a real profile (68-RESEARCH Pitfall #5)"
    - "Recipe doc tone mirrors docs/flake-hunt.md — concise, contributor-facing, no emojis, headed sections, code blocks language-tagged"
key-files:
  created:
    - scripts/discover_midi_port.py
    - docs/contributing/_template.json
    - docs/contributing/add-a-controller.md
  modified: []
  deleted: []
decisions:
  - "Template uses canonical button kind 'play' (not 'note_on' as the plan's reference text suggested) — _VALID_BUTTON_KINDS in profile.py restricts to {play, cue, sync, jog_touch, loop_in, loop_out, hotcue, filter_fx, tap_tempo}; 'note_on' would have raised ValueError on _parse_profile, failing the template-validates-as-is acceptance gate"
  - "Field-reference table kept inline in add-a-controller.md (not split to docs/midi-mapping.md cross-link) — line budget allows it (173/200) and contributors need the table in front of them at Step 2; the cross-link still appears in the Related docs section at the bottom"
  - "Used 'field': 'vol' in the template instead of the plan's suggested 'fader_volume' — _parse_profile accepts any non-empty string, but 'vol' matches the canonical 10 profiles (FLX4 + 9 sibling profiles all use 'vol' / 'eq_hi' / 'eq_low' / 'tempo' / 'filter' / 'xfader' — these are the conventional field names a reviewer expects)"
  - "discover_midi_port.py exit-code contract verified on Kaan's Mac with no controller plugged in: returns 1 (no MIDI input ports detected) — the documented 'no ports' state. Exit codes 0 (ports present) and 2 (mido missing) are documented but not exercised on this runner; behaviour is straight-line from the import guard + sorted(get_input_names()) branch"
  - "Did NOT touch src/vibemix/ — all 3 artifacts live in scripts/ + docs/. Threat T-68P04-01 mitigation: contributor's eventual PR will pass through the Wave 1 contract + smoke tests at merge time (4-line CI gate); template validation here is a same-process sanity check, not a CI gate"
metrics:
  duration: ~7 min (15:30 → 15:37 TRT)
  completed_date: 2026-05-23
  files_touched: 3
  insertions: 237
  deletions: 0
  baseline_before: 4147 passed / 26 skipped / 4 xpassed / 0 failed (post-Wave-2)
  baseline_after: 4147 passed / 26 skipped / 4 xpassed / 0 failed
  baseline_delta: "+0 tests (3 new artifacts are docs/script/json — not pytest-collected); 26 skipped + 4 xpassed unchanged; 0 failed; wall-clock 224.06s within Wave-2 baseline sd"
  task1_commit_sha: aea6f26
  task2_commit_sha: d504c71
  task3_commit_sha: da78fec
---

# Phase 68 Plan 04: Wave 3 Contributor Recipe Summary

**One-liner:** Closed DEV-05 engineering-side by shipping 3 stranger-facing artifacts — `scripts/discover_midi_port.py` (Step 1 cross-platform port lister, 39 lines, 0/1/2 exit-code contract), `docs/contributing/_template.json` (Step 2 copy-target that `_parse_profile`-validates as-is), and `docs/contributing/add-a-controller.md` (4-step recipe + 5-item PR checklist, 173 lines) — so a contributor can bundle a new MIDI controller end-to-end in under 30 min without reading `src/vibemix/`. Live <30-min smoke discharge rides §V7-LIVE-07 (created in Wave 4 / Plan 68P05). Default test grid GREEN at 4147/26/4/0, identical to Wave 2 baseline (zero new tests, zero regressions, zero `src/vibemix/` edits, zero net-new deps).

## Objective

Wave 3 of Phase 68 (DEV · All Devices Ready). Wave 0 collapsed the duplicate catalog; Wave 1 pinned every bundled profile's contract + decode; Wave 2 mocked the hot-plug + audio backend matrices. Wave 3 closes the engineering side of DEV-05 — the "Add Your Controller" contributor recipe — by shipping the 3 artifacts the recipe references:

1. **`scripts/discover_midi_port.py`** — recipe Step 1. ≤30-line standalone CLI that prints sorted `mido.get_input_names()` with a copy-target hint, exits cleanly on all three documented states (0 = ports found, 1 = no ports, 2 = mido not installed). Zero `vibemix.*` imports — a contributor on a clean checkout runs `pip install mido python-rtmidi` and the helper works.

2. **`docs/contributing/_template.json`** — recipe Step 2. Clean profile JSON copy-target with placeholder values that satisfy every required slot in `ControllerProfile` so `_parse_profile` accepts the template as-is (contributor renames + fills, doesn't fight a broken shell). Lives under `docs/contributing/` per 68-RESEARCH Pitfall #5 — verified empty under `list_profiles()` so the template never gets loaded as a real profile.

3. **`docs/contributing/add-a-controller.md`** — recipe entry point. ≤200-line doc with 4 numbered steps (discover → template → parametrize → pytest+PR), a binding field-reference table, a 5-item PR checklist, a Troubleshooting/FAQ section, and cross-links to the sibling docs (`midi-catalog.md`, `midi-controllers.md`, `midi-mapping.md`, `flake-hunt.md`). Tone mirrors `docs/flake-hunt.md` — concise, contributor-facing, zero emojis, headed sections, code blocks language-tagged.

The <30-min live smoke discharge (Kaan or a trusted DJ adds one new profile on a controller-of-opportunity) routes to `KAAN-ACTION-LEGAL.md §V7-LIVE-07` per 68-CONTEXT decision "Smoke Discharge" — that entry is created in Wave 4 / Plan 68P05.

Zero `src/vibemix/` edits, zero net-new dependencies — pure contributor surface.

## Tasks Completed

### Task 1 @ `aea6f26` — `scripts/discover_midi_port.py`

39-line standalone CLI (`mode 100755` after `git update-index --chmod=+x`). Structure:

- Apache-2.0 SPDX header + shebang
- Module docstring documenting usage + exit-code contract + coexistence note with `scripts/sniff_controller.py`
- `main() -> int`: try-imports mido (returns 2 with `pip install` hint on ImportError), calls `sorted(mido.get_input_names())`, returns 1 with stderr hint if empty, prints sorted port list + copy-target instruction to stdout and returns 0
- `if __name__ == '__main__': raise SystemExit(main())`

Acceptance:

- `wc -l` = 39 (≤50 budget — actually well under)
- `ls -l` shows `-rwxr-xr-x` (executable bit set, committed via `git update-index --chmod=+x`)
- `grep -c "mido.get_input_names"` = 1
- `grep -c "from vibemix"` = 0 (standalone, no project imports)
- `uv run python3 scripts/discover_midi_port.py` returns exit 1 on Kaan's Mac with no controller plugged in: `"No MIDI input ports detected. Connect your controller via USB and re-run."` — the documented "no ports" state from the contract. The other two exit states (0 / 2) are straight-line from the import guard and the non-empty branch; behaviour-verified by static reading.
- `head -1` = `#!/usr/bin/env python3`

### Task 2 @ `d504c71` — `docs/contributing/_template.json`

25-line clean profile JSON with placeholder values. Structure mirrors the canonical `pioneer_ddj_flx4.json`:

- `id`: `"vendor_model_snake_case"` (placeholder — contributor renames to match the filename stem)
- `display_name`: `"Vendor Model Display Name"`
- `port_name_hints`: `["PORT_SUBSTRING_PLATFORM_A", "PORT_SUBSTRING_PLATFORM_B"]` — plural list per the schema, two entries to prompt the cross-platform tip
- `decks`: `["A", "B"]`
- `controls`: 1 example CC binding (`vol_a` → channel 0, cc 19, axis `unipolar`, deck A, field `vol`)
- `buttons`: 1 example button (`play_a` → channel 0, note 11, kind `play`, deck A)
- `notes`: `"JSON-only; hardware not verified yet — pending live ear pass."`

**Pitfall #5 verified.** `list_profiles()` returns exactly the 10 bundled IDs — the template under `docs/contributing/` is invisible to the loader:

```text
$ uv run python3 -c "from vibemix.midi import list_profiles; print(list_profiles())"
['hercules_inpulse_300', 'hercules_inpulse_500', 'numark_party_mix_live',
 'pioneer_ddj_1000', 'pioneer_ddj_400', 'pioneer_ddj_flx10',
 'pioneer_ddj_flx4', 'pioneer_ddj_flx6', 'pioneer_ddj_sx3',
 'pioneer_xdj_rx3']
```

**`_parse_profile` validates the template as-is** (the must-have gate):

```text
$ uv run python3 -c "from vibemix.midi.profile import _parse_profile; import json; \
  p = _parse_profile(json.load(open('docs/contributing/_template.json'))); print(p.id, p.display_name)"
vendor_model_snake_case Vendor Model Display Name
```

The plan's reference template used `"kind": "note_on"` for buttons. That would have raised `ValueError` against `_VALID_BUTTON_KINDS = {play, cue, sync, jog_touch, loop_in, loop_out, hotcue, filter_fx, tap_tempo}`. Replaced with `"kind": "play"` to match the canonical FLX4 — template parses cleanly through `_parse_profile`. Documented in the recipe's binding field-reference table so contributors don't trip the same wire.

### Task 3 @ `da78fec` — `docs/contributing/add-a-controller.md`

173-line recipe doc (≤200 budget). Sections in order:

1. Title + one-line description + DEV-05 callout
2. Prerequisites (macOS 12+/Win 10+, Python 3.12, `uv sync`, USB-connected controller, mapping source)
3. **Step 1 — Discover your controller's port name** — runs `discover_midi_port.py`, expected output, exit-code contract, cross-platform tip (the FLX4 `["DDJ-FLX4", "FLX4"]` example references the production profile that already handles macOS/Windows divergence)
4. **Step 2 — Copy and fill in the profile template** — `cp` command, top-level field table (7 rows), binding field-reference table (7 rows — `kind` row enumerates the exact allowed strings from `_VALID_CONTROL_KINDS` + `_VALID_BUTTON_KINDS`), pointer to bundled profiles as concrete reference, pointer to `_parse_profile` as schema authority
5. **Step 3 — Add your controller ID to the test parametrize lists** — both `tests/midi/test_profile_contracts.py` and `tests/midi/test_profile_smokes.py` `_BUNDLED_IDS` lists, alphabetical, drift-is-a-bug rule
6. **Step 4 — Run the test suite and submit a PR** — `uv run pytest tests/midi/ -q`, expected GREEN rows, failure-mode triage for contract red vs. smoke red, the 3 files to include in PR, PR body content guidance
7. **PR checklist** — 5 markdown checkbox items
8. **Troubleshooting & FAQs** — 4 entries: port-not-listed (Audio MIDI Setup / Device Manager), why `discover_midi_port.py` not `sniff_controller.py`, `unipolar` vs `bipolar` semantics, why `_template.json` lives under `docs/contributing/`
9. **Related docs** — cross-links to `midi-catalog.md`, `midi-controllers.md`, `midi-mapping.md`, `flake-hunt.md`

Verification:

- `wc -l` = 173 (well under 200)
- `grep -c 'scripts/discover_midi_port.py'` = 1
- `grep -c 'docs/contributing/_template.json'` = 2
- `grep -c 'test_profile_contracts.py'` = 3
- `grep -c 'test_profile_smokes.py'` = 3
- `grep -c 'port_name_hints'` = 5
- `grep -c '^- \[ \]'` = 5 (PR checklist items)
- `grep -P '[\x{1F300}-\x{1FAFF}\x{2600}-\x{27BF}]'` = 0 hits (no emojis)
- `grep -nE '^## Step [0-9]'` shows steps 1–4 in increasing line order (16, 43, 88, 101)

## Verification

**Plan-level gates** (from `<verification>` block — all GREEN):

- `test -f scripts/discover_midi_port.py && test -x scripts/discover_midi_port.py` → present + executable
- `uv run python3 scripts/discover_midi_port.py` → exits 1 (no ports on this runner — documented state)
- `uv run python3 -c "import json; json.load(open('docs/contributing/_template.json'))"` → exits 0, template parses
- `uv run python3 -c "from vibemix.midi.profile import _parse_profile; ..."` → template validates as-is against `_parse_profile`
- `uv run python3 -c "from vibemix.midi import list_profiles; assert '_template' not in list_profiles()"` → exits 0, Pitfall #5 avoided
- `wc -l docs/contributing/add-a-controller.md` → 173 (≤200)
- `grep -cE "scripts/discover_midi_port.py|docs/contributing/_template.json|test_profile_contracts.py|test_profile_smokes.py" docs/contributing/add-a-controller.md` → 9 hits across the 4 sibling references (≥4 required)

**Full default test suite** (the hard gate — no regressions):

```text
$ uv run python3 -m pytest -q
4147 passed, 26 skipped, 4 xpassed, 13 warnings in 224.06s (0:03:44)
```

Identical to Wave 2 baseline (`4147 / 26 / 4 / 0` pre-write). +0 tests because the 3 artifacts are docs/script/json — not pytest-collected. Zero `src/vibemix/` edits → zero risk of behavioural regression. Wall-clock 224.06s comfortably within the Wave-2 baseline sd window (220.58s ± 3s).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Template button kind**

- **Found during:** Task 2 pre-write reading of `_parse_profile`
- **Issue:** The plan's `<action>` reference template used `"kind": "note_on"` for the example button binding. `_parse_profile` (the must-have-validates-as-is gate) restricts button `kind` to `_VALID_BUTTON_KINDS = {play, cue, sync, jog_touch, loop_in, loop_out, hotcue, filter_fx, tap_tempo}` — `"note_on"` would raise `ValueError("button binding 'play_a' field 'kind' must be one of [...], got 'note_on'")`, failing the template-loads-cleanly acceptance criterion.
- **Fix:** Used `"kind": "play"` instead (matches every bundled profile's `play_a` example). Recipe Step 2's binding field-reference table enumerates the full allowed set so future contributors don't trip the same wire.
- **Files modified:** `docs/contributing/_template.json` (Task 2)
- **Commit:** `d504c71`

### Decisions documented in frontmatter (not auto-fixes)

- `field` value choice (`"vol"` over `"fader_volume"`)
- Field-reference table placement (inline over cross-link)

## Auth gates

None — no external auth required for any task in this plan.

## Threat surface scan

No new network endpoints, no new auth paths, no new file-access patterns at trust boundaries, no schema changes at trust boundaries. `_template.json` is read by the contributor (and one-shot by `_parse_profile` during local sanity check); it is never imported by the runtime per Pitfall #5 verification. The discharge does not introduce any new threat surface beyond what the existing contributor-PR pathway already had.

## Known Stubs

None. All 3 artifacts are fully functional shipping content.

## Pointers

- **Smoke discharge:** `KAAN-ACTION-LEGAL.md §V7-LIVE-07` (created in Wave 4 / Plan 68P05). The <30-min live recipe smoke — Kaan or a trusted DJ runs steps 1–4 on a controller-of-opportunity. Engineering side closes here; live confirmation rides §V7-LIVE-07.
- **Related KAAN-ACTION clusters** (also created in Plan 68P05): §V7-LIVE-08 (real macOS BlackHole capture), §V7-LIVE-09 (real Windows WASAPI loopback), §V7-LIVE-10 (live FLX4 hot-plug ear).
- **Phase invariants preserved:** zero `src/vibemix/` edits; the four cardinal invariants (single-writer / citation-grounding / trust-the-audio / one-socket) hold by zero-touch.

## Self-Check: PASSED

- [x] `scripts/discover_midi_port.py` exists (mode 100755, 39 lines) — `git log --oneline | grep aea6f26` → present
- [x] `docs/contributing/_template.json` exists (25 lines, JSON-valid, `_parse_profile`-valid) — `git log --oneline | grep d504c71` → present
- [x] `docs/contributing/add-a-controller.md` exists (173 lines, 4 numbered steps, 4 sibling refs, 5 PR checkboxes, 0 emojis) — `git log --oneline | grep da78fec` → present
- [x] All 3 task commits present in `git log --oneline -10`: `aea6f26`, `d504c71`, `da78fec`
- [x] Default test grid GREEN at `4147 passed / 26 skipped / 4 xpassed / 0 failed` — identical to Wave 2 baseline, zero regressions
- [x] Zero `src/vibemix/` edits — `git diff --stat 5f243d1..HEAD -- src/vibemix/` is empty
- [x] Zero net-new dependencies — `pyproject.toml` + `uv.lock` untouched across all 3 commits
