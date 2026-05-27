---
phase: 68-all-devices-ready
plan: 04
type: execute
wave: 3
depends_on: ["68-01", "68-02"]
files_modified:
  - scripts/discover_midi_port.py
  - docs/contributing/_template.json
  - docs/contributing/add-a-controller.md
autonomous: true
requirements:
  - DEV-05

must_haves:
  truths:
    - "scripts/discover_midi_port.py exists, is ≤30 lines (excluding shebang + license + docstring), exits 0 when ports are found and prints them sorted"
    - "scripts/discover_midi_port.py exits non-zero with a helpful stderr message when no MIDI ports are detected"
    - "docs/contributing/_template.json validates against profile.py::_parse_profile when the placeholder fields are filled in (verified manually OR via a test that copies + fills + loads)"
    - "docs/contributing/add-a-controller.md is ≤200 lines, lists the exact 4 steps (discover port → copy template → add to parametrize → pytest green + PR), and references the canonical test files from P68P02 (test_profile_contracts.py + test_profile_smokes.py)"
    - "docs/contributing/_template.json lives under docs/contributing/ (NOT under src/vibemix/midi/profiles/) — avoids list_profiles() pollution per 68-RESEARCH Pitfall #5"
  artifacts:
    - path: "scripts/discover_midi_port.py"
      provides: "≤30-line cross-platform mido.get_input_names() helper for contributors' Step 1"
      contains: "mido.get_input_names"
    - path: "docs/contributing/_template.json"
      provides: "Clean profile JSON copy-target with placeholder values that a contributor fills in"
      contains: "port_name_hints"
    - path: "docs/contributing/add-a-controller.md"
      provides: "≤200-line contributor recipe — 4 steps + PR checklist"
      contains: "test_profile_contracts.py"
  key_links:
    - from: "docs/contributing/add-a-controller.md"
      to: "scripts/discover_midi_port.py"
      via: "Step 1 invocation reference"
      pattern: "scripts/discover_midi_port.py"
    - from: "docs/contributing/add-a-controller.md"
      to: "docs/contributing/_template.json"
      via: "Step 2 copy-target reference"
      pattern: "docs/contributing/_template.json"
    - from: "docs/contributing/add-a-controller.md"
      to: "tests/midi/test_profile_contracts.py"
      via: "Step 3 parametrize-list reference"
      pattern: "test_profile_contracts.py"
---

<objective>
Wave 3 — Land the "Add Your Controller" contributor recipe that closes DEV-05 (engineering side). Three new artifacts compose into a self-contained recipe:

1. `scripts/discover_midi_port.py` — ≤30-line cross-platform `mido.get_input_names()` lister (recipe Step 1).
2. `docs/contributing/_template.json` — clean profile JSON copy-target with placeholder values (recipe Step 2). Lives under `docs/contributing/` (NOT under `src/vibemix/midi/profiles/`) to avoid `list_profiles()` pollution per 68-RESEARCH §Pitfall #5.
3. `docs/contributing/add-a-controller.md` — ≤200-line recipe doc with the exact 4-step pattern + PR checklist (recipe entry point).

The smoke discharge (Kaan or trusted DJ adds one new profile in <30 min on a controller-of-opportunity) routes to KAAN-ACTION §V7-LIVE-07 (created in Wave 4 plan 68P05) per 68-CONTEXT decision "Smoke Discharge".

Purpose: Close DEV-05 engineering side. A stranger encountering vibemix should be able to follow this recipe end-to-end without needing to read source code. The recipe explicitly references Wave 1's `test_profile_contracts.py` + `test_profile_smokes.py` — adding `your-controller-id` to both `_BUNDLED_IDS` lists is the 4-line PR.

