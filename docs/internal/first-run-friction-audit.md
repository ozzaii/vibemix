# First-Run Friction Audit — Fresh-Account → First-Session

**Phase:** 57 (sexify-finish) · **Plan:** 57-02 · **Requirement:** POLISH-03
**Audited:** 2026-05-21 · **Method:** on-paper walk of the in-app wizard source +
headless continuity smoke. No log reads (CLAUDE.md privacy rule, absolute).

## What this audit covers

The in-app first-run wizard — the surface a fresh user sees the first time
`vibemix.app` opens — from the `intro` hero through every active step to the
`smoke-test` terminal step, then on to the live session. The goal of POLISH-03:
a fresh user reaches a live session with no confusing or dead-end step before
audio is live.

Engineering closes the code-fixable friction and proves continuity headlessly.
The felt "no friction" walk on a real fresh macOS account is **KAAN-ACTION**
(see Carveouts below) — that is the lived sign-off this audit does not replace.

## The mapped flow

The active wizard chain is owned by `tauri/ui/src/wizard/router.ts`. The first
surface is `intro` (full-surface hero, no step strip). After the hero, the
`STEP_ORDER` array (`router.ts:152-159`) drives the numbered chain, and
`smoke-test` is the terminal full-surface step:

```
intro  →  permissions  →  audio  →  controller  →  profile-consent  →  telemetry-consent  →  smoke-test  →  [ Open vibemix ]  →  live session
(hero)    STEP_ORDER[0]    [1]       [2]            [3]                  [4]                   (terminal)      wizard.done
```

Each numbered step renders into the `#wizard-primary` mount and exposes a forward
affordance (a Continue / Begin / Open control that calls `advanceTo(next)`), plus
a `[ ← Back ]` affordance and an `esc` / `cmd+[` back shortcut
(`router.ts:288-303`). The user is never one-way-trapped.

### Step-by-step continuity + disposition

| # | Step | Forward affordance | Gating | Disposition |
|---|------|--------------------|--------|-------------|
| — | `intro` | `[ Let's go ]` → `advanceTo("permissions")` (`step0-intro.ts:182-189`) | none | NOT-A-GAP — single CTA, always armed. |
| 0 | `permissions` | `[ Continue → ]` → `advanceTo("audio")` (`router.ts:338`) | armed only when both screen-recording + microphone are `granted` (`step1-permissions.ts:189-193`) | NOT-A-GAP (gated-then-armable). See note 1. |
| 1 | `audio` | `[ Continue → ]` → `advanceTo("controller")` (`router.ts:372`) | armed once a window is picked (`windowSelected`); audio-tone pass is NOT required (`step2-output-device.ts:161-173`) | NOT-A-GAP. See note 2. |
| 2 | `controller` | `[ Continue → ]` → `advanceTo("profile-consent")` AND a `[ Skip ]` (`step3-controller.ts:95-104`, `router.ts:451`) | armed on `caught` OR `timeout`; skip always present | NOT-A-GAP. See note 3. |
| 3 | `profile-consent` | `[ Continue ]` → `advanceTo("telemetry-consent")` (`router.ts:462-477`) | none (toggle default-OFF, advancing does not require opt-in) | NOT-A-GAP. |
| 4 | `telemetry-consent` | `[ Continue ]` → `advanceTo("smoke-test")` (`router.ts:487-499`) | none (radio default "Don't share", advancing does not require a choice change) | NOT-A-GAP. |
| — | `smoke-test` | `[ Open vibemix → ]` → `completeWizard()` (`router.ts:521`, `smoke-test.ts:152-161`) | armed only when `greetingPlayed: true` | NOT-A-GAP. See note 4. |

### Notes on the gated steps

**Note 1 — `permissions` gating is correct, not a dead-end.** vibemix cannot
function without microphone (it listens to the master output) and screen
recording (it watches the DJ window) on macOS, so the Continue CTA staying
disabled until both are `granted` is intentional. The recovery path is present
and discoverable: each card has a Grant button that fires the OS prompt
(`request_microphone_permission`) and an Open-Settings deep-link
(`open_screen_recording_settings` / `open_microphone_settings`,
`router.ts:340-358`). A 1 Hz poll (`startStep1PermissionPoll`,
`router.ts:580-633`) picks up the grant and arms Continue automatically. This is
a gated-then-armable step (continuity), not a permanent block. **FIXED?** No
fix needed — gating + recovery already correct.

**Note 2 — `audio` Continue does not strand on a failed tone test.** A prior
strand (Continue requiring `audioPassed`) was already removed: the 1 kHz tone
test can fail on a borked dev rig even when the device works, so Continue arms on
`windowSelected` alone (`step2-output-device.ts:161-169`). The user's "Yes I
heard it" override also locally arms the pass state even if the probe reported a
programmatic mismatch (`router.ts:381-403`). No remaining strand. **FIXED?** No
fix needed — the strand was closed in earlier work.

**Note 3 — `controller` always reaches a forward state.** The MIDI listen
auto-times-out after 10 s (`runMidiListen`, `router.ts:772-814`), and `timeout`
arms Continue exactly like `caught` does (`step3-controller.ts:95`). A `[ Skip ]`
control is always present (`router.ts:451`). A DJ with no controller plugged in
is never stuck. **FIXED?** No fix needed.

