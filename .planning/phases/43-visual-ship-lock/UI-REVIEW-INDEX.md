---
phase: 43-visual-ship-lock
audited_surfaces: 4
audit_loop: critique→execute until zero HIGH
seeded_by: 43-01
---

# Phase 43 — UI Review Index

Tier-1 audit inventory for the Visual Ship Lock phase. Plan 43-01 ships the
audit driver + first audit pass (session window). Closure plans 43-02 / 43-03
run the paired `gsd-ui-checker` + `gsd-ui-auditor` agents against each surface
until zero HIGH findings remain. Plan 43-04 closes the meter rebuild HIGH that
gates the session surface ship.

## Tier-1 Surfaces

| Surface         | Entry file                                                                   | Owner closure plan | Status            |
| --------------- | ---------------------------------------------------------------------------- | ------------------ | ----------------- |
| session         | `tauri/ui/src/session/SessionLayout.ts`                                      | 43-02              | seeded            |
| mascot-overlay  | `tauri/ui/src/overlay/overlay-runtime.ts` + `tauri/ui/src/mascot/renderer.ts`| 43-02              | pending           |
| wizard          | `tauri/ui/src/wizard/onboarding-flow.ts`                                     | 43-03              | pending           |
| calibration     | `tauri/ui/src/wizard/step1-permissions.ts` + `step2-output-device.ts`        | 43-03              | pending           |

**Status values:** `pending` (no audit run yet) → `seeded` (43-01 first pass
findings landed) → `iteration-N` (closure plan running) → `zero-HIGH`
(closure achieved; HIGH count zero) → `passed` (final auditor verdict = PASS).

## Audit Loop Methodology

> Sourced verbatim from `43-CONTEXT.md` §VIS-01:
>
> 1. **`gsd-ui-checker`** — emits BLOCK / FLAG / PASS verdicts on per-element
>    interaction states (hover / focus / active / disabled / drag).
> 2. **`gsd-ui-auditor`** — emits a scored 6-pillar audit:
>    hierarchy / contrast / motion / typography / density / restraint.
> 3. The pair runs **critique → execute** until **zero HIGH findings** per
>    Tier-1 surface.
> 4. Each iteration MUST append a row to the surface's *Audit Loop Log*
>    (iteration / agent / verdict / files_changed / notes) — the audit trail
>    is append-only.

The driver script `scripts/launch/run_ui_audit.py` writes the markdown
skeleton + enforces the surface allowlist; the agents themselves are invoked
interactively from closure plans via the Task tool.

## Severity Buckets

| Severity | Meaning                                                                 |
| -------- | ----------------------------------------------------------------------- |
| HIGH     | **Blocks ship.** Surface cannot pass the audit while a HIGH is open.    |
| MEDIUM   | Strongly-recommended-fix. Closure plan SHOULD close; non-blocking.      |
| LOW      | Nice-to-have / cosmetic. Defer-OK if scope tightens.                    |

## CDJ Whisper Reference

The visual baseline for every Tier-1 surface is the locked CDJ Whisper
direction (per memory `project_visual_direction_cdj_whisper`):

- **Visual contract:** `mocks/vibemix-direction-final.html`
- **Live session shape:** `mocks/vibemix-app-ui.html`
- **Hero demo storyboard:** `mocks/vibemix-cinematic-storyboard.html`
  *(needs v5 re-mock — VIS-08 owner)*
- **Tokens source-of-truth:** `tauri/ui/src/tokens.css`

CDJ Whisper baseline characteristics (do NOT redesign; enforce):

- Pioneer/Roland industrial-design hardware vocabulary.
- 5 warm blacks + **single amber accent** (`--amber-*` family).
- 20/80 rule — accent reserved for LEDs / focal points only.
- Saira (display) + JetBrains Mono (mono) — no Inter / Roboto / Arial.
- Restraint over flourish — one well-orchestrated reveal > fifteen scattered
  hover micro-effects.

## Per-surface audit files

- [`UI-REVIEW-session.md`](./UI-REVIEW-session.md) — seeded by 43-01,
  closed by 43-02. 3 HIGH + 3 MEDIUM + 2 LOW findings at iteration 0.
- `UI-REVIEW-mascot-overlay.md` — to be seeded by 43-02 (the closure
  plan also seeds its second surface before iterating).
- `UI-REVIEW-wizard.md` — to be seeded by 43-03.
- `UI-REVIEW-calibration.md` — to be seeded by 43-03.

The driver script writes these filenames verbatim:

```sh
uv run python scripts/launch/run_ui_audit.py --surface session
uv run python scripts/launch/run_ui_audit.py --surface mascot-overlay
uv run python scripts/launch/run_ui_audit.py --surface wizard
uv run python scripts/launch/run_ui_audit.py --surface calibration
```

`--list` (or no args) prints the same inventory above.

## Closure trail

Audit history is append-only inside each `UI-REVIEW-<surface>.md` under
*Audit Loop Log*. A surface is considered shipped when:

1. Every HIGH finding row carries `_(closed iteration N)_`.
2. The final audit-loop-log row's verdict = `PASS`.
3. The owner closure plan's SUMMARY.md cross-references the audit file
   and the closing iteration.

No HIGH may remain open at the end of Phase 43.
