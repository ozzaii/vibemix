<phase>49</phase>
<phase_name>Win + Mac One-Click Installer Chain</phase_name>
<date>2026-05-18</date>
<mode>auto (gsd-autonomous fully)</mode>

<domain>
Ship a single-action installer on both Mac and Win. User double-clicks `vibemix.dmg` (Mac) or runs `vibemix-installer.exe` (Win) and lands at session-ready state in ≤ 60 s median across fresh-VM matrix per memory `project_one_click_install_hard_req`. Post-install companion script fetches BlackHole / VB-CABLE from official sources (license-clean, signed), runs vendor installers, configures audio routing, verifies BlackHole 48 kHz format per memory `project_v4_canonical_baseline`. OS-mandated friction (Win driver-signature UAC + Mac BlackHole system-extension approval) reframed as forewarning UX. Closes v3.0 SHIP-04 + SHIP-05 + AUDIO-07 pre-stage. THIS PHASE IS A FRONTEND SURFACE (wizard UI) — UI-SPEC required before plan.
</domain>

<canonical_refs>
**REQUIREMENTS (locked):**
- `.planning/REQUIREMENTS.md` § INSTALL — REQ-IDs INSTALL-01..INSTALL-10 (the 10 lines this phase satisfies)
- `.planning/ROADMAP.md` § Phase 49 — goal + success criteria + invariants + Kaan-action surface

**Research baseline (read before planning):**
- `.planning/research/STACK.md` § Bucket 1 — installer chain tools (Inno Setup `/S`, Tauri MSI target, BlackHole probe, VB-CABLE silent install legality)
- `.planning/research/FEATURES.md` § INSTALL — table-stakes / differentiator / anti-feature framework; forewarning UX framing for OS-mandated friction
- `.planning/research/ARCHITECTURE.md` § Feature 1 — companion driver fetch architecture; `companion-sign` release.yml stage between BUILD and SIGN; NEW vs MODIFIED component split
- `.planning/research/PITFALLS.md` — installer pitfalls: silent install regression (Pitfall 1), Apple Silicon vs Intel (Pitfall 1 cont.), Windows SmartScreen + UAC, Mac BlackHole system-extension approval, ProBLE 48 kHz post-install probe, single-machine test trap

**v3.0 components to EXTEND (not redesign):**
- `installer/windows/vibemix-installer.iss` — existing Inno Setup 6 contract; add `[Run]` invoking `fetch_drivers.ps1` + `[Code]` for VB-CABLE EULA dialog
- `scripts/dist/sign_macos.sh` — extend codesign sweep to `installer/companion/*.{sh,py,ps1}`; add as Stage 5 before `create-dmg`
- `scripts/dist/sign_windows.ps1` — extend Authenticode/SignPath signing target list
- `tauri/src-tauri/tauri.conf.json5` — bundle ID locked `world.bravoh.vibemix`; add `msi` target on Win for parity (already present)
- `scripts/dist/install_vm_matrix.{sh,json}` — existing fresh-VM matrix; update expected `onboarding_ms` ceilings reflecting auto-driver fetch
- `.github/workflows/release.yml` — insert `companion-sign` job between BUILD and SIGN
- `src/vibemix/install/blackhole_probe.py` — existing probe; add `auto_install_attempted` payload field (NOT new event type)
- `tauri/ui/src/wizard/` — existing wizard UI; add forewarning copy + driver-fetch CTA

**Invariant-enforcement neighbors (sibling-extend per Phase 47/48 pattern, do NOT widen shared contracts):**
- `scripts/launch/check_no_ai_slop.py` — CONTRACT-PINNED to `scripts/dayzero/launch_copy/`. DO NOT widen. Create `scripts/audit/check_no_slop_install.py` as sibling importing `AI_SLOP_BLOCKLIST` and applying to `installer/companion/onboarding_copy.json` + wizard string sources + UAC forewarning copy.
- `scripts/audit/check_companion_signing.sh` — NEW verifier mirroring `scripts/dist/verify_signed.py` discipline; runs in `release.yml` SIGN stage.

**ADR / Decisions location:**
- `.planning/decisions/` — emit `INSTALL-49-companion-fetch.md` ADR documenting fetch+SHA-256+vendor-sign chain. Existing tenants: `DEP-OPP-01-obs-browser-source.md`, `P85-OVERRIDE-RETIRED.md`.

