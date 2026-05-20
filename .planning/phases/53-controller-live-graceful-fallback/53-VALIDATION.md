---
phase: 53
slug: controller-live-graceful-fallback
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-21
---

# Phase 53 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Covers BRINGUP-03 (DDJ-FLX4 MIDI live + graceful fallback). Engineering ships deterministic tests + the live-wiring fix; the real-FLX4-in-Kaan's-hands drive is Kaan-action.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (`pyproject.toml [tool.pytest.ini_options]`, `addopts = "-ra --strict-markers"`) |
| **Config file** | `pyproject.toml` (markers + addopts) |
| **Quick run command** | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q <files>` |
| **Full suite command** | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` |
| **Estimated runtime** | ~5s (the new MIDI tests are fake-mido / direct-call, no real device, no sleeps beyond patched waits) |

---

## Sampling Rate

- **After every task commit:** Run that task's quick command (the new MIDI test file).
- **After every plan wave:** Run the full default suite.
- **Before `/gsd:verify-work`:** Full default suite must be green.
- **Max feedback latency:** ~30 seconds (full default suite).

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 53-01-01 | 01 | 1 | BRINGUP-03 | — | N/A (local MIDI, no network/secret) | unit | `pytest -q tests/midi/test_state.py -k disconnect` | ❌ W0 (extends) | ⬜ pending |
| 53-01-02 | 01 | 1 | BRINGUP-03 | — | N/A | unit | `pytest -q tests/midi/test_live_binding_profiles_canonical.py` | ❌ W0 | ⬜ pending |
| 53-01-03 | 01 | 1 | BRINGUP-03 | — | N/A | unit | `pytest -q tests/midi/test_flx4_synthetic_decode.py` | ❌ W0 | ⬜ pending |
| 53-01-04 | 01 | 1 | BRINGUP-03 | — | Generic fallback: unknown device degrades, never crashes | unit | `pytest -q tests/midi/test_generic_fallback.py -k decode` | ❌ W0 (extends) | ⬜ pending |
| 53-02-01 | 02 | 2 | BRINGUP-03 | — | Disconnect leaves no stale state readable by reactions | integration | `pytest -q tests/midi/test_disconnect_reconnect.py` | ❌ W0 | ⬜ pending |
| 53-02-02 | 02 | 2 | BRINGUP-03 | — | Watcher+callback compose; no crash on hot-plug churn | integration | `pytest -q tests/midi/test_watcher_callback_integration.py` | ❌ W0 | ⬜ pending |
| 53-02-03 | 02 | 2 | BRINGUP-03 | — | Live session spawns watcher + cleans it up (no orphan task) | unit (source) | `pytest -q tests/test_main_midi_wiring.py` | ❌ W0 | ⬜ pending |
| 53-02-04 | 02 | 2 | BRINGUP-03 | — | N/A (recipe doc; real drive deferred) | manual recipe | `pytest -q tests/test_midi_macos_live.py` (collects deselected) | ❌ W0 (new or extend) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- New test files (created by their owning task; no separate Wave-0 stub pass needed — existing pytest infra + fake-mido helpers in `tests/midi/test_watcher.py` and `tests/test_midi_common.py` cover fixtures):
  - `tests/midi/test_live_binding_profiles_canonical.py`
  - `tests/midi/test_flx4_synthetic_decode.py`
  - `tests/midi/test_disconnect_reconnect.py`
  - `tests/midi/test_watcher_callback_integration.py`
  - `tests/test_main_midi_wiring.py`
- Extended files: `tests/midi/test_state.py` (disconnect-clears-ring), `tests/midi/test_generic_fallback.py` (generic decode no-crash), `tests/test_midi_macos_live.py` (live recipe — create if absent; the existing live-MIDI file is `tests/test_midi_windows_live.py`, so a macOS FLX4 live recipe file may be new).
- Framework: already installed (pytest 7.x). No install step.

*Existing infrastructure (fake-mido `SimpleNamespace`, `_patch_watcher_sleep`, `ListenerHolder` builders) covers all phase fixtures — reuse, do not re-create.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real FLX4 moves (jog/crossfader/knob/pad) register on the bus/UI during a live session | BRINGUP-03 (SC1) | needs the physical controller + eyes on UI | Plug FLX4; `uv run python -m vibemix`; tap `ws://127.0.0.1:8765`; move jog/crossfader/knobs → confirm moves surface. (Recipe in `tests/test_midi_macos_live.py` docstring.) |
| Mid-set unplug → app keeps running on audio alone, no crash; replug → rebinds | BRINGUP-03 (SC2) | needs physical unplug/replug | During the live session, unplug FLX4 → confirm app keeps running, `connected:false` on bus, no MIDI error spam; replug → confirm decode resumes. |
| Boot with controller absent → full session on audio alone, no MIDI-related log errors | BRINGUP-03 (SC3) | needs a real boot without device | Start `uv run python -m vibemix` with no controller → confirm clean startup, quiet listener retries, no error spam. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (manual rows are real-hardware Kaan-action carveouts, explicitly deferred)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (every engineering task has a runnable command; only the live-recipe row is manual)
- [x] Wave 0 covers all MISSING references (new test files created by owning tasks; fixtures reused from existing MIDI test infra)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-21
