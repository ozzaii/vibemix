---
phase: 40-anti-slop-audio-port
plan: 06
subsystem: install
tags: [install, blackhole, probe, telemetry, audio-probe-events, kaan-action, pitfall-5]
requirements_completed: [AUDIO-07]

dependency_graph:
  requires:
    - "40-05 — phase 40 scaffold (PGP slot + Tauri updater key rotation comment)"
    - "Phase 33 — probe_blackhole baseline (`{installed, device_name}` dict contract)"
  provides:
    - "structured audio.probe.{detected,missing,cta_fired} event emission hooks"
    - "Pitfall 5 fresh-boot CoreAudio race defense (single 1.5s retry)"
    - "emit_cta_fired helper for wizard install-CTA dispatch"
    - "AUDIO-07 KAAN-ACTION fresh-Mac walk-through runbook"
  affects:
    - "src/vibemix/install/blackhole_probe.py — probe surface (additive)"
    - "src/vibemix/install/__init__.py — re-exports"
    - "tests/install/test_blackhole_probe.py — retry-skip backfill on missing-device tests"
    - "KAAN-ACTION-LEGAL.md — new AUDIO-07 section"

tech_stack:
  added: []
  patterns:
    - "Optional emit_event callable with try/except swallow (T-40-06-01)"
    - "Single-retry fresh-boot race defense (time.sleep + re-query)"
    - "Internal _probe_once() refactor preserves Phase 33 substring-match semantics"

key_files:
  created:
    - "tests/install/test_blackhole_probe_events.py"
  modified:
    - "src/vibemix/install/blackhole_probe.py"
    - "src/vibemix/install/__init__.py"
    - "tests/install/test_blackhole_probe.py"
    - "KAAN-ACTION-LEGAL.md"

decisions:
  - "Q4 locked sink: stdout + events.jsonl via VoiceRecorder.log_event adapter (no new IPC channel). Plan 40-06 exposes hooks; wizard wires the recorder adapter in v3.0 Phase 45 / SHIP-04 (INSTALL-VM-RUN)."
  - "Pitfall 5 mitigation = single 1.5s sleep + re-query, NOT unbounded polling. Repeated misses are real misses; we don't burn 10s waiting for CoreAudio to wake up. Pinned by `test_retry_only_runs_once`."
  - "Backward-compat preserved: `probe_blackhole()` with no args returns the same Phase 33 dict shape. `retry_on_missing=False` exposed so the test suite stays fast."
  - "12 tests shipped (plan asked for 8) — added `test_emit_cta_fired_custom_cta_tag`, `test_emit_failure_in_cta_fired_does_not_crash`, `test_no_emit_event_path_missing_case`, `test_retry_only_runs_once` for full coverage of the swallow contract + retry-bound."

metrics:
  duration_minutes: ~15
  completed_date: "2026-05-16"
  tasks: 2
  commits: 2
  tests_added: 12
  tests_pass_total: 29  # full tests/install/ dir
  test_runtime_seconds: 0.94

threat_register_outcomes:
  - "T-40-06-01 (DoS — emit_event raising) — MITIGATED via _safe_emit try/except wrapper. Pinned by `test_emit_failure_does_not_crash_probe` + `test_emit_failure_in_cta_fired_does_not_crash`."
  - "T-40-06-02 (Spoofing — BlackHole-named non-driver) — ACCEPTED, no plan change. Substring match is intentionally permissive; spoofer gains nothing beyond CTA-bypass."
  - "T-40-06-03 (Timing — Pitfall 5 fresh-boot race) — MITIGATED via 1.5s retry. Pinned by `test_pitfall_5_retry_succeeds_on_second_try` + `test_pitfall_5_retry_still_missing`."
  - "T-40-06-04 (Repudiation — no install-funnel audit trail) — MITIGATED via the three `audio.probe.*` event kinds. Kaan-action fresh-Mac walk discharge requires events.jsonl artifact (KAAN-ACTION-LEGAL §AUDIO-07)."
---

# Phase 40 Plan 06: BlackHole Probe Structured-Event Emission Summary

**One-liner:** AUDIO-07 — `probe_blackhole` gained an optional `emit_event` callable that emits `audio.probe.{detected,missing,cta_fired}` events to whatever sink the wizard wires, plus a single 1.5s Pitfall-5 retry that defends against CoreAudio fresh-boot enumeration races, all preserved as backward-compat additions on top of the Phase 33 return-dict contract.