Output: 3 new files. Zero edits to `src/vibemix/`. Zero new dependencies. Coexists with existing `scripts/sniff_controller.py` (heavier 226-line JSONL sniffer for full session captures — different scope per 68-RESEARCH §Open Questions #3).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@.planning/phases/68-all-devices-ready/68-CONTEXT.md
@.planning/phases/68-all-devices-ready/68-RESEARCH.md
@.planning/phases/68-all-devices-ready/68-01-SUMMARY.md
@.planning/phases/68-all-devices-ready/68-02-SUMMARY.md

@scripts/sniff_controller.py
@src/vibemix/midi/profile.py
@src/vibemix/midi/profiles/pioneer_ddj_flx4.json
@src/vibemix/midi/profiles/numark_party_mix_live.json

<interfaces>
ControllerProfile schema (from src/vibemix/midi/profile.py — the canonical validator the template must satisfy):
```json
{
  "id": "<vendor>_<model_snake_case>",          // required, str
  "display_name": "Vendor Model Name",          // required, str
  "port_name_hints": ["SUBSTR1", "SUBSTR2"],    // required, list of str (≥ 1, plural)
  "decks": ["A", "B"],                          // required, tuple of str
  "controls": {                                 // required, dict of cc bindings
    "vol_a": {
      "kind": "control_change",
      "channel": 0,
      "cc": 19,
      "axis": "unipolar",                       // unipolar | bipolar | boolean
      "deck": "A",
      "field": "fader_volume"
    }
  },
  "buttons": {                                  // optional but recommended, dict of note bindings
    "play_a": {
      "kind": "note_on",
      "channel": 0,
      "note": 11,
      "deck": "A",
      "field": "play_button"
    }
  },
  "notes": "JSON-only; hardware not verified — pending live ear pass"  // optional, str
}
```

Reference helper precedent — `scripts/sniff_controller.py` (already shipped, 226 lines):
- Full JSONL session capture with metadata.
- COEXISTS with the new `discover_midi_port.py`; different audience (the deep-debug DJ vs. the recipe-Step-1 first-timer).

Per 68-RESEARCH §Pitfall #5: do NOT place `_template.json` under `src/vibemix/midi/profiles/`. The `list_profiles()` filter is `entry.name.endswith(".json")` — leading underscore is NOT excluded.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: scripts/discover_midi_port.py — ≤30-line cross-platform port lister</name>
  <files>scripts/discover_midi_port.py</files>
  <read_first>
    @.planning/phases/68-all-devices-ready/68-CONTEXT.md (decision "scripts/discover_midi_port.py — uses mido.get_input_names() to print attached MIDI port names (≤ 30 lines)")
    @.planning/phases/68-all-devices-ready/68-RESEARCH.md (§Pattern 5 + §Open Questions #3 confirming coexistence with sniff_controller.py)
    @scripts/sniff_controller.py (first 50 lines — confirm the SPDX header + shebang + module docstring convention used in the scripts/ dir)
  </read_first>
  <action>
    Create `scripts/discover_midi_port.py` as a standalone CLI tool. Constraints:
    - ≤ 30 lines for the executable body (shebang + SPDX + docstring + main() + `if __name__` block). Comments inside main() do not count against the 30, but keep the file under ~50 total lines including imports.
    - Standalone — does NOT import from `vibemix.*`. The contributor runs this BEFORE any vibemix setup if needed: `pip install mido python-rtmidi` is the only prerequisite, mirrored in the doc.
    - Cross-platform — works on macOS (CoreMIDI) and Windows (WinMM) out of the box because `mido` wraps RtMIDI which abstracts the OS API.
    - Output: print attached MIDI input port names, one per line, sorted, with an instruction line after explaining "copy the substring that uniquely identifies your controller into the `port_name_hints` field".
    - Exit codes: 0 if ports found and printed; 1 if no ports detected (helpful stderr message); 2 if `mido` is not installed (helpful pip install hint).
    - Make the file executable (`chmod +x` is recorded in the SUMMARY; the shebang `#!/usr/bin/env python3` + the chmod allows `./scripts/discover_midi_port.py` invocation).

    Reference (lifted verbatim from 68-RESEARCH §Pattern 5):

    ```python
    #!/usr/bin/env python3
    # SPDX-License-Identifier: Apache-2.0
    """Discover attached MIDI input port names — Step 1 of add-a-controller.md.

    Usage:
        python3 scripts/discover_midi_port.py

    Prints one port name per line (sorted). Exits 0 with the list, 1 if no ports,
    2 if mido is not installed. Cross-platform: macOS (CoreMIDI) + Windows (WinMM).

    No imports from src/vibemix/ — runs with just `pip install mido python-rtmidi`.
    """
    from __future__ import annotations
    import sys

    def main() -> int:
        try:
            import mido  # noqa: F401  (imported for side effect of confirming install)
        except ImportError:
            print("mido is not installed. Run: pip install mido python-rtmidi", file=sys.stderr)
            return 2
        names = sorted(mido.get_input_names())
        if not names:
            print("No MIDI input ports detected. Connect your controller via USB and re-run.", file=sys.stderr)
            return 1
        print("Attached MIDI input ports:")
        for n in names:
            print(f"  - {n}")
        print("\nCopy the substring that uniquely identifies your controller into the")
        print("'port_name_hints' field of your new profile JSON (see docs/contributing/_template.json).")
        return 0

    if __name__ == "__main__":
        raise SystemExit(main())
    ```

    DO NOT add `--json` / `--verbose` / `--filter` flags — the recipe Step 1 audience needs plain text. The heavier sniff_controller.py owns the full-capture / JSONL surface (per 68-RESEARCH Open Question #3 — both coexist).

    Make it executable: include in the commit the chmod via `git update-index --chmod=+x scripts/discover_midi_port.py`.
  </action>
  <verify>
    <automated>test -f scripts/discover_midi_port.py &amp;&amp; test -x scripts/discover_midi_port.py &amp;&amp; [ $(wc -l &lt; scripts/discover_midi_port.py) -le 50 ] &amp;&amp; uv run python3 scripts/discover_midi_port.py; rc=$?; [ "$rc" = 0 ] || [ "$rc" = 1 ] || [ "$rc" = 2 ] || { echo "unexpected rc=$rc"; exit 1; }; echo OK</automated>
  </verify>
  <acceptance_criteria>
    - `scripts/discover_midi_port.py` exists.
    - File has executable bit (`ls -l scripts/discover_midi_port.py` shows `x` in user perms).
    - Total line count ≤ 50.
    - `grep -c "mido.get_input_names" scripts/discover_midi_port.py` ≥ 1.
    - `grep -c "from vibemix" scripts/discover_midi_port.py` == 0 (no project imports — standalone for contributors).
    - `uv run python3 scripts/discover_midi_port.py` exits 0, 1, or 2 (one of the three documented exits — depending on what ports the runner machine sees; CI macos runner = likely 1, dev machine with FLX4 = likely 0).
    - `head -1 scripts/discover_midi_port.py` is `#!/usr/bin/env python3`.
  </acceptance_criteria>
  <done>
    Standalone executable cross-platform port-lister exists, prints attached MIDI ports with a copy-target instruction, exits cleanly on all 3 documented states (ports / no-ports / mido-missing).
  </done>
</task>

<task type="auto">
  <name>Task 2: docs/contributing/_template.json — clean profile copy-target</name>
  <files>docs/contributing/_template.json</files>
  <read_first>
    @.planning/phases/68-all-devices-ready/68-RESEARCH.md (§Common Pitfalls #5 — DO NOT ship _template.json under src/vibemix/midi/profiles/; place under docs/contributing/ to avoid list_profiles() pollution)
    @src/vibemix/midi/profile.py (read _parse_profile fully — confirm REQUIRED fields and OPTIONAL fields; the template must satisfy every required slot when filled in)
    @src/vibemix/midi/profiles/pioneer_ddj_flx4.json (the gold-standard reference — copy its shape, replace values with placeholders)
    @src/vibemix/midi/profiles/numark_party_mix_live.json (sanity-check the smallest profile shape — confirm decks/controls/buttons shape minimum)
  </read_first>
  <action>
    Create `docs/contributing/_template.json` (note: leading-underscore stem is fine HERE because this is under `docs/contributing/`, not under `src/vibemix/midi/profiles/` — `list_profiles()` will never see it; per 68-RESEARCH Pitfall #5):

    1. Schema: must validate against `profile.py::_parse_profile` when placeholders are replaced with real values.
    2. Required fields populated with placeholder values that signal "fill me in" but still parse cleanly:
       - `id`: `"vendor_model_snake_case"` (string — contributor renames to e.g., `"pioneer_ddj_rev1"`)
       - `display_name`: `"Vendor Model Display Name"`
       - `port_name_hints`: `["PORT_SUBSTRING_PLATFORM_A", "PORT_SUBSTRING_PLATFORM_B"]` (list — contributor replaces with macOS + Windows port substrings discovered via Step 1; per 68-RESEARCH §Pitfall #7 cross-platform nondeterminism advice from FLX4 `["DDJ-FLX4", "FLX4"]`)
       - `decks`: `["A", "B"]`
       - `controls`: a dict with ONE example cc binding (`vol_a` mapping to a unipolar channel-0 control); contributor adds more.
       - `buttons`: a dict with ONE example note binding (`play_a` mapping to a channel-0 note); contributor adds more.
    3. Optional `notes` field: `"JSON-only; hardware not verified yet — pending live ear pass."` (matches the convention from 9 of the 10 bundled profiles).
    4. Inline `_comment` field (NOT validated by `_parse_profile` — but JSON allows extras; verify _parse_profile ignores unknown top-level keys OR omit comments and put explanation in the .md recipe instead):
       - SAFER PATH: omit comments in JSON; the .md recipe (Task 3) is where the field-by-field explanation lives.

    Reference template:

    ```json
    {
      "id": "vendor_model_snake_case",
      "display_name": "Vendor Model Display Name",
      "port_name_hints": ["PORT_SUBSTRING_PLATFORM_A", "PORT_SUBSTRING_PLATFORM_B"],
      "decks": ["A", "B"],
      "controls": {
        "vol_a": {
          "kind": "control_change",
          "channel": 0,
          "cc": 19,
          "axis": "unipolar",
          "deck": "A",
          "field": "fader_volume"
        }
      },
      "buttons": {
        "play_a": {
          "kind": "note_on",
          "channel": 0,
          "note": 11,
          "deck": "A",
          "field": "play_button"
        }
      },
      "notes": "JSON-only; hardware not verified yet — pending live ear pass."
    }
    ```

    Verify the template is valid by hand-walking it through `_parse_profile`'s field checks. If `_parse_profile` rejects this exact shape (e.g., it requires `buttons` to be non-empty, or it strict-rejects unknown axis values), adjust the template until a manual `load_profile()` on a temp-copy-with-renamed-stem succeeds.

    OPTIONAL sanity test (not committed; run locally during this task to verify the template parses):
    ```bash
    # Copy template into a temp slot in profiles/ with a unique name, then load.
    cp docs/contributing/_template.json /tmp/temp_template_profile.json
    sed -i.bak 's/vendor_model_snake_case/_TEMP_TEMPLATE_VALIDATE/g' /tmp/temp_template_profile.json
    # (Then manually copy into a scratch location accessible to load_profile, or import _parse_profile directly.)
    uv run python3 -c "from vibemix.midi.profile import _parse_profile; import json; _parse_profile(json.load(open('/tmp/temp_template_profile.json')))"
    rm /tmp/temp_template_profile.json /tmp/temp_template_profile.json.bak
    ```
    If this manual sanity check fails, the template needs fixing BEFORE the commit lands.
  </action>
  <verify>
    <automated>test -f docs/contributing/_template.json &amp;&amp; uv run python3 -c "import json; data = json.load(open('docs/contributing/_template.json')); assert 'id' in data and 'display_name' in data and 'port_name_hints' in data and isinstance(data['port_name_hints'], list) and len(data['port_name_hints']) &gt;= 1 and 'controls' in data; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `docs/contributing/_template.json` exists.
    - File parses as valid JSON (`json.load` succeeds).
    - Contains all required ControllerProfile fields per `profile.py::_parse_profile`: `id`, `display_name`, `port_name_hints` (plural list, length ≥ 1), `decks`, `controls` (non-empty), `buttons` (non-empty).
    - `port_name_hints` is a list (NOT a singular string — pinned by 68-RESEARCH §Common Pitfalls field-name note).
    - File is under `docs/contributing/` (NOT under `src/vibemix/midi/profiles/` — per 68-RESEARCH Pitfall #5).
    - Optional manual sanity check (per <action>) confirms `_parse_profile` accepts the template when stems are renamed.
  </acceptance_criteria>
  <done>
    Clean placeholder template lives under docs/contributing/, validates against the canonical `_parse_profile` validator, uses the plural `port_name_hints` field, ships ONE example cc + ONE example note binding for contributors to extend.
  </done>
</task>

<task type="auto">
  <name>Task 3: docs/contributing/add-a-controller.md — ≤200-line recipe doc</name>
  <files>docs/contributing/add-a-controller.md</files>
  <read_first>
    @.planning/phases/68-all-devices-ready/68-CONTEXT.md (decision "Contributor Recipe" — the 4 steps + their content)
    @.planning/phases/68-all-devices-ready/68-RESEARCH.md (§User Constraints "Contributor recipe" + §Pitfall #7 cross-platform port enumeration advice)
    @docs/contributing/midi-catalog.md (from Wave 0 — confirm the migration note that this doc compliments; cross-link)
    @docs/midi-controllers.md (already-shipped — list of supported controllers; cross-link)
    @.planning/phases/68-all-devices-ready/68-02-SUMMARY.md (confirm the exact filenames `tests/midi/test_profile_contracts.py` + `tests/midi/test_profile_smokes.py` from Wave 1 to reference in Step 3)
    @CLAUDE.md project-level (confirm the developer-facing tone — casual but precise; no emoji)
  </read_first>
  <action>
    Create `docs/contributing/add-a-controller.md`, ≤200 lines total. Sections (in order):

    1. **Title + intro paragraph** (~5 lines):
       - Title: `# Add Your Controller`
       - One-liner: "Bundle a new MIDI controller into vibemix in under 30 minutes."
       - Mention: works on macOS + Windows; no rebuild required after PR merges.

    2. **Prerequisites** (~10 lines):
       - macOS 12+ or Windows 10+
       - Python 3.12 with the project's `.venv` set up (`uv sync` from repo root)
       - Your controller, connected over USB
       - Familiarity with your controller's MIDI mapping (vendor docs or `scripts/sniff_controller.py` for full capture)

    3. **Step 1 — Discover your controller's port name** (~15 lines):
       - Plug in your controller.
       - Run: `uv run python3 scripts/discover_midi_port.py`
       - Expected output: 1+ port names; copy the substring that uniquely identifies your controller (e.g., `"DDJ-FLX4"`, `"DJControl Inpulse 500"`).
       - macOS vs. Windows tip: the port name often differs across OSes (per 68-RESEARCH §Pitfall #7). Run the script on BOTH OSes if you can — your `port_name_hints` should contain a substring valid on both. Example from `pioneer_ddj_flx4.json`: `["DDJ-FLX4", "FLX4"]` covers macOS's `"DDJ-FLX4 USB MIDI"` and Windows's `"DDJ-FLX4"`.

    4. **Step 2 — Copy and fill in the profile template** (~30 lines):
       - Copy `docs/contributing/_template.json` to `src/vibemix/midi/profiles/<your_vendor>_<your_model>.json` (snake_case, no spaces).
       - Open it and fill in: `id` (must match the filename stem), `display_name` (human-friendly), `port_name_hints` (the list from Step 1), `decks` (typically `["A", "B"]` for 2-deck controllers; `["A", "B", "C", "D"]` for 4-deck), `controls` (one entry per CC mapping), `buttons` (one entry per NOTE mapping).
       - Field reference table (inline — 5-7 rows):
         | Field | Type | Example |
         | --- | --- | --- |
         | `kind` | str | `"control_change"` for CCs, `"note_on"` for buttons |
         | `channel` | int | `0`–`15` (MIDI channel, zero-indexed) |
         | `cc` / `note` | int | `0`–`127` |
         | `axis` (CCs only) | str | `"unipolar"` (0-127), `"bipolar"` (centered at 64), or `"boolean"` (binary) |
         | `deck` | str | `"A"`, `"B"`, `"C"`, `"D"`, or `"MASTER"` |
         | `field` | str | Logical name like `"fader_volume"`, `"eq_low"`, `"play_button"` — choose any descriptor |
       - Hint: copy structure from an existing profile (e.g., `src/vibemix/midi/profiles/pioneer_ddj_flx4.json` for a 2-deck Pioneer controller).

    5. **Step 3 — Add your controller ID to the test parametrize lists** (~10 lines):
       - Open `tests/midi/test_profile_contracts.py`. Add `"<your_vendor>_<your_model>"` to the `_BUNDLED_IDS` list (alphabetically).
       - Open `tests/midi/test_profile_smokes.py`. Add the same ID to its `_BUNDLED_IDS` list.
       - (The lists are intentionally mirrored — one source of truth would be cleaner, but the explicit duplication keeps each test file self-contained.)

    6. **Step 4 — Run the test suite and submit a PR** (~15 lines):
       - Run: `uv run pytest tests/midi/ -q`
       - Expected: every test passes, including 2 new rows in your name.
       - If a row fails:
         - Contract test red → check JSON shape (missing field, duplicate `(channel, cc)`, etc.).
         - Smoke test red → check that every binding's `(channel, cc)` or `(channel, note)` is real for your controller (no typos).
       - Submit a PR with these files:
         - `src/vibemix/midi/profiles/<your_id>.json`
         - `tests/midi/test_profile_contracts.py` (your ID added to `_BUNDLED_IDS`)
         - `tests/midi/test_profile_smokes.py` (your ID added to `_BUNDLED_IDS`)
       - PR body: include your controller model, OS(es) you tested on, and any quirks you ran into.

    7. **PR checklist** (~10 lines, checkbox markdown):
       - [ ] Profile JSON validates locally (`uv run python3 -c "from vibemix.midi import load_profile; assert load_profile('<your_id>') is not None"`)
       - [ ] Both `tests/midi/test_profile_contracts.py` and `tests/midi/test_profile_smokes.py` GREEN with your row
       - [ ] `port_name_hints` covers macOS substring + Windows substring (run Step 1 on both if you can)
       - [ ] `id` matches the filename stem
       - [ ] PR body includes controller model + OS(es) tested

    8. **Troubleshooting & FAQs** (~20 lines):
       - "My port doesn't appear in `discover_midi_port.py`": macOS may need `Audio MIDI Setup` (built-in); Windows may need vendor driver install. If the OS doesn't see the device, vibemix won't either.
       - "Should I use `scripts/sniff_controller.py` instead?": That's the heavy capture tool for full session recordings (226 lines, JSONL output) — useful for reverse-engineering an undocumented mapping but overkill for Step 1. They coexist.
       - "Where do `axis: unipolar` vs `bipolar` matter?": Coach prompts. Bipolar CCs (centered at 64) decode to signed offsets; unipolar (0-127) to absolute positions. Get this wrong and the AI will mis-narrate your moves.
       - "Can I add a controller that's already bundled?": No — duplicates fail the contract test's `(channel, cc)` uniqueness check. Open an issue if you think the existing profile is wrong.

    9. **Related docs** (~5 lines):
       - `docs/contributing/midi-catalog.md` — why `profiles/` is canonical
       - `docs/midi-controllers.md` — list of currently-bundled controllers
       - `docs/midi-mapping.md` — full profile schema reference

    Tone: casual but precise; matches Kaan's CLAUDE.md "casual tone, no bullshit". NO emojis. Code blocks use triple-backtick with language tag.

    Total length check: count the lines as you write. If the body would exceed 200, prune the Troubleshooting / FAQ section first; the load-bearing content is Steps 1–4 + the PR checklist.
  </action>
  <verify>
    <automated>test -f docs/contributing/add-a-controller.md &amp;&amp; [ $(wc -l &lt; docs/contributing/add-a-controller.md) -le 200 ] &amp;&amp; grep -c 'scripts/discover_midi_port.py' docs/contributing/add-a-controller.md | awk '{exit ($1 &gt;= 1 ? 0 : 1)}' &amp;&amp; grep -c 'docs/contributing/_template.json' docs/contributing/add-a-controller.md | awk '{exit ($1 &gt;= 1 ? 0 : 1)}' &amp;&amp; grep -c 'test_profile_contracts.py' docs/contributing/add-a-controller.md | awk '{exit ($1 &gt;= 1 ? 0 : 1)}' &amp;&amp; grep -c 'test_profile_smokes.py' docs/contributing/add-a-controller.md | awk '{exit ($1 &gt;= 1 ? 0 : 1)}'</automated>
  </verify>
  <acceptance_criteria>
    - `docs/contributing/add-a-controller.md` exists.
    - Total line count ≤ 200.
    - References ALL three sibling artifacts: `scripts/discover_midi_port.py` (Step 1), `docs/contributing/_template.json` (Step 2), `tests/midi/test_profile_contracts.py` + `tests/midi/test_profile_smokes.py` (Step 3).
    - Contains a PR checklist (markdown checkbox `- [ ]` style) with ≥ 4 items.
    - Includes the cross-platform port-name advice (per 68-RESEARCH §Pitfall #7) — `grep -c "port_name_hints" docs/contributing/add-a-controller.md` ≥ 1.
    - NO emojis (per CLAUDE.md).
    - The 4 steps appear in order: Step 1 (discover), Step 2 (template), Step 3 (parametrize), Step 4 (pytest + PR).
  </acceptance_criteria>
  <done>
    The contributor recipe doc exists, lists the 4 steps clearly, references all 3 sibling artifacts, is ≤ 200 lines, follows the project's casual-precise tone, and is ready for a stranger to follow end-to-end in <30 min. DEV-05 engineering side closed (live smoke discharge → §V7-LIVE-07 in P05 Wave 4).
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Contributor input (their new JSON + their controller) | Their JSON is parsed by `_parse_profile` (raises ValueError on drift, no code execution); their controller is enumerated read-only via `mido.get_input_names()` (no port open) |
| Template under docs/contributing/ | Lives OUTSIDE `src/vibemix/midi/profiles/` — `list_profiles()` cannot pick it up; pollution avoided |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-68P04-01 | Tampering | Contributor pull request | mitigate | Recipe Step 4's `uv run pytest tests/midi/ -q` gate is the CI line — malformed JSON fails the contract test (Wave 1) before merge; reviewer also confirms PR body has controller model + OS(es). |
| T-68P04-02 | DoS | scripts/discover_midi_port.py | accept | Uses `mido.get_input_names()` (enumeration only — no `open_input`); cannot lock or open a real port. Verified safe by design per 68-RESEARCH §Security Domain row 5. |
| T-68P04-03 | Disclosure | Template + recipe doc | accept | All content is public (Apache-2.0 OSS doc surface); no secrets. |
| T-68P04-04 | Tampering | Template pollution of list_profiles() | mitigate | Per 68-RESEARCH §Pitfall #5, template lives under `docs/contributing/_template.json` — outside the `list_profiles()` glob root. Acceptance gate verifies the path. |
| T-68P04-SC | Tampering | npm/pip/cargo installs | accept | Plan installs no packages. Recipe instructs contributors to `pip install mido python-rtmidi` for the standalone helper — `mido` is already in `pyproject.toml` so contributors using `uv sync` already have it. |
</threat_model>

<verification>
- `test -f scripts/discover_midi_port.py && test -x scripts/discover_midi_port.py` — helper exists + executable.
- `uv run python3 scripts/discover_midi_port.py` — exits 0 / 1 / 2 (one of the three documented states).
- `uv run python3 -c "import json; json.load(open('docs/contributing/_template.json'))"` — template parses.
- `wc -l docs/contributing/add-a-controller.md` — line count ≤ 200.
- `grep -c -E "scripts/discover_midi_port.py|docs/contributing/_template.json|test_profile_contracts.py|test_profile_smokes.py" docs/contributing/add-a-controller.md` — ≥ 4 (all 4 sibling references present).
- `uv run pytest -q` — full suite GREEN (no regression; the 3 new artifacts are docs + script + json, not pytest-collected).
</verification>

<success_criteria>
DEV-05 engineering side closed (ROADMAP P68 SC#5):
- `docs/contributing/add-a-controller.md` exists with the exact 4-step contract-test pattern.
- `docs/contributing/_template.json` exists as the copy-target (safe location — outside profiles/).
- `scripts/discover_midi_port.py` exists as the Step 1 helper.
- PR checklist documents the merge gates.

Live smoke discharge (Kaan or trusted DJ adds one new profile in <30 min) → KAAN-ACTION §V7-LIVE-07 (created in Wave 4 plan 68P05).
</success_criteria>

<output>
Create `.planning/phases/68-all-devices-ready/68-04-SUMMARY.md` when done. Summary MUST record:
- Confirmation the helper exits 0 / 1 / 2 on the runner machine (which exit fired).
- Confirmation the template parses + validates against `_parse_profile` (paste the manual sanity-check output).
- Final line count of `add-a-controller.md` (must be ≤ 200).
- Whether the placeholder field-reference table was kept inline or moved to a separate `docs/midi-mapping.md` cross-link (note the choice — the doc shouldn't lose precision in service of line count).
- Pointer to §V7-LIVE-07 (the smoke-discharge KAAN-ACTION entry — landing in 68P05 Wave 4).
</output>
