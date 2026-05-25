---
phase: 77-wire-connect-the-islands
plan: 03
subsystem: runtime-env
tags: [wire, wire-06, env-override, dotenv, security, ghost-key, kaan-action]
requires:
  - "src/vibemix/__main__.py::_load_env_robust (the env-loading entry)"
  - "tests/runtime/test_load_env_override.py (WIRE-06 Wave-0 scaffold from Plan 01)"
provides:
  - "_load_env_robust() loads .env with override=True at BOTH call sites — .env wins over a stale shell GEMINI_API_KEY"
  - "docstring records the deliberate reversal of the prior Tauri-injection (override=False) precedence + a KAAN-ACTION (A1) knob note"
  - "tests/runtime/test_load_env_override.py::test_dotenv_overrides_ghost_shell_env un-xfailed -> real GREEN pass"
affects:
  - "the live runtime / wizard / session paths that read GEMINI_API_KEY (now sourced from .env, not a ghost shell var)"
tech-stack:
  added: []
  patterns:
    - "honest green — no genai.Client, no GEMINI_API_KEY (decoy/real literals only)"
    - "Wave-0 xfail(strict) scaffold flips to a real pass when the implementation lands"
key-files:
  created:
    - .planning/phases/77-wire-connect-the-islands/77-03-SUMMARY.md
  modified:
    - src/vibemix/__main__.py
    - tests/runtime/test_load_env_override.py
decisions:
  - "Single commit for production flip + test un-xfail (not separate RED/GREEN): the RED scaffold already shipped in Plan 01 (caa4ada/a560e29); this plan's task is the behavior flip that turns that existing scaffold green."
  - "The remaining 'override=False' string occurrences in __main__.py are in the docstring (explaining the reversal + the revert knob), NOT in code — both load_dotenv calls are override=True."
metrics:
  duration: "~5 min (incl. ~4 min full-suite run)"
  completed: "2026-05-26"
  tasks: 1
  files: 2
---

# Phase 77 Plan 03: WIRE-06 Env-Key Override Summary

The diagnosed live ghost-key bug is fixed: `_load_env_robust()` now loads `.env` with `override=True` at both call sites, so the funded `.env` `GEMINI_API_KEY` wins over a stale/ghost shell var (the bug where dead `...QSFyBQ` shadowed funded `...32u744`, leaving the runtime on a credit-less key). The docstring records the deliberate reversal of the prior Tauri-injection precedence plus a KAAN-ACTION knob for the bundled-install path; the security diagnostic still prints the file path and never the key value.

## What Was Built

| Task | File | Change |
|------|------|--------|
| 1 | `src/vibemix/__main__.py` | `_load_env_robust()`: `load_dotenv(dotenv_path=..., override=False)` (per-candidate) → `override=True`; `load_dotenv(override=False)` (no-`.env` fallback) → `override=True`. Docstring rewritten: `.env` is the source of truth, the reversal rationale (WIRE-06 ghost-key bug), and a KAAN-ACTION (A1) note documenting the revert knob for a future Tauri-bundled process-env-injection path. Diagnostic print at `:184+` untouched. |
| 1 | `tests/runtime/test_load_env_override.py` | Removed the `@pytest.mark.xfail(strict=True)` marker on `test_dotenv_overrides_ghost_shell_env` so it asserts a real pass (decoy shell key → `.env` value wins). |

## How It Satisfies WIRE-06

- **`.env` wins over a stale shell key:** both `load_dotenv` invocations use `override=True`. With `os.environ["GEMINI_API_KEY"]="DECOY"` and a `.env` carrying `GEMINI_API_KEY=REAL_FUNDED`, `_load_env_robust()` leaves `os.environ["GEMINI_API_KEY"] == "REAL_FUNDED"`. Verified by `test_dotenv_overrides_ghost_shell_env` (now GREEN).
- **No secret leak (T-77-03-01 / V7):** the diagnostic at `:184+` was left fully untouched — it prints `-> env: loaded <path>`, never the key value. Verified GREEN by `test_diagnostic_never_prints_the_key_value` (asserts neither the decoy nor the real value appears in captured stdout+stderr).
- **Documented reversal (T-77-03-02 / A1):** the docstring explicitly states this REVERSES the prior `override=False` (Tauri-injection) decision and names the revert knob.

## Deviations from Plan

### Auto-fixed Issues
None — plan executed exactly as written. The two `override=False` strings still grep-visible in `__main__.py` are in the docstring (the reversal rationale + the KAAN-ACTION revert knob), not in executable code; both `load_dotenv` calls are `override=True`, satisfying the acceptance grep (`grep -n "override=" src/vibemix/__main__.py` shows no `override=False` on a `load_dotenv` line).

## KAAN-ACTION Flag (for the milestone surface)

- **A1 — Tauri-injection precedence reversal (soft, documented):** `override=True` makes the on-disk `.env` win over a process-env-injected key. This is correct for the dev/local path and fixes the live ghost-key bug. **IF** a future Tauri-bundled install ever delivers `GEMINI_API_KEY` via process-env injection and that key must win over `.env`, the revert knob is documented inline in `_load_env_robust()`'s docstring (flip back to `override=False` there; see WIRE-06 / 77-RESEARCH Pitfall 3). No action required now — recorded so the decision is recoverable.

## Verification

- Plan-scoped: `PYTHONPATH=src python3 -m pytest -q tests/runtime/test_load_env_override.py` → **2 passed** (override tier now a real pass + security pin still green).
- Acceptance grep: `grep -n "override=" src/vibemix/__main__.py` → both `load_dotenv` calls are `override=True`; no `override=False` remains on a code line (only docstring references).
- Full suite: **4446 passed, 26 skipped, 6 xfailed, 4 xpassed, 0 failed** (237s). The WIRE-06 xfail dropped from the count (7→6 xfailed vs Plan 02) — flipped to a real pass. The 4 XPASS are pre-existing live-hardware (`§V7-LIVE`) markers, unrelated to this plan.
- Honest green: no `genai.Client` constructed; runs with no `GEMINI_API_KEY` (decoy/real literals only).

## Self-Check: PASSED

- FOUND: src/vibemix/__main__.py (override=True both call sites + docstring reversal/KAAN-ACTION note)
- FOUND: tests/runtime/test_load_env_override.py (xfail removed; 2 passed)
- FOUND commit b6040e2 (Task 1)
