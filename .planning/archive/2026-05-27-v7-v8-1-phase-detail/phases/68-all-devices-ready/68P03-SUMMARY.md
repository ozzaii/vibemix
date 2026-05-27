---
phase: 68-all-devices-ready
plan: 03
subsystem: midi+platform
tags: [integration, hot-plug, audio-backend, mock-matrix, dev-03, dev-04]
requirements:
  - DEV-03
  - DEV-04
provides:
  - "3-row parametrized hot-plug matrix exercising the v4.0 P53 single-state callback across pioneer_ddj_flx4 + pioneer_ddj_400 + hercules_inpulse_500"
  - "5-row audio backend mock matrix (BlackHole 2ch + BlackHole 16ch + no-BlackHole graceful + WASAPI loopback @ 48k + WASAPI no-loopback OSError fallback)"
  - "read-only invariant on v4.0 P53 hot-plug + Phase 33 BlackHole probe + Phase 33/Wave-2 WASAPI guard (git diff --stat empty across all 4 sacred source paths)"
affects:
  - tests/integration/ (8 pre-existing tests → 16 — +8 new integration rows; default suite 4139 → 4147, all GREEN)
tech-stack:
  added: []
  patterns:
    - "parametrize across 3 profiles by lifting tests/midi/test_disconnect_reconnect.py's _DummyThread + _make_holder + _stub_spawn_listener helpers verbatim (no abstraction into conftest)"
    - "monkeypatch.setitem(sys.modules, 'pyaudiowpatch', MagicMock()) + sys.modules.pop('vibemix.platform._audio_windows', ...) for fixture-scoped Windows mock that survives test repetition (68-RESEARCH Pitfall #4)"
key-files:
  created:
    - tests/integration/test_hotplug_matrix.py
    - tests/integration/test_audio_backends.py
  modified: []
  deleted: []
decisions:
  - "Lifted helpers verbatim from tests/midi/test_disconnect_reconnect.py rather than extracting to tests/integration/conftest.py — keeps the new file self-contained and lets the disconnect_reconnect test file stay the canonical reference (68-RESEARCH Wave 0 Gaps optional note)"
  - "Inpulse-500 sample CC adjusted from the plan's (0, 15, 90) → (1, 4, 90) — that profile's channel-0/cc-15 lookup is empty; the equivalent eq_low_a lives on channel 1, cc 4 (verified via load_profile + ControlBinding inspection before writing the test)"
  - "Did NOT touch list_profiles() / _parse_profile / mark_disconnected / handle_port_change_single_state / assert_wasapi_loopback_rate / probe_blackhole — Threat T-68P03-01 gate held"
  - "Used pytest.raises(OSError, match='no loopback') rather than the SampleRateMismatchError surface for the no-loopback fallback test — Assumption A6 (OSError propagation IS the fallback surface) is verified to be the literal behavior in assert_wasapi_loopback_rate (the function lazy-imports pyaudiowpatch and calls get_default_wasapi_loopback_device → any exception propagates through the finally block that still terminates the PyAudio instance)"
metrics:
  duration: ~6 min (15:13:29 → 15:19:50 TRT)
  completed_date: 2026-05-23
  files_touched: 2
  insertions: 385
  deletions: 0
  baseline_before: 4139 passed / 26 skipped / 4 xpassed / 0 failed (post-Wave-1)
  baseline_after: 4147 passed / 26 skipped / 4 xpassed / 0 failed
  baseline_delta: "+8 tests (3 hotplug parametrized rows + 5 audio backend rows); 26 skipped + 4 xpassed unchanged; 0 failed; wall-clock 220.58s within Wave-1 baseline sd"
  task1_commit_sha: 5f243d1
  task2_commit_sha: f12edbb
---

# Phase 68 Plan 03: Wave 2 Integration Matrices Summary

**One-liner:** Closed DEV-03 (hot-plug across 3 distinct profiles) and DEV-04 (4-fixture audio backend matrix covering BlackHole 2ch/16ch + WASAPI loopback + no-loopback fallback) via two integration-marked test files that compose the already-shipped v4.0 P53 single-state callback + Phase 33 sounddevice mock pattern + Phase 33/Wave-2 pyaudiowpatch sys.modules injection — `+8` GREEN integration rows on top of the post-Wave-1 baseline, zero regressions, zero `src/vibemix/{midi,platform,install}/` edits, zero new dependencies.

