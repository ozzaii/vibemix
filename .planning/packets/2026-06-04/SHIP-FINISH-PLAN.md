# SHIP-FINISH PLAN — 2026-06-04

The endgame, Kaan's shape: **two Codex sessions slice through the ship (wire, build, handshake), Claude continuously scans the repo for missed opportunities and does the last checks, then we ship.** No rushing, but for real.

Source of truth for what's left: `SHIP-READINESS-2026-06-04.md` (verdict: not ready; PKG stale/unsigned, LIVE voice 0%, 2 RED gates). This plan turns that critical path into two disjoint Codex lanes + a scan cadence + a ship definition-of-done.

The two lanes are **disjoint by file path** so neither can stage the other's work on the shared tree. One handshake (the in-GUI key field) is called out in both.

---

## CODEX LANE A — Frontend + IPC + UI

**Island:** ALL `tauri/ui/src/**` + the IPC schema (`messages.schema.json`/`messages.ts`/`validator.generated.mjs`) + `src/vibemix/ui_bus/*.py` + `scripts/check_ipc_schema.py`. NOT any other `src/vibemix/**` Python.

```
/goal SHIP-FINISH lane A — Frontend + IPC + UI. Drive the frontend ship-blockers from
.planning/packets/2026-06-04/SHIP-READINESS-2026-06-04.md to green + shippable, in order:
(1) Fix the RED tsc build gate — `tsc --noEmit` must pass; it blocks the bundle today.
(2) DEMOCRATIZATION #1 (top ship polish): add an in-GUI Gemini-key field + a proxy-mode
toggle in Settings, so a non-dev can paste a key OR flip to the hosted proxy WITHOUT
hand-editing .env. Today the crash banner shows the error but the only fix is editing .env
(a stranger cannot). Persist through the existing settings/config path (config.json
convergence — the Rust store reload()s before save); the secret is written by the backend,
never logged, never committed. Repaint optimistically (data-active locally, per the
frontend convention). HANDSHAKE: if persisting the key needs a backend handler, that handler
is lane B's; you own the IPC message DEF + the UI, B owns the Python side.
(3) Cue Tray UI (the visible cue part from CUE-LAND-ENGINE.md "Sexy UX"): the A-H slot
ladder, the ProvenanceBadge ◇AUTO (hollow) vs ●DJ (filled), a ConfidenceMeter banded to the
policy floors, locked DJ rows, empty-as-empty, one-consent Land button + target picker +
Landed receipt. Pure render of a CueSet (zero model work). Add the library_land_cues IPC
type (you own the schema: run npm run codegen:ipc + the ipc-wiring-checker).
PROOF (by-eye, not just vitest): npm run build && npm test green; on the real rig a fresh
user reaches the brain via the key field/proxy toggle; the Cue Tray renders a CueSet fixture
with correct ◇/● badges, locked DJ rows, empty slots empty.
SHARED LAW — one shared tree (ux-redesign-impeccable): commits survive, uncommitted gets
WIPED by a sibling git op. git add <exact paths> NEVER -A; verify git diff --cached. You own
the IPC schema; backend lanes request types from you. Sidecar 127.0.0.1:8765 = one socket:
pkill -f "python -m vibemix" before any probe. Proof = by-eye/by-bus on current source.
test-passing-but-dark = 0. commit -s, Kaan Özkan <rahipdotaci@gmail.com>. Commit each surface
the instant it is green + proven.
```

---

## CODEX LANE B — Python backend + packaging

**Island:** `src/vibemix/**` Python (state/coach/agent/prompts for the persona tests, library, audio, platform) + `scripts/**` + the PyInstaller specs (`vibemix-core.{macos,windows}.spec`) + their tests. NOT `tauri/ui/**`, NOT the IPC schema.

