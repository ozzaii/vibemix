---
quick_id: 260529-ifq
slug: onboarding-skill-level-wizard-step
date: 2026-05-29
status: complete
---

# Summary — Onboarding skill-level wizard step

The wizard now asks "what's your level?" (beginner / intermediate / pro) and the first
co-host session boots in the chosen persona. Closed a real product gap: the three-level
prompt system shipped without an onboarding selector.

## Commits (atomic, path-scoped — shared tree)

| Commit | What |
|--------|------|
| `b4e9ea29` | `feat(wizard)` — `ipc.wizard.set_skill` message + `WizardLoop` handler writing `ConfigStore.extra["skill"]`; schema oneOf 78→79 + 4 parity sentinels |
| `0a8167cc` | `feat(wizard)` — skill-level step (card + step + router wiring + STEP N/6 renumber across 5 files) |
| `f6240299` | `fix(shell)` — `config.rs save_state` reload-before-save (the clobber fix, below) |
| `f74635fd` | `test(wizard)` — end-to-end chain assertion (write → cold-boot persona env) |

## The non-obvious bug (caught in adversarial review, not by tests)

`tauri-plugin-store` loads `config.json` into a cache ONCE at boot (before the wizard).
The Python handler writes `extra["skill"]` to disk DURING the wizard. At wizard completion,
the Rust `write_first_run_state` → `save_state` serialized the **stale boot cache** and
`fs::write` clobbered the whole file — silently dropping `skill` every run. Tests passed
(the write worked) but the feature would have done nothing for first-run users. Fix:
`store.reload()` before the terminal save merges on-disk keys into the cache. This also
hardens the pre-existing latent clobber of Python-written `mood`/`lens`.

## Verification (all green)

- vitest: 139 files / 1301 tests (incl. new `test_step_skill_level.spec.ts`, 8 specs).
- `tsc --noEmit` + `vite build` clean; `npm run check:ipc` clean.
- pytest `tests/wizard tests/ui_bus`: 252 (handler 5 + integration + parity).
- `scripts/check_ipc_schema.py`: 79 oneOf == 79 wrappers.
- `cargo check`: clean.
- Frontend adversarial review: zero defects. Backend review: the clobber BLOCKER (fixed).

## Anti-creep

+1 IPC message (gated: schema + wrapper + codegen + parity). Reuses the wizard bus (no new
port), `config.json` `extra` (no new store), no new AI provider. One deliberate new surface
(the wizard step). `profile.json` 5-field lock untouched.

## KAAN-ACTION (can't self-verify — interactive Tauri GUI)

- Run the real wizard (`cargo tauri dev` / built app), pick **pro**, confirm
  `~/Library/Application Support/vibemix/config.json` shows `skill:"pro"` after finishing
  onboarding, relaunch, and confirm the co-host boots the PRO prompt cell
  (`-> persona settings: skill=pro` in the sidecar log). The Python + Rust + TS layers are
  unit/integration-verified and `cargo check`-clean; the live GUI walk is the last mile.
- Ear-pass the three level personas if not already done.

## Out of scope / follow-ups

- README feature-matrix sync (phases 91-98) — 4 pre-existing `tests/repo` failures,
  unrelated to this task, owned by the Learn-milestone doc surface.
- Pre-existing latent clobber for live-session `mood`/`lens` via `save_mascot_state` /
  other Rust `save_*` paths — the same `reload()` pattern would fix it; not in this scope.
- Optional: derive `STEP N / M` captions from `STEP_ORDER` so future step inserts don't
  ripple across step files (mechanical renumber kept for this change).