**Copy substitutions dictionary (anti-slop):**
- `docs/internal/copy-substitutions.md` — referenced in ROADMAP P49 invariants ("seamless → one-tap", "robust → tested", "leverage → use"). File does NOT yet exist — plan must CREATE it. Block is reusable across future phases.

**Memory anchors:**
- `project_one_click_install_hard_req` — HARD requirement; ≤60s ceiling; every dep rated green/yellow/red
- `project_v4_canonical_baseline` — BlackHole 48 kHz format requirement; post-install probe MUST confirm
- `feedback_no_scope_creep_clean_utility` — minimum useful surface; OUT: enterprise install features
- `feedback_autonomous_no_grey_area_pause` — auto-accept recommended; defer blockers to Kaan-action
- `project_visual_direction_cdj_whisper` — wizard visual language stays CDJ Whisper (5 warm blacks + single amber accent + restraint + Geist + Fraunces)
- `project_v0_1_0_rc1_open_bugs` — Tauri capability missing for drag + TCC list-population issues; verify regressions don't recur in wizard

**Phase 48 hand-off:**
- `.planning/phases/48-new-dep-integration-opportunity-scan/48-CONTEXT.md` § Decision 9 — companion fetches drivers from Green-rated subset ONLY; BlackHole + VB-CABLE confirmed Green; auditable trail from rating → install-time fetch
- `scripts/audit/dep_ratings.yaml` § `opportunity_evaluations` block — Phase 48 schema extension; companion fetch reads vendor versions from here

**Kaan-action surface (defer, do not block engineering):**
- KAAN-ACTION-LEGAL §INSTALL-COMPANION-SIGN — companion driver Authenticode signing on Win via SignPath (same OSS Foundation cert v3.0 SHIP-CUT awaits). Engineering ships `companion-sign` release.yml stage + verifier; Kaan discharges actual cert at SignPath approval time.
- §INSTALL-VM-RUN — fresh-VM matrix real execution on Tart. Engineering ships `install_vm_matrix.sh --check-60s` harness; Kaan discharges real-VM rehearsal when SignPath cert lands.
- KAAN-ACTION-LEGAL §SHIP-CONTACT-VBAUDIO — Kaan emails VB-Audio for explicit OEM redistribution permission (future optimization). Out of scope for v3.1.
</canonical_refs>

<spec_lock>
**Locked requirements (from `.planning/REQUIREMENTS.md` § INSTALL — do NOT re-decide):**
- INSTALL-01: Clean Mac DMG → wizard → ≤60s session-ready across SHIP-04 fresh-VM matrix
- INSTALL-02: Clean Win EXE → wizard → ≤60s session-ready (Inno Setup `[Run]` invokes VB-CABLE NSIS `/S` or falls back to detect-and-guide if EULA-blocked)
- INSTALL-03: Wizard forewarns OS-mandated friction (Win UAC + Mac system-extension); zero anti-slop blocklist trips
- INSTALL-04: `fetch_drivers.{sh,ps1}` + `driver_manifest.json` downloads + SHA-256 verifies + runs vendor-signed installers
- INSTALL-05: `companion-sign` release.yml stage between BUILD + SIGN; verifier gate at publish
- INSTALL-06: Tauri MSI target wired into release.yml matrix + `INSTALL_READY` stopwatch + 60s CI gate
- INSTALL-07: Uninstall path preserves user library / debrief unless clean-uninstall opt-in
- INSTALL-08: Wizard a11y green (keyboard nav + screen-reader labels + WCAG-AA contrast)
- INSTALL-09: Routing config (Mac Multi-Output Device, Win default-device) automated post-driver-install; kernel-mode install never silenced
- INSTALL-10: BlackHole 48 kHz post-install probe per memory `project_v4_canonical_baseline`

**Locked invariants (from ROADMAP Phase 49 invariants line):**
- Bundle ceiling — companion driver fetch is POST-install, OUT of the 350 MB app bundle
- Bundle ID `world.bravoh.vibemix` — companion scripts spawn under same bundle ID; TCC permissions wizard unchanged
- Anti-slop blocklist — every wizard string + UAC forewarning passes 15-token gate; vocabulary substitution dictionary at `docs/internal/copy-substitutions.md`; NEVER relax the gate
- Bravoh-proxy-only key custody — companion + audio_config NEVER inline AIza pattern; Pitfall-7 scan stays zero matches
- Onboarding 60s ceiling — driver install lands INSIDE the envelope via parallelized driver pull during app extract, NOT by expanding the ceiling

Discussing implementation decisions only — WHAT to build is fully locked by REQUIREMENTS.md + ROADMAP.md.
</spec_lock>

