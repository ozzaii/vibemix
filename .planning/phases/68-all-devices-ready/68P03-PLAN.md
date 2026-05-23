---
phase: 68-all-devices-ready
plan: 03
type: execute
wave: 2
depends_on: ["68-01"]
files_modified:
  - tests/integration/test_hotplug_matrix.py
  - tests/integration/test_audio_backends.py
autonomous: true
requirements:
  - DEV-03
  - DEV-04

must_haves:
  truths:
    - "uv run pytest tests/integration/test_hotplug_matrix.py -m integration -v shows ≥ 3 GREEN parametrized cases (FLX4, DDJ-400, Inpulse-500)"
    - "uv run pytest tests/integration/test_audio_backends.py -m integration -v shows GREEN coverage of BlackHole 2ch + 16ch + WASAPI loopback + no-loopback fallback"
    - "src/vibemix/platform/_midi_common.py is UNMODIFIED (read-only — v4.0 P53 path stays sacred)"
    - "src/vibemix/midi/state.py is UNMODIFIED (read-only — mark_disconnected was hardened in v4.0 P53)"
    - "All 4 mock surfaces use monkeypatch (not raw sys.modules[...] = mock) — fixture-scoped cleanup"
  artifacts:
    - path: "tests/integration/test_hotplug_matrix.py"
      provides: "3-profile parametrized hot-plug matrix (connect → disconnect → reconnect) — DEV-03"
      min_lines: 70
    - path: "tests/integration/test_audio_backends.py"
      provides: "4-fixture audio backend matrix (BlackHole 2ch/16ch + WASAPI loopback + no-loopback) — DEV-04"
      min_lines: 90
  key_links:
    - from: "tests/integration/test_hotplug_matrix.py"
      to: "vibemix.platform._midi_common::handle_port_change_single_state"
      via: "Test imports + read-only invocation"
      pattern: "handle_port_change_single_state"
    - from: "tests/integration/test_audio_backends.py"
      to: "vibemix.install.blackhole_probe::probe_blackhole"
      via: "monkeypatch sd.query_devices + call probe"
      pattern: "probe_blackhole"
    - from: "tests/integration/test_audio_backends.py"
      to: "vibemix.platform._audio_windows::assert_wasapi_loopback_rate"
      via: "monkeypatch.setitem(sys.modules, 'pyaudiowpatch', mock)"
      pattern: "assert_wasapi_loopback_rate"
---

<objective>
Wave 2 — Land the two integration matrices that close DEV-03 (hot-plug across ≥ 3 profiles) and DEV-04 (audio backend mock matrix). Both test files are marked `@pytest.mark.integration`. Both compose ALREADY-SHIPPED patterns (no new abstractions):
- DEV-03 parametrizes the v4.0 P53 `handle_port_change_single_state` callback (proven by `tests/midi/test_disconnect_reconnect.py:45-77`) across FLX4 · DDJ-400 · Inpulse-500.
- DEV-04 uses `monkeypatch.setattr(sd, "query_devices", ...)` for macOS BlackHole 2ch + 16ch + absent (pattern lifted from `tests/install/test_blackhole_probe.py:23-31`) and `monkeypatch.setitem(sys.modules, "pyaudiowpatch", MagicMock())` for Windows WASAPI loopback + no-loopback (pattern lifted from `tests/test_audio_windows.py`).

Purpose: Close DEV-03 (single-state callback hot-plug invariant survives across 3 distinct profiles) + DEV-04 (audio backend mock matrix proves clean entry/exit on macOS + Windows mock targets). Live hardware confirmations (real FLX4 plug/unplug + real BlackHole + real WASAPI) ride to KAAN-ACTION §V7-LIVE-08/09/10 in Wave 4 (P05).

Output: Two new files under `tests/integration/`. Zero edits to `src/vibemix/{midi,platform,install}/`. Zero new dependencies.
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

@src/vibemix/platform/_midi_common.py
@src/vibemix/midi/state.py
@src/vibemix/install/blackhole_probe.py
@src/vibemix/platform/_audio_windows.py
@tests/midi/test_disconnect_reconnect.py
@tests/install/test_blackhole_probe.py
@tests/test_audio_windows.py

<interfaces>
ListenerHolder + handle_port_change_single_state (load-bearing v4.0 P53 path — UNTOUCHED):
```python
from vibemix.platform._midi_common import ListenerHolder, handle_port_change_single_state
from vibemix.platform import _midi_common
# handle_port_change_single_state(holder: ListenerHolder, event: tuple) -> None
#   event = ('connected', port_name: str, profile: ControllerProfile)
#         | ('disconnected', port_name: str)
# Single-state invariant: id(holder.controller_state) MUST NOT change across (dis)connects
```

