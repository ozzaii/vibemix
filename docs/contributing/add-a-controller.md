# Add Your Controller

Bundle a new MIDI DJ controller into vibemix in under 30 minutes. Works on macOS and Windows. No rebuild required after the PR merges — the profile is bundled JSON loaded at session start.

This recipe is what closes DEV-05 of v7.0 (Open House). If you hit a snag, file an issue — the recipe is part of the product, not just docs.

## Prerequisites

- macOS 12+ or Windows 10+
- Python 3.12, with the repo's `.venv` set up (`uv sync` from the repo root)
- Your controller, connected over USB
- Familiarity with your controller's MIDI mapping (vendor docs, the Mixxx
  controller-mappings repo, or `scripts/sniff_controller.py` for a full
  capture)

## Step 1 — Discover your controller's port name

Plug your controller into USB. Then:

```bash
uv run python3 scripts/discover_midi_port.py
```

You should see one or more port names, one per line:

```
Attached MIDI input ports:
  - DDJ-FLX4 USB MIDI

Copy the substring that uniquely identifies your controller into the
'port_name_hints' field of your new profile JSON (see docs/contributing/_template.json).
```

The script exits `0` when ports are found, `1` when none are detected (re-seat
the USB cable, then check Audio MIDI Setup on macOS or Device Manager on
Windows), and `2` if `mido` is not installed.

**Cross-platform tip.** Port names often differ across OSes — `pioneer_ddj_flx4.json` ships
`["DDJ-FLX4", "FLX4"]` because macOS reports `"DDJ-FLX4 USB MIDI"` while Windows
reports just `"DDJ-FLX4"`. If you can run Step 1 on both OSes, do — your
`port_name_hints` list should contain a substring that matches on each.

## Step 2 — Copy and fill in the profile template

Copy the template into the canonical profiles directory:

```bash
cp docs/contributing/_template.json \
   src/vibemix/midi/profiles/<your_vendor>_<your_model>.json
```

Use `snake_case` for the filename — no spaces, lowercase. The `id` field
**must** match the filename stem.

Open the new file and fill in:

| Field             | Type                | Example                                                                       |
| ----------------- | ------------------- | ----------------------------------------------------------------------------- |
| `id`              | str                 | `"pioneer_ddj_rev1"` — matches filename stem                                  |
| `display_name`    | str                 | `"Pioneer DDJ-REV1"` — human-friendly                                         |
| `port_name_hints` | list[str], non-empty| `["DDJ-REV1", "REV1"]` — substrings from Step 1, ideally macOS + Windows      |
| `decks`           | list[str]           | `["A", "B"]` for 2-deck, `["A", "B", "C", "D"]` for 4-deck                    |
| `controls`        | dict of CC bindings | one entry per knob/fader (see below)                                          |
| `buttons`         | dict of note bindings | one entry per pad/button (see below)                                        |
| `notes`           | str (optional)      | `"JSON-only; hardware not verified yet — pending live ear pass."`             |

**Binding field reference** (each entry under `controls` or `buttons`):

| Field      | Type | Allowed values                                                       |
| ---------- | ---- | -------------------------------------------------------------------- |
| `kind`     | str  | `"cc"` for controls; one of `play`, `cue`, `sync`, `jog_touch`, `loop_in`, `loop_out`, `hotcue`, `filter_fx`, `tap_tempo` for buttons |
| `channel`  | int  | `0`–`15` (MIDI channel, zero-indexed)                                |
| `cc`       | int  | `0`–`127` (controls only)                                            |
| `note`     | int  | `0`–`127` (buttons only)                                             |
| `axis`     | str  | `"unipolar"` (knobs/faders, 0–127) or `"bipolar"` (tempo / filter / xfader, centered at 64) — controls only |
| `deck`     | str  | `"A"`, `"B"`, `"C"`, `"D"`, or `null` for master-section (xfader)    |
| `field`    | str  | Logical name like `"vol"`, `"eq_hi"`, `"eq_mid"`, `"eq_low"`, `"tempo"`, `"filter"`, `"xfader"` — controls only |

**Concrete reference.** Copy structure from a bundled profile that
matches your controller's deck layout — `src/vibemix/midi/profiles/pioneer_ddj_flx4.json`
is the canonical 2-deck Pioneer shape; `src/vibemix/midi/profiles/pioneer_ddj_sx3.json`
is a 4-deck reference if your controller has C/D decks.

