# Phase 57: Sexify Finish - Research

**Researched:** 2026-05-21
**Domain:** UI polish (CDJ-Whisper visual pass) + carryover-bug close + first-run friction — on EXISTING surfaces. Tauri 2.x (Rust) + vanilla TS/Vite UI + Three.js mascot + Python sidecar (read-only here).
**Confidence:** HIGH (every claim grounded by reading in-tree source on disk; the three carryover bugs were already implemented in commit `fac4c4a` and verified against current working-tree state)

## Summary

Phase 57 is **polish + bug-close + first-run friction tightening on surfaces that already exist and already pass their tests** (711 vitest green, confirmed live this session). It is NOT a rebuild. Three things ship: (1) an `impeccable`-driven CDJ-Whisper visual pass on the two Tier-1 live surfaces (the live session view `tauri/ui/src/session/SessionLayout.ts` + the mascot overlay `tauri/ui/mascot.html` + `tauri/ui/src/mascot/chrome.css`) converging to zero-HIGH ui-checker/ui-auditor; (2) closing + real-app-verifying the three v0.1.0-rc1 carryover bugs; (3) walking fresh-account first-run → first-session and removing code-fixable friction.

**Key finding that reshapes POLISH-02:** all three carryover bugs were *already fixed* in commit `fac4c4a` ("fix(tauri): mascot drag + chrome strip + permissions deep-link", 2026-05-14) and the fixes are present + intact in the current working tree. The drag capability `core:window:allow-start-dragging` is in `capabilities/default.json:9`; the JS-API drag fallback is wired in `mascot/index.ts:144-163` and `index.html:23` titlebar; the chrome strip is hidden via `chrome.css:42-46`; the permission deep-link uses direct `std::process::Command::new("open")` in `permissions.rs:28-34` (deprecated `shell().open()` removed). So POLISH-02 is largely a **verify-and-harden** task (add headless assertions that pin these fixes against regression, then Kaan confirms on the real Mac), NOT a from-scratch fix. The one genuinely-open item the memory note flags is the **sidecar binary rebuild** (`scripts/build_sidecar.py`) — the bundled binary predates the line-buffer/watchdog fixes — but that is arguably Phase 58 (ship artifacts) territory; flag it, do not assume it.

**Live-coordination constraint is load-bearing.** Kaan has uncommitted WIP in exactly the two Tauri files this phase's bug-close touches (`mascot_window.rs`, `tauri.conf.json5`). His WIP is a mascot off-screen guard + Retina logical-unit fix + a `beforeDevCommand` launch fix — all Phase-57-adjacent and complete. The Tauri-file bug work executes **INLINE on main, layered on his WIP, NOT in worktrees** (a worktree forks from HEAD without his uncommitted changes and would clobber them on merge). The good news: the three bug fixes do not collide with his WIP regions — they live in different files (`capabilities/default.json`, `chrome.css`, `permissions.rs`, `mascot.html`, `mascot/index.ts`) or are already-committed. So the inline surgery is small and his work is preserved + committed together, attributed to him.

**Primary recommendation:** Treat POLISH-02 as "verify the `fac4c4a` fixes are intact + add regression assertions + surface the 3 real-app confirmations as KAAN-ACTION." Treat POLISH-01 as a focused `impeccable polish` + paired ui-checker/ui-auditor pass on two files' worth of surface (SessionLayout + mascot overlay), held to CDJ-Whisper (DESIGN.md + `mocks/vibemix-direction-final.html`). Treat POLISH-03 as a wizard step-order/copy/dead-end audit + a first-run smoke vitest. Do NOT touch Kaan's python/persona WIP. Do NOT use worktrees for the two Tauri files.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Live coordination with Kaan's parallel WIP (LOCKED this session):**
- Kaan is actively editing `tauri/src-tauri/src/mascot_window.rs` + `tauri/src-tauri/tauri.conf.json5` this session (uncommitted): a `beforeDevCommand` dev-launch fix (`npm --prefix ui run dev` → `npm run dev`) and a mascot-window off-screen guard (physical→logical Retina unit fix + persisted-origin on-screen clamp). These are coherent, complete, Phase-57-adjacent fixes (mascot window quality + first-run launch).
- Kaan said "hallet" (Claude handles the Tauri carryover bugs). The two Tauri-file carryover bugs (drag capability → `tauri.conf.json5`/capabilities; mascot chrome strip → `mascot_window.rs` window decorations) execute **INLINE on the main checkout, layered on top of Kaan's uncommitted WIP — NOT in worktrees** (a worktree forks from HEAD without his WIP and would conflict on merge / clobber his work). His Tauri WIP is preserved and committed together with the bug fixes, attributed to him.
- **Kaan's persona/prompt WIP is OFF-LIMITS to this phase** (uncommitted, mid-tuning): `src/vibemix/__main__.py`, `agent/dj_cohost.py`, `audio/constants.py` (INVOKE_AUDIO_SECONDS 18→30), `prompts/matrix.py` (react-don't-go-silent), `tests/agent/test_persona.py` / `test_dj_cohost.py` / `test_dj_cohost_prompt_diet.py`. Phase 57 does NOT touch these — leave them untouched/uncommitted.
- **Visual pass: run `impeccable` autonomously, Kaan reviews.** Run the `impeccable` skill + paired ui-checker/ui-auditor on the Tier-1 surfaces to zero-HIGH; the "is it genuinely beautiful" call is Kaan's eye (the felt sign-off). Non-colliding visual work (UI CSS/TS, mascot.html overlay styling) may use worktrees normally — it does not collide with Kaan's python/rust WIP.

**Visual polish (POLISH-01) — `impeccable` skill, Kaan directive:**
- Use the `impeccable` skill for the visual polish pass (Kaan directive 2026-05-21), not just default ui-phase/ui-review. Target Tier-1 live surfaces: the session/live view + the mascot overlay. Hold the locked **CDJ-Whisper** direction: 5 warm blacks, single amber accent (4 intensities), tactility via faint glow not faux-3D bevels, Geist + Fraunces type (NOTE: see Pitfall 5 — DESIGN.md/memory say Saira + JetBrains Mono; reconcile at plan-time), 20/80 rule, textured material feel, readability + restraint. Enforce via the project-local `frontend-enforcement` skill.
- **Gate:** paired ui-checker + ui-auditor pass with **zero HIGH findings**. The felt "looks peak / sexy" is Kaan's review.
- **Mascot overlay = the Three.js GLB rig** (`tauri/ui/mascot.html`) per the Phase 56 correction — the surface the shipped app loads. Visual polish targets that rig's presentation, not the dead root sprite overlay. Richer per-mode art remains v2.x; this is a presentation/consistency pass.