## Objective

Wave 2 of Phase 68. Wave 0 collapsed the duplicate catalog; Wave 1 pinned every bundled profile's contract + decode. Wave 2 lifts the same "compose existing patterns, never invent" approach into the integration tier:

1. **DEV-03 — hot-plug matrix** (`tests/integration/test_hotplug_matrix.py`): parametrize the canonical v4.0 P53 single-state callback (`handle_port_change_single_state`) across three distinct profiles — Pioneer DDJ-FLX4 · Pioneer DDJ-400 · Hercules DJControl Inpulse 500 — asserting the connect → disconnect → reconnect cycle preserves `id(controller_state)`, clears the moves ring on disconnect (v4.0 P53 `mark_disconnected` ring-clear in `src/vibemix/midi/state.py`), and resumes decode on a fresh ring on reconnect. The production callback is the test surface — never modified.

2. **DEV-04 — audio backend mock matrix** (`tests/integration/test_audio_backends.py`): mock the two production audio device-enumeration boundaries vibemix relies on — `sounddevice.query_devices()` on macOS (BlackHole probe via `vibemix.install.blackhole_probe`) and `pyaudiowpatch.PyAudio()` on Windows (WASAPI loopback guard via `vibemix.platform._audio_windows::assert_wasapi_loopback_rate`). Five mock fixtures covering present-2ch / present-16ch / absent-graceful / loopback-found / no-loopback-OSError, all fixture-scoped via `monkeypatch.setattr` + `monkeypatch.setitem(sys.modules, ...)`.

Live hardware confirmations (real FLX4 plug/unplug + real BlackHole capture + real WASAPI loopback) ride KAAN-ACTION §V7-LIVE-08/09/10 on the Wave 4 (P05) clock — Wave 2 is the engineering-green close.

## What Shipped

**Two commits — strict one-file-per-task atomic split:**

| Task | Commit | File | Lines | Test cases |
| ---- | ------ | ---- | ----- | ---------- |
| 1 | `5f243d1` — `test(68-03): hot-plug matrix across 3 profiles — DEV-03` | `tests/integration/test_hotplug_matrix.py` | 173 | 3 GREEN parametrized |
| 2 | `f12edbb` — `test(68-03): audio backend mock matrix (BlackHole + WASAPI) — DEV-04` | `tests/integration/test_audio_backends.py` | 212 | 5 GREEN |

**Net stats:** 2 files created · 385 insertions · 0 deletions · 2 commits.

### `tests/integration/test_hotplug_matrix.py` (173 lines)

One parametrized test `test_hotplug_single_state_across_three_profiles(monkeypatch, profile_id, port_name, sample_cc)` over an explicit 3-row `_PROFILES` list. Per row: stub `spawn_listener` to a `_DummyThread`, build a `ListenerHolder` seeded with a `ControllerState(profile=…)` + fake mido (lifted verbatim from `tests/midi/test_disconnect_reconnect.py:_make_holder`), capture `orig_id = id(controller_state)`, then drive a CONNECT → state-mutate → DISCONNECT → RECONNECT sequence asserting:

| Phase | Invariant pinned |
| ----- | ---------------- |
| CONNECT | `is_connected() is True`, `bound_port == port_name`, `id(controller_state) == orig_id` (no rebuild) |
| state mutate | one synthetic `control_change` for a real binding → `len(moves_since(0.0)) >= 1` (decode wiring intact for this profile) |
| DISCONNECT | `is_connected() is False`, `moves_since(0.0) == []` (ring cleared per v4.0 P53), `bound_port is None`, `id(controller_state) == orig_id` (still no rebuild) |
| RECONNECT | `is_connected() is True`, `id(controller_state) == orig_id`, `moves_since(0.0) == []` (fresh ring) |