**Note 4 — `smoke-test` Open-CTA always arms, even on greeting failure.** The
greeting cascade can fail (no Gemini key, offline), but `runSmokeTest`'s catch
branch still sets `greetingPlayed: true` so the Open-vibemix CTA arms and the
user can proceed past a borked greeting into the session
(`router.ts:833-839`). No terminal dead-end. **FIXED?** No fix needed.

### Persisted `visible:false` mascot recovery (RESEARCH Runtime State Inventory)

The persisted mascot window state can carry `visible:false` across launches,
which the RESEARCH flagged as a possible fresh-account confusion. On a genuinely
fresh account this does not arise (no persisted state yet), and Kaan's
uncommitted off-screen-guard WIP clamps stale origins. The recovery — the tray
"Toggle Mascot" item — exists and is the documented path. This audit confirms the
recovery exists; no code edit is warranted because the fresh-account path does
not hit the stale-state case. **Disposition: NOT-A-GAP for first run.**

## Resolution: forewarning / driver-fetch / 48k-probe (RESEARCH Open Question 3)

These three components exist in the tree but are absent from `STEP_ORDER`:

- `tauri/ui/src/wizard/step-forewarning.ts` — header: "Phase 49 INSTALL-03".
  Two-card OS forewarning surface (macOS BlackHole system-extension approval /
  Windows VB-CABLE UAC) shown **before the driver fetch fires**.
- `tauri/ui/src/wizard/step-driver-fetch.ts` — header: "Phase 49
  INSTALL-01/02/04/06". Orchestrates the companion fetch via the
  `run_companion_fetch` Tauri command (spawns
  `installer/companion/fetch_drivers.{sh,ps1}`) + parallel driver/TCC/proxy
  probes + the onboarding stopwatch.
- `tauri/ui/src/wizard/step-48k-probe.ts` — header: "Phase 49 INSTALL-10".
  Post-driver-install BlackHole 48 kHz format probe.

**Resolution: installer-companion-only — intentional, NOT wired into the in-app
`STEP_ORDER`.** Evidence:

1. All three carry explicit `Phase 49 INSTALL-*` headers tying them to the
   one-click-install lifecycle, not the in-app first-run wizard.
2. The `router.ts` type comment is explicit: the Phase 49 step types are
   "Registered as types here; the render-switch below routes them. Full
   integration into the step-strip ordering is plan-49-04 (Inno Setup + DMG
   firstrun hook ties them to install lifecycle)" (`router.ts:50-53`).
3. They run during installation — driver fetch, system-extension / UAC approval,
   and the post-install format check — i.e. before the app's in-app wizard ever
   mounts. Their copy lives in `copy.json::steps.{forewarning,driver_fetch,
   format_check}`, separate from the in-app step renderers.
4. The work they would do inside the wizard is already covered by the in-app
   `audio` step (`step2-output-device.ts`): BlackHole presence detection, the
   install-page banner, device selection, and the 1 kHz audio probe. Wiring the
   installer steps into `STEP_ORDER` would duplicate that surface and add steps —
   and adding steps is itself friction.

Per the audit principle "default to NOT adding steps unless the audit shows a
concrete friction the step removes": none of the three removes a first-run
friction that the in-app `audio` step does not already handle. They stay
installer-companion-only. No `STEP_ORDER` / router edit is made.

## Code-fixable friction found

**None.** The in-app chain has a forward affordance at every step, the two
historically-stranding cases (audio-fail strand, smoke-test greeting failure) are
already closed, the gated steps are gated-then-armable with discoverable
recovery, and the installer-companion-step question resolves to "intentional,
out of the in-app flow." No copy change and no router/step-order change is
warranted. The deliverable that closes the remaining gap is the continuity smoke
(plan Task 2), which pins the no-dead-end property against regression.

This is a valid clean-walk outcome under the plan's scope guardrail: "If the
audit finds NO code-fixable friction beyond the continuity smoke, that is a valid
outcome — document the clean walk; do not invent edits."

## Phase 58 dependency: sidecar binary staleness

The bundled sidecar binary at `tauri/src-tauri/binaries/vibemix-core-{arch}/`
predates the line-buffer + watchdog source fixes (memory
`project_v0_1_0_rc1_open_bugs`, open item #1). On a real run the FATAL log may
lag behind the live source behaviour. `scripts/build_sidecar.py` regenerates it.

This rebuild is **NOT done here** — it is a Phase 58 ship-artifact dependency
(REL-01 maps artifact rebuild to Phase 58; RESEARCH Open Question 1 / Assumption
A1). It is surfaced here as a dependency: if Kaan's live fresh-account walk hits
log lag, the sidecar rebuild in Phase 58 is the resolution. Do not block this
plan on it.

## KAAN-ACTION carveouts (not auto-completed)

- **Real fresh macOS account first-run → first-session-with-audio walk** on
  Kaan's Mac — the felt "no friction / no dead-ends" sign-off. Engineering proves
  continuity headlessly (the smoke) and closes code-fixable friction (none
  found); the lived walk is Kaan's.
- **macOS Privacy-list population on a truly fresh account** — whether vibemix
  appears in the Privacy list after wizard boot is OS-registration state, only
  verifiable on a real fresh account (RESEARCH Open Question 2). The prime path
  (`_prime_tcc_registration`) is wired; the real check is Kaan's.
- **Sidecar binary rebuild** — Phase 58 (above).