**Carryover bugs (POLISH-02) — close + real-app verify:**
- The three v0.1.0-rc1 carryover bugs: (a) Tauri drag capability missing; (b) mascot chrome strip; (c) TCC permissions list does not populate. Close the code for each.
- **Real-app verification of all three is KAAN-ACTION** (needs the real Mac). Engineering ships the code fix + automated assertions where a headless test is meaningful; the visual/interaction confirmation rides the live-drive surface.

**Fresh-account first-run (POLISH-03):**
- Walk a fresh macOS account first-run → first-session and tighten the friction points: no dead-ends, no confusing steps before audio is live. Engineering closes any code-fixable friction (copy, step order, dead links, missing guidance) + an automated first-run smoke where possible. The **real fresh-account walk on Kaan's Mac is KAAN-ACTION** (the felt "no friction" sign-off).

### Claude's Discretion
- The specific `impeccable` sub-command(s) to run on each surface (e.g. `polish`, `critique`, `layout`) — discretion within the zero-HIGH gate.
- Which regression assertions to add for the three carryover-bug fixes (headless test surface choice).
- The exact wizard friction fixes (copy/step-order/dead-end) discovered during the walk audit.

### Deferred Ideas (OUT OF SCOPE)
- **Felt "looks peak / sexy" visual sign-off** on Tier-1 surfaces (Kaan's eye) — KAAN-ACTION.
- **Real-app verification of the 3 carryover bugs** (drag works, chrome strip gone, TCC list populates) on Kaan's Mac — KAAN-ACTION.
- **Fresh-account first-run walk** on a real fresh macOS account (the felt "no friction" sign-off) — KAAN-ACTION.
- **v2.x full-3D mascot art pass** (Meshy/Mixamo) — NOT this phase.
- New features, signed-publish gates (Phase 58).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| POLISH-01 | Tier-1 live surfaces (session view, mascot overlay) get a final visual pass — zero HIGH findings, CDJ-Whisper consistency held. | Surfaces located: `tauri/ui/src/session/SessionLayout.ts` (33k, session view composer) + `tauri/ui/mascot.html` + `tauri/ui/src/mascot/chrome.css` (overlay presentation). `impeccable` skill present at `~/.claude/plugins/cache/impeccable/.../3.1.0/`, `polish.md`/`critique.md`/`audit.md` references available. DESIGN.md + PRODUCT.md present (impeccable context ready). frontend-enforcement skill at `.claude/skills/frontend-enforcement/SKILL.md`. CDJ-Whisper spec in `mocks/vibemix-direction-final.html` + memory `project_visual_direction_cdj_whisper`. Baseline: 711 vitest green. |
| POLISH-02 | v0.1.0-rc1 carryover bugs closed — Tauri drag capability, mascot chrome strip, TCC list-population. | ALL THREE already implemented in commit `fac4c4a` (2026-05-14), present in working tree: drag cap `capabilities/default.json:9` + JS-API drag `mascot/index.ts:144-163` + `index.html:23`; chrome strip hidden `chrome.css:42-46`; permission deep-link `permissions.rs:28-34`; TCC check/prime path `runtime/wizard.py:155-217` + `platform/_permissions_macos.py`. Regression-assertion surfaces identified (`tests/security/test_capability_snapshot.py`, `tests/security/test_tauri_plugin_macos_permissions_wired.py`, vitest `chrome.css`/drag specs). Real-app confirm = KAAN-ACTION. |
| POLISH-03 | Fresh-account first-run → first-session flow is friction-checked and tightened. | Wizard step order mapped: `router.ts:152-158` STEP_ORDER = intro → permissions → audio → controller → profile-consent → telemetry-consent → smoke-test → "Open vibemix". `forewarning`/`driver-fetch`/`48k-probe` (Phase 49) exist as components but are NOT in active STEP_ORDER — friction-audit candidate. Existing wizard vitest specs: `blackhole-step`, `windows-smartscreen-step`, `tcc-permissions`, `onboarding-flow`, `step0-intro`. First-run smoke scaffold `wizard/smoke-test.ts`. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Tier-1 visual polish (session view) | Browser/Client (vanilla TS + CSS in `tauri/ui/src/session/`) | — | Pure presentation; SessionLayout is presentation-only (no IPC, no state — confirmed in file header). Polish lives entirely in CSS tokens + component markup. |
| Mascot overlay presentation | Browser/Client (`mascot.html` + `chrome.css`) | Frontend Server (Tauri window flags in `mascot_window.rs`) | The transparent-overlay look is split: window-level flags (transparent/decorations/always-on-top) live in Rust `mascot_window.rs`; the in-canvas chrome (border, captions) lives in `chrome.css`. The chrome strip bug is a CSS-tier fix; the window decoration is already correct in Rust. |
| Window drag | Frontend Server (Tauri capability + window API) | Browser/Client (drag-region markup + JS startDragging) | Drag is a Tauri-runtime concern: needs `core:window:allow-start-dragging` capability (Rust-config tier) + a JS trigger (`startDragging()` API, client tier) because `data-tauri-drag-region` is unreliable on transparent+decorations:false macOS windows. |
| TCC permission check + list-population | API/Backend (Python sidecar `runtime/wizard.py` + `platform/_permissions_macos.py`) | Frontend Server (`permissions.rs` deep-link) + Browser (poll in `router.ts`) | The actual TCC read (AVCaptureDevice / CGPreflight) + the prime-registration that *adds vibemix to the macOS Privacy list* runs in the Python sidecar over the WS bus. The Rust `permissions.rs` only opens the Settings deep-link; the UI only polls + renders. The "list does not populate" symptom is a macOS-registration concern owned by the sidecar's `_prime_tcc_registration`. |
| First-run wizard flow/copy | Browser/Client (`tauri/ui/src/wizard/*`) | API/Backend (sidecar wizard handlers `runtime/wizard.py`) | Step order, copy, dead-ends are pure UI router concerns; the sidecar only answers IPC requests. Friction fixes are client-tier; the sidecar contract stays fixed. |

## Standard Stack

This is a polish phase on an existing app. **No new external packages are introduced.** The stack is what already ships.

### Core (already in tree — verified)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Tauri | 2.x (`$schema: schema.tauri.app/config/2`) | Desktop shell; window mgmt, capabilities, IPC | Already the app shell; `tauri.conf.json5` + `capabilities/default.json` are the config surface for the drag bug. |
| `@tauri-apps/api` | `^2.11` (UI devDep) | JS bindings — `getCurrentWindow().startDragging()` | The reliable drag path on transparent macOS windows (used in `mascot/index.ts`). |
| `three` | `^0.170.0` | Mascot 3D rig render | The shipped mascot surface (Phase 56 correction). Visual pass is presentation-only — does NOT touch renderer.ts. |
| `tauri-plugin-macos-permissions` | `2.3.0` (pinned, Cargo.toml) | macOS TCC check/request | Wired per `tests/security/test_tauri_plugin_macos_permissions_wired.py`; capability namespace allowlisted in `default.json:20-26`. |
| `vitest` | `^2.1` | UI test runner | Baseline 711 tests green; the regression-assertion + first-run-smoke home. |
| pytest | (repo root, Python 3.12) | Sidecar + capability-snapshot + tauri-config tests | `tests/security/test_capability_snapshot.py`, `tests/tauri/`, `tests/capabilities/` headless gates. |

### Supporting (skills/tooling)
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `impeccable` skill | 3.1.0 (`~/.claude/plugins/cache/impeccable/`) | Visual polish/critique/audit | POLISH-01 visual pass (Kaan directive). Sub-commands: `polish`, `critique`, `audit`, `layout`, `typeset`. Reads PRODUCT.md + DESIGN.md (both present at repo root). |
| `frontend-enforcement` skill | (project-local) | CDJ-Whisper 20/80 + textured material + no-AI-slop gate | Auto-loaded by ui-checker/ui-auditor/executor/planner per `.planning/config.json::agent_skills`. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `impeccable` skill | default gsd-ui-phase/ui-review | Kaan explicitly directed `impeccable` for this pass. Default review is the gate (zero-HIGH ui-checker/ui-auditor); impeccable is the *craft* layer on top. Use both. |
| JS `startDragging()` | `data-tauri-drag-region` HTML attr alone | The HTML attr is unreliable on transparent+decorations:false macOS windows (documented in `fac4c4a` commit msg + `chrome.css` + `mascot/index.ts` comments). Keep BOTH (attr as hint, JS as the reliable trigger) — already the case. |

**Installation:** None. No `npm install` / `pip install` / `cargo add` required for any POLISH-* item. (If a planner proposes a new dep, it is out of scope per `feedback_no_scope_creep_clean_utility` + Gemini-only invariants.)

## Package Legitimacy Audit

**Not applicable — this phase installs zero external packages.** It is a polish + bug-verify + first-run-friction pass on existing in-tree surfaces. No npm/PyPI/crates additions. slopcheck/registry-verification gate is vacuously satisfied (empty install set).

**Packages removed due to slopcheck [SLOP] verdict:** none (no packages considered).
**Packages flagged as suspicious [SUS]:** none.

## Architecture Patterns

### System Architecture Diagram

```text
                          ┌─────────────────────────────────────────────┐
   USER (fresh macOS      │            TAURI SHELL (Rust)                │
   account, first run)    │                                             │
        │                 │  main.rs .setup()                           │
        ▼                 │    ├─ spawn sidecar (vibemix --wizard)      │
   open vibemix.app ──────┼──▶ ├─ create main window (1440×900,         │
                          │    │     decorations:false, drag via cap)   │
                          │    └─ create_mascot_window()  ◀── Kaan WIP  │
                          │         (transparent, decorations:false,    │      ┌──────────────┐
                          │          off-screen guard + Retina fix)     │      │ macOS TCC /  │
                          │                                             │      │ Privacy list │
                          │  permissions.rs:                            │      └──────▲───────┘
                          │    open_screen_recording_settings ──────────┼─ open ──────┘ (deep-link)
                          │    (direct Command::new("open"), NOT shell) │
                          └───────────────┬─────────────────────────────┘
                                          │ WS bus 127.0.0.1:8765
                          ┌───────────────▼─────────────────────────────┐
   WIZARD WEBVIEW         │         PYTHON SIDECAR (vibemix --wizard)    │
   (tauri/ui/index.html)  │   runtime/wizard.py  WizardLoop             │
        │                 │     boot() ─▶ _prime_tcc_registration() ────┼──▶ AVCaptureDevice.requestAccess
   router.ts STEP_ORDER:  │     _on_permission_check ──▶ platform/      │    CGRequestScreenCaptureAccess
   intro→permissions──────┼──▶    _permissions_macos.py                 │    (THIS registers the app in
   →audio→controller→     │     (poll @1Hz, ipc.permission.state)       │     the Privacy list)
   profile-consent→       │                                             │
   telemetry-consent→     │   _on_list_devices / _on_list_windows /     │
   smoke-test→            │   _on_probe_audio / _on_smoke_test          │
   "Open vibemix"  ───────┼──▶ ipc.wizard.done ─▶ sidecar exits,        │
        │                 │     Rust respawns vibemix WITHOUT --wizard  │
        ▼                 └─────────────────────────────────────────────┘
   FIRST SESSION (live)        SessionLayout.ts renders 3-col deck;
   tauri/ui/src/session/       mascot.html overlay floats over desktop
   SessionLayout.ts            (chrome strip hidden, drag via JS API)

   POLISH-01 targets: SessionLayout.ts (center deck) + mascot.html/chrome.css (overlay)
   POLISH-02 targets: default.json (drag cap) + chrome.css (strip) + wizard.py/_permissions_macos.py (TCC)
   POLISH-03 targets: router.ts STEP_ORDER + step copy + dead-end audit + first-run smoke
```

### Recommended Project Structure (where each item lives — DO NOT create new dirs)
```
tauri/
├── src-tauri/
│   ├── tauri.conf.json5            # KAAN WIP (beforeDevCommand fix) — read working tree
│   ├── src/mascot_window.rs        # KAAN WIP (off-screen guard + Retina) — read working tree
│   ├── src/permissions.rs          # POLISH-02(c): deep-link via Command::new("open") [DONE]
│   └── capabilities/
│       ├── default.json            # POLISH-02(a): core:window:allow-start-dragging [DONE @ :9]
│       └── ../capabilities-snapshot/SNAPSHOT.json  # MUST regen if default.json changes
└── ui/
    ├── index.html                  # main window drag-region [DONE @ :23]
    ├── mascot.html                 # POLISH-01/02(b): overlay markup + drag-region
    └── src/
        ├── mascot/chrome.css       # POLISH-02(b): chrome strip hidden [DONE @ :42-46]
        ├── mascot/index.ts         # POLISH-02(a): JS startDragging [DONE @ :144-163]
        ├── session/SessionLayout.ts  # POLISH-01: Tier-1 session view
        ├── session/components/*.ts   # POLISH-01: meters, timecode, cohost panel, etc.
        ├── tokens.css              # CDJ-Whisper design tokens (27k)
        └── wizard/router.ts        # POLISH-03: STEP_ORDER + step wiring
```

### Pattern 1: Inline-on-WIP Tauri surgery (NOT worktrees)
**What:** The two Tauri files Kaan is editing (`mascot_window.rs`, `tauri.conf.json5`) carry uncommitted WIP. Any POLISH-02 change in or near them must be made **directly on the main checkout**, layered on his uncommitted state.
**When to use:** ANY edit to `mascot_window.rs` or `tauri.conf.json5`, AND any commit that includes them.
**Why:** A worktree (`Agent(isolation="worktree")`) forks from HEAD, which does NOT contain Kaan's uncommitted WIP. Merging the worktree back would either conflict or clobber his changes (memory `feedback_worktree_must_sync_main_first` — and worktrees can't even see uncommitted-on-main changes). The good news: the three bug fixes do NOT need to touch `mascot_window.rs` (chrome strip is a `chrome.css` fix; drag is `default.json` + `mascot/index.ts`; the window decorations in `mascot_window.rs` are already correct: `transparent(true)`, `decorations(false)`). So inline surgery is minimal and his WIP rides through untouched. Non-colliding visual work (CSS/TS in `session/`, `mascot.html` styling) MAY use worktrees — it shares zero files with his WIP.
**Example:**
```text
# Kaan's working-tree WIP confirmed this session (git diff HEAD):
#   tauri.conf.json5     : beforeDevCommand "npm --prefix ui run dev" → "npm run dev" (+comment)
#   mascot_window.rs     : off-screen guard (mut x/y + primary_logical_size clamp)
#                          + Retina logical-unit fix (physical→logical in default_top_right)
# These are complete + Phase-57-adjacent. Preserve + commit WITH the bug fixes, attribute to Kaan.
```