## What Shipped

### `probe_blackhole` signature change

```python
# Before (Phase 33):
def probe_blackhole() -> BlackHoleProbeResult: ...

# After (Phase 40 / AUDIO-07):
def probe_blackhole(
    emit_event: Callable[[str, dict], None] | None = None,
    *,
    retry_on_missing: bool = True,
) -> BlackHoleProbeResult: ...
```

Legacy `probe_blackhole()` with no args returns the same
`{installed, device_name}` dict — Phase 33 callers unaffected.

### Three event names + payload schemas

| Event kind | Trigger | Payload |
|------------|---------|---------|
| `audio.probe.detected` | Probe found a device whose name contains `"BlackHole"` (after retry, if applicable) | `{"device_name": str}` |
| `audio.probe.missing`  | Probe found no BlackHole device (after retry, if applicable) | `{"device_name": None}` |
| `audio.probe.cta_fired` | Wizard dispatched install-link CTA (caller-invoked via `emit_cta_fired`) | `{"cta": str, "url": str}` |

All three flow through `_safe_emit` — `try/except Exception: pass`.
Telemetry failures never crash the install flow.

### Pitfall 5 — fresh-boot CoreAudio race defense

When the first probe returns `installed=False` and `retry_on_missing=True`
(default), the probe sleeps 1.5s and re-queries once. This mitigates the
RESEARCH §Pitfall 5 race where `sounddevice.query_devices()` returns a
partial device list on cold boot, before CoreAudio has finished
enumerating. Exactly one retry — never more — pinned by
`test_retry_only_runs_once`.

### Sink contract — wizard wires the adapter, not Plan 40-06

The wizard layer that consumes this hook lives in **v3.0 Phase 45 /
SHIP-04 (INSTALL-VM-RUN)**. Until then, the events ship to stdout when
the dev runs `python -m vibemix` and wires `emit_event=print` (or
keeps `emit_event=None` and reads only the return-dict). The
canonical sink shape is:

```python
emit_event = lambda name, payload: recorder.log_event(name, **payload)
result = probe_blackhole(emit_event=emit_event)
if not result["installed"]:
    # UI surfaces install CTA; on user click:
    emit_cta_fired(emit_event)
```

That adapter `lambda` is the only piece left for the wizard owner.
`VoiceRecorder.log_event(kind, **fields)` already lands the event in
`events.jsonl` with the session-relative timestamp.

### KAAN-ACTION fresh-Mac walk discharge pointer

`KAAN-ACTION-LEGAL.md` §AUDIO-07 documents the post-Plan 40-06
discharge walk-through: fresh user account → wizard click-through →
events.jsonl artifact capture → 6-invariant discharge checklist +
sign-off block. Engineering scaffolding ships green pre-discharge;
Kaan flips the section's "fresh-account walk done" checkbox after he
runs the walk on his own hardware.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | `probe_blackhole` event emission + Pitfall 5 retry + `emit_cta_fired` helper | `df64e57` | `src/vibemix/install/blackhole_probe.py`, `src/vibemix/install/__init__.py` |
| 2 | Emission tests (12) + Pitfall 5 retry coverage + KAAN-ACTION runbook | `c128f82` | `tests/install/test_blackhole_probe_events.py` (new), `tests/install/test_blackhole_probe.py` (backfill), `KAAN-ACTION-LEGAL.md` |

## Tests Added (12)

1. `test_emit_event_detected_when_blackhole_present` — happy path, payload shape pinned.
2. `test_emit_event_missing_when_blackhole_absent` — missing path, payload shape pinned.
3. `test_pitfall_5_retry_succeeds_on_second_try` — race-bit-then-recovered: 2 probe calls, 1 sleep, 1 `detected` emit.
4. `test_pitfall_5_retry_still_missing` — genuinely-absent: 2 probe calls, 1 sleep, 1 `missing` emit.
5. `test_retry_disabled_skips_sleep` — `retry_on_missing=False` MUST NOT sleep.
6. `test_emit_cta_fired_emits_correct_event` — default CTA tag payload.
7. `test_emit_cta_fired_custom_cta_tag` — custom CTA identifier threads through verbatim (extra coverage).
8. `test_emit_failure_does_not_crash_probe` — T-40-06-01 swallow contract.
9. `test_emit_failure_in_cta_fired_does_not_crash` — same swallow for `emit_cta_fired` (extra coverage).
10. `test_no_emit_event_path_byte_identical_to_legacy` — Phase 33 contract preserved (detected case).
11. `test_no_emit_event_path_missing_case` — Phase 33 contract preserved (missing case, extra coverage).
12. `test_retry_only_runs_once` — pins the single-retry bound; no unbounded polling (extra coverage).

