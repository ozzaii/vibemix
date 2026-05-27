# Phase 68: All Devices Ready — Research

**Researched:** 2026-05-23
**Domain:** MIDI controller catalog reconciliation · contract / smoke / hot-plug / audio-backend test surfaces · contributor recipe
**Confidence:** HIGH

## Summary

Phase 68 is a **reconciliation + wiring + test-discharge** phase, not a feature phase. Every artifact this phase produces is grounded in code that already ships: `profile.py`'s hand-rolled validator IS the schema check, `state.py::ControllerState.handle_msg` IS the synthetic-MIDI smoke surface, `_midi_common.handle_port_change_single_state` + `state.py::mark_disconnected` IS the hot-plug path closed in v4.0 P53, and `blackhole_probe._query_devices` IS the audio-backend mock seam already proven by `tests/install/test_blackhole_probe.py`. The phase reads as: *port_name_hint(s) audit → contract test (parametrize across the 10) → synthetic smoke (mido-shaped `SimpleNamespace`) → 3-profile hot-plug (compose existing tests) → audio matrix (mock `sounddevice.query_devices` + `pyaudiowpatch`) → contributor recipe doc + ship-existing `scripts/sniff_controller.py`-style helper → atomic catalog reconciliation*.

Two CONTEXT.md claims that DO NOT match the on-disk reality and must be corrected before planning starts:

1. **Field name:** CONTEXT calls it `port_name_hint`. The actual schema field, accepted by `profile.py::_parse_profile` and present in ALL 10 `profiles/*.json`, is **`port_name_hints` (plural, non-empty list)**. The audit / contract test must assert `port_name_hints`, not invent a new singular field. `schema.json` (which lives in `src/vibemix/midi/` for the LEGACY `MidiMapLoader` registry) does NOT have to be touched — `profile.py` IS the canonical validator.
2. **The two catalogs are NOT just different IDs — they are DIFFERENT SCHEMAS.** `controllers/*.json` uses the legacy `{vendor, model, description, verified, controls{...}}` shape with flat cc+note mixed dict; `profiles/*.json` uses `{id, display_name, port_name_hints, decks, controls{}, buttons{}, notes?}` with separated cc / note maps and typed `kind`/`axis`/`field`. A "merge" of the two overlapping FLX4 / DDJ-400 files is meaningless because they encode different ontologies. The reconciliation is **delete controllers/, delete map_loader.py (and its test), then update every README / a11y / KAAN-ACTION reference that points at `controllers/`** — there is nothing to port in.

**Primary recommendation:** Take `profiles/` as canonical (already true at runtime). Delete `controllers/` + `map_loader.py` + `tests/midi/test_map_loader.py` + `tests/midi/test_live_binding_profiles_canonical.py` (the gate becomes vacuous after the dead catalog is gone). Update every doc / a11y script / README controller grid to the actual 10 bundled IDs in `profiles/`. New artifacts: `tests/midi/test_profile_contracts.py` (10-row parametrize), `tests/midi/test_profile_smokes.py` (10-row CC + NOTE exercise), `tests/integration/test_hotplug_matrix.py` (FLX4 + 400 + Inpulse-500 reusing `handle_port_change_single_state`), `tests/integration/test_audio_backends.py` (mock `sounddevice.query_devices` + `pyaudiowpatch.PyAudio`), `docs/contributing/add-a-controller.md`, `docs/contributing/midi-catalog.md`, `scripts/discover_midi_port.py`.

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Canonical catalog: `profiles/`** — the winner. `controllers/` (which hosts an additional 8 non-bundled profiles + 2 overlaps with `profiles/`) is deleted after migration.
- **Schema is `src/vibemix/midi/profile.py`'s hand-rolled `_parse_profile`** — `schema.json` (which validates the dead `controllers/` schema) is OUT of the canonical path. Extend `profile.py` ONLY if a new field (e.g., a stricter `port_name_hint` audit) is required; otherwise leave alone.
- **Every `profiles/*.json` MUST already validate against `_parse_profile`** (they do — `test_profiles_all_controllers.py` already pins this). Validation library: NO new dep — `jsonschema>=4.23` IS already in pyproject.toml (line 90), but the active live-binding path uses `profile.py`'s hand-roller, NOT `jsonschema`. Contract test should call `load_profile(id)` and assert non-None — no `jsonschema.validate` needed.
- **Contract test:** `tests/midi/test_profile_contracts.py` — parametrized over the 10 bundled IDs (this set already exists at `tests/midi/test_profiles_all_controllers.py::_ALL_CONTROLLER_IDS`). Each test loads JSON via `map_loader` — **CORRECTION: via `load_profile()` from `vibemix.midi.profile`**, validates by construction success, asserts non-empty `port_name_hints`, asserts every `cc`/`note` referenced exactly once.
- **Synthetic-MIDI smoke:** `tests/midi/test_profile_smokes.py` — generate `mido.Message` (use `SimpleNamespace` per the established `test_flx4_synthetic_decode.py` pattern), push through `find_mapping` → `ControllerState.handle_msg` → `MusicState`. No real device required.
- **Hot-plug matrix:** `tests/integration/test_hotplug_matrix.py` marked `@pytest.mark.integration`. 3 profiles: FLX4 · DDJ-400 · Inpulse-500. Reuse the v4.0 P53 `handle_port_change_single_state` callback (proven by `tests/midi/test_disconnect_reconnect.py`); the path stays **UNTOUCHED**.
- **Audio backend matrix:** `tests/integration/test_audio_backends.py` marked `@pytest.mark.integration`. macOS BlackHole 2ch + 16ch + Windows WASAPI loopback + edge no-loopback fallback. Mock via `monkeypatch.setattr(sounddevice, "query_devices", ...)` + `sys.modules["pyaudiowpatch"] = MagicMock()` — both patterns already shipped.
- **Contributor recipe:** `docs/contributing/add-a-controller.md` ≤ 200 lines. Step 1 = discover port via `scripts/discover_midi_port.py`, Step 2 = copy `_template.json` (NEW under `profiles/`), Step 3 = add ID to parametrize list in both new contract / smoke test files, Step 4 = `uv run pytest tests/midi/ -q` GREEN + PR.
- **`scripts/discover_midi_port.py`** — ≤ 30 lines, uses `mido.get_input_names()` printer, cross-platform. NOTE: precedent already exists at `scripts/sniff_controller.py` (226 lines, fuller-featured JSONL sniffer). The new helper is a STRIPPED-DOWN port-name lister meant for the recipe Step 1 — they coexist.
- **Smoke discharge to `KAAN-ACTION-LEGAL.md §V7-LIVE-07`** under `gsd-autonomous fully` — the engineering side ships when recipe + template + helper land; the <30-min live smoke is the Kaan-ear discharge clock.

### Claude's Discretion