<decisions>

### Decision 1 — Companion script layout: `installer/companion/` sibling to `installer/windows/`

[auto] Per ARCHITECTURE.md § Feature 1 NEW components table. Sibling pattern matches existing `installer/windows/`:
- `installer/companion/fetch_drivers.sh` (Mac)
- `installer/companion/fetch_drivers.ps1` (Win)
- `installer/companion/driver_manifest.json` (single source of truth: SHA-256 + canonical URL + version + license-ack text for BlackHole + VB-CABLE)
- `installer/companion/audio_config.py` (post-driver Multi-Output Device / WASAPI default routing)
- `installer/companion/onboarding_copy.json` (all user-facing wizard strings; copy decoupled from logic for one-grep anti-slop extension)

**Rationale:** Architecture is already designed in ARCHITECTURE.md § Feature 1. Sibling pattern mirrors `installer/windows/vibemix-installer.iss` adjacency. Single JSON for copy = one new path for the anti-slop sibling-script to target.

### Decision 2 — Driver fetch strategy: POST-install fetch from vendor URLs, NOT bundled redistribution

[auto] Companion downloads BlackHole signed `.pkg` from `existential.audio` and VB-CABLE installer from `vb-audio.com` at install time, SHA-256 verifies against pinned `driver_manifest.json`, runs vendor's signed installer.

**Rationale:**
- VB-CABLE EULA reserves "written agreement for OEM/bundle redistribution" — safest path is post-install fetch per ARCHITECTURE.md § Feature 1 § Open questions #1
- BlackHole legal status similar — ExistentialAudio sign-off would be needed for bundle redistribution (PITFALLS.md confirms)
- Post-install fetch keeps the app bundle OUT of the 350 MB ceiling (invariant)
- SHA-256 in `driver_manifest.json` gives reproducibility without legal exposure
- Offline-installer fallback documented in onboarding_copy.json per INSTALL-04

### Decision 3 — Companion signing: Bravoh codesign on Mac + SignPath Authenticode on Win, as `companion-sign` release.yml stage