### Pattern 2: Capability-snapshot drift gate
**What:** `capabilities/default.json` has a committed canonical mirror `capabilities-snapshot/SNAPSHOT.json`. A pytest gate (`tests/security/test_capability_snapshot.py`) fails CI if they diverge.
**When to use:** If ANY POLISH-02 work edits `default.json` (e.g. if the drag cap needed adding — it does NOT, it's already there).
**Why:** Editing `default.json` without running `python scripts/dist/snapshot_capabilities.py --write` and committing the new SNAPSHOT.json fails the test + CI. Since `core:window:allow-start-dragging` is already present + committed, no snapshot regen is needed unless new work touches the file.
```python
# Source: tests/security/test_capability_snapshot.py (read this session)
def test_committed_snapshot_matches_current_default(mod):
    raw = json.loads(DEFAULT.read_text(encoding="utf-8"))
    rendered = mod.render(raw)
    committed = SNAPSHOT.read_text(encoding="utf-8")
    assert committed == rendered  # drift → run snapshot_capabilities.py --write + commit
```

### Pattern 3: JS-API drag over data-tauri-drag-region
**What:** Window drag on transparent + decorations:false macOS windows uses `getCurrentWindow().startDragging()` on `mousedown`, not the `data-tauri-drag-region` HTML attribute alone.
**When to use:** Verifying / regression-testing the drag fix.
**Why:** The HTML attr is unreliable on this window config on macOS 26.x (documented in commit `fac4c4a` + inline comments). Both are kept: the attr as a hint, the JS handler as the reliable trigger. The capability `core:window:allow-start-dragging` is REQUIRED for `startDragging()` to be permitted (symptom without it: "window.start_dragging not allowed" in devtools).
```typescript
// Source: tauri/ui/src/mascot/index.ts:144-163 (read this session)
const mod = await import("@tauri-apps/api/window");
const tauriWin = mod.getCurrentWindow();
document.addEventListener("mousedown", (ev) => {
  const me = ev as MouseEvent;
  if (me.button !== 0) return;                  // left-click only
  if ((me.target as HTMLElement)?.closest("[data-no-drag]")) return;
  tauriWin.startDragging().catch(/* … */);      // the reliable path
});
```

### Anti-Patterns to Avoid
- **Worktree for the Tauri-file work:** forks from HEAD without Kaan's WIP → clobbers it. Inline-on-main only for `mascot_window.rs` / `tauri.conf.json5` + any commit that includes them.
- **Touching Kaan's python/persona WIP:** `__main__.py`, `agent/dj_cohost.py`, `audio/constants.py`, `prompts/matrix.py`, `tests/agent/test_*` are OFF-LIMITS. Phase 57 must not edit, commit, or revert them.
- **Re-implementing the carryover bug fixes from scratch:** they exist + work. Verify + add regression assertions; don't rewrite.
- **Spreading amber across the surface during the visual pass:** breaks 20/80 (frontend-enforcement hard rule #2). Amber is the single deck-light accent; demote competing amber to silk (see `step1-permissions.ts:46-67` for the precedent fix).
- **Editing `mascot.html` markup that tests rely on:** `chrome.css` keeps `.mascot-window__top-label` / `__state-caption` in markup (display:none) specifically so HMR/tests don't break. Hide via CSS, don't delete the markup.
- **`renderer.ts` / Three.js scene edits during POLISH-01:** the visual pass is presentation/chrome only (CONTEXT: "not richer per-mode art, that's v2.x"). Don't touch the 3D rig pipeline.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Window drag on transparent macOS window | Custom pointer-tracking + window.setPosition loop | `getCurrentWindow().startDragging()` + `core:window:allow-start-dragging` cap | Already wired in `mascot/index.ts`; the Tauri API handles the native drag loop + multi-monitor. |
| macOS TCC permission read | `tccutil` shell-out / sqlite TCC.db read | `AVCaptureDevice.authorizationStatusForMediaType_` + `Quartz.CGPreflightScreenCaptureAccess()` (in `_permissions_macos.py`) | Reading TCC.db directly is SIP-blocked + fragile; the AVFoundation/Quartz APIs are the supported read path. Already implemented. |
| Adding app to macOS Privacy list | Manual plist / installer registration | `CGRequestScreenCaptureAccess()` + `AVCaptureDevice.requestAccess` in `_prime_tcc_registration` | The OS only lists the app AFTER a capture-API request fires; the prime path on wizard boot does exactly this. Already implemented. |
| Visual quality scoring | Ad-hoc eyeballing | `impeccable` (`polish`/`critique`/`audit`) + paired ui-checker/ui-auditor + frontend-enforcement checklist | The zero-HIGH gate + CDJ-Whisper consistency need a repeatable rubric, not vibes. |
| Capability JSON integrity | Hand-diffing default.json | `scripts/dist/snapshot_capabilities.py` + `test_capability_snapshot.py` | The snapshot test is the canonical drift gate; regen via the script, never hand-edit SNAPSHOT.json. |

**Key insight:** Every "hard" part of this phase (drag, TCC, list-population) was already solved by `fac4c4a` using the supported platform APIs. The custom-solution temptation here is to "re-fix" working code — resist it. The real work is *proving* the fixes hold (regression assertions) and the *felt* visual quality (impeccable + Kaan's eye).

## Runtime State Inventory

> Phase 57 is polish + bug-verify + first-run-friction. It is NOT a rename/refactor/migration. The closest "state" concern is persisted UI/window config that can carry stale values across the carryover-bug fixes. Audited explicitly:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | **Persisted mascot window state** `MascotWindowState` in `~/Library/Application Support/world.bravoh.vibemix/config.json` (x/y/width/height/visible/click_through). Kaan's WIP off-screen guard already clamps stale off-screen origins. The memory note flags `visible:false` can stick (recovery = tray "Toggle Mascot"). | None for the bug fixes (Kaan's WIP handles the off-screen case). If first-run audit (POLISH-03) finds a fresh-account dead-end from `visible:false`, the tray recovery already exists — verify it's discoverable, code-edit only if not. |
| Live service config | **macOS TCC grants** (Privacy list state) live in the OS TCC database, NOT in git/config. The "list does not populate" bug is about whether vibemix appears there after wizard boot. Owned by `_prime_tcc_registration` (wizard.py:155). | No data migration — this is OS-registration behavior. Verify the prime path fires on fresh boot (KAAN-ACTION on real Mac, since the macOS Privacy list is OS state). Headless: assert `_prime_tcc_registration` is called from `boot()` (wizard.py:153). |
| OS-registered state | **None for vibemix on macOS** (no Task Scheduler/launchd/pm2 names with phase-relevant strings). The app is launched by the user / Tauri, not OS-registered. | None. Verified — no launchd plists or scheduled tasks in the vibemix surface. |
| Secrets/env vars | `.env` at repo root holds `GEMINI_API_KEY` (+ `OPENROUTER_API_KEY`). No rename touches these; this phase doesn't read them. | None — verified by scope (no AI calls in polish/bug-verify/first-run-friction work; smoke-test uses bundled offline-greeting.wav fallback). |
| Build artifacts | **Bundled sidecar binary** at `tauri/src-tauri/binaries/vibemix-core-{arch}/` predates the line-buffer + watchdog source fixes (memory `project_v0_1_0_rc1_open_bugs` open item #1). Stale binary = the FATAL log may lag on a real run. | Flag for plan-time: `scripts/build_sidecar.py` regenerates it. ARGUABLY Phase 58 (ship artifacts) territory, not POLISH. Surface as an open question; do NOT silently assume it's in-scope. |

**Nothing found in category OS-registered state:** None — verified by inspecting the launch path (Tauri `main.rs` spawns the sidecar; no launchd/cron/scheduler registration in tree).

## Common Pitfalls

### Pitfall 1: Treating POLISH-02 as a fresh fix instead of a verify-and-harden
**What goes wrong:** Re-implementing the drag/chrome/TCC fixes from scratch, introducing regressions in working code.
**Why it happens:** The phase brief says "close the three carryover bugs" — sounds like they're open. They're not; `fac4c4a` (2026-05-14) closed all three and the fixes are intact in the working tree.
**How to avoid:** Plan POLISH-02 as: (1) confirm each fix is present (file:line cited in this doc), (2) add a headless regression assertion that pins it, (3) surface the real-app interaction confirm as KAAN-ACTION. Only write NEW code if a regression assertion reveals an actual gap.
**Warning signs:** A plan task that says "implement window drag" or "add chrome strip CSS" — those are already done.

### Pitfall 2: Worktree clobbers Kaan's uncommitted Tauri WIP
**What goes wrong:** A subagent spawned with `isolation="worktree"` forks from HEAD, which lacks Kaan's uncommitted `mascot_window.rs` + `tauri.conf.json5` changes. Editing those files in the worktree → merge conflict or silent clobber of his work.
**Why it happens:** Worktrees can't see uncommitted-on-main changes; the GSD default for parallel work is worktree isolation.
**How to avoid:** Any task touching `mascot_window.rs` / `tauri.conf.json5` (or committing them) runs INLINE on main. Per CONTEXT this is LOCKED. Non-colliding visual work (session/ CSS, mascot.html styling, chrome.css) may use worktrees since it shares no files with his WIP.
**Warning signs:** A plan task with `isolation: worktree` that lists a Tauri config/rust file in its file set.

### Pitfall 3: Editing the wrong mascot overlay surface
**What goes wrong:** Polishing the dead root `mascot.html` sprite overlay instead of the shipped Three.js GLB rig.
**Why it happens:** There are historically two mascot surfaces; Phase 56's research correction established that the SHIPPED app loads `tauri/ui/mascot.html` (the Three.js rig via `src/mascot/index.ts`), and the root sprite overlay is dead.
**How to avoid:** POLISH-01 mascot work targets `tauri/ui/mascot.html` + `tauri/ui/src/mascot/chrome.css` (the overlay chrome wrapper) — NOT renderer.ts (the 3D scene) and NOT any root sprite file. Confirmed: `mascot.html` is loaded by `mascot_window.rs:104` (`WebviewUrl::App("mascot.html")`).
**Warning signs:** A task editing `renderer.ts`, GLB assets, or a root-level sprite overlay.

### Pitfall 4: Capability-snapshot drift breaks CI
**What goes wrong:** Editing `capabilities/default.json` without regenerating `capabilities-snapshot/SNAPSHOT.json` → `test_capability_snapshot.py` fails CI.
**Why it happens:** The two files must stay byte-identical (canonicalized); the snapshot is committed separately.
**How to avoid:** If POLISH-02 work edits `default.json` (it should NOT need to — the drag cap is already there), run `python scripts/dist/snapshot_capabilities.py --write` and commit BOTH files together.
**Warning signs:** `test_capability_snapshot.py::test_committed_snapshot_matches_current_default` red after a capabilities edit.

### Pitfall 5: Typography spec conflict (Geist+Fraunces vs Saira+JetBrains Mono)
**What goes wrong:** CONTEXT/REQUIREMENTS say "Geist + Fraunces"; DESIGN.md + memory `project_visual_direction_cdj_whisper` + the live tokens.css say **Saira (variable) + JetBrains Mono**, and explicitly state "Fraunces italic was wrong, removed" and "no italic anywhere." Applying Geist/Fraunces would regress the locked CDJ-Whisper direction.
**Why it happens:** The CONTEXT block carried a stale font pairing from an earlier draft; the in-tree truth (DESIGN.md + tokens.css + the rejected-Fraunces memory) is authoritative.
**How to avoid:** Plan-time + impeccable pass: hold the IN-TREE typography (Saira + JetBrains Mono per DESIGN.md / tokens.css `--type-display` / `--type-body`), NOT Geist/Fraunces. The visual pass should NOT introduce Geist or Fraunces. Flag this conflict to Kaan if a plan proposes the font swap.
**Warning signs:** A task adding Geist or Fraunces font-face / `--type-*` token changes — that contradicts the locked direction.

### Pitfall 6: Anti-slop blocklist false-trip on new wizard copy
**What goes wrong:** First-run friction fixes (POLISH-03) that add/edit copy may trip the anti-slop blocklist (15-token + `\bdeeply\s+\w+` regex) enforced across installer/wizard copy.
**Why it happens:** The blocklist scopes wizard copy; words like "seamless", "leverage", "delight", "unlock", "magical" are banned (see `tcc-permissions.ts:69` "no slop" note).
**How to avoid:** Any new/edited wizard copy passes the blocklist. NEVER relax the gate (Risk #5 in STATE.md). Tune the copy, not the blocklist. Reference banned tokens in `docs/internal/copy-substitutions.md`.
**Warning signs:** A copy edit using a banned token; the anti-slop sibling check (`scripts/audit/check_no_slop_install.py`) failing.

## Code Examples

Verified patterns from in-tree source (read this session):

### Mascot chrome strip — already hidden (POLISH-02b)
```css
/* Source: tauri/ui/src/mascot/chrome.css:25-46 (read this session) */
.mascot-window {
  position: relative; width: 100vw; height: 100vh;
  overflow: hidden; background: transparent; border: none; box-shadow: none;
}
/* Phase 14 chrome elements — kept in markup so HMR / tests don't break,
 * but visually hidden. */
.mascot-window > .border-anim,
.mascot-window__top-label,
.mascot-window__state-caption { display: none; }   /* ← the strip is gone */
```

### Permission deep-link — direct open, not deprecated shell (POLISH-02c)
```rust
// Source: tauri/src-tauri/src/permissions.rs:27-34 (read this session)
#[cfg(target_os = "macos")]
fn open_url(url: &str) -> Result<(), String> {
    std::process::Command::new("open")   // direct — shell().open() was silently failing on macOS 26.3
        .arg(url).spawn().map(|_| ())
        .map_err(|e| format!("open spawn failed: {e}"))
}
```

### TCC prime-registration — adds vibemix to the Privacy list (POLISH-02c)
```python
# Source: src/vibemix/runtime/wizard.py:155-182 (read this session)
def _prime_tcc_registration(self) -> None:
    from vibemix.platform import permissions
    mic_status = permissions.check_microphone_permission()
    if mic_status == "notDetermined":
        permissions.request_microphone_permission()      # fires AVCaptureDevice dialog → app listed
    scr_status = permissions.check_screen_recording_permission()
    if scr_status != "authorized":
        permissions.request_screen_recording_permission() # CGRequestScreenCaptureAccess → app listed
```

### Wizard step order (POLISH-03 audit baseline)
```typescript
// Source: tauri/ui/src/wizard/router.ts:152-158 (read this session)
const STEP_ORDER: WizardStep[] = [
  "intro", "permissions", "audio", "controller",
  "profile-consent", "telemetry-consent", "smoke-test",
];
// NOTE: "forewarning", "driver-fetch", "48k-probe" (Phase 49 components)
// exist but are NOT in STEP_ORDER — a friction-audit candidate (are they
// meant to be in the flow? dead components? intentional for installer-only?).
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `data-tauri-drag-region` HTML attr only | `getCurrentWindow().startDragging()` JS API + cap | `fac4c4a` 2026-05-14 | Drag works on transparent+decorations:false macOS windows. |
| `app.shell().open(url)` for Settings deep-link | `std::process::Command::new("open")` direct | `fac4c4a` 2026-05-14 | Grant buttons actually open System Settings (shell plugin was silently failing on macOS 26.3). |
| Phase 14 "v5 chrome" glass rect + captions on mascot | Bare transparent overlay, chrome hidden via CSS | `fac4c4a` 2026-05-14 | Mascot composites transparently over desktop again (no opaque strip). |
| Mascot window saved physical px, restored as logical | Logical-unit math + off-screen clamp | Kaan WIP (uncommitted, this session) | Window can't spawn off-screen / doubled on Retina. |

**Deprecated/outdated:**
- `tauri_plugin_shell::open` / `app.shell().open()`: silently fails on recent macOS; use `Command::new("open")` (already migrated in `permissions.rs` + `recordings.rs` per `8b810a6`).
- CONTEXT's "Geist + Fraunces" typography: superseded by Saira + JetBrains Mono (DESIGN.md / tokens.css / memory). See Pitfall 5.
- The "vibemix not in Settings list" 2026-05-13 observation: flagged STALE in `project_v0_1_0_rc1_open_bugs` (#3) — both mic + screen showed `authorized` on Kaan's Mac per standalone sidecar log. POLISH-02(c) is therefore likely a confirm-not-fix; the real-app check is KAAN-ACTION.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The sidecar-binary-rebuild (`scripts/build_sidecar.py`) is Phase 58 (ship) territory, not POLISH | Runtime State Inventory / Open Questions | If it's in-scope for 57, a verify-only POLISH-02 misses a real first-run lag bug. Flagged as open question, not assumed-done. |
| A2 | The "TCC list does not populate" bug is already addressed (prime path) and POLISH-02(c) is verify-not-fix | Summary / Pitfall 1 | If the prime path regressed or the real Mac still shows empty, new code is needed. Real-app check is KAAN-ACTION, so the gap surfaces there. |
| A3 | The 3 carryover-bug fixes in `fac4c4a` are still present in working tree (not reverted by later commits) | Summary / POLISH-02 | Verified by reading current working-tree files this session (chrome.css, permissions.rs, default.json, mascot/index.ts) — LOW risk, but plan should re-grep at execution. |
| A4 | The visual pass holds Saira+JetBrains Mono (in-tree), NOT CONTEXT's Geist+Fraunces | Pitfall 5 / State of the Art | If Kaan actually wants Geist/Fraunces now, the in-tree direction is wrong — but DESIGN.md + memory + tokens.css all say Saira/JetBrains. Flag to Kaan; do not swap silently. |
| A5 | `forewarning`/`driver-fetch`/`48k-probe` being absent from STEP_ORDER is intentional (installer-companion path) OR dead — needs the friction audit to determine | POLISH-03 / Code Examples | If they SHOULD be in the flow, the fresh-account walk has a missing-step gap; if dead, they're cruft. The POLISH-03 audit resolves this. |

## Open Questions

1. **Is the sidecar binary rebuild in scope for Phase 57 or Phase 58?**
   - What we know: the bundled binary predates source fixes (line-buffer/watchdog); `scripts/build_sidecar.py` regenerates it; memory flags it as a v0.1.0-rc1 open item.
   - What's unclear: REQUIREMENTS maps "all engineering release gates pass on real artifacts" to Phase 58 (REL-01), which implies artifact rebuild is Phase 58. But a stale binary affects first-run (POLISH-03) on a real Mac.
   - Recommendation: Treat the rebuild as Phase 58; in Phase 57, NOTE the staleness in the first-run findings and surface it as a dependency, not an in-phase task. If Kaan's live-drive (KAAN-ACTION) hits the lag, escalate.

2. **Does the macOS Privacy list actually populate on a fresh account, or is the bug stale?**
   - What we know: the prime path (`_prime_tcc_registration`) fires the capture-API requests that register the app; standalone sidecar log showed `authorized` for both; the "not in list" observation is flagged STALE.
   - What's unclear: whether a truly-fresh macOS account (never granted) shows vibemix in the list after wizard boot.
   - Recommendation: Headless — assert `_prime_tcc_registration` is invoked from `boot()` (wizard.py:153) and that `_on_permission_check` fires `request_*` on `notDetermined`. Real confirmation is KAAN-ACTION (fresh-account walk).

3. **Are `forewarning`/`driver-fetch`/`48k-probe` meant to be in the live wizard flow?**
   - What we know: they exist as components (Phase 49 installer companion) but are absent from `router.ts` STEP_ORDER.
   - What's unclear: intentional (installer-only path, separate from the in-app wizard) vs. a missing-step friction gap.
   - Recommendation: Resolve during the POLISH-03 friction audit by reading the Phase 49 wiring + the installer flow; if installer-only, document the boundary; if a gap, add to STEP_ORDER.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node + npm (UI test/build) | POLISH-01/02/03 vitest + first-run smoke | ✓ | npm present (711 tests ran in ~6s this session) | — |
| `vitest` | regression assertions + first-run smoke | ✓ | `^2.1` | — |
| pytest (Python 3.12) | capability-snapshot + tauri-config + sidecar assertions | ✓ | 3.12 (.venv); `python3 -m pytest -q` per CONTRIBUTING | — |
| `cargo` (Tauri build) | building the app to interaction-test drag/chrome on real Mac | ✓ (1.95.0) but HEAVY | 1.95.0 | Headless: Rust unit tests (`mascot_window.rs` has 4) + Python static gates on config/capabilities. Full build/drive = KAAN-ACTION. |
| `impeccable` skill | POLISH-01 visual pass | ✓ | 3.1.0 (`~/.claude/plugins/cache/impeccable/`) | frontend-enforcement + default ui-checker/ui-auditor if skill load fails. |
| DESIGN.md / PRODUCT.md | impeccable context | ✓ | present at repo root | — |
| Real macOS app (drag/chrome/TCC interaction + felt visual) | POLISH-02 real-app verify + POLISH-01 felt sign-off + POLISH-03 fresh-account walk | KAAN-ACTION | — | None — these are inherently real-hardware/human-eye checks (per CONTEXT deferred). |

**Missing dependencies with no fallback:** None for engineering. The real-Mac interaction confirmations (drag works, chrome gone, TCC list populates, "looks peak", "no friction") are inherently KAAN-ACTION, not missing tooling.

**Missing dependencies with fallback:** Full `cargo tauri build`/drive is heavy + needs the real Mac for the interaction tests → fall back to headless assertions (capability JSON present, CSS display:none, deep-link Command form, prime-path invoked, vitest drag/chrome specs) + surface the interaction confirm as KAAN-ACTION.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | UI: `vitest ^2.1` (jsdom). Sidecar/config: `pytest` (Python 3.12). Rust: `cargo test` (heavy). |
| Config file | `tauri/ui/vitest.config.ts`; `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd tauri/ui && npm test` (711 tests, ~6s) |
| Full suite command | UI: `cd tauri/ui && npm test`; Python: `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| POLISH-01 | CDJ-Whisper consistency on Tier-1 surfaces; zero HIGH; 20/80 held; no AI-slop type | manual-eye + skill-gate | `impeccable polish`/`audit` + paired ui-checker/ui-auditor (agent gate, not a unit test) | partial — ui-checker/ui-auditor are agent gates; existing component vitest (`meter.test.ts`, `citation-strip.test.ts`, `hype-mode-indicator.test.ts`) guards behavior, not felt quality |
| POLISH-01 | Visual changes don't break component render contracts | unit | `cd tauri/ui && npm test` (regression on the 711 baseline) | ✅ 711 green |
| POLISH-02a | Drag capability present + JS drag wired | unit/static | pytest assert `core:window:allow-start-dragging` in `default.json`; vitest assert `startDragging` handler in `mascot/index.ts` | ❌ Wave 0 — add assertion (cap is present, test is not) |
| POLISH-02a | Capability snapshot not drifted | static | `python3 -m pytest tests/security/test_capability_snapshot.py -q` | ✅ exists |
| POLISH-02b | Chrome strip hidden (display:none on top-label/state-caption/border-anim) | unit | vitest: import `chrome.css` text, assert `.mascot-window__top-label { display: none }` (or jsdom computed-style check) | ❌ Wave 0 — add assertion |
| POLISH-02c | Deep-link uses direct `open` not shell; prime path invoked on boot | static/unit | pytest: assert `Command::new("open")` in `permissions.rs` (no `shell().open`); assert `_prime_tcc_registration` called in `boot()` (wizard.py) + `request_*` on `notDetermined` (wizard.py `_on_permission_check`) | ❌ Wave 0 — add assertion; `test_tauri_plugin_macos_permissions_wired.py` exists for the plugin wiring |
| POLISH-02 | macOS plugin still wired (Cargo pin + main.rs register + cap allowlist) | static | `python3 -m pytest tests/security/test_tauri_plugin_macos_permissions_wired.py -q` | ✅ exists |
| POLISH-03 | Wizard step continuity — no dead-end before audio live; STEP_ORDER reaches "Open vibemix" | unit | vitest first-run smoke: drive `OnboardingFlow` / `router` advanceTo chain intro→…→smoke-test; assert each step renders + a next exists until smoke-test | ❌ Wave 0 — extend (`onboarding-flow.spec.ts` + step specs exist; add a continuity smoke) |
| POLISH-03 | New/edited wizard copy passes anti-slop blocklist | static | `python3 scripts/audit/check_no_slop_install.py` (sibling check) | ✅ exists |

### Sampling Rate
- **Per task commit:** `cd tauri/ui && npm test` (the 711-test UI suite, ~6s) + the touched pytest gate (`-k capability` / `-k permissions` / `-k slop`).
- **Per wave merge:** full `npm test` + full `python3 -m pytest -q` (sidecar + security + tauri config gates).
- **Phase gate:** UI suite green + Python suite green + capability-snapshot + plugin-wired + anti-slop-install all green, before `/gsd:verify-work`. Then KAAN-ACTION live-drive for the 3 felt/real-app confirmations.

### Wave 0 Gaps
- [ ] `tests/security/test_drag_capability_present.py` (or extend an existing security test) — assert `core:window:allow-start-dragging` in `default.json` — covers POLISH-02a
- [ ] vitest spec asserting `mascot/chrome.css` hides `.mascot-window__top-label` / `__state-caption` / `.border-anim` (display:none) — covers POLISH-02b
- [ ] vitest spec asserting `mascot/index.ts` wires the document-mousedown `startDragging()` handler — covers POLISH-02a
- [ ] pytest assert `permissions.rs` uses `Command::new("open")` (no `shell().open`) + `wizard.py boot()` calls `_prime_tcc_registration` + `_on_permission_check` fires `request_*` on `notDetermined` — covers POLISH-02c
- [ ] vitest first-run continuity smoke — drive the wizard STEP_ORDER chain to "Open vibemix" with no dead-end (extend `onboarding-flow.spec.ts`) — covers POLISH-03
- [ ] (conditional) if `default.json` is edited at all: regenerate `capabilities-snapshot/SNAPSHOT.json` via `scripts/dist/snapshot_capabilities.py --write`

*(Most of POLISH-02's CODE is already shipped; the Wave 0 gaps are the missing REGRESSION ASSERTIONS that pin the fixes, plus the POLISH-03 continuity smoke. POLISH-01's felt quality is intentionally not unit-testable — it's the impeccable/ui-auditor gate + Kaan's eye.)*

## Security Domain

> `security_enforcement` is absent from `.planning/config.json` (= default enabled), but this is a UI-polish + bug-verify + first-run-friction phase with a near-zero new-attack surface. The relevant controls are about NOT regressing existing security posture, not adding new endpoints.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface in this phase (the app has no login; API-key proxy is Bravoh-side, out of scope). |
| V3 Session Management | no | No web sessions. |
| V4 Access Control | yes (preserve) | Tauri capability allowlist (`default.json`) is the access-control boundary. Do NOT broaden it. The drag cap is already minimal-scoped; the snapshot test enforces it. |
| V5 Input Validation | yes (preserve) | Wizard copy edits must pass the anti-slop blocklist; sidecar arg validators in `default.json` (`^--(wizard\|session\|debrief)$`, session-dir regex) must stay intact if any config is touched. |
| V6 Cryptography | no | No crypto in this phase (updater minisign key is Phase 18/58 territory; untouched here). |

### Known Threat Patterns for {Tauri desktop + macOS TCC + WS-bus IPC}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Capability over-grant (adding broad window/shell perms while "fixing" drag) | Elevation of Privilege | Keep `default.json` minimal; `core:window:allow-start-dragging` is the exact scoped perm; snapshot test gates drift. |
| Privacy-rule violation while debugging first-run/TCC (reading Kaan's OZ/Hermes logs) | Information Disclosure | ABSOLUTE: bring-up/first-run debugging reads vibemix's OWN Tauri console + sidecar.log ONLY (`fs:allow-read-text-file` scoped to `$APPLOCALDATA/vibemix/logs/sidecar.log`). Off-limits paths in CLAUDE.md (`~/.hermes`, `~/hermes-rig/logs`, `~/.lmstudio`) are never touched. |
| Window-title leak via list_windows (if first-run audit touches window picker) | Information Disclosure | `_on_list_windows` logs COUNT only, never titles (wizard.py:377). Preserve this — never add title logging. |
| Anti-slop gate relaxation to pass new copy | Tampering (with quality contract) | NEVER relax the blocklist; tune the copy. Sibling check `check_no_slop_install.py` enforces. |

## Sources

### Primary (HIGH confidence — read on disk this session)
- `.planning/phases/57-sexify-finish/57-CONTEXT.md` — user decisions, live-coordination block
- `.planning/REQUIREMENTS.md` (POLISH-01/02/03 + traceability) + `.planning/STATE.md` (project history, risks, invariants)
- `git show fac4c4a` — the carryover-bug-fix commit (drag + chrome + permissions deep-link)
- `git diff HEAD` on `mascot_window.rs` + `tauri.conf.json5` — Kaan's uncommitted WIP confirmed
- `tauri/src-tauri/tauri.conf.json5`, `src/mascot_window.rs`, `src/permissions.rs`, `capabilities/default.json` (working tree)
- `tauri/ui/index.html`, `mascot.html`, `src/mascot/chrome.css`, `src/mascot/index.ts`
- `tauri/ui/src/wizard/router.ts`, `step1-permissions.ts`, `onboarding-flow.ts`, `smoke-test.ts`, `components/permissions-card.ts`, `components/tcc-permissions.ts`
- `src/vibemix/runtime/wizard.py`, `src/vibemix/platform/_permissions_macos.py`
- `tests/security/test_capability_snapshot.py`, `tests/security/test_tauri_plugin_macos_permissions_wired.py`
- `.claude/skills/frontend-enforcement/SKILL.md`; `~/.claude/plugins/cache/impeccable/.../SKILL.md` + `polish.md`; `DESIGN.md`/`PRODUCT.md` presence
- Live: `cd tauri/ui && npm test` → 711 passed (75 files, ~6s)
- Memory: `project_v0_1_0_rc1_open_bugs`, `project_visual_direction_cdj_whisper`

### Secondary (MEDIUM confidence)
- `.planning/config.json` (nyquist_validation:true, agent_skills, no security_enforcement key)

### Tertiary (LOW confidence)
- None — all claims grounded in on-disk source or live tool output.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new deps; verified against `package.json`, `Cargo.toml` pins, in-tree usage.
- Architecture (carryover-bug locations): HIGH — every fix cited file:line, confirmed present in working tree, cross-checked against the `fac4c4a` commit.
- Pitfalls: HIGH — derived from real conflicts (Kaan WIP, font spec mismatch, snapshot drift gate, dead overlay surface) found in-tree.
- Visual-pass scope: HIGH on the *what* (files + skill + gate); the felt-quality outcome is inherently KAAN-ACTION (not a confidence question).
- First-run friction: MEDIUM — step order + smoke surfaces mapped; the actual friction points need the POLISH-03 audit walk (and the real-account walk is KAAN-ACTION).

**Research date:** 2026-05-21
**Valid until:** 2026-05-28 (7 days — Kaan's WIP is actively changing the two Tauri files; re-grep at execution to confirm A3/A4 still hold).
