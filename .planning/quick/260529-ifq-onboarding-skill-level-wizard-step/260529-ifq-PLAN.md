---
quick_id: 260529-ifq
slug: onboarding-skill-level-wizard-step
date: 2026-05-29
status: complete
---

# Quick 260529-ifq — Onboarding skill-level wizard step

## Problem

vibemix ships three DJ levels (beginner / intermediate / pro), each with its own tuned
co-host prompt cell (the 6-cell `(skill × mode)` matrix in `prompts/matrix.py`). The level
is resolvable only via `VIBEMIX_SKILL_LEVEL` (default `intermediate`) or the live Settings
drawer — **the onboarding wizard never lets a first-run user pick their level.** The feature
exists end-to-end except for the onboarding capture UI.

## Approach

Add a wizard step at position 4 (after `controller`) that persists the chosen level to
`ConfigStore.extra["skill"]` in `config.json`, read at cold boot by
`apply_persona_config_to_env` → `VIBEMIX_SKILL_LEVEL`. The wizard bus has no
`ipc.settings.set` handler, so persistence uses a dedicated fire-and-forget message
`ipc.wizard.set_skill` (mirrors the `ipc.profile.set_consent` precedent).

## Tasks

1. **Backend IPC + handler** — `ipc.wizard.set_skill` message (schema + `WizardSetSkill`
   wrapper + `__init__` exports + `check_ipc_schema` example + 4 parity-count bumps 78→79 +
   `codegen:ipc`); `WizardLoop._on_wizard_set_skill` writes `extra["skill"]` via
   `load_config`/`save_config`. TDD handler + integration test.
2. **Frontend step** — new `components/skill-level.ts` (3-radio card, single amber accent,
   pre-selected `intermediate`) + `step-skill-level.ts`; wire `router.ts` (union / state /
   default / STEP_ORDER / step strip / back-nav / render dispatch / 3 controller forward-nav
   repoints) + renumber `STEP N/6` captions across 5 step files; vitest spec.
3. **Persistence clobber fix** (found in adversarial review) — `tauri/src-tauri/src/config.rs`
   `save_state` now `reload()`s config.json before its terminal write so the Rust
   `write_first_run_state` no longer overwrites the Python-written `skill`.

## Verification

- `npm run codegen:ipc && npm run check:ipc && npm run build && npm test` (vitest 1301 green).
- `python scripts/check_ipc_schema.py` → 79 == 79.
- `pytest tests/wizard tests/ui_bus` → 252 green (handler + integration + parity).
- `cargo check` → clean.
- End-to-end (manual, GUI): run wizard → pick `pro` → `config.json` has `skill:"pro"` →
  relaunch → `-> persona settings: skill=pro` + co-host boots PRO cell.