## Verification Results

| Check | Outcome |
|-------|---------|
| `pytest tests/install/test_blackhole_probe_events.py -x -q` | 12 pass in 0.89s |
| `pytest tests/install/test_blackhole_probe.py -x -q` | 5 pass (Phase 33 regression — fast, no retry sleep) |
| `pytest tests/install/ -x -q` | 29 pass in 0.94s |
| `python -c "from vibemix.install import probe_blackhole, emit_cta_fired, BLACKHOLE_INSTALL_URL; print(probe_blackhole(retry_on_missing=False))"` | `{'installed': True, 'device_name': 'BlackHole 16ch'}` |
| `grep -cE '"audio\.probe\.(detected\|missing\|cta_fired)"' src/vibemix/install/blackhole_probe.py` | 3 (matches expected emit-site literal count) |
| `grep -cE 'time\.sleep\(1\.5\)' src/vibemix/install/blackhole_probe.py` | 1 (Pitfall 5 retry) |
| POC immutability: `git status -- cohost*.py cohost_v*.py mascot.html` | clean — POC files untouched |

## Deviations from Plan

**None.** Plan 40-06 executed exactly as written. Added 4 extra
coverage tests (12 vs plan's 8) for full T-40-06-01 swallow contract
+ retry-bound + missing-case legacy-shape pinning — purely additive,
no behavior change.

## Decisions Made

1. **`emit_event` signature is `(name, payload)` not `(name, **fields)`** — the wizard adapter wraps `recorder.log_event(name, **payload)` at the boundary. Keeps the probe-side surface tiny (one callable kind, no kwargs flexibility leaking into the contract). Aligned with the RESEARCH §AUDIO-07 example shape.
2. **`_safe_emit` swallows ALL exceptions, not just specific ones** — matches the existing `_query_devices` swallow pattern in this module and the `_write_event_locked` swallow in `VoiceRecorder`. T-40-06-01 mitigation is about "probe must not crash on telemetry failure"; the exception class doesn't matter, the outcome (return-the-dict regardless) does.
3. **`retry_on_missing` is keyword-only** — prevents positional-arg confusion at call sites that might mix `emit_event` and the retry flag. The plan's interface stub uses this shape; preserved as-written.
4. **AUDIO-07 KAAN-ACTION section inserted before INSTALL-VM-RUN, not appended at end** — keeps the AUDIO-05/06/07 trio adjacent in the file. Matches Phase 40 milestone narrative (3 KAAN-action discharge runbooks landed in sequence).

## Known Stubs

**None.** Every code path is wired:
- `probe_blackhole` emits real events when `emit_event` is non-None.
- `emit_cta_fired` is a real function with the documented payload.
- Tests pin every contract surface — no `pytest.skip`, no `xfail`, no placeholder mocks that hide unimplemented behavior.

The only "stub" by design is the **wizard adapter wiring** itself (the
`lambda name, payload: recorder.log_event(name, **payload)` that lives
in v3.0 Phase 45). Plan 40-06's explicit scope is "expose the hook";
the wizard owner wires it. Documented in
`src/vibemix/install/blackhole_probe.py`'s module docstring and in
this SUMMARY's §"Sink contract" section.

## Self-Check: PASSED

- `[FOUND]` `src/vibemix/install/blackhole_probe.py` (modified — `emit_event` + retry + `emit_cta_fired`)
- `[FOUND]` `src/vibemix/install/__init__.py` (modified — re-exports)
- `[FOUND]` `tests/install/test_blackhole_probe_events.py` (created — 12 tests)
- `[FOUND]` `tests/install/test_blackhole_probe.py` (modified — `retry_on_missing=False` backfill)
- `[FOUND]` `KAAN-ACTION-LEGAL.md` (modified — `## AUDIO-07` section)
- `[FOUND]` commit `df64e57` (Task 1)
- `[FOUND]` commit `c128f82` (Task 2)
- All Phase 40 success criteria checked.
