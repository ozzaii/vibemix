---
phase: 68-all-devices-ready
plan: 02
type: execute
wave: 1
depends_on: ["68-01"]
files_modified:
  - tests/midi/test_profile_contracts.py
  - tests/midi/test_profile_smokes.py
autonomous: true
requirements:
  - DEV-01

must_haves:
  truths:
    - "uv run pytest tests/midi/test_profile_contracts.py -v shows 10 GREEN parametrized cases (one per bundled profile)"
    - "uv run pytest tests/midi/test_profile_smokes.py -v shows 10 GREEN parametrized cases (one per bundled profile)"
    - "Each profile loads via load_profile() — no jsonschema dependency in the test surface"
    - "Each profile has non-empty port_name_hints (plural list of str, length ≥ 1)"
    - "Every CC + NOTE binding in each profile fires exactly one event through ControllerState.handle_msg with no exceptions"
  artifacts:
    - path: "tests/midi/test_profile_contracts.py"
      provides: "10-row parametrized contract test — DEV-01 (a) + (c)"
      min_lines: 50
    - path: "tests/midi/test_profile_smokes.py"
      provides: "10-row parametrized synthetic-MIDI smoke — DEV-01 (b)"
      min_lines: 60
  key_links:
    - from: "tests/midi/test_profile_contracts.py"
      to: "vibemix.midi.profile::load_profile"
      via: "import + per-row call"
      pattern: "from vibemix.midi import load_profile"
    - from: "tests/midi/test_profile_smokes.py"
      to: "vibemix.midi.state::ControllerState"
      via: "instance per row + handle_msg loop"
      pattern: "from vibemix.midi.state import ControllerState"
---

<objective>
Wave 1 — Land the 10-row parametrized contract test + synthetic-MIDI smoke that close DEV-01. Each of the 10 bundled profile IDs gets:
- A contract row that loads via `load_profile()`, asserts non-None ControllerProfile, asserts non-empty `port_name_hints` tuple, asserts no duplicate `(channel, cc)` or `(channel, note)` bindings within the profile.
- A smoke row that builds a `ControllerState(profile=...)`, generates a `SimpleNamespace`-shaped `mido.Message` per CC + NOTE binding, pushes each through `ControllerState.handle_msg`, asserts no exceptions raised + `events_since(0.0)` ≥ 1 event surfaced.

Purpose: Close DEV-01 — every bundled profile is now data-contract-pinned. Future profile JSON drift (wrong field name, duplicate binding, empty port_name_hints) reds CI before landing. Foundational for DEV-05's contributor recipe (Wave 3): the 4-step pattern in `docs/contributing/add-a-controller.md` literally references these two test files.

Output: Two new files under `tests/midi/`. Zero edits to `src/vibemix/`. Zero new dependencies. Composes the patterns shipped at `tests/midi/test_profiles_all_controllers.py:35-47` (the canonical `_BUNDLED_IDS` list) and `tests/midi/test_flx4_synthetic_decode.py:33-42` (the `SimpleNamespace` MIDI factory).
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

@src/vibemix/midi/__init__.py
@src/vibemix/midi/profile.py
@src/vibemix/midi/state.py
@src/vibemix/midi/profiles/pioneer_ddj_flx4.json
@tests/midi/test_profiles_all_controllers.py
@tests/midi/test_flx4_synthetic_decode.py

<interfaces>
Public exports from `vibemix.midi`:
```python
from vibemix.midi import load_profile, list_profiles, find_mapping
# load_profile(id: str) -> ControllerProfile | None
# list_profiles() -> tuple[ControllerProfile, ...]
# find_mapping(port_name: str) -> ControllerProfile | None
```

ControllerProfile frozen-dataclass fields (from `src/vibemix/midi/profile.py`):
```python
@dataclass(frozen=True)
class ControllerProfile:
    id: str
    display_name: str
    port_name_hints: tuple[str, ...]   # NON-EMPTY plural list — assert ≥ 1 entry
    decks: tuple[str, ...]
    controls: dict[str, ControlBinding]   # cc bindings: ControlBinding(kind, channel, cc, axis, deck, field)
    buttons: dict[str, ControlBinding]    # note bindings: ControlBinding(kind, channel, note, deck, field)
    notes: str | None = None
```

ControlBinding fields used in tests:
- `channel: int`, `cc: int | None`, `note: int | None`, `axis: str` ("unipolar" / "bipolar" / "boolean"), `deck: str`, `field: str`.

