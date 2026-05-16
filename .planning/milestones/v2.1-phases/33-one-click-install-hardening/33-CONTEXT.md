# Phase 33: One-Click Install Hardening - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning (depends on Phase 38 signed binary — autonomous mode lands scaffold + tests; final smoke validation gated on Phase 38 + Kaan-action)
**Mode:** Auto-generated (gsd-autonomous fully)

<domain>
## Phase Boundary

"Icon tap → grant permissions → ready to mix" zero-friction onboarding on a fresh Mac + Windows VM in ≤ 60s; no API key entry surface ever exists.

**Mapped REQ-IDs (9):** INSTALL-01 (TCC pre-grant wizard with macOS Settings deep-links), INSTALL-02 (tauri-plugin-macos-permissions wire), INSTALL-03 (BlackHole 2ch auto-detect + one-click install), INSTALL-04 (Windows Defender SmartScreen handling via SignPath chain), INSTALL-05 (first-launch onboarding ≤60s), INSTALL-06 (TCC revoke mid-session graceful degrade), INSTALL-07 (bundle ID `world.bravoh.vibemix` CI lock), INSTALL-08 (fresh-VM rehearsal automation tart matrix), INSTALL-09 (API key entry NEVER — assertion test).

**In scope (autonomous):**
- TCC permissions deep-link wizard for macOS 12.3 / 14 / 15 fallback ladder + "Why we need this" copy.
- `tauri-plugin-macos-permissions = "2.3.0"` Rust crate wire (macOS only).
- BlackHole 2ch probe + one-click install button in onboarding wizard.
- TCC revoke mid-session detector + toast "Microphone access lost — paused" graceful degrade.
- Bundle ID `world.bravoh.vibemix` CI grep gate against `tauri.conf.json` (Pitfall P63).
- v2.0 → v2.1 upgrade test (TCC permissions carry over).
- `scripts/install_rehearsal/` skeleton + tart VM matrix config (gated on workflow_dispatch + nightly).
- API key entry surface assertion test — grep all wizard/settings TS for Gemini key input fields → must be zero.
- First-launch onboarding flow scaffold (Tauri WebviewWindow walking TCC + audio device + controller + AI test reaction).