- Exact test filenames (lock `test_profile_contracts.py` per success criterion text).
- Synthetic-MIDI fixture shape — pick `SimpleNamespace(type=..., channel=..., control=..., value=...)` (matches `test_flx4_synthetic_decode.py::_cc / _note_on / _note_off` exactly).
- Schema-validator library choice — **DO NOT use `jsonschema` for `profiles/*.json`**; the canonical validator is `profile.py::_parse_profile`. Use it via `load_profile(id)`.
- `_template.json` location — recommend **`src/vibemix/midi/profiles/_template.json`** (the `_` prefix excludes it from `list_profiles()` because `_template` won't match `find_mapping` substring on any real port name; `_parse_profile` will raise on it if loaded, which is fine — it is never loaded by glob). Alternative: `docs/contributing/template.json` as a copy-target. The in-profiles location is cleaner; gating issue is `list_profiles()` iterates the dir — verify `_template.json` is excluded (it WILL be discovered because the filter is `.endswith(".json")`, not "starts with `_`"). **Conclusion: ship the template at `docs/contributing/_template.json` to avoid loader pollution.** Alternative: extend `list_profiles()` to skip leading-underscore stems.

### Deferred Ideas (OUT OF SCOPE)

- Contract tests for the 8 non-bundled controllers under `controllers/` (Mixtrack-Pro-FX, Mixtrack-Platinum-FX, Kontrol-S2, Kontrol-S4, MC-6000, MC-7000, DDJ-200, DDJ-Rev1) — defer to a future polish phase. These files are DELETED from the repo in P68 (their content lives in git history).
- Live audio capture parity tests (real BlackHole + real WASAPI) — §V7-LIVE-08/09 Kaan-clock items.
- Controller-specific feature flags (e.g., XDJ-RX3 screen output) — defer.
- Multi-controller simultaneous mode — defer.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEV-01 | 10 bundled MIDI profiles each have (a) schema-valid contract test, (b) synthetic-MIDI smoke through `find_mapping`+`ControllerState`+`MusicState`, (c) non-empty `port_name_hint(s)`. | `## Standard Stack` (already-shipped `load_profile` + `ControllerState`) + `## Code Examples` (synthetic-MIDI factory pattern from `test_flx4_synthetic_decode.py`) + `## Runtime State Inventory` row 1 (no stored data — pure JSON catalog) |
| DEV-02 | Duplicate `controllers/` ↔ `profiles/` catalogs reconciled to single source of truth — one canonical dir, one schema, one loader, with migration note. | `## Common Pitfalls` (the catalogs are DIFFERENT schemas, not just different IDs — merge is delete-and-update-references) + `## Runtime State Inventory` rows 2-5 (README grid · a11y script · KAAN-ACTION refs · `test_readme_shape.py::REQUIRED_CONTROLLERS` · `docs/midi-mapping.md` schema-shape drift) |
| DEV-03 | Hot-plug verified across ≥3 distinct profiles via `test_hotplug_matrix.py`; v4.0 P53 `start_port_watcher` + `mark_disconnected` + single-state callback survives untouched. | `## Code Examples` (`tests/midi/test_disconnect_reconnect.py` is the template — extend to 3 profiles via parametrize) |
| DEV-04 | Audio backend matrix (BlackHole 2ch/16ch · WASAPI loopback + edge no-loopback fallback) covered with mocked CoreAudio + WASAPI. | `## Code Examples` (`tests/install/test_blackhole_probe.py` shows the `sd.query_devices` monkeypatch; `tests/test_audio_windows.py` shows the `sys.modules["pyaudiowpatch"] = MagicMock()` injection) |
| DEV-05 | `docs/contributing/add-a-controller.md` recipe with template JSON, 4-step pattern, `scripts/discover_midi_port.py` helper, PR checklist. End-to-end smoke (Kaan or DJ adds 1 profile <30 min). | `## Code Examples` (existing `scripts/sniff_controller.py` precedent, 226 lines — the new helper is the stripped-down recipe entry; coexists) + `## State of the Art` (mido cross-platform port enumeration) |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Profile catalog (JSON files) | Source tree (`src/vibemix/midi/profiles/`) | — | Static data; loaded via `importlib.resources` at runtime |
| Profile schema validation | Python lib (`vibemix.midi.profile::_parse_profile`) | — | Hand-rolled validator (no pydantic — Phase 6 ban); raises ValueError on drift |
| Live MIDI decode | Python lib (`vibemix.midi.state::ControllerState`) | — | Profile-parameterized lookup tables; thread-safe via `threading.Lock` |
| Hot-plug detection | Python lib (`vibemix.midi.watcher::port_watcher_task`) | — | Async polling loop (2s default); emits `('connected', ...) / ('disconnected', ...)` |
| Hot-plug state mutation | Python lib (`vibemix.platform._midi_common::handle_port_change_single_state`) | — | Single-state callback; mutates existing ControllerState in place |
| Audio device enumeration (macOS) | Python lib (`vibemix.install.blackhole_probe::_query_devices`) | OS (CoreAudio via sounddevice/PortAudio) | Probe-only; never opens a stream |
| Audio device enumeration (Windows) | Python lib (`vibemix.platform._audio_windows::assert_wasapi_loopback_rate`) | OS (WASAPI via pyaudiowpatch) | Pre-open guard; raises on rate mismatch |
| Contract / smoke tests | pytest test layer (`tests/midi/`, `tests/integration/`) | — | Pure assertion layer; never opens hardware |
| Contributor recipe | Documentation tier (`docs/contributing/add-a-controller.md`) + Tools tier (`scripts/discover_midi_port.py`) | — | No runtime code path |

## Standard Stack

### Core (ALREADY SHIPPED — Phase 68 does NOT install new deps)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pytest` | `>=8.0` (dev) | Test runner | Project-wide; `pytest.mark.parametrize` shipped in 67P02 + every existing midi test |
| `pytest-mock` | `>=3.15.1` (dev) | `mocker` fixture for `mocker.patch` | Already used in `tests/midi/test_watcher.py` |
| `mido` | `>=1.3.3` | MIDI port enumeration + message type | `mido.get_input_names()` is the cross-platform discovery API; `mido.Message` is the canonical message shape (we mock-it with `SimpleNamespace`) |
| `sounddevice` | `>=0.5.5` | CoreAudio device enumeration on macOS | `sd.query_devices()` returns list of dicts with `name` + `max_input_channels` |
| `pyaudiowpatch` | `>=0.2.12 ; sys_platform == 'win32'` | WASAPI loopback | `PyAudio().get_default_wasapi_loopback_device()` returns dict with `name` + `index` + `defaultSampleRate` |
| `jsonschema` | `>=4.23,<5` | (NOT USED by P68 contract test — `profiles/*.json` validates via `profile.py::_parse_profile`, not jsonschema) | Already in pyproject.toml for `ipc.*` validation; available if we need it. v7.0 zero-new-dep rule held. |

**No new deps.** Verified by reading `pyproject.toml` lines 28-119 + `uv.lock` (jsonschema 4.26.0, pytest-mock 3.15.1+, mido 1.3.3+ all locked). [VERIFIED: pyproject.toml + uv.lock]

### Supporting (test-helper patterns)

| Library / Pattern | Purpose | When to Use |
|-------------------|---------|-------------|
| `unittest.mock.MagicMock` + `sys.modules` injection | Mock platform-gated modules (`pyaudiowpatch` on macOS dev box) | Audio backend WASAPI test on a macOS CI runner |
| `monkeypatch.setattr(sd, "query_devices", ...)` | Stub `sounddevice.query_devices` return | Audio backend macOS test (BlackHole 2ch / 16ch / absent) |
| `types.SimpleNamespace` | mock `mido.Message` shape (only needs `.type`, `.channel`, `.control` / `.note`, `.value` / `.velocity`) | Synthetic-MIDI smoke per `test_flx4_synthetic_decode.py::_cc`, `_note_on`, `_note_off` |
| `@pytest.mark.parametrize("profile_id", _BUNDLED_IDS)` | Parametrize over the 10 bundled IDs | Contract test + smoke test |
| `@pytest.mark.integration` | Mark integration tests | hot-plug matrix + audio backend matrix (already declared in `pyproject.toml` line 202) |

### Installation

**ZERO new dependencies.** Phase 68 hard-locked at no new deps by v7.0 acid test (REQUIREMENTS.md "v7.0 net-new dependencies = 0"). Every test pattern reuses shipped libraries.

```bash
# No `uv add` / `pip install` invocations in this phase.
# Verification:
git diff pyproject.toml  # MUST be empty for the dependency / dependency-group / pytest sections
git diff uv.lock         # MUST be empty
```

## Package Legitimacy Audit

> Skipped — no packages are installed in this phase. All dependencies (`pytest`, `pytest-mock`, `mido`, `sounddevice`, `pyaudiowpatch`, `jsonschema`) are already in `pyproject.toml` + `uv.lock` and were vetted in prior milestones (Phase 9 / 11 / 27 / 33 / 40). [VERIFIED: pyproject.toml + uv.lock]

## Architecture Patterns

### System Architecture Diagram

```
                            ┌───────────────────────────────┐
                            │  src/vibemix/midi/profiles/   │
   profile JSON files  ───▶ │  *.json (10 bundled + maybe   │
   (static catalog)         │   _template.json contributor) │
                            └───────────┬───────────────────┘
                                        │  importlib.resources
                                        ▼
                            ┌───────────────────────────────┐
                            │  vibemix.midi.profile         │
                            │  ──────────────────────────── │
                            │  _parse_profile()  ◀ canonical │  hand-rolled validator
                            │  load_profile()    schema      │  raises ValueError on drift
                            │  list_profiles()                │
                            └───────────┬───────────────────┘
                                        │
                ┌───────────────────────┼────────────────────────┐
                ▼                       ▼                        ▼
       ┌─────────────────┐   ┌──────────────────┐   ┌──────────────────────┐
       │ vibemix.midi.   │   │ vibemix.midi.    │   │ tests/midi/          │
       │ registry        │   │ state            │   │ test_profile_        │
       │ ─────────────── │   │ ──────────────── │   │ contracts.py  (NEW)  │
       │ find_mapping()  │   │ ControllerState  │   │ test_profile_        │
       │ find_mapping_   │   │ .handle_msg()    │   │ smokes.py     (NEW)  │
       │   or_generic()  │   │ .deck_snapshot() │   └──────────────────────┘
       └────────┬────────┘   │ .mark_connected  │
                │            │ .mark_disconnect │
                ▼            │ .events_since    │
       ┌─────────────────┐   └─────────┬────────┘
       │ vibemix.midi.   │             │
       │ watcher         │             │
       │ ──────────────  │             │
       │ port_watcher_   │             │
       │  task()         │             │
       │ (poll mido @2s) │             │
       └────────┬────────┘             │
                │                      │
                ▼                      │
       ┌──────────────────────────────┐│
       │ vibemix.platform._midi_      ││  load-bearing path
       │ common.handle_port_change_   │◀─  closed in v4.0 P53
       │ single_state()               │   STAYS UNTOUCHED
       │ ──────────────────────────── │
       │ ('connected', port, profile) │
       │ ('disconnected', port)       │
       └──────┬───────────────────────┘
              │
              ▼
   ┌─────────────────────────────────┐
   │ tests/integration/              │
   │ test_hotplug_matrix.py  (NEW)   │  3 profiles via parametrize
   │ ─────────────────────────────── │  FLX4 · DDJ-400 · Inpulse-500
   │ Reuses ListenerHolder +         │
   │ handle_port_change_single_state │
   │ from test_disconnect_reconnect  │
   └─────────────────────────────────┘

                                      ┌──────────────────────────────────┐
   sounddevice.query_devices() ─────▶ │ vibemix.install.blackhole_probe  │
   pyaudiowpatch.PyAudio()    ──────▶ │ vibemix.platform._audio_windows  │
                                      └────────────┬─────────────────────┘
                                                   │
                                                   ▼
                                      ┌──────────────────────────────────┐
                                      │ tests/integration/               │
                                      │ test_audio_backends.py  (NEW)    │
                                      │ ──────────────────────────────── │
                                      │ Mock sd.query_devices →          │
                                      │   BlackHole 2ch  / 16ch / absent │
                                      │ Mock pyaudiowpatch.PyAudio →     │
                                      │   loopback present / absent      │
                                      └──────────────────────────────────┘

   Contributor recipe path (Tools tier):
   ┌──────────────────────────┐
   │ scripts/discover_midi_   │  ≤30 lines · mido.get_input_names()
   │ port.py            (NEW) │
   └──────────────┬───────────┘
                  │
                  ▼  (informs)
   ┌──────────────────────────┐
   │ docs/contributing/       │  Step 1 (discover) → 2 (copy template)
   │ add-a-controller.md      │  → 3 (add to parametrize) → 4 (pytest green + PR)
   │                  (NEW)   │
   └──────────────────────────┘
   ┌──────────────────────────┐
   │ docs/contributing/       │  migration note · 1 paragraph
   │ midi-catalog.md  (NEW)   │  "why profiles/ won, what was deleted"
   └──────────────────────────┘
   ┌──────────────────────────┐
   │ docs/contributing/       │  copy-target — clean profile shape
   │ _template.json   (NEW)   │  with placeholder vendor/model/hints
   └──────────────────────────┘
```

### Recommended Project Structure (target state after P68)

```
src/vibemix/midi/
├── __init__.py                  # unchanged (re-exports load_profile/find_mapping/etc.)
├── profile.py                   # unchanged (canonical validator)
├── registry.py                  # unchanged (find_mapping / find_mapping_or_generic)
├── state.py                     # unchanged (ControllerState, MidiEvent)
├── watcher.py                   # unchanged (port_watcher_task)
├── generic.py                   # unchanged (GENERIC_MIDI_ID, make_generic_profile)
├── profiles/                    # CANONICAL · 10 JSONs + __init__.py
│   ├── __init__.py
│   ├── hercules_inpulse_300.json
│   ├── hercules_inpulse_500.json
│   ├── numark_party_mix_live.json
│   ├── pioneer_ddj_400.json
│   ├── pioneer_ddj_1000.json
│   ├── pioneer_ddj_flx4.json
│   ├── pioneer_ddj_flx6.json
│   ├── pioneer_ddj_flx10.json
│   ├── pioneer_ddj_sx3.json
│   └── pioneer_xdj_rx3.json
├── controllers/                 # ⊘ DELETED (was the orphan MidiMapLoader catalog)
├── map_loader.py                # ⊘ DELETED (was the orphan; no live consumer per the gate)
└── schema.json                  # ⊘ DELETED (was only consumed by map_loader.py)

tests/midi/
├── test_profile_contracts.py    # NEW · 10-row parametrize · contract
├── test_profile_smokes.py       # NEW · 10-row parametrize · synthetic-MIDI smoke
├── test_profiles_all_controllers.py  # unchanged (existing golden — complementary)
├── test_flx4_synthetic_decode.py     # unchanged
├── test_profile_flx4_golden.py       # unchanged
├── test_profile.py                   # unchanged
├── test_registry.py                  # unchanged
├── test_state.py                     # unchanged
├── test_watcher.py                   # unchanged
├── test_watcher_callback_integration.py  # unchanged
├── test_disconnect_reconnect.py      # unchanged (reused as integration template)
├── test_generic_fallback.py          # unchanged
├── test_live_binding_profiles_canonical.py  # ⊘ DELETED (vacuous after controllers/ + map_loader.py gone)
├── test_map_loader.py                # ⊘ DELETED (gates a deleted module)
└── test_sniff_controller.py          # unchanged (gates scripts/sniff_controller.py)

tests/integration/
└── test_hotplug_matrix.py       # NEW · marker integration · 3 profiles (FLX4 · 400 · Inpulse-500)
└── test_audio_backends.py       # NEW · marker integration · macOS BlackHole + Win WASAPI + edges

scripts/
├── discover_midi_port.py        # NEW · ≤30 lines · mido.get_input_names() lister
└── sniff_controller.py          # unchanged (heavier JSONL sniffer — coexists, different scope)

docs/contributing/                # NEW directory
├── add-a-controller.md          # NEW · ≤200 lines · 4-step recipe + PR checklist
├── midi-catalog.md              # NEW · 1-paragraph migration note
└── _template.json               # NEW · clean controller profile copy-target

docs/midi-mapping.md             # PATCHED · current "slug/port_name_substr/deck_a" schema is stale; rewrite to match profile.py shape
docs/midi-controllers.md         # PATCHED · table already matches profiles/ — minor cleanup

README.md                        # PATCHED · "Supported controllers" 10-cell table reshaped to the actual profiles/ set
                                 # (was DDJ-200 · 400 · FLX4 · REV1 · Kontrol-S2 · S4 · MC-6000 · MC-7000 · Mixtrack Platinum-FX · Mixtrack Pro-FX
                                 #  becomes  FLX4 · FLX6 · FLX10 · 400 · 1000 · SX3 · XDJ-RX3 · Numark Party Mix Live · Inpulse-300 · Inpulse-500)
docs/assets/controllers/         # PATCHED · 10 SVG placeholders rekeyed to profile slugs (asset paths in README + grid script)
tests/repo/test_readme_shape.py  # PATCHED · REQUIRED_CONTROLLERS list updated to the actual 10
scripts/launch/check_readme_grids_a11y.py  # PATCHED · update reference to profiles/ (the comment says "src/vibemix/midi/controllers/*.json")
KAAN-ACTION-LEGAL.md             # PATCHED · §LAUNCH-04 references rekeyed (controllers/ → profiles/)
```

### Pattern 1: 10-row parametrized contract test

**What:** Single test function, parametrized over the 10 bundled profile IDs. Each parametrize row calls `load_profile(id)`, asserts non-None + non-empty `port_name_hints` + every binding referenced exactly once.

**When to use:** DEV-01 (a) — schema-valid contract test. Each row gives one named `test_<id>_loads_and_validates[<id>]` case in `pytest -v`.

**Example:**

```python
# Source: pattern lifted from tests/midi/test_profiles_all_controllers.py
# (which already parametrizes over _ALL_CONTROLLER_IDS — Phase 68 adds a tighter contract on top)
import pytest
from vibemix.midi import load_profile

_BUNDLED_IDS = [
    "hercules_inpulse_300",
    "hercules_inpulse_500",
    "numark_party_mix_live",
    "pioneer_ddj_1000",
    "pioneer_ddj_400",
    "pioneer_ddj_flx10",
    "pioneer_ddj_flx4",
    "pioneer_ddj_flx6",
    "pioneer_ddj_sx3",
    "pioneer_xdj_rx3",
]

@pytest.mark.parametrize("profile_id", _BUNDLED_IDS)
def test_profile_loads_and_validates(profile_id):
    profile = load_profile(profile_id)
    assert profile is not None
    # port_name_hints: tuple of non-empty str, length ≥ 1
    assert isinstance(profile.port_name_hints, tuple) and len(profile.port_name_hints) >= 1
    for hint in profile.port_name_hints:
        assert isinstance(hint, str) and hint
    # No duplicate (channel, cc) or (channel, note) within a profile
    cc_keys = [(b.channel, b.cc) for b in profile.controls.values()]
    note_keys = [(b.channel, b.note) for b in profile.buttons.values()]
    assert len(cc_keys) == len(set(cc_keys)), f"duplicate cc in {profile_id}"
    assert len(note_keys) == len(set(note_keys)), f"duplicate note in {profile_id}"
```

### Pattern 2: 10-row synthetic-MIDI smoke test

**What:** Parametrize over the 10 IDs. Per profile, generate one `SimpleNamespace` MIDI message per CC + NOTE binding; push each through a `ControllerState(profile=...)` instance; assert no exceptions + every binding fires its expected handler.

**When to use:** DEV-01 (b) — exercises `find_mapping` → `ControllerState` → `MusicState` (or directly `ControllerState.handle_msg`). MusicState integration optional; ControllerState handle_msg is the canonical decode boundary.

**Example:**

```python
# Source: factory pattern lifted verbatim from tests/midi/test_flx4_synthetic_decode.py
from types import SimpleNamespace
import pytest
from vibemix.midi import load_profile
from vibemix.midi.state import ControllerState

def _cc(channel, control, value):
    return SimpleNamespace(type="control_change", channel=channel, control=control, value=value)

def _note_on(channel, note, velocity=127):
    return SimpleNamespace(type="note_on", channel=channel, note=note, velocity=velocity)

@pytest.mark.parametrize("profile_id", _BUNDLED_IDS)
def test_profile_synthetic_midi_smoke(profile_id):
    profile = load_profile(profile_id)
    cs = ControllerState(profile=profile)

    # Hit every CC binding — record the event count before/after.
    before = len(cs.events_since(0.0))
    for binding in profile.controls.values():
        cs.handle_msg(_cc(binding.channel, binding.cc, 80 if binding.axis == "unipolar" else 90))
    # Hit every NOTE binding.
    for binding in profile.buttons.values():
        cs.handle_msg(_note_on(binding.channel, binding.note, velocity=127))

    after_events = cs.events_since(0.0)
    # At least one event per binding (some buttons like jog_touch may not all emit,
    # but the assertion is "no crash + at least one event surface").
    assert len(after_events) > before, f"{profile_id}: no events surfaced — decode broken"
```

### Pattern 3: Hot-plug matrix (3 profiles)

**What:** Parametrize the existing `tests/midi/test_disconnect_reconnect.py` pattern across FLX4 + 400 + Inpulse-500. Drive the production `handle_port_change_single_state` callback through connected → disconnected → connected; assert state preservation per profile.

**When to use:** DEV-03. The path under test is the v4.0 P53 single-state callback — **DO NOT modify it**; the test must read-only against the production function.

**Example:**

```python
# Source: tests/midi/test_disconnect_reconnect.py (parametrized over 3 profiles)
from types import SimpleNamespace
import pytest
from vibemix.midi import load_profile
from vibemix.midi.state import ControllerState
from vibemix.platform import _midi_common
from vibemix.platform._midi_common import ListenerHolder, handle_port_change_single_state

_PROFILES = [
    ("pioneer_ddj_flx4", "DDJ-FLX4 USB MIDI", (0, 19, 110)),   # vol_a
    ("pioneer_ddj_400",  "DDJ-400",            (0, 19, 100)),   # vol_a
    ("hercules_inpulse_500", "DJControl Inpulse 500", (0, 15, 90)),  # eq_low_a or similar
]

class _DummyThread:
    def join(self, timeout=None): pass

def _holder(profile, port_name):
    cs = ControllerState(profile=profile)
    fake_mido = SimpleNamespace(
        get_input_names=lambda: [port_name],
        open_input=lambda name: SimpleNamespace(__enter__=lambda s: s, __exit__=lambda *a: False, poll=lambda: None),
    )
    return ListenerHolder(controller_state=cs, listener_thread=None, listener_stop=None, mido_module=fake_mido)

@pytest.mark.integration
@pytest.mark.parametrize("profile_id,port_name,sample_cc", _PROFILES)
def test_hotplug_preserves_state_across_three_profiles(monkeypatch, profile_id, port_name, sample_cc):
    monkeypatch.setattr(_midi_common, "spawn_listener", lambda *a, **k: _DummyThread())
    profile = load_profile(profile_id)
    holder = _holder(profile, port_name)
    orig_id = id(holder.controller_state)

    handle_port_change_single_state(holder, ("connected", port_name, profile))
    holder.controller_state.handle_msg(SimpleNamespace(
        type="control_change", channel=sample_cc[0], control=sample_cc[1], value=sample_cc[2]))
    assert holder.controller_state.moves_since(0.0)

    handle_port_change_single_state(holder, ("disconnected", port_name))
    assert holder.controller_state.is_connected() is False
    assert holder.controller_state.moves_since(0.0) == []  # ring cleared by mark_disconnected
    assert id(holder.controller_state) == orig_id  # NOT rebuilt — single-state invariant

    handle_port_change_single_state(holder, ("connected", port_name, profile))
    assert holder.controller_state.is_connected() is True
    assert id(holder.controller_state) == orig_id
```

### Pattern 4: Audio backend mock (macOS + Windows + edge)

**What:** Use `monkeypatch.setattr` for `sounddevice.query_devices` (macOS); inject `MagicMock` into `sys.modules["pyaudiowpatch"]` BEFORE importing the audio-windows module (Windows-on-mac CI). Both patterns are ALREADY shipped in the test tree.

**When to use:** DEV-04.

**Example (macOS BlackHole 2ch + 16ch + absent):**

```python
# Source: tests/install/test_blackhole_probe.py verbatim
import pytest
from vibemix.install import blackhole_probe

def _patch_devices(monkeypatch, devices):
    import sounddevice as sd
    def _fake_query(idx=None):
        return devices if idx is None else (devices[idx] if 0 <= idx < len(devices) else {})
    monkeypatch.setattr(sd, "query_devices", _fake_query)

@pytest.mark.integration
def test_audio_backend_blackhole_2ch_present(monkeypatch):
    _patch_devices(monkeypatch, [{"name": "BlackHole 2ch", "max_output_channels": 2}])
    result = blackhole_probe.probe_blackhole(retry_on_missing=False)
    assert result == {"installed": True, "device_name": "BlackHole 2ch"}

@pytest.mark.integration
def test_audio_backend_blackhole_16ch_present(monkeypatch):
    _patch_devices(monkeypatch, [{"name": "BlackHole 16ch", "max_output_channels": 16}])
    result = blackhole_probe.probe_blackhole(retry_on_missing=False)
    assert result["installed"] is True
    assert result["device_name"] == "BlackHole 16ch"

@pytest.mark.integration
def test_audio_backend_no_loopback_driver_fallback(monkeypatch):
    """Edge: no loopback driver — graceful absent return (NOT a crash)."""
    _patch_devices(monkeypatch, [{"name": "Built-in Output"}, {"name": "AirPods"}])
    result = blackhole_probe.probe_blackhole(retry_on_missing=False)
    assert result == {"installed": False, "device_name": None}  # graceful
```

**Example (Windows WASAPI loopback):**

```python
# Source: tests/test_audio_windows.py::_make_fake_pa pattern
import sys
from unittest.mock import MagicMock
import pytest

@pytest.mark.integration
def test_audio_backend_wasapi_loopback_found(monkeypatch):
    # Inject mock pyaudiowpatch BEFORE _audio_windows imports it lazily.
    fake_pa_mod = MagicMock()
    fake_instance = MagicMock()
    fake_instance.get_default_wasapi_loopback_device.return_value = {
        "name": "Speakers (Realtek) [Loopback]",
        "index": 7,
        "defaultSampleRate": 48000.0,
    }
    fake_pa_mod.PyAudio.return_value = fake_instance
    monkeypatch.setitem(sys.modules, "pyaudiowpatch", fake_pa_mod)

    from vibemix.platform._audio_windows import assert_wasapi_loopback_rate
    index, name = assert_wasapi_loopback_rate(expected=48000)
    assert index == 7
    assert "Loopback" in name
```

### Pattern 5: Minimal `scripts/discover_midi_port.py`

**What:** ≤30-line standalone script. Uses `mido.get_input_names()`; prints attached MIDI port names cross-platform.

**When to use:** DEV-05 Step 1.

**Example (template — pseudocode-level):**

```python
#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Discover attached MIDI input port names — Step 1 of add-a-controller.md.

Usage:
    python3 scripts/discover_midi_port.py

Prints one port name per line, sorted. Exits 0 with a hint if no ports found.
No imports from src/vibemix/ — runs with just `pip install mido python-rtmidi`.
"""
from __future__ import annotations
import sys

def main() -> int:
    try:
        import mido  # noqa
    except ImportError:
        print("mido not installed. Run: pip install mido python-rtmidi", file=sys.stderr)
        return 2
    names = sorted(mido.get_input_names())
    if not names:
        print("No MIDI input ports detected. Connect your controller via USB and re-run.", file=sys.stderr)
        return 1
    print("Attached MIDI input ports:")
    for n in names:
        print(f"  - {n}")
    print("\nCopy the substring that uniquely identifies your controller into the")
    print("'port_name_hints' field of your new profile JSON.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

### Anti-Patterns to Avoid

- **DO NOT use `jsonschema.validate(profile_json, schema.json)`** as the contract test. `schema.json` validates the LEGACY `controllers/` schema and is also slated for deletion. The canonical validator is `profile.py::_parse_profile` (called via `load_profile`).
- **DO NOT add `jsonschema` calls to the test surface** — it forces a dep already-installed but adds noise; `load_profile()` raises ValueError on schema drift already.
- **DO NOT rebuild the v4.0 P53 hot-plug callback.** The test must read-only against `handle_port_change_single_state` — only `tests/integration/test_hotplug_matrix.py` is created; `src/vibemix/platform/_midi_common.py` is NEVER edited.
- **DO NOT include `_template.json` in the runtime profile loader path** without verifying `list_profiles()` filters it. The current filter is `entry.name.endswith(".json")` — leading underscore is NOT excluded. Safer: place `_template.json` under `docs/contributing/`, not `src/vibemix/midi/profiles/`.
- **DO NOT delete `tests/midi/test_live_binding_profiles_canonical.py` and `tests/midi/test_map_loader.py` silently** — flag them in the migration note in `docs/contributing/midi-catalog.md` so future archaeology is straightforward.
- **DO NOT extend the field name to `port_name_hint` (singular)** in `profiles/*.json` — that breaks every existing test that reads `profile.port_name_hints`. Use the existing plural `port_name_hints` everywhere; the CONTEXT.md singular reference is a copy-edit drift.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Profile schema validation | Custom jsonschema doc + jsonschema.validate calls | `vibemix.midi.profile::_parse_profile` (called by `load_profile`) | Hand-rolled validator is the project convention (no pydantic — Phase 6 ban). Already covers every field + raises ValueError with profile name. |
| Mock `mido.Message` | Real mido fixture | `types.SimpleNamespace(type=..., channel=..., control=..., value=...)` | `ControllerState.handle_msg` only reads `.type` / `.channel` / `.control` / `.note` / `.value` / `.velocity` — duck typing works |
| Mock CoreAudio enumeration | Real `sounddevice` device list | `monkeypatch.setattr(sd, "query_devices", lambda idx=None: [...])` | `_query_devices()` in `blackhole_probe.py` is a single-point indirection; mock at that boundary |
| Mock WASAPI loopback | Real `pyaudiowpatch.PyAudio` | `monkeypatch.setitem(sys.modules, "pyaudiowpatch", MagicMock())` BEFORE first method-body import in `_audio_windows.py` | Lazy import discipline lets the module load cleanly on macOS; inject mock before lazy import fires |
| Hot-plug callback | Custom callback wrapper | `vibemix.platform._midi_common::handle_port_change_single_state` (v4.0 P53) | The production callback IS the test surface. ListenerHolder + spawn_listener stubbing pattern shipped in `test_disconnect_reconnect.py`. |
| Cross-platform port enumeration | OS-specific subprocess calls | `mido.get_input_names()` | mido wraps RtMIDI which uses CoreMIDI on macOS + WinMM on Windows; cross-platform out of the box |

**Key insight:** Every artifact in P68 either (a) imports something that already ships, or (b) parametrizes a test pattern that already ships. There is NO new abstraction layer.

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| **Stored data** | None — `profiles/*.json` are static assets; ControllerState is in-process only; no DB, no SQLite, no persistent cache. | None |
| **Live service config** | None — no external services involved. mido + sounddevice + pyaudiowpatch all probe at runtime; no saved config to migrate. | None |
| **OS-registered state** | None — no Windows Task Scheduler / launchd / systemd entries for the midi subsystem. | None |
| **Secrets and env vars** | None — `GEMINI_API_KEY` is the only project env var; midi has none. | None |
| **Build artifacts / installed packages** | `src/vibemix/midi/__pycache__/` + `src/vibemix/midi/profiles/__pycache__/` + `src/vibemix/midi/controllers/__pycache__/` — stale pyc files for the deleted `controllers/` + `map_loader.py` will persist until next `find . -name __pycache__ -exec rm -rf {} +` or a fresh CI checkout. NOT a correctness issue; harmless. | Optional: include `rm -rf src/vibemix/midi/__pycache__ src/vibemix/midi/controllers/__pycache__` in the cleanup commit. CI runs from fresh checkout, no impact. |

### Cross-repo references to `midi/controllers/` (DEV-02 reconciliation surface)

This is the *real* runtime state inventory for the catalog merge — every reference that points at the deleted directory must update or break:

| Reference | File:Line | Action |
|-----------|-----------|--------|
| README "Supported controllers" table | `README.md:133-156` | REWRITE — 10-cell table updated to the profiles/ set (FLX4·FLX6·FLX10·400·1000·SX3·XDJ-RX3·PartyMixLive·Inpulse-300·Inpulse-500) |
| README image refs | `README.md:139-152` (10 × `<img src="docs/assets/controllers/...svg">`) | RENAME or REKEY — 10 SVG placeholders rekeyed to new slugs (e.g. `pioneer-ddj-flx4.svg`); KAAN-ACTION §LAUNCH-04 surface |
| README mention | `README.md:135` ("sourced verbatim from `src/vibemix/midi/controllers/`") | EDIT — link target changes to `src/vibemix/midi/profiles/` |
| README anti-drift comment | `README.md:156` ("canonical 10 controller set is locked against `src/vibemix/midi/controllers/*.json`") | EDIT — pin to `profiles/*.json` |
| Sniff invocation in README | `README.md:164` ("`python3 scripts/sniff_controller.py`") | UNCHANGED (sniff script stays; new helper is a separate `discover_midi_port.py`) |
| a11y grid check | `scripts/launch/check_readme_grids_a11y.py:18-20, 62` | EDIT — `controllers/*.json` → `profiles/*.json`; CONTROLLERS_CELL_COUNT stays 10 |
| Test gate REQUIRED_CONTROLLERS | `tests/repo/test_readme_shape.py:51-62` | REWRITE — update list to new 10 (DDJ-FLX4 stays; DDJ-200/REV1/Kontrol/MC-6000/MC-7000/Mixtrack ALL removed; FLX6, FLX10, 1000, SX3, XDJ-RX3, Party Mix Live, Inpulse-300, Inpulse-500 added) |
| Test gate asset refs | `tests/repo/test_readme_shape.py:33-39` | UNCHANGED (`docs/assets/controllers/` stays as directory ref) |
| KAAN-ACTION §LAUNCH-04 | `KAAN-ACTION-LEGAL.md:1670, 1682, 1707, 1754` (4 refs) | EDIT — `controllers/*.json` → `profiles/*.json`; canonical-10 list updated |
| Mapping doc | `docs/midi-mapping.md:1-77` (schema example at lines 34-52) | REWRITE — current "slug/port_name_substr/deck_a" schema does not match `profile.py`; replace with the actual schema shown in `docs/midi-controllers.md` |
| Controllers doc | `docs/midi-controllers.md` | UNCHANGED — table already matches the profiles/ set verbatim |
| Anti-drift dual-map gate | `tests/midi/test_live_binding_profiles_canonical.py` | DELETE — vacuous once `controllers/` + `map_loader.py` are gone |
| MidiMapLoader unit tests | `tests/midi/test_map_loader.py` | DELETE — module-under-test deleted |
| `.planning/PROJECT.md` references | `:18, :233, :372` (3 refs to `midi/controllers/`) | EDIT — `controllers/` → `profiles/` |
| v3.0 archive plan refs | `.planning/milestones/v3.0-ROADMAP.md:111`, `v3.0-REQUIREMENTS.md:78` | OPTIONAL annotate (archive — leave for historical accuracy; OR add note at top of files) |
| Phase 27 SUMMARY refs | `.planning/milestones/v2.1-phases/27-eval-harness-v2-0-carry-forward-close-out/27-09-SUMMARY.md` (and PLAN.md / RESEARCH.md in the same dir, ~10 refs) | UNCHANGED — historical archives stay correct-for-their-time |

**This is the load-bearing list for the migration commit.** Missing any of these references (especially `tests/repo/test_readme_shape.py::REQUIRED_CONTROLLERS` and `scripts/launch/check_readme_grids_a11y.py`) breaks CI immediately — they are dynamic gates that read the README at test time.

## Common Pitfalls

### Pitfall 1: "Catalog reconciliation = JSON content merge"
**What goes wrong:** Treating the duplicate `controllers/ddj-flx4.json` ↔ `profiles/pioneer_ddj_flx4.json` as needing field-by-field comparison and merge.
**Why it happens:** CONTEXT.md's migration plan reads "for the 2 overlaps... keep `profiles/` version; archive `controllers/` version ONLY IF the file contents differ meaningfully". This reads as "compare contents and choose the better one".
**Reality:** They use ENTIRELY DIFFERENT schemas (top-level fields, control structure, value semantics). `controllers/ddj-flx4.json` has `{vendor, model, description, verified, controls{"vol_a": {type, channel, value, semantic, status}}}`; `profiles/pioneer_ddj_flx4.json` has `{id, display_name, port_name_hints, decks, controls{"vol_a": {kind, channel, cc, axis, deck, field}}, buttons{}}`. There is nothing to merge — they encode different ontologies, and only `profiles/` is consumed by the runtime.
**How to avoid:** Treat the reconciliation as DELETE-AND-UPDATE-REFERENCES, not MERGE. The "loser" content survives in git history; nothing of value is lost because nothing in `controllers/` was being used by the runtime.
**Warning signs:** Anyone proposing to "port the `verified: true/false` field into the profiles schema" — that field was a `MidiMapLoader`-era concept that maps to nothing in `ControllerProfile`. The `notes` field on `ControllerProfile` already carries the "JSON-only / hardware-pending" status string for 9 of 10 profiles.

### Pitfall 2: README controller grid mismatch
**What goes wrong:** Adding the contract tests, then realizing the README "Supported controllers" 10-cell grid shows a *different 10* (the `controllers/` set, with DDJ-200 / REV1 / Kontrol-S2/S4 / MC-6000/7000 / Mixtrack Platinum-FX / Pro-FX) than the success criterion 10 (the `profiles/` set). The a11y gate + `test_readme_shape.py::REQUIRED_CONTROLLERS` then fail.
**Why it happens:** Phase 44 (v3.0) locked the README grid against `controllers/*.json` (see `tests/repo/test_readme_shape.py` comment lines 47-50 + `scripts/launch/check_readme_grids_a11y.py:19`). That gate becomes immediately wrong the moment `controllers/` is deleted.
**How to avoid:** P68 MUST include README + grid script + `REQUIRED_CONTROLLERS` + KAAN-ACTION §LAUNCH-04 updates in the SAME atomic commit as the directory deletion. The deletion-commit cannot land alone.
**Warning signs:** Running `uv run pytest tests/repo/test_readme_shape.py -v` after the deletion: 10 parametrized test cases will fail. Run that test EARLY in plan execution to surface the breakage.

### Pitfall 3: Hot-plug test that opens a real port
**What goes wrong:** The hot-plug test tries to open a real `mido` port (via `mido.open_input(...)`) and either fails (no controller plugged) or — worse — opens an actual device and locks it for the test duration.
**Why it happens:** Forgetting to `monkeypatch.setattr(_midi_common, "spawn_listener", lambda *a, **k: _DummyThread())` before the test body. The shipped `test_disconnect_reconnect.py::_stub_spawn_listener` shows the exact stub.
**How to avoid:** Lift the `_DummyThread` + `_stub_spawn_listener` helpers into a shared module (`tests/integration/conftest.py` is the natural home) or copy the pattern verbatim into the new test file. The `spawn_listener` stub MUST land BEFORE any `handle_port_change_single_state` call.

### Pitfall 4: WASAPI mock contamination across tests
**What goes wrong:** `sys.modules["pyaudiowpatch"] = MagicMock()` is injected by test A, then test B (or a later test in the same file) reads `pyaudiowpatch` and sees the stale MagicMock, producing nondeterministic behavior.
**Why it happens:** `sys.modules` injection persists until process exit; `monkeypatch.setitem` cleans up at fixture teardown, but ad-hoc `sys.modules[...] = mock` does not.
**How to avoid:** ALWAYS use `monkeypatch.setitem(sys.modules, "pyaudiowpatch", fake)` — never `sys.modules["pyaudiowpatch"] = fake`. Verified pattern in `tests/test_audio_windows.py` already.

### Pitfall 5: `_template.json` polluting `list_profiles()`
**What goes wrong:** Shipping `src/vibemix/midi/profiles/_template.json` as a contributor copy-target. `profile.py::list_profiles()` filters by `name.endswith(".json")` — leading underscore is NOT excluded. `find_mapping()` then either returns the template profile by alphabetic-id tiebreak, OR `_parse_profile` raises on the placeholder values.
**Why it happens:** Mental model: "leading underscore = private in Python" doesn't translate to filesystem glob.
**How to avoid:** Ship the template at `docs/contributing/_template.json` (outside the loader's resource directory) — NOT under `src/vibemix/midi/profiles/`. Alternative: extend `list_profiles()` to skip leading-underscore stems (one-line change to `profile.py`), but that's a touch on stable code for a doc-tier concern.

### Pitfall 6: Deleting `test_live_binding_profiles_canonical.py` removes safety net before validating the new state
**What goes wrong:** The `test_live_binding_profiles_canonical.py` gate explicitly pins that `controllers/` + `map_loader.py` are NOT in the live decode path. Deleting it before validating the new tree leaves a window where a future refactor could re-introduce the dual-map confusion.
**Why it happens:** The gate is named "test_live_binding_profiles_canonical" — its function (anti-drift) is not obvious from the name; the deleter might think it's a duplicate of `test_profiles_all_controllers.py`.
**How to avoid:** Delete the gate + the source files (`controllers/` + `map_loader.py`) + the gate's companion test (`test_map_loader.py`) in the SAME commit; document in `docs/contributing/midi-catalog.md` that the dual-map state is gone and the gate retired with it.

### Pitfall 7: Cross-platform mido enumeration nondeterminism
**What goes wrong:** `mido.get_input_names()` returns different strings across macOS vs. Windows for the same physical controller (`"DDJ-FLX4 USB MIDI"` on macOS vs. `"DDJ-FLX4"` on Windows). The `port_name_hints` list must include BOTH substrings.
**Why it happens:** RtMIDI exposes OS-native names; CoreMIDI and WinMM enumerate differently. `pioneer_ddj_flx4.json` already handles this with `["DDJ-FLX4", "FLX4"]`.
**How to avoid:** The contract test should assert `port_name_hints` has ≥1 entry (CONTEXT.md), but the recipe doc should advise contributors to add BOTH a long and a short hint. Pattern lifted from FLX4. Add this to `add-a-controller.md` Step 2.

## Code Examples

### Example 1: Synthetic-MIDI factory (lifted verbatim from `test_flx4_synthetic_decode.py`)

```python
# Source: tests/midi/test_flx4_synthetic_decode.py:33-42
from types import SimpleNamespace

def _cc(channel: int, control: int, value: int):
    return SimpleNamespace(type="control_change", channel=channel, control=control, value=value)

def _note_on(channel: int, note: int, velocity: int = 127):
    return SimpleNamespace(type="note_on", channel=channel, note=note, velocity=velocity)

def _note_off(channel: int, note: int):
    return SimpleNamespace(type="note_off", channel=channel, note=note, velocity=0)
```

### Example 2: ListenerHolder fixture (lifted from `test_disconnect_reconnect.py`)

```python
# Source: tests/midi/test_disconnect_reconnect.py:45-72
class _DummyThread:
    def __init__(self): self.joined = False
    def join(self, timeout=None): self.joined = True

def _make_holder(profile, port_name) -> ListenerHolder:
    cs = ControllerState(profile=profile)
    fake_mido = SimpleNamespace(
        get_input_names=lambda: [port_name],
        open_input=lambda name: SimpleNamespace(
            __enter__=lambda self: self, __exit__=lambda *a: False, poll=lambda: None
        ),
    )
    return ListenerHolder(
        controller_state=cs,
        listener_thread=None,
        listener_stop=None,
        mido_module=fake_mido,
    )

def _stub_spawn_listener(monkeypatch):
    monkeypatch.setattr(_midi_common, "spawn_listener", lambda *a, **k: _DummyThread())
```

### Example 3: sounddevice mock (lifted verbatim from `test_blackhole_probe.py`)

```python
# Source: tests/install/test_blackhole_probe.py:23-31
def _patch_devices(monkeypatch, devices):
    import sounddevice as sd
    def _fake_query(idx=None):
        if idx is None:
            return devices
        return devices[idx] if 0 <= idx < len(devices) else {}
    monkeypatch.setattr(sd, "query_devices", _fake_query)
```

### Example 4: pyaudiowpatch mock (lifted from `test_audio_windows.py`)

```python
# Source: tests/test_audio_windows.py::_make_fake_pa (paraphrased shape)
import sys
from unittest.mock import MagicMock

def _inject_fake_pyaudiowpatch(monkeypatch, loopback_info=None):
    fake_pa_mod = MagicMock()
    fake_instance = MagicMock()
    if loopback_info is not None:
        fake_instance.get_default_wasapi_loopback_device.return_value = loopback_info
    else:
        # Edge case: no loopback driver — raise OSError
        fake_instance.get_default_wasapi_loopback_device.side_effect = OSError("no loopback")
    fake_pa_mod.PyAudio.return_value = fake_instance
    # Ensure stale import doesn't shadow the mock
    sys.modules.pop("vibemix.platform._audio_windows", None)
    monkeypatch.setitem(sys.modules, "pyaudiowpatch", fake_pa_mod)
```

### Example 5: 10-row parametrize list (lifted verbatim from `test_profiles_all_controllers.py`)

```python
# Source: tests/midi/test_profiles_all_controllers.py:35-47
_BUNDLED_IDS = [
    "hercules_inpulse_300",
    "hercules_inpulse_500",
    "numark_party_mix_live",
    "pioneer_ddj_1000",
    "pioneer_ddj_400",
    "pioneer_ddj_flx10",
    "pioneer_ddj_flx4",
    "pioneer_ddj_flx6",
    "pioneer_ddj_sx3",
    "pioneer_xdj_rx3",
]
# This is THE ten. The success-criterion 10. No drift.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded `_CC_MAP` / `_NOTE_MAP` in `cohost_v4.py` | Declarative JSON profiles + `ControllerProfile` dataclass | Phase 9 (v2.0) | All 10 controllers now data-driven; new contributor adds 1 JSON, not Python |
| Dual-catalog `controllers/` + `profiles/` | Single canonical `profiles/` directory | **Phase 68 (this phase)** | Eliminates "which one does the registry actually use?" ambiguity |
| `jsonschema.validate(json, schema.json)` (legacy MidiMapLoader path) | `profile.py::_parse_profile` hand-rolled validator | Phase 9 (v2.0) — never wired in, MidiMapLoader stayed orphan | Hand-rolled is canonical; jsonschema retained for `ipc.*` only |
| Rebuild ControllerState on every hot-plug | Single-state `mark_connected` / `mark_disconnected` in place | Phase 53 (v4.0) | Hot-plug doesn't break downstream `ws_broadcast` / `state_refresh_loop` consumers reading the captured state object |
| Real MIDI port open in tests | `SimpleNamespace`-duck-typed `mido.Message` + `_stub_spawn_listener` | Phase 9+ | All midi tests run on Kaan's macOS dev box + GH macos-13/14 runners with no hardware |

**Deprecated / outdated:**
- `vibemix.midi.map_loader::MidiMapLoader` — slated for deletion in P68. Never wired into runtime; the dual-map gate (`test_live_binding_profiles_canonical.py`) explicitly pins this.
- `src/vibemix/midi/schema.json` — consumed only by the deleted `map_loader.py`; slated for deletion alongside.
- `src/vibemix/midi/controllers/*.json` — 10 files; all deleted (8 non-bundled + 2 overlaps with `profiles/`).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `_template.json` placed under `docs/contributing/` (NOT under `src/vibemix/midi/profiles/`) is the cleanest choice. | Claude's Discretion | Low — alternative is one-line edit to `list_profiles()` to skip `_`-prefix stems; either works |
| A2 | Deleting `tests/midi/test_live_binding_profiles_canonical.py` + `tests/midi/test_map_loader.py` is acceptable (the gates become vacuous when their targets are deleted). | Recommended Project Structure | Low — both tests gate code that is itself being deleted; no behavioral coverage is lost |
| A3 | README "Supported controllers" grid must be rewritten to the actual 10 in `profiles/` in the SAME atomic commit as the directory deletion. | Pitfall 2 | High if missed — the deletion-commit will red-fail `tests/repo/test_readme_shape.py` immediately |
| A4 | `docs/assets/controllers/*.svg` placeholder slug renames (e.g., `ddj-200.svg` → no longer needed; `pioneer-ddj-flx6.svg` → new) ride with the README rewrite. | Cross-repo References | Medium — broken image references in the README render as alt-text-only, a11y gate may still pass but UX is degraded |
| A5 | The synthetic-MIDI smoke does NOT need to push events all the way to `MusicState`; pushing through `ControllerState.handle_msg` + asserting `events_since` length is sufficient per success criterion text ("through find_mapping + ControllerState + state.MusicState"). | Pattern 2 | Low — if a stricter MusicState integration is required, plan extends the smoke to instantiate MusicState and assert state diffs. Cheap to add. |
| A6 | The audio backend "no-loopback-driver fallback" test means: when `get_default_wasapi_loopback_device()` raises OSError, the call site (e.g., `assert_wasapi_loopback_rate`) propagates / surfaces a clean message — NOT that vibemix has a separate fallback code path. | Pattern 4 / `test_audio_backend_no_loopback_driver_fallback` | Medium — if Kaan expected a "silent fallback to non-loopback capture" code path, that doesn't exist; the wizard surfaces the install affordance |
| A7 | The hot-plug 3-profile matrix uses `handle_port_change_single_state` (not the older `handle_port_change` rebuild path). | Pattern 3 | Low — single-state is the production path per `test_disconnect_reconnect.py`'s test name |
| A8 | "10 bundled" means exactly the 10 `profiles/` IDs from CONTEXT.md success criterion; the 8 additional `controllers/`-only controllers (Mixtrack-Pro-FX, Mixtrack-Platinum-FX, Kontrol-S2, Kontrol-S4, MC-6000, MC-7000, DDJ-200, DDJ-Rev1) are NOT bundled in P68 — they go away with the directory. | User Constraints / Deferred Ideas | High if wrong — but CONTEXT.md, REQUIREMENTS.md DEV-01, and README all spell out the same 10. Confidence: HIGH. |

**This table is non-empty:** Each row above should be re-confirmed by Kaan or by re-reading CONTEXT.md before the planner produces irreversible artifacts (renaming README assets, deleting `controllers/`, etc.).

## Open Questions

1. **README grid asset renames — are SVG filenames part of the commit, or does KAAN-ACTION §LAUNCH-04 own the asset rotation?**
   - What we know: SVGs at `docs/assets/controllers/*.svg` are placeholder wordmarks per §LAUNCH-04; CONTEXT comment says "real trademark-compliant logos land via Kaan-discharge before public launch."
   - What's unclear: Whether P68 swaps to placeholder-for-the-new-10 (engineering side) or routes the whole rotation to §LAUNCH-04.
   - Recommendation: P68 ships placeholder SVGs with new filenames (regenerate from the existing placeholder generator) to keep the README grid + a11y gate green; §LAUNCH-04 still owns the real-logo rotation. Two separate discharges.

2. **Synthetic-MIDI smoke depth: ControllerState only, or push through to MusicState?**
   - What we know: Success criterion says "through `find_mapping` + `ControllerState` + `state.MusicState`".
   - What's unclear: MusicState integration adds a layer of state-refresh-loop coupling; ControllerState alone validates the decode path completely.
   - Recommendation: Default to ControllerState-only (cheaper, matches the existing `test_flx4_synthetic_decode.py` shape); if the planner judges MusicState needed for "complete chain", add a single MusicState integration assertion at the end of the smoke per profile.

3. **`scripts/discover_midi_port.py` vs. existing `scripts/sniff_controller.py` — naming / overlap?**
   - What we know: `scripts/sniff_controller.py` (226 lines) already exists; provides the JSONL sniffer with port enumeration.
   - What's unclear: Whether `discover_midi_port.py` is a new lightweight helper (≤30 lines, just list ports) or just an alias / rename of the existing sniffer.
   - Recommendation: Ship the new lightweight script — it has a different scope (port enumeration for recipe Step 1) and a different audience (the contributor who just wants port names, not a full MIDI capture). Both coexist. Reference both in the recipe doc.

4. **Should the planner delete the entire `controllers/` directory in one task, or in a sequence of "remove file by file" tasks?**
   - What we know: 10 JSON files + 0 Python files = 10 file deletions.
   - What's unclear: Whether the planner prefers a single `git rm -r src/vibemix/midi/controllers/` task or per-file tasks.
   - Recommendation: Single atomic task — same commit as `git rm map_loader.py + schema.json + tests/midi/test_map_loader.py + tests/midi/test_live_binding_profiles_canonical.py`. The migration note documents the per-file content for audit.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | All tests | ✓ | 3.12.x in `.venv/` | — |
| `pytest` | Test runner | ✓ | `>=8.0` (uv.lock) | — |
| `pytest-mock` | `mocker` fixture | ✓ | `>=3.15.1` (uv.lock) | — |
| `mido` | MIDI port enumeration in `scripts/discover_midi_port.py` + integration tests | ✓ | `>=1.3.3` (uv.lock) | — |
| `python-rtmidi` | mido backend | ✓ | `>=1.5.8` (uv.lock) | — |
| `sounddevice` | macOS audio mock target | ✓ | `>=0.5.5` (uv.lock) | — |
| `pyaudiowpatch` | Windows audio mock target | ✓ on Windows only; mocked via `MagicMock` on macOS dev box | `>=0.2.12` win32-only | sys.modules MagicMock injection works on macOS |
| `jsonschema` | NOT consumed by P68 — pyproject.toml has it for `ipc.*` validation; available if needed | ✓ | `>=4.23,<5` | — |
| `uv` runner | `uv run pytest -q` | ✓ | system | `source .venv/bin/activate && pytest -q` |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.

[VERIFIED: pyproject.toml lines 28-119 + uv.lock]

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (lines 196-209) |
| Quick run command | `uv run pytest tests/midi/ -q` |
| Full suite command | `uv run pytest -q` (4158 passed baseline from 67P04 + this phase's additions) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEV-01 | 10 bundled profiles each: contract test + synthetic smoke + non-empty `port_name_hints` | unit | `uv run pytest tests/midi/test_profile_contracts.py tests/midi/test_profile_smokes.py -v` | ❌ Wave 0 (NEW) |
| DEV-02 | Single canonical catalog; no broken refs; migration note | repo-shape (find + uniq) + repo tests | `find src/vibemix/midi -name "*.json" \| xargs -I{} basename {} .json \| sort \| uniq -c \| awk '$1 > 1'` returns empty; `uv run pytest tests/repo/test_readme_shape.py -q` GREEN after README rewrite | ❌ Wave 0 (DELETE controllers/+map_loader.py + PATCH README + DELETE 2 tests) |
| DEV-03 | Hot-plug ≥3 distinct profiles via `start_port_watcher` + `mark_disconnected` + single-state callback (UNTOUCHED) | integration | `uv run pytest tests/integration/test_hotplug_matrix.py -m integration -v` | ❌ Wave 1 (NEW) |
| DEV-04 | Audio backend matrix: BlackHole 2ch/16ch + WASAPI loopback + no-loopback fallback (mocked) | integration | `uv run pytest tests/integration/test_audio_backends.py -m integration -v` | ❌ Wave 1 (NEW) |
| DEV-05 | Contributor recipe docs + template + discover helper; <30-min smoke discharge | doc presence + manual smoke | `test -f docs/contributing/add-a-controller.md && test -f docs/contributing/_template.json && test -f scripts/discover_midi_port.py && uv run pytest tests/midi/ -q` | ❌ Wave 2 (NEW docs + helper); smoke = §V7-LIVE-07 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/midi/ -q` (~70 cases now; grows by ~30 new parametrized rows with P68)
- **Per wave merge:** `uv run pytest tests/midi/ tests/integration/ tests/repo/test_readme_shape.py -q` (the surface most likely to drift)
- **Phase gate:** `uv run pytest -q` full suite GREEN (must hold the 4158-passed baseline ± new additions); add `-m integration` separately

### Wave 0 Gaps
- [ ] `tests/midi/test_profile_contracts.py` — covers DEV-01 (a + c)
- [ ] `tests/midi/test_profile_smokes.py` — covers DEV-01 (b)
- [ ] `tests/midi/conftest.py` (optional) — shared `_BUNDLED_IDS` + factory helpers, OR copy verbatim into both new files
- [ ] `tests/integration/conftest.py` (optional) — `_DummyThread` + `_stub_spawn_listener` shared between hot-plug + future tests
- [ ] DELETE: `src/vibemix/midi/controllers/` (10 files), `src/vibemix/midi/map_loader.py`, `src/vibemix/midi/schema.json`, `tests/midi/test_map_loader.py`, `tests/midi/test_live_binding_profiles_canonical.py`
- [ ] PATCH: `README.md` (10-cell grid + 2 anti-drift comments + 1 link), `tests/repo/test_readme_shape.py::REQUIRED_CONTROLLERS`, `scripts/launch/check_readme_grids_a11y.py` (comment refs), `KAAN-ACTION-LEGAL.md` §LAUNCH-04 (4 refs), `docs/midi-mapping.md` schema example, `.planning/PROJECT.md` (3 refs), `docs/assets/controllers/*.svg` (rename 10 placeholder files to new slugs)
- [ ] NEW: `docs/contributing/add-a-controller.md`, `docs/contributing/midi-catalog.md`, `docs/contributing/_template.json`, `scripts/discover_midi_port.py`
- [ ] No framework install needed — pytest + pytest-mock already in dev deps

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — no auth surface in this phase |
| V3 Session Management | no | N/A |
| V4 Access Control | no | N/A — JSON catalog is bundled static data |
| V5 Input Validation | yes | `vibemix.midi.profile::_parse_profile` validates every field, raises ValueError with profile name on drift. NEW contract test pins this. |
| V6 Cryptography | no | N/A |
| V12 Files and Resources | partial | Profile JSON loading uses `importlib.resources.files(...).joinpath(f"{name}.json")` + `.is_file()` guard before open — bundled-resource scope; no user-controlled path |
| V14 Configuration | yes | The migration deletes a code path (`map_loader.py`) — supply-chain hygiene by reducing attack surface |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed contributor JSON profile crashes the loader | DoS | `_parse_profile` raises ValueError with profile name — handled at the call site by `load_profile` returning None (file not found path); ValueError surfaces to the user with a clear "profile X: field Y is required" message. The new contract test (P68) catches this at CI time, before a malformed profile lands in main. |
| Contributor JSON specifies controls/buttons with malicious payloads | Tampering | No code is executed from JSON — JSON parses into frozen dataclasses with primitive fields (int channel, int cc, str field). No `eval()`, no module loading, no callable references. SAFE. |
| Audio device probe leaks system info via error messages | Disclosure | `blackhole_probe._safe_emit` already swallows emit failures; the device-name strings emitted are user-facing (BlackHole 2ch / device name) — no PII, no system path. SAFE. |
| Hot-plug test interferes with other concurrent tests | Tampering | Hot-plug test uses `monkeypatch.setattr` (fixture-scoped cleanup) for `spawn_listener` stub. `monkeypatch.setitem(sys.modules, ...)` for pyaudiowpatch is also fixture-scoped. SAFE. |
| `scripts/discover_midi_port.py` accidentally opens / locks a real MIDI port | Availability | The helper uses `mido.get_input_names()` (enumeration only, no `open_input`) — no port is opened. SAFE by design. |

`security_enforcement` defaults to enabled (absent in `.planning/config.json` for this repo per default rule). The above table is the security-domain pass for P68.

## Sources

### Primary (HIGH confidence)

- **`src/vibemix/midi/profile.py`** (Read 383 lines) — canonical schema validator; field `port_name_hints` plural confirmed; `notes` optional field confirmed. [VERIFIED: codebase]
- **`src/vibemix/midi/registry.py`** (Read 60 lines) — `find_mapping` / `find_mapping_or_generic` semantics; alphabetic-id tiebreak. [VERIFIED: codebase]
- **`src/vibemix/midi/state.py`** (Read 466 lines) — `ControllerState.handle_msg`, `mark_disconnected`, ring-clear-on-disconnect Phase 53 hardening, MidiEvent dataclass. [VERIFIED: codebase]
- **`src/vibemix/midi/watcher.py`** (Read 124 lines) — `port_watcher_task` async polling shape; emits `('connected', port, profile)` / `('disconnected', port)`. [VERIFIED: codebase]
- **`src/vibemix/midi/map_loader.py`** (Read 166 lines) — the deletion target. Confirms `CONTROLLERS_DIR = Path(__file__).parent / "controllers"` and the orphan jsonschema validation path. [VERIFIED: codebase]
- **`src/vibemix/midi/schema.json`** (Read full) — validates the `controllers/` schema (vendor/model/description/verified/controls{} flat dict). NOT the validator for `profiles/`. [VERIFIED: codebase]
- **`src/vibemix/midi/generic.py`** (Read 79 lines) — generic-MIDI fallback shape; deck assumption `('A', 'B')`. [VERIFIED: codebase]
- **`src/vibemix/midi/__init__.py`** (Read 60 lines) — public re-exports (no `MidiMapLoader` in `__all__`). [VERIFIED: codebase]
- **`src/vibemix/platform/_midi_common.py`** (Read excerpts) — `handle_port_change_single_state` (the live hot-plug callback); `ListenerHolder` shape. [VERIFIED: codebase]
- **`src/vibemix/install/blackhole_probe.py`** (Read 234 lines) — `_query_devices()` monkeypatch seam; `probe_blackhole(retry_on_missing=False)` for fast tests. [VERIFIED: codebase]
- **`src/vibemix/platform/_audio_windows.py`** (Read 100 lines) — `assert_wasapi_loopback_rate` shape; lazy-import discipline. [VERIFIED: codebase]
- **`tests/midi/test_disconnect_reconnect.py`** (Read 178 lines) — hot-plug test template; `_DummyThread` + `_stub_spawn_listener` patterns. [VERIFIED: codebase]
- **`tests/midi/test_flx4_synthetic_decode.py`** (Read 166 lines) — synthetic-MIDI factory pattern. [VERIFIED: codebase]
- **`tests/midi/test_profiles_all_controllers.py`** (Read 266 lines) — existing 10-row parametrize pattern; `_ALL_CONTROLLER_IDS` list is canonical. [VERIFIED: codebase]
- **`tests/midi/test_watcher.py`** (Read 363 lines) — async watcher test patterns + `mocker.patch` discipline. [VERIFIED: codebase]
- **`tests/midi/test_live_binding_profiles_canonical.py`** (Read 154 lines) — dual-map gate; targets the artifacts P68 deletes. [VERIFIED: codebase]
- **`tests/install/test_blackhole_probe.py`** (Read full) — sounddevice mock pattern. [VERIFIED: codebase]
- **`tests/test_audio_windows.py`** (Read 80 lines) — pyaudiowpatch sys.modules injection pattern. [VERIFIED: codebase]
- **`tests/repo/test_readme_shape.py`** (Read 100 lines) — REQUIRED_CONTROLLERS gate that needs updating. [VERIFIED: codebase]
- **`scripts/launch/check_readme_grids_a11y.py`** (Read 100 lines) — a11y + balance + cell-count gate against `controllers/*.json` reference. [VERIFIED: codebase]
- **`scripts/sniff_controller.py`** (Read first 50 lines + line count) — existing 226-line JSONL sniffer; coexists with the new ≤30-line `discover_midi_port.py`. [VERIFIED: codebase]
- **`pyproject.toml`** (Read full) — confirms `jsonschema>=4.23,<5`, `mido>=1.3.3`, `sounddevice>=0.5.5`, `pyaudiowpatch>=0.2.12 ; sys_platform == 'win32'`, `pytest>=8.0`, `pytest-mock>=3.15.1`; markers `integration`, `macos_audio`, `windows_only`. [VERIFIED: codebase]
- **`uv.lock`** (greppped jsonschema entry) — `jsonschema-4.26.0`, `jsonschema-specifications-2025.9.1`. [VERIFIED: codebase]
- **`README.md`** (Read first 170 lines) — Supported controllers grid + `<video src="docs/assets/demo.mp4">` placeholder + 5 sibling badge format. [VERIFIED: codebase]
- **`docs/midi-controllers.md`** (Read 80 lines) — table already lists the 10 `profiles/` IDs; pattern doc is mostly correct. [VERIFIED: codebase]
- **`docs/midi-mapping.md`** (Read 60 lines) — schema example uses STALE shape (`slug`/`port_name_substr`/`deck_a` — doesn't match `profile.py`). [VERIFIED: codebase]
- **`.planning/REQUIREMENTS.md`** (Read full) — DEV-01..05 acceptance criteria verbatim. [VERIFIED]
- **`.planning/ROADMAP.md`** Phase 68 section (Read lines 74-84) — phase goal + success criteria 1-5. [VERIFIED]
- **`.planning/STATE.md`** (Read full) — confirms Phase 67 closed, P68 next; baseline 4158 passed. [VERIFIED]
- **`.planning/phases/68-all-devices-ready/68-CONTEXT.md`** (Read full) — locked decisions consumed verbatim. [VERIFIED]

### Secondary (MEDIUM confidence)

- Cross-platform `mido.get_input_names()` semantics — MEDIUM (CITED via mido docs; behavior pinned by 226-line `scripts/sniff_controller.py` precedent that already enumerates cross-platform).
- WASAPI loopback no-driver behavior on Windows — MEDIUM (the `assert_wasapi_loopback_rate` shape suggests `OSError` from `pyaudiowpatch` is the surface; mocking with `side_effect = OSError(...)` is the standard pattern).

### Tertiary (LOW confidence)

- Whether `docs/assets/controllers/*.svg` filename rotation is fully owned by §LAUNCH-04 or partially in P68 — LOW (resolved into Assumption A4 + Open Question 1 — flag for planner)

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — every dep is in `pyproject.toml` + `uv.lock`; no new packages
- Architecture: **HIGH** — every code path is read end-to-end (profile.py, registry.py, state.py, watcher.py, _midi_common.py, blackhole_probe.py, _audio_windows.py)
- Pitfalls: **HIGH** — every pitfall has a corresponding shipped test demonstrating the right pattern; the catalog-reconciliation pitfall is verified by reading both schemas and confirming they are incompatible ontologies
- DEV-02 reconciliation surface (the cross-repo find-and-replace inventory): **HIGH** — every reference was grep'd and individually verified; the README + grid-script + test-gate triangle is the critical correctness surface
- Audio backend mocking: **HIGH** — both macOS and Windows mock patterns are already shipped (verified by reading `test_blackhole_probe.py` + `test_audio_windows.py`)

**Research date:** 2026-05-23
**Valid until:** 2026-06-22 (30 days — stable infrastructure phase, no fast-moving deps)

## RESEARCH COMPLETE

**Phase:** 68 — All Devices Ready
**Confidence:** HIGH

### Key Findings

1. **CONTEXT.md has a field-name drift:** the canonical schema field is `port_name_hints` (plural list), NOT `port_name_hint` (singular). All 10 profiles already carry it. Contract test asserts the plural form.
2. **The two catalogs use INCOMPATIBLE schemas, not just different IDs.** `controllers/*.json` is the orphan MidiMapLoader ontology; `profiles/*.json` is the live `ControllerProfile` ontology. "Reconciliation" = DELETE-AND-UPDATE-REFERENCES, NOT merge. Verified by reading both `ddj-flx4.json` files end-to-end.
3. **Cross-repo deletion impact is non-trivial.** README's 10-cell "Supported controllers" grid currently lists the `controllers/` set (DDJ-200/REV1/Kontrol/MC/Mixtrack); `tests/repo/test_readme_shape.py::REQUIRED_CONTROLLERS` enforces this list; `scripts/launch/check_readme_grids_a11y.py` + KAAN-ACTION §LAUNCH-04 + `docs/midi-mapping.md` schema example all reference `controllers/`. P68 must rewrite the README grid + update the test gate + update the a11y script + update KAAN-ACTION + rewrite the schema example + rename 10 SVG placeholders **in the SAME commit as the directory deletion** or CI immediately reds.
4. **Zero net-new dependencies.** `jsonschema`, `mido`, `sounddevice`, `pyaudiowpatch`, `pytest`, `pytest-mock` all already in `pyproject.toml` + `uv.lock`. v7.0's zero-new-dep rule holds by default.
5. **Every test pattern P68 needs already ships.** Synthetic-MIDI factory (`test_flx4_synthetic_decode.py`), 10-row parametrize (`test_profiles_all_controllers.py`), hot-plug ListenerHolder + DummyThread + spawn_listener stub (`test_disconnect_reconnect.py`), sounddevice mock (`test_blackhole_probe.py`), pyaudiowpatch sys.modules injection (`test_audio_windows.py`). P68 composes them; it does not invent any new pattern.
6. **The v4.0 P53 hot-plug callback is read-only in this phase.** `_midi_common.handle_port_change_single_state` + `state.mark_disconnected` are NOT modified. The 3-profile hot-plug test parametrizes the existing single-profile test.
7. **`scripts/sniff_controller.py` already exists** (226 lines, JSONL sniffer). The new `scripts/discover_midi_port.py` (≤30 lines) has a different scope — coexists; recipe doc references both.

### File Created

`/Users/ozai/projects/dj-set-ai/.planning/phases/68-all-devices-ready/68-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | Every dep verified in pyproject.toml + uv.lock; zero new deps |
| Architecture | HIGH | Every midi module + audio probe + hot-plug callback read end-to-end |
| Pitfalls | HIGH | Each pitfall verified against shipped code or shipped test |
| DEV-02 reconciliation surface | HIGH | Cross-repo `grep -rn midi/controllers` exhaustive; every reference catalogued in §Runtime State Inventory |
| Audio backend mocking | HIGH | Both macOS + Windows patterns already shipped, verified |

### Open Questions

See `## Open Questions` section — 4 items:
1. README SVG asset rotation: P68-engineering-side placeholders vs. §LAUNCH-04 real-logo discharge
2. Synthetic-MIDI smoke depth: ControllerState only or push to MusicState
3. `discover_midi_port.py` vs. `sniff_controller.py` — coexist (recommended)
4. Atomic vs. file-by-file deletion of `controllers/`

### Ready for Planning

Research complete. Planner can now decompose P68 into waves:
- **Wave 0:** Atomic reconciliation commit (delete `controllers/` + `map_loader.py` + `schema.json` + 2 orphan tests; PATCH README grid + a11y script + REQUIRED_CONTROLLERS + KAAN-ACTION § + docs/midi-mapping.md schema example + 10 SVG renames; ADD `docs/contributing/midi-catalog.md` migration note)
- **Wave 1:** Contract test + synthetic smoke for DEV-01 (`tests/midi/test_profile_contracts.py` + `tests/midi/test_profile_smokes.py`)
- **Wave 2:** Integration matrices for DEV-03 + DEV-04 (`tests/integration/test_hotplug_matrix.py` + `tests/integration/test_audio_backends.py`)
- **Wave 3:** Contributor recipe for DEV-05 (`docs/contributing/add-a-controller.md` + `docs/contributing/_template.json` + `scripts/discover_midi_port.py`)
- **Wave 4:** KAAN-ACTION §V7-LIVE-07 (smoke discharge) + §V7-LIVE-08/09/10 (BlackHole live · WASAPI live · FLX4 hot-plug ear) cluster wiring under `gsd-autonomous fully`

Dependency spine: Wave 0 first (catalog must be canonical before contract tests run); Waves 1-3 parallelize on the green Wave-0 baseline; Wave 4 is doc-only KAAN-ACTION surface authoring.