[auto] New release.yml stage between BUILD and SIGN (per ARCHITECTURE.md data-flow diagram):
- Mac: extend `scripts/dist/sign_macos.sh` Stage 5 (codesign companion `.sh`, `.py` files BEFORE `create-dmg`)
- Win: extend SignPath GH Action manifest to include `installer/companion/fetch_drivers.ps1` and `installer/companion/audio_config.py` as separate artifacts (per ARCHITECTURE.md § Open questions #2 — SignPath supports Authenticode on `.ps1` but each artifact may need separate submission)
- New verifier `scripts/audit/check_companion_signing.sh` mirrors `scripts/dist/verify_signed.py` discipline; runs at SIGN-stage gate

**Rationale:** Companion scripts spawn under bundle ID `world.bravoh.vibemix` (invariant); they must be Bravoh-signed for the OS to treat them as trusted neighbors of the main bundle. SignPath cert discharge = Kaan-action §INSTALL-COMPANION-SIGN — engineering ships scaffold + verifier in this phase; Kaan discharges cert at SignPath approval time.

### Decision 4 — Forewarning copy lives in `installer/companion/onboarding_copy.json`, NOT inlined in wizard React components

[auto] Wizard React/TS in `tauri/ui/src/wizard/` reads strings from `onboarding_copy.json`. Single grep target for anti-slop. Single localization point for future i18n (out of scope v3.1).

**Forewarning copy directives (per INSTALL-03):**
- Win UAC: "Windows will ask permission to install an audio driver — click Yes"
- Mac system-extension: "Allow BlackHole in System Settings → Privacy & Security"
- Apple Silicon Reduced Security path: docs only — wizard does NOT auto-trigger Recovery Mode (per PITFALLS.md)
- Fallback copy if auto-install fails: "BlackHole couldn't auto-install — run this one-line brew command and re-launch vibemix" (anti-slop substitution per `docs/internal/copy-substitutions.md`)

**Anti-slop sibling-script gate:** `scripts/audit/check_no_slop_install.py` imports `AI_SLOP_BLOCKLIST` from `scripts.launch.check_no_ai_slop` and applies the 15-token + `\bdeeply\s+\w+` regex to `installer/companion/onboarding_copy.json`. Per `feedback_no_gsd_orchestra_for_trivial_tweaks` and Phase 47/48 sibling-script learning — DO NOT widen `scripts/launch/check_no_ai_slop.py`'s pinned target paths.

### Decision 5 — Copy substitutions dictionary at `docs/internal/copy-substitutions.md` (CREATE in this phase)

[auto] Per ROADMAP P49 invariants. Initial vocabulary substitution dictionary:
- "seamless" → "one-tap"
- "robust" → "tested"
- "leverage" → "use"
- "deeply integrated" → forbidden (regex `\bdeeply\s+\w+`)
- "intuitive" → "clear"
- "powerful" → "fast" (or omit)
- "delightful" → "good"
- "AI-powered" → "Gemini-grounded" (vibemix is Gemini-only; specificity is anti-slop)
- "smart" → "responsive"
- "next-generation" → forbidden

Reusable across future phases. Anti-slop checker reads this file as its substitution suggestion source.

### Decision 6 — Wizard step shape: 4 cards (Welcome / Forewarning / Driver fetch / BlackHole 48 kHz probe), CDJ Whisper visual

[auto] Existing wizard at `tauri/ui/src/wizard/` already has steps. Add explicit step ordering per UI-SPEC (next workflow step):
1. **Welcome** — single CTA "Set up vibemix" (anti-slop pass: not "Get started seamlessly")
2. **OS forewarning** — UAC (Win) / system-extension (Mac) explainer card BEFORE driver fetch fires; one amber accent button, restraint per CDJ Whisper memory
3. **Driver fetch + audio routing** — companion script invocation, progress bar tied to `INSTALL_READY` stopwatch event, MIDI / TCC / Bravoh proxy probes run in parallel
4. **BlackHole 48 kHz probe** — post-install verification per INSTALL-10; on FAIL, fallback card surfaces brew one-liner per memory `project_v4_canonical_baseline`

**Visual language:** CDJ Whisper baseline. 5 warm blacks + single amber accent (4 intensities). Tactility via faint glow not faux-3D bevels. Geist (body) + Fraunces (display) typeface. Reference: `mocks/vibemix-direction-final.html`.

### Decision 7 — Onboarding stopwatch: existing v3.0 `INSTALL_READY` event, NOT new IPC

[auto] Per ARCHITECTURE.md § Feature 1 MODIFIED components — reuse existing `audio.probe.cta_fired` event family; add ONLY a `auto_install_attempted` payload field. Zero new IPC messages (preserves v3.0 IPC contract). Median across SHIP-04 matrix computed by `scripts/dist/install_vm_matrix.sh --check-60s` (NEW flag). 60s CI gate fails if median exceeds budget.

### Decision 8 — Uninstall path: preserve user library + debrief data by default; clean-uninstall opt-in CTA

[auto] Per INSTALL-07. Default uninstall removes:
- App bundle + `installer/companion/` artifacts
- Audio-routing config (Multi-Output Device / Win default-device override)
- App caches (`~/Library/Caches/world.bravoh.vibemix` / `%LOCALAPPDATA%\vibemix\cache`)

Default uninstall PRESERVES:
- User library (recordings, debriefs)
- Mascot profile + ghost calibration
- Anti-slop blocklist user overrides (if any)

Clean-uninstall opt-in card in uninstall dialog: "Remove all vibemix data including recordings and debriefs?" (anti-slop: "Remove", not "wipe clean").

### Decision 9 — fresh-VM matrix execution: scaffold harness, defer real-run to §INSTALL-VM-RUN

[auto] Engineering ships:
- `scripts/dist/install_vm_matrix.sh --check-60s` flag (median onboarding_ms across configured rows)
- 5-row matrix preserves: macOS 12.3 Intel / 14 AS / 15 AS / Win 10 / Win 11
- CI gate fires median computation against `install_vm_matrix.json` `onboarding_ms_budget` ceiling
- Simulation mode for CI (mock the Tart spawn) — real-VM execution gated on §INSTALL-VM-RUN Kaan discharge

**Rationale:** Tart VMs require macOS host + Apple Developer cert; CI runners do NOT have license to spin them up freely. SHIP-04 v3.0 was scoped exactly this way (pre-stage discharge). Phase 49 inherits the gate.

### Decision 10 — Plan structure: 6 plans

[auto] Planner will produce ~6 plans tracking the 10 INSTALL requirements:
- **Plan 01** — companion script scaffold (`installer/companion/fetch_drivers.{sh,ps1}` + `driver_manifest.json` + `audio_config.py` + `onboarding_copy.json`)
- **Plan 02** — release.yml `companion-sign` stage + verifier (`scripts/audit/check_companion_signing.sh`) + ADR (`INSTALL-49-companion-fetch.md`)
- **Plan 03** — wizard UI: 4 cards + forewarning copy + CDJ Whisper visual + a11y pass
- **Plan 04** — Inno Setup `[Run]` + `[Code]` updates + Mac DMG post-install hook + 48 kHz probe glue
- **Plan 05** — `install_vm_matrix.sh --check-60s` harness + simulation mode + 60s CI gate
- **Plan 06** — copy substitutions doc + sibling-script anti-slop check (`scripts/audit/check_no_slop_install.py`) + uninstall path (clean-uninstall opt-in)

</decisions>

<code_context>
**Reusable assets (from `scout_codebase`):**
- `installer/windows/vibemix-installer.iss` — existing Inno Setup contract; `[Run]` + `[Code]` sections support driver fetch invocation per Inno Setup 6 docs
- `tauri/src-tauri/tauri.conf.json5` — bundle ID `world.bravoh.vibemix` locked; `msi` target already in matrix; `app + dmg` Mac targets locked
- `scripts/dist/sign_macos.sh` — Stage 5 hook point for companion codesign
- `scripts/dist/sign_windows.ps1` — SignPath GH Action submission point
- `scripts/dist/install_vm_matrix.{sh,json}` — 5-row VM matrix already scaffolded; adds `--check-60s` flag
- `scripts/launch/check_no_ai_slop.py` — exports `AI_SLOP_BLOCKLIST` for sibling-script import (Phase 47/48 pattern)
- `scripts/audit/check_no_slop_opp.py` — Phase 48 sibling-script precedent for this pattern
- `tauri/ui/src/wizard/` — existing first-launch wizard (v3.0 SHIP-04); add 4-card step shape
- `src/vibemix/install/blackhole_probe.py` — existing probe; payload extension only
- `mocks/vibemix-direction-final.html` — CDJ Whisper visual baseline reference

**Patterns to follow:**
- Sibling-script over shared-tool extension (Phase 47/48 invariant per `feedback_no_gsd_orchestra_for_trivial_tweaks`)
- POST-install vendor fetch over redistribution bundle (license + bundle-size hygiene)
- Sample-rate post-install probe over trust-on-install-success (per memory `project_v4_canonical_baseline`)
- Existing event family extension over new IPC (preserves v3.0 IPC contract)
- Copy in JSON, logic in code (single anti-slop grep target)

**Integration points:**
- Phase 48 hand-off: `dep_ratings.yaml` `opportunity_evaluations` block — companion reads vendor versions from here (Green-rated subset only)
- Phase 50 hand-off: SHIPPED `.dmg` from this phase drives Phase 50 e2e harness; `install_vm_matrix.sh` outputs feed Phase 50's report.html

**Test surfaces:**
- Existing `.github/workflows/install-rehearsal.yml` — add `--with-companion` dry-run flag
- New `scripts/audit/check_companion_signing.sh` — verifier
- New `scripts/audit/check_no_slop_install.py` — sibling-script anti-slop
</code_context>

<deferred>
**Noted for v3.x or future phases (not in scope for Phase 49):**

- **VB-Audio OEM redistribution agreement** — Kaan emails VB-Audio for explicit OEM/bundle permission. Out of scope v3.1; tracked as KAAN-ACTION-LEGAL §SHIP-CONTACT-VBAUDIO.
- **i18n on wizard copy** — `onboarding_copy.json` is structured to support localization but v3.1 is en-only (matches Bravoh v1 closed beta scope).
- **Reduced Security Apple Silicon auto-reboot path** — out of scope (cannot auto-reboot user into Recovery Mode); wizard documents the manual path.
- **Linux installer** — explicitly excluded per PROJECT.md (Mac + Win only in v1).
- **Auto-update over installer** — Tauri updater is scaffolded but auto-update flow is separate from first-install; tracked for v3.x backlog.
- **Companion install telemetry** — opt-in beacon for install success/failure timing on real-user machines. Out of scope; tracked for v3.x backlog.
</deferred>

<next_steps>
This phase IS a frontend surface (wizard UI). Next workflow step is `Skill(skill="gsd-ui-phase", args="49")` which generates `49-UI-SPEC.md` for the wizard surface. Then `gsd-plan-phase 49` produces ~6 plans. Then `gsd-execute-phase 49 --no-transition`. Then `gsd-code-review 49`. Then `gsd-ui-review 49` (advisory).
</next_steps>