ControllerState methods used in hot-plug test:
```python
cs.handle_msg(msg)              # decode a synthetic SimpleNamespace MIDI msg
cs.moves_since(0.0) -> list     # the moves ring buffer (cleared on disconnect per v4.0 P53)
cs.is_connected() -> bool
cs.mark_connected(port_name: str)  # not directly called — handle_port_change_single_state drives this
```

blackhole_probe API (from src/vibemix/install/blackhole_probe.py):
```python
from vibemix.install import blackhole_probe
result = blackhole_probe.probe_blackhole(retry_on_missing=False)
# returns dict: {"installed": bool, "device_name": str | None}
# internally calls sd.query_devices() — monkeypatch that to control the test scenario
```

_audio_windows API (from src/vibemix/platform/_audio_windows.py):
```python
from vibemix.platform._audio_windows import assert_wasapi_loopback_rate
index, name = assert_wasapi_loopback_rate(expected=48000)
# internally lazy-imports pyaudiowpatch and calls PyAudio().get_default_wasapi_loopback_device()
# raises OSError if no loopback driver — that IS the "no-loopback fallback" surface
```

Synthetic MIDI factory (per 68-RESEARCH §Pattern 3 + tests/midi/test_disconnect_reconnect.py):
```python
from types import SimpleNamespace
SimpleNamespace(type="control_change", channel=0, control=19, value=110)  # sample volume_a CC for FLX4
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: tests/integration/test_hotplug_matrix.py — 3-profile hot-plug matrix (DEV-03)</name>
  <files>tests/integration/test_hotplug_matrix.py</files>
  <read_first>
    @.planning/phases/68-all-devices-ready/68-CONTEXT.md
    @.planning/phases/68-all-devices-ready/68-RESEARCH.md (§Pattern 3 + §Code Examples 2 + §Common Pitfalls #3 + §Anti-Patterns to Avoid item 3 "DO NOT rebuild the v4.0 P53 hot-plug callback")
    @tests/midi/test_disconnect_reconnect.py (full 178 lines — this is the parametrize target; `_DummyThread` + `_make_holder` + `_stub_spawn_listener` patterns; lift them verbatim into the new file or import from the existing test module)
    @src/vibemix/platform/_midi_common.py (read `ListenerHolder` dataclass + `handle_port_change_single_state` function — confirm signatures; NEVER modify)
    @src/vibemix/midi/state.py (read `ControllerState.mark_connected`, `mark_disconnected`, `moves_since`, `is_connected`, `handle_msg` — confirm signatures; NEVER modify)
    @src/vibemix/midi/profiles/pioneer_ddj_flx4.json (sample profile for FLX4 row — pick a control with `channel=0, cc=19` for the sample handle_msg between connect/disconnect)
    @src/vibemix/midi/profiles/pioneer_ddj_400.json (sample profile for DDJ-400 row — pick a similar volume CC for parity)
    @src/vibemix/midi/profiles/hercules_inpulse_500.json (sample profile for Inpulse-500 row — pick any CC)
  </read_first>
  <behavior>
    - Test (per row): `monkeypatch.setattr(_midi_common, "spawn_listener", lambda *a, **k: _DummyThread())` BEFORE the test body (per 68-RESEARCH Pitfall #3 — forgetting this opens a real port).
    - Build a `ListenerHolder` with a `_DummyThread`-stubbed mido module (no real port opens) for the profile.
    - Capture `orig_id = id(holder.controller_state)`.
    - Phase 1 — CONNECT: `handle_port_change_single_state(holder, ("connected", port_name, profile))`. Then push one synthetic CC msg via `holder.controller_state.handle_msg(...)`. Assert `len(holder.controller_state.moves_since(0.0)) >= 1`.
    - Phase 2 — DISCONNECT: `handle_port_change_single_state(holder, ("disconnected", port_name))`. Assert `is_connected() is False`, `moves_since(0.0) == []` (ring cleared per v4.0 P53), `id(holder.controller_state) == orig_id` (single-state invariant — NOT rebuilt).
    - Phase 3 — RECONNECT: `handle_port_change_single_state(holder, ("connected", port_name, profile))`. Assert `is_connected() is True`, `id(holder.controller_state) == orig_id` (still single-state).
    - Marker: `@pytest.mark.integration`.
    - Anti-pattern (FORBIDDEN per 68-RESEARCH §Pitfall #3): real `mido.open_input(...)`. Anti-pattern (FORBIDDEN per Anti-Patterns item 3): editing `_midi_common.py`.
  </behavior>
  <action>
    Create `tests/integration/test_hotplug_matrix.py` composing the patterns from `tests/midi/test_disconnect_reconnect.py` (lift the `_DummyThread` + `_make_holder` + `_stub_spawn_listener` helpers verbatim; do NOT abstract into conftest.py — keep self-contained per 68-RESEARCH §Wave 0 Gaps optional note):

    1. Module docstring + SPDX header. The docstring says: "DEV-03 hot-plug matrix. Parametrizes the v4.0 P53 single-state callback across 3 distinct profiles (FLX4 · DDJ-400 · Inpulse-500). The production callback (`vibemix.platform._midi_common::handle_port_change_single_state`) is read-only — this test MUST NOT modify it."
    2. Imports:
       ```python
       from types import SimpleNamespace
       import pytest
       from vibemix.midi import load_profile
       from vibemix.midi.state import ControllerState
       from vibemix.platform import _midi_common
       from vibemix.platform._midi_common import ListenerHolder, handle_port_change_single_state
       ```
    3. `_PROFILES` constant — 3 tuples `(profile_id, port_name, sample_cc)`:
       ```python
       _PROFILES = [
           ("pioneer_ddj_flx4", "DDJ-FLX4 USB MIDI", (0, 19, 110)),
           ("pioneer_ddj_400",  "DDJ-400",            (0, 19, 100)),
           ("hercules_inpulse_500", "DJControl Inpulse 500", (0, 15, 90)),
       ]
       ```
       The `(channel, cc, value)` for each row picks a real CC from the corresponding profile JSON (verify via the read-first step that each profile has a control at the chosen (channel, cc) so `handle_msg` actually fires an event).
    4. Helpers (LIFTED VERBATIM from `tests/midi/test_disconnect_reconnect.py`):
       ```python
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
       ```
       (If `ListenerHolder` dataclass fields differ slightly from what test_disconnect_reconnect.py uses — e.g., `mido_module` kwarg name — match the existing test file exactly. Read it first.)
    5. Parametrized test:
       ```python
       @pytest.mark.integration
       @pytest.mark.parametrize("profile_id,port_name,sample_cc", _PROFILES)
       def test_hotplug_single_state_across_three_profiles(monkeypatch, profile_id, port_name, sample_cc):
           monkeypatch.setattr(_midi_common, "spawn_listener", lambda *a, **k: _DummyThread())
           profile = load_profile(profile_id)
           assert profile is not None
           holder = _make_holder(profile, port_name)
           orig_id = id(holder.controller_state)

           # CONNECT
           handle_port_change_single_state(holder, ("connected", port_name, profile))
           assert holder.controller_state.is_connected() is True
           channel, control, value = sample_cc
           holder.controller_state.handle_msg(SimpleNamespace(
               type="control_change", channel=channel, control=control, value=value))
           assert len(holder.controller_state.moves_since(0.0)) >= 1, \
               f"{profile_id}: no moves surfaced after connect — handle_msg not wired"

           # DISCONNECT — single-state invariant holds (id preserved, ring cleared)
           handle_port_change_single_state(holder, ("disconnected", port_name))
           assert holder.controller_state.is_connected() is False
           assert holder.controller_state.moves_since(0.0) == [], \
               f"{profile_id}: ring not cleared on disconnect — v4.0 P53 invariant broken"
           assert id(holder.controller_state) == orig_id, \
               f"{profile_id}: ControllerState rebuilt — single-state invariant broken"

           # RECONNECT — id still preserved
           handle_port_change_single_state(holder, ("connected", port_name, profile))
           assert holder.controller_state.is_connected() is True
           assert id(holder.controller_state) == orig_id
       ```
    6. Confirm `tests/integration/__init__.py` exists (it does per the prior `ls` — already shipped). No directory creation needed.
  </action>
  <verify>
    <automated>uv run pytest tests/integration/test_hotplug_matrix.py -m integration -v 2&gt;&amp;1 | tee /tmp/68P03-T1.log | tail -30 &amp;&amp; grep -c PASSED /tmp/68P03-T1.log | awk '{exit ($1 == 3 ? 0 : 1)}' &amp;&amp; git diff --stat -- src/vibemix/platform/_midi_common.py src/vibemix/midi/state.py | grep -c '^' | awk '{exit ($1 == 0 ? 0 : 1)}'</automated>
  </verify>
  <acceptance_criteria>
    - `uv run pytest tests/integration/test_hotplug_matrix.py -m integration -v` exits 0 with exactly 3 PASSED parametrized rows.
    - `git diff --stat -- src/vibemix/platform/_midi_common.py src/vibemix/midi/state.py` shows ZERO modifications (the v4.0 P53 path is sacred).
    - `grep -c "@pytest.mark.integration" tests/integration/test_hotplug_matrix.py` ≥ 1 (proper marker).
    - `grep -c "mido.open_input\|rtmidi" tests/integration/test_hotplug_matrix.py` == 0 (no real port opens).
    - `grep -c "spawn_listener" tests/integration/test_hotplug_matrix.py` ≥ 1 (the monkeypatch stub IS present — per 68-RESEARCH Pitfall #3).
    - File is ≥ 70 lines.
  </acceptance_criteria>
  <done>
    File exists, 3 hot-plug rows GREEN across distinct profiles, single-state invariant (id preserved across (dis)connects) pinned, v4.0 P53 source path untouched; DEV-03 closed.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: tests/integration/test_audio_backends.py — 4-fixture audio backend mock matrix (DEV-04)</name>
  <files>tests/integration/test_audio_backends.py</files>
  <read_first>
    @.planning/phases/68-all-devices-ready/68-CONTEXT.md
    @.planning/phases/68-all-devices-ready/68-RESEARCH.md (§Pattern 4 + §Code Examples 3 + §Code Examples 4 + §Common Pitfalls #4 + §Assumption A6)
    @tests/install/test_blackhole_probe.py (full file — `_patch_devices` helper at lines 23-31 is the canonical sd.query_devices monkeypatch pattern; lift it)
    @tests/test_audio_windows.py (full file — `_make_fake_pa` pattern at top of file is the canonical pyaudiowpatch sys.modules injection; lift it)
    @src/vibemix/install/blackhole_probe.py (read `probe_blackhole(retry_on_missing=False)` signature + return shape `{"installed": bool, "device_name": str | None}`)
    @src/vibemix/platform/_audio_windows.py (read `assert_wasapi_loopback_rate(expected=...)` signature + behavior on missing loopback — per 68-RESEARCH Assumption A6, OSError surfaces are the "no-loopback fallback" — that's the expectation)
  </read_first>
  <behavior>
    - Test 1 — `test_audio_backend_macos_blackhole_2ch_present`: monkeypatch `sd.query_devices` to return a single-element list `[{"name": "BlackHole 2ch", "max_output_channels": 2}]`; call `probe_blackhole(retry_on_missing=False)`; assert `result == {"installed": True, "device_name": "BlackHole 2ch"}`.
    - Test 2 — `test_audio_backend_macos_blackhole_16ch_present`: same shape but `[{"name": "BlackHole 16ch", "max_output_channels": 16}]`; assert `result["installed"] is True` + `result["device_name"] == "BlackHole 16ch"`.
    - Test 3 — `test_audio_backend_macos_no_blackhole_graceful`: monkeypatch with `[{"name": "Built-in Output"}, {"name": "AirPods"}]`; assert `result == {"installed": False, "device_name": None}` (graceful absent — NOT a crash).
    - Test 4 — `test_audio_backend_windows_wasapi_loopback_found`: inject MagicMock pyaudiowpatch via `monkeypatch.setitem(sys.modules, "pyaudiowpatch", fake_pa_mod)` BEFORE importing `_audio_windows`; configure `get_default_wasapi_loopback_device.return_value = {"name": "Speakers (Realtek) [Loopback]", "index": 7, "defaultSampleRate": 48000.0}`; assert `assert_wasapi_loopback_rate(expected=48000)` returns `(7, "...")` and the returned name contains "Loopback".
    - Test 5 — `test_audio_backend_windows_no_loopback_driver`: inject MagicMock pyaudiowpatch with `get_default_wasapi_loopback_device.side_effect = OSError("no loopback")`; assert calling `assert_wasapi_loopback_rate(expected=48000)` raises an OSError (or whichever specific exception `_audio_windows` propagates — read the source to confirm; per 68-RESEARCH Assumption A6 the propagation IS the fallback surface).
    - All tests marked `@pytest.mark.integration`.
    - Anti-pattern (FORBIDDEN per 68-RESEARCH Pitfall #4): bare `sys.modules["pyaudiowpatch"] = fake` — always use `monkeypatch.setitem` for fixture-scoped cleanup.
  </behavior>
  <action>
    Create `tests/integration/test_audio_backends.py` composing the two shipped mock patterns:

    1. Module docstring + SPDX header. Docstring says: "DEV-04 audio backend matrix. Mocked CoreAudio (sounddevice.query_devices) + mocked WASAPI (pyaudiowpatch via sys.modules injection). Live capture parity rides §V7-LIVE-08/09 (Kaan-clock items per 68-CONTEXT.md)."

    2. Imports + helpers:
       ```python
       import sys
       from unittest.mock import MagicMock
       import pytest
       ```

    3. Reusable helper (LIFTED VERBATIM from `tests/install/test_blackhole_probe.py:23-31`):
       ```python
       def _patch_devices(monkeypatch, devices):
           import sounddevice as sd
           def _fake_query(idx=None):
               if idx is None:
                   return devices
               return devices[idx] if 0 <= idx < len(devices) else {}
           monkeypatch.setattr(sd, "query_devices", _fake_query)
       ```

    4. Reusable helper (LIFTED from `tests/test_audio_windows.py::_make_fake_pa` pattern):
       ```python
       def _inject_fake_pyaudiowpatch(monkeypatch, loopback_info=None, raises_oserror=False):
           fake_pa_mod = MagicMock()
           fake_instance = MagicMock()
           if raises_oserror:
               fake_instance.get_default_wasapi_loopback_device.side_effect = OSError("no loopback driver")
           else:
               fake_instance.get_default_wasapi_loopback_device.return_value = loopback_info
           fake_pa_mod.PyAudio.return_value = fake_instance
           # Prevent stale import from shadowing the mock
           sys.modules.pop("vibemix.platform._audio_windows", None)
           monkeypatch.setitem(sys.modules, "pyaudiowpatch", fake_pa_mod)
       ```

    5. Five tests (one per scenario above), each `@pytest.mark.integration`. macOS tests follow the verbatim shape from 68-RESEARCH §Pattern 4. Windows tests:

       ```python
       @pytest.mark.integration
       def test_audio_backend_windows_wasapi_loopback_found(monkeypatch):
           _inject_fake_pyaudiowpatch(monkeypatch, loopback_info={
               "name": "Speakers (Realtek) [Loopback]",
               "index": 7,
               "defaultSampleRate": 48000.0,
           })
           from vibemix.platform._audio_windows import assert_wasapi_loopback_rate
           index, name = assert_wasapi_loopback_rate(expected=48000)
           assert index == 7
           assert "Loopback" in name

       @pytest.mark.integration
       def test_audio_backend_windows_no_loopback_driver_fallback(monkeypatch):
           _inject_fake_pyaudiowpatch(monkeypatch, raises_oserror=True)
           from vibemix.platform._audio_windows import assert_wasapi_loopback_rate
           with pytest.raises(OSError):
               assert_wasapi_loopback_rate(expected=48000)
       ```

       Adjust the import path / function name if `_audio_windows.py` source reveals a different signature (e.g., the function may be a method on a class, or the lazy-import boundary may be different). Read first — the goal is "exercise the actual production callsite the wizard uses on Windows", not invent a parallel surface.

    6. NO new fixtures in conftest.py — each test self-contains its mock setup via `monkeypatch`.
  </action>
  <verify>
    <automated>uv run pytest tests/integration/test_audio_backends.py -m integration -v 2&gt;&amp;1 | tee /tmp/68P03-T2.log | tail -30 &amp;&amp; grep -c PASSED /tmp/68P03-T2.log | awk '{exit ($1 &gt;= 4 ? 0 : 1)}'</automated>
  </verify>
  <acceptance_criteria>
    - `uv run pytest tests/integration/test_audio_backends.py -m integration -v` exits 0 with ≥ 4 PASSED rows (BlackHole 2ch + 16ch + no-blackhole + WASAPI-found + optional no-loopback = 4 or 5).
    - `grep -c "sys.modules\[" tests/integration/test_audio_backends.py` == 0 (no bare sys.modules assignment — must use `monkeypatch.setitem` per 68-RESEARCH Pitfall #4).
    - `grep -c "monkeypatch.setitem(sys.modules" tests/integration/test_audio_backends.py` ≥ 1 (the safe pattern IS present).
    - `grep -c "@pytest.mark.integration" tests/integration/test_audio_backends.py` ≥ 4 (every test carries the marker).
    - `git diff --stat -- src/vibemix/install/blackhole_probe.py src/vibemix/platform/_audio_windows.py` shows ZERO modifications (source untouched).
    - File is ≥ 90 lines.
  </acceptance_criteria>
  <done>
    File exists, ≥ 4 audio-backend rows GREEN covering BlackHole 2ch + 16ch + absent + WASAPI loopback (+ optional WASAPI no-loopback OSError surface), mock pattern is fixture-scoped (monkeypatch), source code under `vibemix.install.blackhole_probe` + `vibemix.platform._audio_windows` is untouched; DEV-04 closed.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| v4.0 P53 hot-plug path | `_midi_common.handle_port_change_single_state` + `state.mark_disconnected` — load-bearing in the live binding loop; tests must be read-only |
| Audio backend mocks | sys.modules injection must NOT bleed across tests (Pitfall #4); use monkeypatch.setitem for fixture-scoped cleanup |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-68P03-01 | Tampering | v4.0 P53 callback source | mitigate | Acceptance gate `git diff --stat -- src/vibemix/platform/_midi_common.py src/vibemix/midi/state.py` MUST be empty; tests import + invoke, never edit. |
| T-68P03-02 | Tampering | Test cross-contamination via sys.modules | mitigate | All sys.modules injection uses `monkeypatch.setitem` (fixture-scoped cleanup) — bare `sys.modules[x] = mock` is forbidden by acceptance grep. |
| T-68P03-03 | DoS | Real port open attempt | mitigate | Hot-plug test monkeypatches `spawn_listener` to `_DummyThread()` BEFORE any `handle_port_change_single_state` call (per 68-RESEARCH Pitfall #3). No `mido.open_input` import in the test file. |
| T-68P03-04 | Disclosure | Test failure messages | accept | Failure messages include profile_id / device-name — public catalog data, no PII. |
| T-68P03-SC | Tampering | npm/pip/cargo installs | accept | Plan installs no packages. `sounddevice`, `pyaudiowpatch`, `pytest` already in `uv.lock`. |
</threat_model>

<verification>
- `uv run pytest tests/integration/test_hotplug_matrix.py -m integration -v` — 3 GREEN rows (FLX4, DDJ-400, Inpulse-500).
- `uv run pytest tests/integration/test_audio_backends.py -m integration -v` — ≥ 4 GREEN rows (BlackHole 2ch + 16ch + absent + WASAPI loopback + optional no-loopback OSError).
- `git diff --stat -- src/vibemix/platform/_midi_common.py src/vibemix/midi/state.py src/vibemix/install/blackhole_probe.py src/vibemix/platform/_audio_windows.py` shows zero modifications.
- `uv run pytest -q` (full default grid, no `-m integration`) — does NOT collect the new tests by default; baseline preserved.
- `uv run pytest -m integration -q` — full integration suite still GREEN, includes the new rows.
</verification>

<success_criteria>
- DEV-03 closed (ROADMAP P68 SC#3): hot-plug (connect → disconnect → reconnect with state preservation) GREEN across 3 distinct profiles (FLX4 + DDJ-400 + Inpulse-500) via `tests/integration/test_hotplug_matrix.py`; the v4.0 P53 single-state callback path survives untouched.
- DEV-04 closed (ROADMAP P68 SC#4): audio backend matrix GREEN with mocked CoreAudio (BlackHole 2ch + 16ch + absent) and mocked WASAPI (loopback + no-loopback fallback) via `tests/integration/test_audio_backends.py`.
- Live FLX4 plug/unplug + real BlackHole + real WASAPI confirmations ride to KAAN-ACTION §V7-LIVE-08/09/10 in Wave 4 (P05).
</success_criteria>

<output>
Create `.planning/phases/68-all-devices-ready/68-03-SUMMARY.md` when done. Summary MUST record:
- Exact GREEN row counts per test file (3 for hotplug, ≥ 4 for audio backends).
- Confirmation that `git diff --stat` against the 4 sacred source paths (`_midi_common.py`, `midi/state.py`, `blackhole_probe.py`, `_audio_windows.py`) is empty.
- Any signature surprise found while reading the source (e.g., `assert_wasapi_loopback_rate` returns a different shape than 68-RESEARCH described; or `ListenerHolder` has different field names).
- The 3 sample CCs picked per profile for the hot-plug test (so Wave 4's §V7-LIVE-10 live FLX4 ear-pass discharge can verify the same CC fires on real hardware).
</output>
