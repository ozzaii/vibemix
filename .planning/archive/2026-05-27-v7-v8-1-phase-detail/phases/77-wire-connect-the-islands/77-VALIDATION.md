---
phase: 77
slug: wire-connect-the-islands
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-26
---

# Phase 77 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `PYTHONPATH=src python3 -m pytest -q -k "wire or grounding or ingest or dotenv or curator or load_env or persona"` |
| **Full suite command** | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` |
| **Estimated runtime** | ~120 seconds (full suite, 4449+ tests) |

---

## Sampling Rate

- **After every task commit:** Run quick run command (scoped `-k`)
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

> Every WIRE-0x requirement maps to an automated proof (no API key needed — honest green). Live e2e on the funded key is a KAAN-ACTION (produce-and-park), never blocks. Wave 0 (Plan 01) creates the failing stubs that Waves 1-2 turn green by removing `xfail(strict=True)` markers.

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 77-01-T1 | 01 | 0 | WIRE-01, WIRE-05 | unit (scaffold) | `pytest -q tests/agent/test_dj_cohost_grounding.py tests/memory/test_ingest_wiring.py` | ⬜ pending |
| 77-01-T2 | 01 | 0 | WIRE-04, WIRE-06 | unit (scaffold) | `pytest -q tests/library/test_curator_persona_seam.py tests/runtime/test_load_env_override.py` | ⬜ pending |
| 77-01-T3 | 01 | 0 | WIRE-02, WIRE-03 | regression pin | `pytest -q tests/repo/test_wire_regression_pins.py` | ⬜ pending |
| 77-02-T1 | 02 | 1 | WIRE-04 | unit + source-text | `pytest -q tests/prompts/test_matrix.py tests/library/test_curator_persona_seam.py` | ⬜ pending |
| 77-02-T2 | 02 | 1 | WIRE-04 | unit + source-text | `pytest -q tests/library/test_agent.py tests/library/test_codex_curate.py tests/library/test_curator_persona_seam.py` | ⬜ pending |
| 77-03-T1 | 03 | 1 | WIRE-06 | unit | `pytest -q tests/runtime/test_load_env_override.py` | ⬜ pending |
| 77-04-T1 | 04 | 2 | WIRE-01 | unit (off-loop) | `pytest -q tests/agent/test_dj_cohost_grounding.py tests/agent/test_dj_cohost.py` | ⬜ pending |
| 77-04-T2 | 04 | 2 | WIRE-01, WIRE-05 | unit + source-text | `pytest -q tests/memory/test_ingest_wiring.py tests/agent/test_dj_cohost_grounding.py` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Sampling continuity check:** No 3 consecutive tasks lack an automated verify — every task above has an `<automated>` command. PASS.

---

## Wave 0 Requirements (Plan 01)

- [x] Test file for WIRE-01 (`tests/agent/test_dj_cohost_grounding.py`): grounding kwarg + off-loop dispatch on track-aware events + `[track:<id>]` citation survives the EvidenceRegistry gate + cold-path byte-identity. Two-tier (source-text gate + behavioral fakes), mirrors `tests/memory/test_ingest_wiring.py`. xfail(strict) on not-yet-wired assertions.
- [x] Test for WIRE-05 (extend `tests/memory/test_ingest_wiring.py`): main()-path assertion that `_session_ipc._fire_ingest("boot")` + close ingest fire gated on `recall_enabled`, flag-off no-op, and `run_boot_sweeps`/`on_session_close` are ABSENT (no double-retention). xfail(strict) until Plan 04.
- [x] Test for WIRE-04 (`tests/library/test_curator_persona_seam.py`): curator voice sourced from the matrix seam; grounding RULES preserved verbatim; co-host-only blocks absent from curator voice. xfail(strict) on seam tier until Plan 02.
- [x] Test for WIRE-06 (`tests/runtime/test_load_env_override.py`): decoy `GEMINI_API_KEY` shell env var → `.env` value wins under `override=True`; PLUS a green security pin that the key VALUE is never logged. xfail(strict) on override tier until Plan 03.
- [x] Regression pins for WIRE-02 / WIRE-03 (`tests/repo/test_wire_regression_pins.py`): detectors surface evidence + register; `detected_genre` surfaced confidence-gated. GREEN immediately (shipped behavior) — locks against regression, no new logic.

*Existing pytest infrastructure covers all phase requirements — no framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live co-host cites the actually-playing track in a real DJ session | WIRE-01 | Needs funded Gemini key + live audio (BlackHole) | KAAN-ACTION: run `uv run python -m vibemix`, play a known library track, confirm a real `[track:<id>]` citation in a reaction |
| `memory.db` actually fills on a real live session | WIRE-05 | Needs funded key + a real session + `VIBEMIX_RECALL_ENABLED=1` | KAAN-ACTION: run a session with the flag on, confirm `memory.db` populated; recall fuel for RECALL-EAR |
| Tauri-bundled install key-injection precedence after override flip | WIRE-06 | The Tauri process-env-injection path is not exercised offline (A1) | KAAN-ACTION: if a bundled install injects the key via process env (not `.env`), verify the override=True flip is acceptable; the docstring records the knob to revisit |

*All unit-level phase behaviors have automated verification; only the live-audio/bundled-install end-to-end items are manual (parked for Kaan, never block under `gsd-autonomous fully`).*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (the four wires' failing stubs + the WIRE-02/03 pins)
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned (nyquist-compliant). Wave 0 (Plan 01) must run first to create the stubs; `wave_0_complete` flips true after Plan 01 executes.