The 3 sample CCs picked per profile (each verified against the loaded profile's `controls` dict at write-time so the row actually fires):

| Profile | Port name (substring) | Sample CC (channel, cc, value) | Binding hit |
| ------- | --------------------- | ------------------------------ | ----------- |
| `pioneer_ddj_flx4` | `DDJ-FLX4 USB MIDI` | `(0, 19, 110)` | `vol_a` (deck A volume, unipolar) |
| `pioneer_ddj_400` | `DDJ-400` | `(0, 19, 100)` | `vol_a` (deck A volume, unipolar) |
| `hercules_inpulse_500` | `DJControl Inpulse 500` | `(1, 4, 90)` | `eq_low_a` (deck A EQ low, unipolar) |

The Inpulse-500 row is the one place the plan's suggested sample (`(0, 15, 90)`) had to be adjusted — that profile's channel 0 has no CC 15 binding (its eq_low_a lives on channel 1, cc 4). The plan explicitly flagged the row 3 sample as "or similar"; the picked alternative still exercises the same shape (unipolar EQ knob → `moves_since(0.0)` surfaces a knob tier-cross or big-delta move). This sample CC is also the load-bearing knob for the future §V7-LIVE-10 live ear-pass on the Inpulse-500 (whenever a unit lands).

Helpers (`_DummyThread`, `_make_holder`, `_stub_spawn_listener`) were lifted verbatim from `tests/midi/test_disconnect_reconnect.py:45-77` per 68-RESEARCH Pattern 3 — the disconnect_reconnect file stays the canonical reference; the new file keeps these self-contained rather than abstracting into a shared `conftest.py` (the wave's optional-extraction note left this to discretion; self-contained reads cleaner for a 3-row parametrize).

### `tests/integration/test_audio_backends.py` (212 lines)

Five `@pytest.mark.integration`-marked tests, no parametrize (the failure-modes are heterogeneous enough that explicit per-case test names read better in `pytest -v`):

| # | Test | Mock surface | Asserts |
| - | ---- | ------------ | ------- |
| 1 | `test_audio_backend_macos_blackhole_2ch_present` | `sd.query_devices` returns `[{"name": "BlackHole 2ch", "max_output_channels": 2}, {"name": "AirPods Pro", ...}]` | `probe_blackhole(retry_on_missing=False) == {"installed": True, "device_name": "BlackHole 2ch"}` |
| 2 | `test_audio_backend_macos_blackhole_16ch_present` | `[{"name": "BlackHole 16ch", "max_output_channels": 16}]` | `installed is True`, `device_name == "BlackHole 16ch"` (variant accepted) |
| 3 | `test_audio_backend_macos_no_blackhole_graceful` | `[{"name": "Built-in Output", ...}, {"name": "AirPods Pro", ...}]` | `{"installed": False, "device_name": None}` (graceful fallback; the wizard CTA branch) |
| 4 | `test_audio_backend_windows_wasapi_loopback_found` | `monkeypatch.setitem(sys.modules, "pyaudiowpatch", MagicMock())` with `get_default_wasapi_loopback_device.return_value = {"name": "Speakers (Realtek(R) Audio) [Loopback]", "index": 7, "defaultSampleRate": 48000.0, "maxInputChannels": 2}` | `assert_wasapi_loopback_rate(expected=48000)` returns `(7, "...Loopback...")` |
| 5 | `test_audio_backend_windows_no_loopback_driver_fallback` | same shape but `get_default_wasapi_loopback_device.side_effect = OSError("no loopback driver")` | `pytest.raises(OSError, match="no loopback")`, plus the temporary `PyAudio` instance's `terminate()` is called exactly once via the production `finally` block (no leak on the raise path) |

Two reusable helpers, each lifted verbatim from the canonical references:

- `_patch_devices` — exactly the shape from `tests/install/test_blackhole_probe.py:23-31` (the `idx is None → list` / `0 <= idx < len(devices) → dict` / `else → {}` branch matches the production `_query_devices()` indirection's expectations).
- `_inject_fake_pyaudiowpatch` — the `tests/test_audio_windows.py::_make_fake_pa` shape, with one additive feature: `raises_oserror=True` flips the loopback query to raise `OSError("no loopback driver")` instead of returning a dict. Calls `sys.modules.pop("vibemix.platform._audio_windows", None)` before the `monkeypatch.setitem` so the next `from vibemix.platform._audio_windows import assert_wasapi_loopback_rate` re-binds the lazy `import pyaudiowpatch` against the fake (no stale-module shadowing across tests — 68-RESEARCH Pitfall #4 mitigation).

Anti-pattern guarded by acceptance gate: zero bare `sys.modules[...] = mock` lines (grep `sys.modules\[` returns 0 — the docstring was rewritten mid-task from `sys.modules[x] = mock` to "sys.modules assignment" prose so the literal grep gate fires).

## Acceptance Criteria — All Met

| Criterion | Result |
| --------- | ------ |
| `uv run pytest tests/integration/test_hotplug_matrix.py -m integration -v` exits 0 with exactly 3 PASSED rows | ✓ 3/3 GREEN (0.19s wall) |
| `git diff --stat -- src/vibemix/platform/_midi_common.py src/vibemix/midi/state.py` shows ZERO modifications | ✓ empty diff |
| `grep -c "@pytest.mark.integration" tests/integration/test_hotplug_matrix.py` ≥ 1 | ✓ 1 |
| `grep -c "mido.open_input\|rtmidi" tests/integration/test_hotplug_matrix.py` == 0 | ✓ 0 (no real port opens) |
| `grep -c "spawn_listener" tests/integration/test_hotplug_matrix.py` ≥ 1 | ✓ 6 (stub function name + docstring refs — all the load-bearing usages) |
| `tests/integration/test_hotplug_matrix.py` ≥ 70 lines | ✓ 173 |
| `uv run pytest tests/integration/test_audio_backends.py -m integration -v` exits 0 with ≥ 4 PASSED rows | ✓ 5/5 GREEN (0.19s wall) |
| `grep -c "sys.modules\[" tests/integration/test_audio_backends.py` == 0 (no bare sys.modules assignment) | ✓ 0 |
| `grep -c "monkeypatch.setitem(sys.modules" tests/integration/test_audio_backends.py` ≥ 1 | ✓ 2 |
| `grep -c "@pytest.mark.integration" tests/integration/test_audio_backends.py` ≥ 4 | ✓ 5 |
| `git diff --stat -- src/vibemix/install/blackhole_probe.py src/vibemix/platform/_audio_windows.py` shows ZERO modifications | ✓ empty diff |
| `tests/integration/test_audio_backends.py` ≥ 90 lines | ✓ 212 |
| `uv run pytest -m integration -q` exits 0 (full integration suite) | ✓ 16 passed / 4161 deselected in 6.67s (8 pre-existing + 8 new) |
| `uv run pytest -q` default-suite baseline preserved | ✓ 4147 passed / 26 skipped / 4 xpassed / 0 failed (+8 vs Wave-1 baseline of 4139, exactly the 3 + 5 new rows; zero regressions) |
| Wall-clock for full suite | 220.58s — within the post-Wave-1 218.09s baseline sd (no perf regression) |

### Read-only invariant on all 4 sacred source paths

```
git diff --stat HEAD~2 HEAD -- \
  src/vibemix/platform/_midi_common.py \
  src/vibemix/midi/state.py \
  src/vibemix/install/blackhole_probe.py \
  src/vibemix/platform/_audio_windows.py
```

→ empty output. The v4.0 P53 hot-plug callback path, the v4.0 P53 mark_disconnected ring-clear, the Phase 33 BlackHole probe, and the Phase 33/Wave-2 WASAPI loopback guard are all unmodified across this plan. Threat T-68P03-01 (Tampering: v4.0 P53 callback source) and T-68P02-equivalent (Tampering: audio probe / guard sources) — held.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan's Inpulse-500 sample CC (0, 15, 90) doesn't exist in that profile**

- **Found during:** Task 1 write — verifying the row 3 sample CC against the loaded profile before committing to the parametrize list
- **Issue:** The plan's `_PROFILES` table reads `("hercules_inpulse_500", "DJControl Inpulse 500", (0, 15, 90))` with comment "eq_low_a or similar". The actual `pioneer_ddj_flx4`-style binding shape (channel=0, cc=15 → eq_low_a) does NOT apply to Inpulse-500 — that profile uses channel 1, cc 4 for its `eq_low_a`. A `handle_msg` against `(0, 15, ...)` would hit no binding and `moves_since(0.0)` would be empty, failing the row.
- **Fix:** Rewrote the row 3 entry to `("hercules_inpulse_500", "DJControl Inpulse 500", (1, 4, 90))` after `PYTHONPATH=src python3 -c "from vibemix.midi import load_profile; ..."` confirmed `(1, 4)` maps to `eq_low_a` on the Inpulse-500. The plan explicitly flagged the row 3 sample with "or similar", so the adjustment is in-scope; the SUMMARY records the picked CC so future §V7-LIVE-10 live ear-pass on a real Inpulse-500 fires the same knob.
- **Files modified:** `tests/integration/test_hotplug_matrix.py` (the row 3 tuple)
- **Why no Rule 4 (architectural):** picking a different CC inside the same parametrize row is a sample-data choice, not a structural change. The test's assertion shape stays identical across all three rows.

**2. [Rule 1 - Bug] Docstring contained literal `sys.modules[x] = mock` triggering the acceptance grep gate**

- **Found during:** Task 2 verification — `grep -cE 'sys\.modules\[' tests/integration/test_audio_backends.py` returned 1 (acceptance gate requires 0)
- **Issue:** The `_inject_fake_pyaudiowpatch` helper docstring explained the anti-pattern by reproducing the literal forbidden form `sys.modules[x] = mock`. The grep gate doesn't distinguish between docstring prose and live code — both surface as a hit.
- **Fix:** Reworded the docstring sentence from `never bare ``sys.modules[x] = mock`` (...)` to `never bare sys.modules assignment (...)`. Semantic meaning preserved; literal `sys.modules[` no longer present anywhere in the file. Re-ran the full test file and the grep — 5/5 GREEN, 0 bare hits.
- **Files modified:** `tests/integration/test_audio_backends.py` (one docstring line)
- **Why a bug and not a style nit:** acceptance gate enforcement is part of the plan's success criteria; failing to satisfy the literal gate would have blocked the commit. Caught by the verification phase, fixed before commit, no leakage.

### Plan-level TDD gate sequence

Both Wave 2 tasks were authorized as `tdd="true"` (RED → GREEN → REFACTOR). Same pattern as Wave 1 — the gate logic enforced by both test files is a property the production code already satisfies (v4.0 P53 + Phase 33 surfaces are mature and pinned by their own existing tests; Wave 2's job is parametrizing across multiple profiles / mock fixtures, not introducing new behaviour). Running the test files against the current tree produces GREEN immediately. Per the TDD execution flow's fail-fast rule, an unexpected GREEN at RED phase requires investigation — investigation here confirms the tests are testing what they say (every assertion is observable behavior of the existing production paths; the parametrize spreads the assertion across 3 distinct profile bindings and 4 distinct audio device-enumeration mock surfaces). The "TDD RED" gate fires for any FUTURE regression in the v4.0 P53 single-state invariant or the Phase 33 BlackHole/WASAPI probe contract; landing the tests against the current GREEN production code is the correct flow for test-only WIP that pins existing behavior.

Both commits use `test(...)` prefix (no `feat(...)` commit because zero production code was added — the production code already exists and is being pinned across additional dimensions, not built).

### Auth Gates

None.

## Threat-model verification

| Threat ID | Disposition | How verified |
| --------- | ----------- | ------------ |
| T-68P03-01 (Tampering: v4.0 P53 callback source) | mitigate | `git diff --stat HEAD~2 HEAD -- src/vibemix/platform/_midi_common.py src/vibemix/midi/state.py` is empty across both task commits — every assertion drives the production callback through monkeypatched `spawn_listener` + fake mido + real `handle_port_change_single_state` import; source untouched. |
| T-68P03-02 (Tampering: test cross-contamination via sys.modules) | mitigate | All pyaudiowpatch injection uses `monkeypatch.setitem(sys.modules, "pyaudiowpatch", fake)` — fixture-scoped cleanup. Bare `sys.modules[x] = mock` is grep-gated to zero across the file (Rule 1 fix above). The 5 audio backend tests run in succession in `pytest -m integration` (test 4 then test 5 reuses the injection helper) and both pass cleanly — no contamination from test 4's `loopback_info` dict bleeding into test 5's `side_effect = OSError(...)`. |
| T-68P03-03 (DoS: real port open attempt) | mitigate | Hot-plug test monkeypatches `spawn_listener` to `_DummyThread()` BEFORE any `handle_port_change_single_state` call (per the canonical Phase 53 pattern). `grep -c "mido.open_input\|rtmidi" tests/integration/test_hotplug_matrix.py` returns 0 — no real port open imports. The fake mido inside `_make_holder` exposes `open_input` as a context-manager returning `poll=lambda: None`, but that path is never reached because `spawn_listener` is stubbed. |
| T-68P03-04 (Disclosure: test failure messages) | accept | All failure messages embed `profile_id` (hotplug) or device-name (audio). Profile IDs + device names are public catalog data — no PII. |
| T-68P03-SC (Tampering: npm/pip/cargo installs) | accept | Plan installs no packages. `pyproject.toml` + `uv.lock` both untouched (verified via `git diff` of staged files at both commits). |

## Open Questions Resolved

**68-RESEARCH §Pitfall #4 — WASAPI mock contamination across tests.**

**Answer: `monkeypatch.setitem(sys.modules, ...)` + per-helper `sys.modules.pop("vibemix.platform._audio_windows", None)` is sufficient.**

Rationale: the two WASAPI tests in this file (`test_audio_backend_windows_wasapi_loopback_found` + `test_audio_backend_windows_no_loopback_driver_fallback`) both inject a fresh `MagicMock` via the helper. The helper's `sys.modules.pop("vibemix.platform._audio_windows", None)` evicts the stale `_audio_windows` module from the cache, so the next `from vibemix.platform._audio_windows import assert_wasapi_loopback_rate` re-imports the module fresh — and at re-import time, the lazy `import pyaudiowpatch` inside the function body picks up the new MagicMock. The two tests run cleanly in sequence with no leakage (verified locally; per-test `terminate()` `call_count` is exactly 1 in each).

If a future plan adds a third WASAPI test with a different `loopback_info` shape, the same helper invocation will work — no `conftest.py` extraction needed yet.

## Binding-Shape Observations (for Wave 4 KAAN-ACTION live ear)

The 3 sample CCs used in the hot-plug test are the load-bearing knobs to verify on real hardware during the §V7-LIVE-10 live ear-pass:

- **FLX4** — `(channel=0, cc=19, value=110)` is `vol_a` (the deck A volume slider all the way up). Live: with FLX4 plugged + djay Pro in focus, pushing the channel A volume slider to max should fire a `moves_since(0.0)` entry with `A_vol up (big)` or similar.
- **DDJ-400** — `(channel=0, cc=19, value=100)` is the same `vol_a` (Pioneer reuses the binding shape across the DDJ family). Live: same hardware action.
- **Inpulse-500** — `(channel=1, cc=4, value=90)` is `eq_low_a`. Live: rotating the deck A EQ low knob away from center should fire a knob tier-cross move (e.g. `flat→cut`).

These three knobs are the smallest sufficient sample for the §V7-LIVE-10 ear-pass; broader binding coverage rides Wave 1's `test_profile_smokes.py` (which already exercises every CC + NOTE binding across all 10 profiles).

## Known Stubs / Threat Flags

None. Two new test files; zero production code touched; zero new dependencies; no new surfaces introduced.

## Self-Check: PASSED

Verified post-write (and re-confirmed after the `9cd0132` metadata commit):

- **Files created exist:**
  - `tests/integration/test_hotplug_matrix.py` — FOUND (173 lines, `wc -l` confirms)
  - `tests/integration/test_audio_backends.py` — FOUND (212 lines, `wc -l` confirms)
  - `.planning/phases/68-all-devices-ready/68P03-SUMMARY.md` — this file
- **Commits exist on `live-tuning-or-brain`:**
  - `5f243d1` (Task 1) — `git log --oneline -3` confirms
  - `f12edbb` (Task 2) — `git log --oneline -3` confirms
- **Test count delta verified:**
  - Pre-Wave-2: 4139 passed (post-Wave-1 baseline from 68P02-SUMMARY.md)
  - Post-Wave-2: 4147 passed (full-suite run after Task 2 commit; wall-clock 220.58s)
  - Delta: +8 (exactly 3 hotplug parametrized rows + 5 audio backend rows) ✓ math reconciled
- **Sacred-source paths read-only:**
  - `git diff --stat HEAD~2 HEAD -- src/vibemix/platform/_midi_common.py src/vibemix/midi/state.py src/vibemix/install/blackhole_probe.py src/vibemix/platform/_audio_windows.py` → empty (verified directly above)

## What's next

Phase 68 Wave 3 (Plan 68P04) — contributor recipe: `scripts/discover_midi_port.py` (≤ 30 lines, `mido.get_input_names()` cross-platform lister) + `docs/contributing/_template.json` (clean controller profile copy-target) + `docs/contributing/add-a-controller.md` (≤ 200 lines, 4-step + PR checklist). The Wave 2 baseline (4147) is what Wave 3 should target. Wave 4 (68P05) — append §V7-LIVE-07..10 KAAN-ACTION clusters (controller-recipe smoke · macOS BlackHole live · Windows WASAPI live · live FLX4 hot-plug ear).