ControllerState methods used:
```python
from vibemix.midi.state import ControllerState
cs = ControllerState(profile=profile)
cs.handle_msg(msg)            # accepts mido.Message-shaped SimpleNamespace
cs.events_since(0.0) -> list  # event ring buffer
```

SimpleNamespace MIDI factory (LIFTED VERBATIM from tests/midi/test_flx4_synthetic_decode.py:33-42):
```python
from types import SimpleNamespace
def _cc(channel, control, value):
    return SimpleNamespace(type="control_change", channel=channel, control=control, value=value)
def _note_on(channel, note, velocity=127):
    return SimpleNamespace(type="note_on", channel=channel, note=note, velocity=velocity)
def _note_off(channel, note):
    return SimpleNamespace(type="note_off", channel=channel, note=note, velocity=0)
```

Canonical 10 IDs (LIFTED VERBATIM from tests/midi/test_profiles_all_controllers.py:35-47):
```python
_BUNDLED_IDS = [
    "hercules_inpulse_300", "hercules_inpulse_500", "numark_party_mix_live",
    "pioneer_ddj_1000", "pioneer_ddj_400", "pioneer_ddj_flx10", "pioneer_ddj_flx4",
    "pioneer_ddj_flx6", "pioneer_ddj_sx3", "pioneer_xdj_rx3",
]
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: tests/midi/test_profile_contracts.py — 10-row contract test</name>
  <files>tests/midi/test_profile_contracts.py</files>
  <read_first>
    @.planning/phases/68-all-devices-ready/68-CONTEXT.md
    @.planning/phases/68-all-devices-ready/68-RESEARCH.md (§Pattern 1 + §Code Examples 5 + §Anti-Patterns to Avoid item 1 "DO NOT use jsonschema")
    @src/vibemix/midi/profile.py (full file — confirms ControllerProfile frozen-dataclass field shape + `port_name_hints` plural + `_parse_profile` raises ValueError on drift)
    @src/vibemix/midi/__init__.py (confirms `load_profile` re-export)
    @tests/midi/test_profiles_all_controllers.py (full file — `_ALL_CONTROLLER_IDS` canonical 10 list at lines 35-47; pattern is the closest existing analog)
    @src/vibemix/midi/profiles/pioneer_ddj_flx4.json (the canonical shape — confirms `port_name_hints` is a list of str)
    @src/vibemix/midi/profiles/numark_party_mix_live.json (sanity-check the smallest-bundled profile has the same shape)
  </read_first>
  <behavior>
    - Test 1 (per row): `load_profile(profile_id)` returns a non-None `ControllerProfile`. ValueError surfacing from `_parse_profile` is a FAIL (means the bundled JSON drifted).
    - Test 2 (per row): `profile.port_name_hints` is a tuple of length ≥ 1; every entry is a non-empty `str`.
    - Test 3 (per row): No duplicate `(channel, cc)` pair across `profile.controls.values()` — duplicate CC binding within a profile is a JSON authoring bug.
    - Test 4 (per row): No duplicate `(channel, note)` pair across `profile.buttons.values()` — duplicate NOTE binding within a profile is a JSON authoring bug.
    - Edge case: A profile with empty `buttons` dict (e.g., a deck-only controller) is acceptable — the duplicate-note check trivially passes on empty.
    - Anti-pattern (do NOT do): `jsonschema.validate(profile_json, schema_json)` — `schema.json` is being deleted in Wave 0; the canonical validator is `profile.py::_parse_profile` invoked by `load_profile`. 68-RESEARCH §Anti-Patterns to Avoid item 1.
  </behavior>
  <action>
    Create `tests/midi/test_profile_contracts.py` with this exact shape (compose verbatim — DO NOT invent new patterns; per 68-RESEARCH.md §Anti-Patterns, do NOT use `jsonschema`):

    1. Module docstring + SPDX header matching the project convention (`# SPDX-License-Identifier: Apache-2.0`).
    2. Imports: `import pytest`, `from vibemix.midi import load_profile`.
    3. `_BUNDLED_IDS` module-level constant — LIFT VERBATIM from `tests/midi/test_profiles_all_controllers.py:35-47` (alphabetical-ish, 10 entries). Add a comment: `# THE ten. Success-criterion 10 per ROADMAP P68 SC#1. Mirrored from test_profiles_all_controllers.py.`
    4. Single parametrized test function: `@pytest.mark.parametrize("profile_id", _BUNDLED_IDS)` decorating `def test_profile_loads_and_validates(profile_id):` with the 4-behavior assertion body (see <behavior>).
    5. Assertions use plain `assert` (matches project convention — no pytest-fixtures-as-state).
    6. Failure messages MUST include the `profile_id` (e.g., `assert ..., f"duplicate (channel, cc) in {profile_id}"`) so a red row in CI surfaces the offending profile immediately.
    7. NO `import jsonschema` — the contract is enforced by `load_profile()` raising ValueError on drift (which becomes a test ERROR, not just a FAIL).

    Reference implementation (per 68-RESEARCH §Pattern 1 — adapt names/comments to project conventions but keep semantics):

    ```python
    import pytest
    from vibemix.midi import load_profile

    _BUNDLED_IDS = [
        "hercules_inpulse_300", "hercules_inpulse_500", "numark_party_mix_live",
        "pioneer_ddj_1000", "pioneer_ddj_400", "pioneer_ddj_flx10",
        "pioneer_ddj_flx4", "pioneer_ddj_flx6", "pioneer_ddj_sx3", "pioneer_xdj_rx3",
    ]

    @pytest.mark.parametrize("profile_id", _BUNDLED_IDS)
    def test_profile_loads_and_validates(profile_id):
        profile = load_profile(profile_id)
        assert profile is not None, f"load_profile({profile_id!r}) returned None — missing JSON?"
        assert isinstance(profile.port_name_hints, tuple), f"{profile_id}: port_name_hints must be tuple"
        assert len(profile.port_name_hints) >= 1, f"{profile_id}: port_name_hints is empty"
        for hint in profile.port_name_hints:
            assert isinstance(hint, str) and hint, f"{profile_id}: blank/non-str hint {hint!r}"
        cc_keys = [(b.channel, b.cc) for b in profile.controls.values()]
        assert len(cc_keys) == len(set(cc_keys)), f"{profile_id}: duplicate (channel, cc) in controls"
        note_keys = [(b.channel, b.note) for b in profile.buttons.values()]
        assert len(note_keys) == len(set(note_keys)), f"{profile_id}: duplicate (channel, note) in buttons"
    ```

    Do NOT split into multiple test functions; ONE parametrized function delivers 10 named cases per `pytest -v`.
  </action>
  <verify>
    <automated>uv run pytest tests/midi/test_profile_contracts.py -v 2&gt;&amp;1 | tee /tmp/68P02-T1.log | tail -30 &amp;&amp; grep -c PASSED /tmp/68P02-T1.log | awk '{exit ($1 == 10 ? 0 : 1)}'</automated>
  </verify>
  <acceptance_criteria>
    - `uv run pytest tests/midi/test_profile_contracts.py -v` exits 0 with exactly 10 PASSED rows (one per `_BUNDLED_IDS` entry).
    - `pytest tests/midi/test_profile_contracts.py --collect-only -q` lists exactly 10 test IDs of the form `test_profile_loads_and_validates[hercules_inpulse_300]` etc.
    - `grep -c "import jsonschema" tests/midi/test_profile_contracts.py` returns 0 (anti-pattern not introduced).
    - `grep -c "port_name_hints" tests/midi/test_profile_contracts.py` ≥ 2 (the plural field name is referenced; no singular `port_name_hint` drift).
    - File is ≥ 50 lines (including comments + spacing).
  </acceptance_criteria>
  <done>
    File exists, 10 contract rows GREEN, plural field name pinned, no jsonschema import; DEV-01 (a) + (c) closed for all 10 bundled profiles.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: tests/midi/test_profile_smokes.py — 10-row synthetic-MIDI decode smoke</name>
  <files>tests/midi/test_profile_smokes.py</files>
  <read_first>
    @.planning/phases/68-all-devices-ready/68-CONTEXT.md
    @.planning/phases/68-all-devices-ready/68-RESEARCH.md (§Pattern 2 + §Code Examples 1 + §Open Questions #2)
    @tests/midi/test_flx4_synthetic_decode.py (full file — `_cc/_note_on/_note_off` factories at lines 33-42; this IS the pattern to lift)
    @src/vibemix/midi/state.py (focus: ControllerState.__init__, handle_msg, events_since, mark_connected — these are the public test surface)
    @src/vibemix/midi/profile.py (ControlBinding fields: channel, cc, note, axis — used to compute synthetic value)
    @src/vibemix/midi/profiles/pioneer_ddj_flx4.json (sample binding shapes for both controls (cc) and buttons (note))
    @src/vibemix/midi/profiles/numark_party_mix_live.json (smaller profile — sanity-check the smoke still surfaces ≥ 1 event)
  </read_first>
  <behavior>
    - Test (per row): Load profile via `load_profile(profile_id)`. Build `cs = ControllerState(profile=profile)`. Mark connected so events flow.
    - For every binding in `profile.controls.values()`: emit one `_cc(binding.channel, binding.cc, value)` where `value` is `80` for `axis=="unipolar"` and `90` for `axis=="bipolar"` (boolean CCs map to 127); push into `cs.handle_msg(msg)`. No exception must raise.
    - For every binding in `profile.buttons.values()`: emit one `_note_on(binding.channel, binding.note, velocity=127)`; push into `cs.handle_msg(msg)`. No exception must raise.
    - After all bindings emitted: `len(cs.events_since(0.0)) >= 1` — at least one event surfaced (per 68-RESEARCH §Assumption A5, ControllerState-only assertion is sufficient; the success criterion's "→ MusicState" chain is exercised in production, not required in the smoke).
    - Failure mode that this test catches: a binding's `field` reference doesn't match a `MusicState` field name → ControllerState raises KeyError → test FAILS on that profile_id with a clear message.
    - Edge case: profile with empty `buttons` (deck-only controller) — controls-only iteration must still surface events; assertion stays valid.
  </behavior>
  <action>
    Create `tests/midi/test_profile_smokes.py` with this exact shape (compose from 68-RESEARCH §Pattern 2; lift the `_cc`/`_note_on`/`_note_off` factory verbatim from `tests/midi/test_flx4_synthetic_decode.py:33-42`):

    1. Module docstring + SPDX header.
    2. Imports: `from types import SimpleNamespace`, `import pytest`, `from vibemix.midi import load_profile`, `from vibemix.midi.state import ControllerState`.
    3. `_BUNDLED_IDS` — same list as Task 1 (mirror, not re-derive — comment cross-refers to `test_profile_contracts.py`).
    4. SimpleNamespace factories — VERBATIM from `tests/midi/test_flx4_synthetic_decode.py:33-42`:
       ```python
       def _cc(channel, control, value):
           return SimpleNamespace(type="control_change", channel=channel, control=control, value=value)
       def _note_on(channel, note, velocity=127):
           return SimpleNamespace(type="note_on", channel=channel, note=note, velocity=velocity)
       ```
    5. Value helper:
       ```python
       def _value_for_axis(axis: str) -> int:
           # unipolar = 0-127 range, pick mid-high; bipolar = center-offset; boolean = on-state.
           return {"unipolar": 80, "bipolar": 90, "boolean": 127}.get(axis, 64)
       ```
    6. Single parametrized test function:
       ```python
       @pytest.mark.parametrize("profile_id", _BUNDLED_IDS)
       def test_profile_synthetic_midi_smoke(profile_id):
           profile = load_profile(profile_id)
           assert profile is not None, f"{profile_id}: load_profile returned None"
           cs = ControllerState(profile=profile)
           cs.mark_connected(profile.port_name_hints[0])  # mirror live binding path
           for binding in profile.controls.values():
               msg = _cc(binding.channel, binding.cc, _value_for_axis(binding.axis))
               cs.handle_msg(msg)  # MUST NOT raise — any raise fails the test
           for binding in profile.buttons.values():
               msg = _note_on(binding.channel, binding.note, velocity=127)
               cs.handle_msg(msg)
           events = cs.events_since(0.0)
           assert len(events) >= 1, f"{profile_id}: zero events surfaced — decode broken or all bindings dropped"
       ```
    7. NO additional fixtures, NO `conftest.py` changes. Self-contained.

    Notes on edge cases:
    - If `cs.mark_connected(...)` has a different signature than `(port_name: str)` in the actual `state.py`, adjust based on the read-first step. Per 68-RESEARCH §Sources state.py is 466 lines — the read should reveal the exact signature; do NOT guess. If it does not take a port name, use `cs.mark_connected()` no-arg.
    - If `ControllerState.handle_msg` requires the profile to already be set before any message is decoded (it does — `profile=` is passed at `__init__`), the constructor call above is sufficient.
    - If `axis` field name doesn't exist on a binding (e.g., `kind: "button"` only carries `note`), the value helper's default `64` survives and `_note_on` is the right shape — no failure.
  </action>
  <verify>
    <automated>uv run pytest tests/midi/test_profile_smokes.py -v 2&gt;&amp;1 | tee /tmp/68P02-T2.log | tail -30 &amp;&amp; grep -c PASSED /tmp/68P02-T2.log | awk '{exit ($1 == 10 ? 0 : 1)}'</automated>
  </verify>
  <acceptance_criteria>
    - `uv run pytest tests/midi/test_profile_smokes.py -v` exits 0 with exactly 10 PASSED rows.
    - `pytest tests/midi/test_profile_smokes.py --collect-only -q` lists 10 test IDs of the form `test_profile_synthetic_midi_smoke[<id>]`.
    - `grep -c "SimpleNamespace" tests/midi/test_profile_smokes.py` ≥ 1 (factory pattern lifted, not real `mido.Message`).
    - `grep -c "from vibemix.midi.state import ControllerState" tests/midi/test_profile_smokes.py` == 1.
    - `grep -c "MusicState" tests/midi/test_profile_smokes.py` == 0 OR ≥ 1 — both acceptable per 68-RESEARCH §Open Questions #2 (ControllerState-only is sufficient; MusicState integration is an optional extension if the planner judges needed).
    - `uv run pytest tests/midi/ -q` (full midi test directory) exits 0 — the new file does NOT regress any existing test.
    - File is ≥ 60 lines (including comments + spacing).
  </acceptance_criteria>
  <done>
    File exists, 10 smoke rows GREEN, every CC + NOTE binding exercised through `ControllerState.handle_msg` per profile without exceptions, ≥ 1 event surfaced per profile, no regression against existing tests/midi/ suite; DEV-01 (b) closed for all 10 bundled profiles.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Contributor JSON | A future contributor JSON authoring drift (wrong field name, duplicate cc, empty port_name_hints) MUST red CI before landing |
| Synthetic-vs-real-MIDI | The smoke tests use `SimpleNamespace` ducks; real `mido.Message` parity rides §V7-LIVE-10 (live FLX4 ear) — not v7.0 engineering scope |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-68P02-01 | Tampering | Contributor profile JSON | mitigate | Contract test rejects empty `port_name_hints`, duplicate `(channel, cc)`, duplicate `(channel, note)`; `_parse_profile` raises ValueError on missing required fields. |
| T-68P02-02 | Disclosure | Test failure messages | accept | Failure messages include `profile_id` for fast diagnosis — no PII; controller IDs are public catalog names. |
| T-68P02-03 | DoS | Test runtime cost | accept | 10 parametrized rows × ~50 bindings each = ~500 in-process operations; well under 1 second total. No I/O, no network. |
| T-68P02-SC | Tampering | npm/pip/cargo installs | accept | Plan installs no packages. All deps (`pytest`, `mido` for type-shape only, `pytest-mock` not needed) already in `uv.lock`. |
</threat_model>

<verification>
- `uv run pytest tests/midi/test_profile_contracts.py -v` — 10 GREEN rows.
- `uv run pytest tests/midi/test_profile_smokes.py -v` — 10 GREEN rows.
- `uv run pytest tests/midi/ -q` — full midi suite GREEN; new tests do not regress `test_profiles_all_controllers.py`, `test_flx4_synthetic_decode.py`, `test_profile.py`, etc.
- `uv run pytest -q` (full default grid) — within ±20 of the post-Wave-0 baseline (new GREEN rows added, no losses).
</verification>

<success_criteria>
DEV-01 closed for all 10 bundled profiles (ROADMAP P68 SC#1):
- Each profile has a schema-valid contract test → `test_profile_contracts.py` (Task 1).
- Each profile has a synthetic-MIDI smoke through `find_mapping` + `ControllerState` + `state.MusicState` chain → `test_profile_smokes.py` (Task 2; ControllerState-only assertion per 68-RESEARCH Assumption A5).
- Each profile JSON declares non-empty `port_name_hints` (plural list) — pinned by Task 1's contract test.
</success_criteria>

<output>
Create `.planning/phases/68-all-devices-ready/68-02-SUMMARY.md` when done. Summary MUST record:
- Pytest output proving 10 GREEN rows per test file.
- Total new test count delta vs Wave-0 baseline (expect +20).
- Whether the smoke test extended into MusicState integration (per 68-RESEARCH Open Question #2) or stayed at ControllerState-only (Assumption A5 default).
- Any binding shape surprise discovered while reading the profiles (e.g., empty `buttons` dict in any profile, unusual `axis` values like `wheel` or `infinite`) — flag for Wave 3's contributor recipe.
</output>