The full schema authority is `src/vibemix/midi/profile.py::_parse_profile` — if your
JSON loads cleanly through it, your profile is valid. The contract test
(Step 3) runs `_parse_profile` for you.

## Step 3 — Add your controller ID to the test parametrize lists

Two test files own the bundled-profile list. Add your `<your_vendor>_<your_model>`
ID (the filename stem) to **both**, in alphabetical order:

- `tests/midi/test_profile_contracts.py` — open it, find the `_BUNDLED_IDS`
  list, add your ID.
- `tests/midi/test_profile_smokes.py` — open it, find the `_BUNDLED_IDS`
  list, add your ID.

The two lists are intentionally mirrored — drift between them is itself a
contract bug. Adding to one and not the other will fail review.

## Step 4 — Run the test suite and submit a PR

From the repo root:

```bash
uv run pytest tests/midi/ -q
```

You should see two new GREEN rows with your ID — one from the contract test
(field-level invariants: port hints non-empty, no duplicate `(channel, cc)` or
`(channel, note)` pairs) and one from the synthetic-MIDI smoke (every binding
decodes through `ControllerState.handle_msg` and surfaces at least one event).

**If a row fails:**

- **Contract test red** → JSON shape issue. Read the assertion message; common
  causes are an empty `port_name_hints` list, a duplicate `(channel, cc)` pair
  (two knobs claiming the same wire), or a typo in a field name.
- **Smoke test red** → a binding decoded but emitted no event. Check that every
  `(channel, cc)` or `(channel, note)` pair is real for your controller (no
  typos), the `field` is a non-empty string, and `axis` is either `unipolar`
  or `bipolar` for controls.

Submit a PR with these files:

- `src/vibemix/midi/profiles/<your_id>.json`
- `tests/midi/test_profile_contracts.py` (your ID added to `_BUNDLED_IDS`)
- `tests/midi/test_profile_smokes.py` (your ID added to `_BUNDLED_IDS`)

PR body: include your controller model, the OS(es) you tested on, any quirks
you ran into, and a one-line note on how you sourced the mapping (vendor docs,
Mixxx mapping, sniff capture, live ear).

## PR checklist

- [ ] Profile JSON loads via `uv run python3 -c "from vibemix.midi import load_profile; assert load_profile('<your_id>') is not None"`
- [ ] `tests/midi/test_profile_contracts.py` and `tests/midi/test_profile_smokes.py` are both GREEN with your row
- [ ] `port_name_hints` covers your macOS substring + Windows substring (run Step 1 on both if you can)
- [ ] `id` matches the filename stem exactly
- [ ] PR body includes the controller model + OS(es) tested + mapping source

## Troubleshooting & FAQs

**My port doesn't appear in `discover_midi_port.py`.** macOS may need Audio
MIDI Setup (built-in) to expose the device; Windows may need a vendor driver
install. If the OS doesn't see the device, vibemix won't either.

**Should I use `scripts/sniff_controller.py` instead?** That's the heavy
capture tool for full session recordings (226 lines, JSONL output) — useful
for reverse-engineering an undocumented mapping. The lightweight
`discover_midi_port.py` here is the right tool for Step 1. They coexist.

**Where do `axis: unipolar` vs `bipolar` matter?** Coach prompts. Bipolar
CCs (centered at 64) decode to signed offsets from center; unipolar (0–127)
decode to absolute positions. Get this wrong and the AI mis-narrates your
moves — a tempo nudge gets described as a fader sweep.

**Can I add a controller that's already bundled?** No — duplicate
`(channel, cc)` or `(channel, note)` pairs across `_BUNDLED_IDS` would shadow
each other through the listener's lookup tables. Open an issue if you think
the existing profile is wrong, and we'll iterate it in place.

**Why is `_template.json` under `docs/contributing/` and not next to the real
profiles?** Anything ending in `.json` inside `src/vibemix/midi/profiles/` is
picked up by `list_profiles()` — a leading underscore does not exclude it. The
template lives one directory over so the bundled-profile list stays clean.

## Related docs

- `docs/contributing/midi-catalog.md` — why `profiles/` is canonical (v7.0 Phase 68 migration note)
- `docs/midi-controllers.md` — list of currently-bundled controllers + status
- `docs/midi-mapping.md` — full profile schema reference
- `docs/flake-hunt.md` — sibling contributor doc on the 10× test-determinism protocol