**Out of scope (autonomous; deferred via KAAN-ACTION-LEGAL.md):**
- ACTUAL fresh-VM smoke test runs (Kaan-action via tart on Mac VMs + Windows VMs — requires real disk space + macOS license).
- ACTUAL ≤60s timing validation on real hardware (Kaan-action).
- ACTUAL Defender SmartScreen reputation seeding (Phase 38 SignPath chain + waiting period).
- ACTUAL signed MSI / DMG (Phase 38 dep — uses Phase 38's signed-binary verifier surface).

**Pure out of scope:**
- Linux install (Linux excluded from v1).
- App Store / Microsoft Store distribution (out of scope; v2.2 stretch).
- Multi-arch installer (universal2 sidecar already handled in Phase 27 REC-09).
- Auto-update on first launch (auto-updater wires later, not Phase 33).
- Settings recovery / migration tool.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion (locked per gsd-autonomous fully)

Grounded in:
- ROADMAP Phase 33 verbatim
- REQUIREMENTS.md INSTALL-01..09
- Pitfalls P50 (macOS Settings reorg), P63 (bundle ID change → TCC reset), P67 (telemetry default-OFF — Phase 34 shipped), P69 (universal2 sidecar — Phase 27 shipped), P71 (TCC revoke graceful)
- v2.0 Phase 11 wizard (shipped)
- Phase 27 universal2 sidecar (shipped via target-triple)
- Phase 32 wizard consent toggle pattern (shipped)
- Memory `project_one_click_install_hard_req` — HARD requirement, ≤60s

### TCC deep-link wizard (INSTALL-01 / P50)
- File: `tauri/ui/src/wizard/components/tcc-permissions.ts` (vanilla TS).
- Per-version Settings URL ladder:
  - macOS 12.3: `x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone`
  - macOS 14: `x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone`
  - macOS 15: `x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?Privacy_Microphone`
  - Fallback: `x-apple.systempreferences:com.apple.preference.security` (open root Privacy pane)
- Permissions covered: Microphone, Screen Recording, Accessibility, Automation.
- "Why we need this" copy per permission. CDJ Whisper visual.

### tauri-plugin-macos-permissions (INSTALL-02)
- Cargo.toml: `tauri-plugin-macos-permissions = "2.3.0"` under `[target.'cfg(target_os = "macos")'.dependencies]`.
- Rust wire in `tauri/src-tauri/src/lib.rs` (or main.rs).
- Frontend invocation via Tauri command bridge.

### BlackHole 2ch probe (INSTALL-03)
- Sidecar `sec_check.py`-style probe: enumerate CoreAudio devices, check for `BlackHole 2ch`.
- If absent: surface in onboarding wizard with "Install BlackHole 2ch" button.
- Install button: `open https://existential.audio/blackhole/` (official installer URL — opens browser, user installs system-level driver).
- One-click is technically two-click (download + install pkg) due to macOS sudo requirement — documented honestly.

### First-launch onboarding flow (INSTALL-05)
- Tauri WebviewWindow chain: TCC grants → audio device pick → controller probe → AI test reaction.
- Target: ≤60s end-to-end on real hardware. Stopwatch in test scaffolding.
- Each step shows skip-able fallback (e.g., if BlackHole absent, advance with warning; if MIDI absent, advance without).

### TCC revoke mid-session graceful degrade (INSTALL-06 / P71)
- Per-launch re-check on session start.
- In-session: subscribe to TCC change events via `tauri-plugin-macos-permissions`.
- On revoke: toast "Microphone access lost — paused" + pause audio capture + offer re-grant button. NO crash.
- Test: simulate revoke event, assert pause + toast + no crash.

### Bundle ID lock (INSTALL-07 / P63)
- CI grep: `world.bravoh.vibemix` in `tauri/src-tauri/tauri.conf.json` `identifier` field.
- If changed: TCC permissions reset on user's machine → forced re-grant → bad UX.
- v2.0 → v2.1 upgrade test: install v2.0 binary → grant TCC → upgrade to v2.1 → assert TCC carries over (bundle ID stable).

### Fresh-VM rehearsal (INSTALL-08)
- `scripts/install_rehearsal/` skeleton:
  - `mac_vm_setup.sh` — tart spin up macOS 12.3/14/15 VMs.
  - `win_vm_setup.ps1` — Windows 10/11 VMs.
  - `rehearsal_runner.py` — orchestrates install + first-launch + timing.
- CI: gated on `workflow_dispatch` + nightly cron (NOT every PR — VM resources cost).
- Test: scaffold/syntax-validation only; real VM runs are KAAN-ACTION-LEGAL.md.

### API key NEVER (INSTALL-09)
- Grep gate: `tauri/ui/src/**/*.ts` for any input field that captures Gemini API key (e.g., regex against label/placeholder text containing "AIza", "api key", "gemini key").
- Memory `project_one_click_install_hard_req` — proxy-only path enforced.
- Test: `test_no_api_key_input_surface` — fail if such a field exists.

### Frontend convention
- Vanilla TS, CDJ Whisper visual.
- Wizard pattern shared with Phase 32 consent toggle.

### Phase 38 dependency
- INSTALL-04 (Defender SmartScreen) requires Phase 38 signed MSI. Phase 33 implements the "How to allow" KB fallback + scaffold; actual SignPath chain validation is Phase 38.
- Empty-signing-secret skip pattern allows tests to pass without real signing.

### Test discipline
- TCC deep-link ladder test: macOS 12.3/14/15 each → correct URL emitted.
- BlackHole probe test: mock CoreAudio enumeration, assert button surfaced when absent.
- TCC revoke test: simulate event, assert toast + pause.
- Bundle ID grep test: corrupt `tauri.conf.json` → CI fails.
- Upgrade test: v2.0→v2.1 TCC carryover (mocked).
- API key surface grep: synthetic input field → fails.
- Onboarding stopwatch: scaffold only (real hardware Kaan-action).
- Fresh-VM rehearsal: syntax + dry-run only.

</decisions>

<code_context>
## Existing Code Insights

- **v2.0 Phase 11 (shipped)** — wizard scaffold at `tauri/ui/src/wizard/`.
- **Phase 27 REC-09 (shipped)** — universal2 sidecar via target-triple convention.
- **Phase 32 (shipped)** — consent toggle wizard pattern, vanilla TS.
- **Phase 34 (shipped)** — Capability snapshot lint + sec_check.py (audit boot banner).
- **Phase 38 (in flight)** — release.yml signing scaffold, SignPath wire.
- **tauri-plugin-macos-permissions = "2.3.0"** — locked in STATE.md v2.1 deps.
- **Memory `project_one_click_install_hard_req`** — HARD requirement, ≤60s, no key entry.

Codebase maps under `.planning/codebase/` feed plan-phase research.

</code_context>

<specifics>
## Specific Ideas

- **macOS 15 Settings reorg is real** (P50) — verified Sequoia changed deep-link paths.
- **Bundle ID is sacred** (P63) — `world.bravoh.vibemix` locked Day 1.
- **No API key entry surface, EVER** (memory `project_one_click_install_hard_req`).
- **60-second target** — measured icon-tap to first AI reaction.
- **One-click install of BlackHole** — practically two-click (sudo pkg), documented honestly.
- **TCC revoke is rare but real** — graceful pause beats crash.

</specifics>

<deferred>
## Deferred Ideas

- **Linux install** — out of scope.
- **App Store / MS Store distribution** — v2.2 stretch.
- **Auto-update on first launch** — separate flow, later.
- **Multi-language onboarding** — v2.2.
- **Onboarding telemetry** — Phase 34 default-OFF stays.
- **Recovery / migration tool** — out of scope.

</deferred>

<kaan_action_required>
## Critical: Kaan-Action Required (KAAN-ACTION-LEGAL.md)

Phase 33 autonomous deliverables: TCC ladder + plugin wire + probe + degrade + bundle lock + API-key-surface grep + VM rehearsal scaffold + tests.

Kaan-action items:
1. **INSTALL-VM-RUN:** Actual tart VM matrix execution on real macOS 12.3/14/15 + Windows 10/11. Disk space + macOS license required.
2. **INSTALL-60S-CHECK:** Stopwatch validation of ≤60s onboarding on real hardware (post-Phase-38 signed binary).
3. **INSTALL-DEFENDER:** Defender SmartScreen reputation propagation (post-Phase-38 SignPath chain + 1-2 week waiting period).
4. **INSTALL-BLACKHOLE-PROBE:** Validate one-click install flow on a fresh Mac that doesn't have BlackHole.

All autonomous tests run against synthetic fixtures.
</kaan_action_required>