```
/goal SHIP-FINISH lane B — Python backend + packaging. Drive the backend ship-blockers from
.planning/packets/2026-06-04/SHIP-READINESS-2026-06-04.md to green + shippable, in order:
(1) Fix the 5 RED agent persona/grounding tests — re-pin them to the landed Sven coach
identity, or revert the drift; the suite must go green at HEAD.
(2) Whitelist the auto_crate stop_reason write in the toolset whitelist (or revert it) so
test_no_seen_relaxation passes — the full-tree gate is RED on it today.
(3) KEYSTONE prep: harden the audio route-doctor so it DETERMINISTICALLY resolves the
BlackHole 2ch-vs-16ch flip and names the exact fix (the doctor ranks 2ch at one run and 16ch
37 min later on the same rig — find why, make auto_master_recommendation stable across
repeated runs). The live capture itself is Kaan's hand (owner-gate); your job is the doctor +
capture-readiness so the capture can't be taken on a coin-flip device.
(4) Cue-landing engine backend — execute the CUE-LAND-ENGINE.md /goal verbatim: provenance
stamp FIRST (close the source leak on the folder/cue_export path + the VM name prefix), then
cue_landing.py core (CueSet/LandedCue/land), then Viber auto-cue-on-export at toolset.py:990.
(5) Once 1-3 are green and src is clean: commit any dirty src surgically, rebuild the sidecar
AND the DMG at HEAD, run the release gates (MOSS bundle / learn wavs / signing / freshness
manifest). Sign + notarize is external (SignPath/Apple, Kaan's clock) — produce the gated
build and report exactly which gates pass vs wait on the external clock.
HANDSHAKE: lane A is adding an in-GUI Gemini-key field + proxy toggle; if it needs a backend
handler to persist the key to keychain/.env, that handler is YOURS — coordinate the message
name with A (A owns the IPC schema def). Never log or commit the secret.
PROOF (test-passing alone is not done): full suite green at HEAD (pytest -q); the doctor
names a deterministic master device; cue proof per CUE-LAND-ENGINE.md (pyrekordbox re-parse
biconditional, zero DB writes); a fresh sidecar+DMG at HEAD with an honest gate report.
SHARED LAW — one shared tree (ux-redesign-impeccable): commits survive, uncommitted gets
WIPED by a sibling git op. git add <exact paths> NEVER -A; verify git diff --cached. IPC
schema = FRONTEND lane only. Sidecar 127.0.0.1:8765 = one socket: pkill -f "python -m vibemix"
before any probe. Proof = by-ear/by-bus on current source + grounding-review on any co-host
line. test-passing-but-dark = 0. commit -s, Kaan Özkan <rahipdotaci@gmail.com>. Commit each
piece atomically the moment it is green + proven.
```

---

## Continuous opportunity scan (Claude, ongoing)

Kaan: "scan scan scan — be sure we didn't miss any opportunity." Cadence: a baseline scan now, then a re-scan each time a lane lands a chunk (the tree changed, so re-check). Each scan is a multi-modal sweep, adversarially filtered so it protects the ship instead of growing scope:

- **dark-gold** — built-but-dark / 0-caller modules that are shippable value not in the critical path.
- **dead-wire** — computed-but-unsurfaced state that is a cheap wire-win.
- **quick-wins** — small high-leverage flips (NEXT-MOVES-VERIFIED leftovers).
- **missed-integrations** — cross-engine reuse not yet exploited.

Every candidate is tagged **SHIP-BLOCKING-MISS** (we'd regret not shipping it → feed the lanes) vs **POST-SHIP-BACKLOG** (real, but after v1) vs **NOT-REAL**. Output lands as `MISSED-OPPORTUNITIES-SCAN-<n>.md`. The ruthless filter is the point: no scope creep into the ship.

---

## Claude's last checks — ship definition-of-done

Ship only when ALL of these are true (3 proof tiers; test-green is not enough):

1. **SRC** — full pytest green at HEAD; `npm run build && npm test` green; both RED gates (5 persona tests, auto_crate stop-reason, tsc) cleared; IPC codegen current.
2. **PKG** — a fresh sidecar + DMG built AT HEAD (not the ~158-commit-stale one), all release gates pass (MOSS bundle present, learn wavs, Developer-ID signed, notarized + stapled, updater + freshness manifest correct), and the sidecar boots clean.
3. **LIVE / keystone** — one captured real set: nonzero music_rms + voice_rms + at least one grounded co-host line whose citation resolves in EvidenceRegistry. This is the "a stranger hears it" gate. (Kaan's hand on the rig; doctor must name a deterministic device first.)
4. **Democratization** — a fresh non-dev user reaches the brain (in-GUI key field or hosted proxy with credits), models auto-fetch, the wizard routes audio. No hand-editing .env.
5. **No ship-critical dark gold left** — the latest scan shows zero SHIP-BLOCKING-MISS open.
6. **Honesty / grounding intact** — provenance guards (auto cues never masquerade as DJ), no slop on any co-host line, grounding-review clean on touched reaction surfaces.

When 1-6 hold: **ship.**
