# Stack Research — v3.1 Distribution-Ready Pass

**Domain:** Cross-platform AI desktop app — Win+Mac distribution polish on top of an engineering-shipped v3.0 OSS RC. Five new capability surfaces: (1) one-click installer chain, (2) dep audit/pin lockfile, (3) new-dep opportunity scan, (4) end-to-end MacBook test, (5) real mascot GLBs with full emotion coverage.

**Researched:** 2026-05-17

**Confidence:**
- **HIGH** on installer/lockfile tooling — uv, Tauri 2.11.x bundler, Inno Setup 6, syft/SBOM/cargo-deny all verified at PyPI/crates.io/official sources on research day.
- **HIGH** on test tooling — Playwright + tauri-driver + pixelmatch all verified; tauri-plugin-playwright is the documented 2026 workaround for the Tauri-on-macOS limitation.
- **MEDIUM** on mascot GLB pipeline — Mixamo retarget pipeline already scaffolded in `scripts/mascot/` (Phase 43-05); v3.1 picks ONE of Mixamo+Adobe / Ready Player Me / Auto-Rig Pro for production assets. Recommendation locked in §5 but the Kaan-aesthetic selection is per-asset.
- **MEDIUM** on Windows driver silent-install — VB-CABLE / Voicemeeter parameters are documented externally; we ship a wrapper that **detects + guides** rather than fully-silent installs (silent kernel-driver install requires admin escalation we don't want).
- **LOW** on `tauri-plugin-playwright` production maturity — `0.1.0` early-stage; alternative is the official WebDriver/`tauri-driver` route which is "pre-alpha" upstream. Both flagged for plan-time validation.

---

## TL;DR — what changes for v3.1

v3.0 shipped an engineering-green OSS RC with a release pipeline (Apple notarytool + SignPath + Inno Setup MSI + signed-binary verifier). v3.1 is **the distribution polish layer** — it adds:

| Bucket | Net new tools/deps | Install rating | What it enables |
|---|---|---|---|
| 1. **Installer chain** | NONE new (already have Inno Setup + Tauri bundler + `tart` scaffold). Adds **scripted detection-+-guidance for BlackHole / VB-CABLE** + post-install audio-device wiring. | 🟢 GREEN | Closes "user double-clicks DMG/MSI, system extension approves, virtual-audio configured, app ready" — no terminal commands. |
| 2. **Dep audit + lockfile** | `uv==0.11.14` (Python lockfile + sync) + `cyclonedx-python==7.3.0` (SBOM extension to v3.0 syft path) + `cargo-deny==0.18.x` (already in v3.0 rust-cve.yml — verify version pin). | 🟢 GREEN | Reproducible `uv sync` on Mac+Win; CycloneDX SBOM beside existing SPDX; license CI gate via cargo-deny; pinact for GH Actions SHA pinning. |
| 3. **New-dep opportunity scan** | **None RED, none YELLOW** confirmed for inclusion. Audited: `Dante Via` / `Loopback Audio` / `Soundflower` rejected (commercial / dead). MIDI: nothing new (cdj-link-py / ProDJ Link still rejected per memory). Apple Silicon: existing `arch=universal2` covers via P27-06 target-triple convention. | 🟢 GREEN | No new deps; existing baseline already covers the surface. v3.1 explicitly **does NOT widen the stack** beyond hardening — preserves clean-utility constraint. |
| 4. **E2E MacBook test** | `tauri-plugin-playwright==0.1.0` (Rust crate, native webview Playwright bridge) + `@playwright/test==1.50.x` (npm) + `pixelmatch==7.1.0` (visual diff) + `pytest-playwright==0.5.x` (Python sidecar test harness). | 🟡 YELLOW (test-only, never ships to user) | One CLI runs the full app, plays a recorded WAV through a virtual loopback, asserts evidence registry citations + screenshots Tier-1 surfaces + scores mascot frame-rate + emits `eval/macbook-pass/<date>/report.html`. |
| 5. **Mascot real GLBs** | NONE new (already have `three==^0.170.0` + `@gltf-transform/cli==^4.0.0` + `gltf-pipeline==^4.1.0` + Phase 43-05 Mixamo scaffold). Production decision: **Mixamo (free, free-account) + Adobe `auto-rigger` for 5 prep_*.glb retargets**. Reject Ready Player Me (no ARKit blendshapes, character style mismatch) and Auto-Rig Pro ($40 paid Blender add-on, manual). | 🟢 GREEN | 5 prep_*.glb placeholders (44-56 KB stubs) get replaced with 400-1200 KB real clips per the existing two-tier bundle-gate; Emotion + Reaction layers already cover the additive state machine. |

**Net impact on bundle size:** Net delta is dominated by mascot GLB asset growth (5 × ~600 KB stubs → 5 × ~800-1000 KB = ~+4 MB) within the existing 25 MB mascot cap (Phase 31). Bundle stays well under the 350 MB hard cap. **Zero new runtime Python deps.** `uv` and `cyclonedx-python` are dev/CI-only (never ship in PyInstaller `.spec`). `tauri-plugin-playwright` is `dev-dependencies` only — never in release build.

**Net impact on user install action:** **Zero new manual user actions.** Both installers already prompt for permissions. v3.1 adds *detect-and-guide* UX for BlackHole/VB-CABLE (link to vendor `.pkg`/`.exe` if missing; system extension approval still user-driven — Apple/Microsoft constraint, not avoidable).

**Net impact on CI minutes:** `+~3 min/PR` (uv resolve + cyclonedx + cargo-deny). E2E MacBook test runs **nightly on `macos-14` only**, not per-PR (~20 min/run; expensive). Visual baselines fingerprinted; baseline updates require `--update-snapshots` PR.

**Rejected outright** (preserved as anti-list, per memory `feedback_no_scope_creep_clean_utility`): Loopback Audio (commercial, $99), Soundflower (dead/unsigned), poetry-as-replacement-for-uv (slower resolver, weaker lockfile), Pixelmatch alternatives (`looks-same`, `resemblejs` — pixelmatch is Playwright's built-in), Ready Player Me API integration (different art style + ARKit-only blendshapes mismatch our additive Mixamo skeleton), Auto-Rig Pro (paid Blender plugin; Mixamo auto-rig is free and already scaffolded).

---

## I. What Stays Exactly the Same (DO NOT change — v3.0 baseline)

Every entry below is shipped in v3.0 and works. The v3.1 layer is strictly additive on this baseline. Re-doing any of these is regression risk.

| Layer | Component | Locked Version | v3.0 anchor |
|---|---|---|---|
| Runtime | Python | **3.12.x** | `pyproject.toml: requires-python = ">=3.12,<3.13"` |
| Sidecar packager | PyInstaller | **6.20.0** | `vibemix-core.macos.spec` + `.windows.spec`; universal2 via target-triple (P27-06) |
| Mac signing | Apple `notarytool` + Developer ID + create-dmg + stapler | (system) | `scripts/dist/sign_macos.sh` |
| Win signing | SignPath OSS Foundation cert via `signpath/github-action-submit-signing-request@v1.2.0` | **v1.2.0** | `.github/workflows/release.yml` |
| Win installer | Inno Setup 6 (`iscc installer/windows/vibemix-installer.iss`) | **Inno Setup 6** | `installer/windows/vibemix-installer.iss` |
| Mac bundle | Tauri 2 bundler `app + dmg` targets | **tauri==2.11**, **tauri-build==2.6** | `tauri/src-tauri/Cargo.toml` |
| Tauri plugins | shell/store/fs/positioner/updater/process/global-shortcut | 2.3–2.10 (per crate) | `tauri/src-tauri/Cargo.toml` |
| Three.js | mascot renderer | **three^0.170.0** | `tauri/ui/package.json` |
| GLB pipeline | `@gltf-transform/cli` + `gltf-pipeline` | **^4.0.0 / ^4.1.0** | `tauri/ui/package.json` devDeps |
| Brain | livekit-agents + livekit-plugins-google + google-genai | **1.5.8 / 1.5.8 / 2.0.1+** | `pyproject.toml dependencies` |
| Audio | sounddevice + numpy + scipy + mido + python-rtmidi | **0.5.5 / 2.4.4 / 1.17.1 / 1.3.3 / 1.5.8** | `pyproject.toml dependencies` |
| CI security | gitleaks (`secret-scan.yml`) + pip-audit + osv-scanner (`python-cve.yml`) + cargo-audit + cargo-deny (`rust-cve.yml`) + syft SBOM (`sbom.yml`) | (action pins) | `.github/workflows/` |
| Install rehearsal scaffold | `tart` (CirrusLabs) VM matrix (macOS 12.3/14/15) + `rehearsal_runner.py` | (scaffold only) | `scripts/install_rehearsal/` |
| Bundle ID | `world.bravoh.vibemix` LOCKED (Pitfall P63) | (constant) | `bundle-id-lock.yml` CI gate |

**If a v3.1 plan proposes changing any row above, kick back to research.** v3.1 is hardening + polish, not a stack rewrite.

---

## II. v3.1 Stack Additions — Bucket by Bucket

### Bucket 1: One-Click Installer Chain (Win + Mac)

**Goal:** User downloads `vibemix-3.1.0.dmg` or `vibemix-3.1.0-setup.exe` → double-clicks → grants permissions → app opens ready. Zero terminal commands. BlackHole (Mac) / VB-CABLE (Win) detected and guided into install if missing. Audio devices auto-routed.

**New runtime deps: NONE.** Already shipping Tauri 2.11 bundler + Inno Setup 6 + PyInstaller `.onedir` + `tart` VM scaffold.

**New scripts / config changes (no new packages):**

| Item | Type | Purpose | Where it lives |
|---|---|---|---|
| `scripts/install/post_install_audio_setup.sh` (Mac) + `.ps1` (Win) | Shell scripts | Detect BlackHole/VB-CABLE post-install; if missing, open vendor download page; if present, run audio-device probe (already shipping `probe_blackhole` from Phase 40 AUDIO-07) | New |
| First-run wizard `audio-setup.html` updates | TS/HTML | Step 2 of wizard adds explicit "Install BlackHole" / "Install VB-CABLE" CTA cards with download links; pings the probe endpoint until detected | Update `tauri/ui/src/wizard/` |
| Inno Setup `[Run]` section update | `.iss` patch | `Filename: "{tmp}\vb-cable-installer.exe"; Parameters: "/S"; Flags: shellexec waituntilterminated` — bundled VB-CABLE installer with NSIS `/S` silent flag inside our installer (legal: VB-CABLE EULA allows redistribution with attribution; verify at plan time) | `installer/windows/vibemix-installer.iss` |
| Mac DMG post-install hook | `.pkg` postinstall script | Cannot bundle BlackHole `.pkg` redistribution legally without ExistentialAudio sign-off — instead open `https://existential.audio/blackhole/` on first run if `probe_blackhole` returns `missing`. Document this as a "1-click install with one user-driven sub-install" constraint. | `scripts/install/firstrun_blackhole_guide.sh` |

**Tauri bundle targets to keep:** `app + dmg` on Mac (already in `tauri.conf.json5`). Add **`msi` target on Windows for parity** so users who prefer MSI over EXE get one; Inno Setup EXE remains primary (per release.yml). Tauri 2.x WiX-based MSI is built-in (`bundle.targets: ["msi"]`), no new crate.

**Verified flags (silent install reference):**
- **Inno Setup:** `installer.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART` — fully headless. ([Inno Setup Silent Install reference](https://www.advancedinstaller.com/innosetup-silent-install-uninstall-paramaters.html))
- **NSIS (VB-CABLE):** `/S` (uppercase), optional `/D=path` for install dir. ([NSIS Silent Install reference](https://silentinstallhq.com/nsis-silent-install-parameters-reference-guide/))
- **BlackHole `.pkg` silent:** `sudo installer -pkg BlackHole2ch.pkg -target /` — but this **requires sudo** which we can't safely solicit from a Tauri sidecar without first-run elevation UX. **Conclusion: do not silent-install BlackHole; guide user via wizard step.** Documented constraint per [BlackHole Installation wiki](https://github.com/ExistentialAudio/BlackHole/wiki/Installation) — system extension approval is user-driven by macOS design.

**Install impact rating: 🟢 GREEN.**
- Mac: still 1-click for app itself; BlackHole is a one-time secondary install with vendor `.pkg` (user clicks "Allow" in System Settings → Security). User action: ≤3 clicks total.
- Win: full silent-chain feasible (VB-CABLE `/S` bundled inside Inno Setup). User action: 1 click.

**Why this is in scope for v3.1 specifically:** v3.0 shipped the `probe_blackhole` detection (AUDIO-07) + wizard skeleton, but the wizard never had real CTAs for the missing-driver case. v3.1 closes the loop. Without it, every fresh-install user hits a silent failure ("nothing happens when DJ plays").

---

### Bucket 2: Dependency Audit + Pin + Lockfile + SBOM

**Goal:** Every runtime dep pinned + locked + cross-platform reproducible. CycloneDX SBOM published alongside existing SPDX. Stale/unused deps culled. License gate at CI for Rust + Python.

**New tooling (CI/dev only — never ships in PyInstaller bundle):**

| Tool | Version | License | Purpose | When to use |
|---|---|---|---|---|
| **`uv`** | **0.11.14** | Apache-2.0 / MIT | Cross-platform Python lockfile (`uv.lock`); replaces `pip` + `pip-tools` + `virtualenv` for dev install; portable `uv sync` produces identical envs on Mac/Win/Linux | Replace ad-hoc `pip install` in CI + local dev. CI: `uv sync --locked` (fails if lockfile out-of-sync). Dev: `uv pip install -e .`. |
| **`cyclonedx-python`** | **7.3.0** | Apache-2.0 | CycloneDX-format SBOM generator (complement to existing syft SPDX path) | CI step in `sbom.yml` after the existing syft step; uploads `sbom.cdx.json` as second release asset |
| **`pinact`** | **v3.x** (`suzuki-shunsuke/pinact`) | MIT | GH Actions SHA pinning — replaces all `@v4` mutable refs with full commit SHA in `.github/workflows/*.yml` | One-shot transform + pre-commit hook to keep SHAs pinned; closes supply-chain attack vector |
| **`cargo-deny`** | **0.18.x** (verify pin via `cargo install --locked cargo-deny@0.18`) | Apache-2.0 / MIT | Already installed in `rust-cve.yml` Phase 34; v3.1 adds explicit `deny.toml` with license allowlist (Apache-2.0, MIT, BSD-2-Clause, BSD-3-Clause, ISC, Unicode-DFS-2016) + GPL-bans | Tighten existing usage; emit allowlist violations as CI errors not warnings |

**Lockfile mechanic:**
- Add `uv.lock` to repo (cross-platform universal resolution — same lockfile on Mac/Win)
- CI in `python-cve.yml` adds step `uv sync --locked` before `pip-audit`; sync failure = stale lockfile → fail
- Dev workflow: `uv lock --upgrade-package <name>` to bump one dep; `uv lock` to refresh all

**Dep audit / cull pass (v3.1 manual one-time pass — no tooling change, just discipline):**
- Verify `livekit-plugins-openai` is still in `pyproject.toml` (line 35) — `not used directly in cohost code` per CLAUDE.md; **PROPOSE REMOVAL** unless livekit-agents has hard transitive dep (verify via `uv pip tree`).
- Verify `google-cloud-speech` + `google-cloud-texttospeech` are not actively used (per CLAUDE.md `not directly imported`); cull if transitive only.
- Verify pinned versions in `pyproject.toml` match `pip list` (Python 3.14 `.venv` likely contains drift since `pyproject.toml` targets 3.12) → freshly resolve to 3.12 baseline via uv.

**License gate update** (`tauri/src-tauri/deny.toml` — new file):
```toml
[licenses]
allow = ["Apache-2.0", "MIT", "BSD-2-Clause", "BSD-3-Clause", "ISC", "Unicode-DFS-2016", "MPL-2.0"]
deny  = ["GPL-2.0", "GPL-3.0", "AGPL-3.0", "LGPL-3.0"]  # Apache-2.0 + DCO license discipline
confidence-threshold = 0.93
[bans]
multiple-versions = "warn"
```

**Install impact rating: 🟢 GREEN.** All CI/dev only. Zero user-facing surface change.

**Why this is in scope for v3.1 specifically:** v3.0 ships pip-audit + cargo-audit + cargo-deny + syft already (Phase 34), but there's **no lockfile** — `pyproject.toml` is constraints-only, the `.venv` is whatever-`pip-installed`. CycloneDX SBOM is not currently emitted (only SPDX). Pinact is not in CI. These three gaps are the "dep audit" tail of v3.1's distribution-ready thesis.

---

### Bucket 3: New-Dep + Integration Opportunity Scan

This is the **research-pass-and-explicitly-reject-most** bucket. v3.1 is hardening, not stack expansion.

**Candidates audited:**

| Candidate | Category | Install impact | Verdict | Reason |
|---|---|---|---|---|
| **`Dante Via`** (Audinate) | Mac virtual audio alternative | 🔴 RED | REJECT | Commercial ($60), proprietary; BlackHole covers the use case for free |
| **`Loopback Audio`** (Rogue Amoeba) | Mac virtual audio alternative | 🔴 RED | REJECT | Commercial ($99); BlackHole free + open-source |
| **`Soundflower`** | Mac virtual audio legacy | 🔴 RED | REJECT | Abandonware (2014); unsigned; supplanted by BlackHole entirely |
| **`Voicemeeter Banana`** (VB-Audio) | Win virtual audio alternative | 🟡 YELLOW | DEFER (Voicemeeter Standard recommendation in wizard only; do NOT bundle) | Free for VB-CABLE; Banana is donationware with more mixers. Documented as optional "advanced user" path in wizard, NOT in installer. |
| **`pyrekordbox==0.4.4`** XML import | Rekordbox library | 🟢 GREEN | ALREADY IN v3.0 (per pyproject.toml lines 35-60); v3.1 makes no change |
| **`mixxx-osc` PR #14388** | Mixxx adapter | 🟡 YELLOW | DEFER to v3.x candidate scope (per memory `project_v2_open_candidates`) | Upstream PR still unmerged in Mixxx mainline; ship behind feature flag in a future milestone. NOT v3.1. |
| **`prodj-link`** (Java + LAN) | Pioneer ProDJ Link | 🔴 RED | REJECT (per memory `project_v2_open_candidates`) | Wrong market (CDJ hardware not bedroom DJs); Java runtime + LAN config violates one-click install |
| **`beat-this`** Rust crate | Beat-grid detection | 🟡 YELLOW | DEFER (mentioned in v3.x backlog per PROJECT.md line 234) | Non-Gemini path; "gated on install-size budget"; needs separate phase |
| **`cdj-link-py`** | ProDJ Link Python | 🔴 RED | REJECT | Same reasons as `prodj-link` |
| **Numark / Hercules new controllers** | Additional MIDI maps | 🟢 GREEN | DEFER to v3.x Mixxx-corpus-transpile path (per memory `project_v2_open_candidates`) | Not a new dep; just JSON files. v3.1 doesn't widen the 10-controller library — that's a separate v3.x scope item |
| **macOS 26+ (Tahoe/Sonoma successor)** | OS support | 🟢 GREEN | VERIFY at plan time | Phase 33 v2.1 ladder covers 12.3 / 14 / 15; v3.1 INSTALL-VM matrix should add 16 if shipping post-release |
| **Apple Silicon perf** | Hardware-specific | 🟢 GREEN | NO ACTION | Phase 27-06 target-triple universal2 already covers; verify benchmarks include M1/M2/M3/M4 variants in nightly e2e (Bucket 4) |
| **Windows 11 24H2 + WASAPI changes** | OS-version edge | 🟢 GREEN | VERIFY | `PyAudioWPatch==0.2.12.8` (Phase 7) covers WASAPI loopback; spot-check on Win11 24H2 in install-rehearsal matrix |

**Net conclusion:** Zero new runtime deps land in v3.1. The bucket is intentionally narrow per `feedback_no_scope_creep_clean_utility` memory. Two opportunities — Voicemeeter Standard documentation + macOS 16 / Win11 24H2 matrix expansion — are documentation/CI changes, not new packages.

**Install impact rating: 🟢 GREEN (because nothing lands).** This bucket's outcome is a documented decision log, not a code delta.

**Why this is in scope for v3.1 specifically:** v3.0 close left v3.x candidates open (`project_v2_open_candidates` memory) — this bucket explicitly confirms nothing from that list crosses into v3.1 boundary. v3.1 stays narrow.

---

### Bucket 4: End-to-End MacBook Test Harness

**Goal:** One CLI command runs the full app, plays a recorded master-output WAV through a virtual loopback, asserts (a) AI reactions are evidence-cited, (b) Tier-1 UI surfaces match visual baselines, (c) mascot frame-rate ≥60fps p99, (d) latency TTFT p95 ≤ target. Emits structured `report.html` and `report.json` with pass/fail per dimension.

**New dev/CI deps (test-only — never ships):**

| Tool | Version | License | Purpose | Notes |
|---|---|---|---|---|
| **`@playwright/test`** | **1.50.x** (latest stable) | Apache-2.0 | Browser/webview automation API used for visual-regression assertions on Tier-1 surfaces | npm dev dep; not bundled |
| **`tauri-plugin-playwright`** | **0.1.0** (early-stage; verify maturity at plan time) | MIT | Native-webview Playwright bridge — controls WKWebView (Mac) / WebView2 (Win) with Playwright API; closes the documented gap that "Playwright flat-out doesn't work because Tauri uses WebKit not Chromium" | Rust dev-dependency in `Cargo.toml`; gated under `[features] test = []` so production builds don't ship it. **Risk: 0.1.0 maturity** — fallback is `tauri-driver` (WebDriver protocol) which is "pre-alpha" per official docs. |
| **`pixelmatch`** | **7.1.0** | ISC | Pixel-level image diff — Playwright's built-in screenshot comparison library; controls visual baseline thresholds | Already transitive of `@playwright/test`; no explicit install needed |
| **`pytest-playwright`** | **0.5.x** | Apache-2.0 | Python sidecar test harness — drives the Python sidecar from pytest while Playwright drives the UI | Optional; use only if we want Python-side assertions in same test |
| **`coverage[toml]`** | **7.x** | Apache-2.0 | Python coverage for sidecar coverage during e2e runs | Already likely transitive; explicit pin in dev-deps |

**Audio loopback test fixtures (no new deps; uses existing tooling):**
- Existing `sounddevice` + a recorded `tests/e2e/fixtures/dj_set_5min.wav` (already in v3.0 GATE-03 corpus path — 6 × 30-min DJ session WAVs in git-LFS)
- macOS: route via BlackHole 2ch on test agent (CI runner has it pre-installed via `tart` VM image)
- Plays the WAV → master output → BlackHole → sidecar audio capture → Gemini → reaction → mascot → screenshot

**E2E test orchestration (new file: `scripts/macbook_pass/run.sh`):**
```bash
# Single entrypoint Kaan invokes on his M-series MacBook
./scripts/macbook_pass/run.sh --duration 5min --genre hardtek --capture-baselines false
# Outputs: eval/macbook-pass/<UTC>/report.html + report.json + screenshots/ + audio/ + traces/
```

**Dimensions measured (pass/fail per axis — feeds the v3.1 ship gate):**

| Dimension | Tool | Threshold | Source of truth |
|---|---|---|---|
| **Functional** | pytest + tauri-plugin-playwright | All 7 critical flows green (session start → genre pick → set play → reactions emitted → citation strip visible → debrief opens → mascot animates) | New `tests/e2e/test_macbook_pass.py` |
| **Visual (Tier-1 surfaces)** | Playwright `toHaveScreenshot()` + pixelmatch | `maxDiffPixelRatio: 0.02` per Phase 43 surface (session / mascot overlay / wizard / calibration) | Reuses Phase 43 audit driver baselines |
| **Aesthetic (CDJ Whisper)** | Reuse Phase 43 `gsd-ui-auditor` output script | Zero HIGH findings (same as Phase 43 release gate) | `.planning/phases/43-*/UI-REVIEW-*.md` |
| **Usability** | Playwright trace + timing assertions | First-reaction TTFT p95 ≤ 3.5s; wizard onboarding ≤ 60s; mascot frame rate ≥ 60fps p99 | Latency stack v2 (Phase 41) telemetry + Phase 43-04 perf gate |
| **Hallucination** | Reuse `check_ear_test.sh` Gate 2b output | Zero `felt_slop` flags in Kaan's ear-test for this session | Phase 42-03 schema |

**Install impact rating: 🟡 YELLOW** — but **only test-only, never user-facing**. The yellow is acknowledgment that `tauri-plugin-playwright==0.1.0` is early-stage and may need a fallback to tauri-driver / WebDriver if it can't drive WKWebView reliably. Plan-time spike required.

**Why this is in scope for v3.1 specifically:** v3.0 GATE-05 ear-test is **human-driven** (Kaan listens 30 min + writes a JSON). v3.1's MacBook pass is the **engineering-side automation** that catches regressions BETWEEN ear-tests — visual + functional + perf flagging in CI cadence, not just Kaan-eyeball-once-per-release. Without this, the only signal between ear-tests is "PR didn't crash CI."

---

### Bucket 5: Mascot Real GLBs with Full Emotion Coverage

**Goal:** Replace the 5 `prep_*.glb` 44-56 KB placeholder stubs with real animated clips at the 400 KB – 1200 KB per-clip band, covering Base + Emotion + Anticipation + Reaction layers across all event classes. Mascot must be visible on every supported window/screen-share path.

**Existing v3.0 baseline (verified):**
- ✅ `tauri/ui/assets/mascot/character.glb` (the Neon Rebel rig, Mixamo-skeleton) ALREADY LANDED
- ✅ 5 placeholder `prep_*.glb` files exist (44-56 KB each — intentional bundle-gate exit-2 signal per Phase 43-05 decision)
- ✅ Mixamo retarget scaffold in `scripts/mascot/` (CLI + slot taxonomy + draco shell-out + two-tier bundle-gate)
- ✅ Three.js `AdditiveAnimationBlendMode` + `AnimationUtils.makeClipAdditive()` already wired (Phase 31)
- ✅ 4-layer additive state machine (Base + Emotion + Anticipation + Reaction) in production (Phase 31 v2.1)
- ✅ `@gltf-transform/cli==^4.0.0` + `gltf-pipeline==^4.1.0` already in `tauri/ui/package.json` devDeps

**v3.1 production decision: Mixamo + Adobe auto-rig path** (per memory `project_mascot_as_vtuber_personality_surface`).

| Pipeline option | Cost | Quality | Decision |
|---|---|---|---|
| **Mixamo + Adobe auto-rigger** (free w/ Adobe ID) | Free | Production-grade for stylised characters; skeleton convention matches existing rig | ✅ **RECOMMENDED** — already scaffolded by Phase 43-05; just needs Kaan-driven asset selection from Mixamo library |
| **Ready Player Me API** | Free for non-commercial; paid for commercial (Bravoh = commercial) | ARKit blendshape style — doesn't match additive Mixamo skeleton; needs full re-rig of character.glb | ❌ REJECT — art-style mismatch + would force `character.glb` regression |
| **Auto-Rig Pro (Blender)** | $40 paid plugin | Highest quality for custom rigs; manual workflow | ❌ REJECT — paid + manual; Mixamo + auto-rigger covers the same surface for free |
| **AccuRIG 2.0** (Reallusion) | Free | FBX/USD export only; no native GLB | ❌ REJECT — extra conversion step + USD-via-Blender introduces new dep |
| **Meshy / Hunyuan3D** | Free tier | Generative; for character creation not retargeting | ⏸️ DEFER — useful for `/hatch` v2.x stretch goal (memory `project_mascot_as_vtuber_personality_surface`); not v3.1 |
| **Polyhaven / Sketchfab CC-licensed clips** | Free | Variable | ⏸️ DEFER — Mixamo library is wider for stylised humanoid |

**Required clips for v3.1 close** (5 prep_*.glb retargets covering Emotion + Anticipation + Reaction layer permutations):

| Slot | Mascot animation intent | Event-class trigger |
|---|---|---|
| `prep_lean_in_neutral.glb` | Mascot leans forward, neutral expression | Pre-DROP anticipation; pre-LAYER_ARRIVAL |
| `prep_lean_in_hyped.glb` | Lean-in + amped body language | Pre-DROP (peak phase building) |
| `prep_head_turn_left.glb` | Head turn to "left deck" | Pre-MIX_MOVE (audible-deck shifting left) |
| `prep_head_turn_right.glb` | Head turn to "right deck" | Pre-MIX_MOVE (audible-deck shifting right) |
| `prep_settle.glb` | Return-to-idle posture | After event window closes |

**Already-shipped non-prep animations** (per `tauri/ui/assets/mascot/animations/` listing):
- ✅ `walking.glb`, `running.glb`, `magic_genie.glb`, `indoor_swing.glb`, `hip_hop_dance_3.glb`, `fast_lightning.glb`, `funny_dancing_01.glb`, `funny_dancing_03.glb`, `alert_quick_turn.glb`, `all_night_dance.glb`, `big_wave_hello.glb`, `shrug.glb`, `wave_for_help.glb` (Base + Reaction layer pool)

**New tooling: NONE.** The full pipeline (gltf-transform + gltf-pipeline + draco compression + Phase 43-05 retarget CLI) is already installed. v3.1 production is **Kaan-aesthetic asset selection** running through the existing tools.

**Install impact rating: 🟢 GREEN.** Asset growth is +~4 MB (5 stubs × ~50 KB → 5 real clips × ~800 KB). Stays under the existing 25 MB total mascot cap.

**Why this is in scope for v3.1 specifically:** Phase 43-05 shipped the bundle-gate as **intentionally-exit-2 on stub presence** (visible signal that §VIS-04 discharge is pending). v3.1 closes the gate to exit-0. Without it, every release CI run carries an expected-fail signal in the bundle audit — fine for v3.0 (engineering-pre-stage), regressive if v3.1 ships without flipping.

---

## III. v3.1 Per-Platform Constraints

### macOS-only paths

| Capability | Implementation | Constraint |
|---|---|---|
| BlackHole 2ch system extension | User-driven approval (System Settings → Security → "Allow") | Apple system-extension policy — **cannot silent-install**; wizard guides user |
| Tauri WKWebView e2e drive | `tauri-plugin-playwright` (or `tauri-driver` fallback) | Native WKWebView only; no Chromium |
| Universal2 sidecar | Phase 27-06 target-triple convention (NOT lipo-merge) | aarch64-apple-darwin + x86_64-apple-darwin shipped separately; sidecar.rs picks at runtime |
| `tart` install-VM matrix | macOS 12.3 / 14 / 15 (Phase 33 ladder) + add macOS 16 if released | Disk space + macOS license required for real VM execution — Kaan-action under `gsd-autonomous fully` |
| BlackHole detect-and-guide UX | `probe_blackhole` (Phase 40 AUDIO-07) + wizard step | Vendor link (`existential.audio/blackhole`) opens in default browser; user runs vendor `.pkg`; system extension prompt |

### Windows-only paths

| Capability | Implementation | Constraint |
|---|---|---|
| VB-CABLE NSIS silent install | `/S` flag bundled inside Inno Setup `[Run]` section | Verify VB-CABLE EULA permits redistribution; if not, fall back to detect-and-guide (same pattern as Mac BlackHole) |
| Tauri WebView2 e2e drive | `tauri-plugin-playwright` (WebView2 supports CDP natively per [zudo-tauri Playwright Engine Pitfall](https://takazudomodular.com/pj/zudo-tauri/docs/frontend/playwright-engine-pitfall/)) | Lower risk than WKWebView path — WebView2 is Chromium-based |
| SignPath MSI signing | Existing `signpath/github-action-submit-signing-request@v1.2.0` (Phase 38) | OSS Foundation cert approval ~1-week SLA; KAAN-ACTION-LEGAL §SHIP-02 |
| Inno Setup → MSI parity | Add `msi` to Tauri `bundle.targets` for users who prefer MSI | No new tool; Tauri 2.x WiX integration is built-in |

### Cross-platform additions

| Capability | Implementation |
|---|---|
| `uv.lock` cross-platform universal resolution | Mac+Win identical lockfile (per [uv Locking docs](https://docs.astral.sh/uv/concepts/resolution/)) |
| CycloneDX SBOM via `cyclonedx-python` | CI step after syft; uploaded as `sbom.cdx.json` release asset |
| `pinact` SHA pinning of GH Actions | All `.yml` workflows converted in one commit + pre-commit hook |
| Visual baseline regression via Playwright + pixelmatch | Baselines in `tests/e2e/baselines/`; `--update-snapshots` PR workflow |
| Mascot real-clip retarget via Phase 43-05 CLI | Same pipeline both OSes; Mixamo asset fetch is web-browser-only (Adobe ID) |

---

## IV. License Audit (v3.1 additions only)

| New dep / tool | License | Linkable with vibemix's Apache-2.0 + DCO? | Notes |
|---|---|---|---|
| `uv==0.11.14` | Apache-2.0 / MIT | ✅ Yes | Dev/CI only; never ships in PyInstaller bundle |
| `cyclonedx-python==7.3.0` | Apache-2.0 | ✅ Yes | Dev/CI only |
| `pinact` v3.x | MIT | ✅ Yes | Dev/CI only |
| `cargo-deny` 0.18.x | Apache-2.0 / MIT | ✅ Yes | Already in v3.0 CI |
| `@playwright/test` 1.50.x | Apache-2.0 | ✅ Yes | Dev/CI only; never bundled |
| `tauri-plugin-playwright` 0.1.0 | MIT | ✅ Yes | Dev-dependency only (`[features] test`) |
| `pixelmatch` 7.1.0 | ISC | ✅ Yes | Transitive of Playwright |
| `pytest-playwright` 0.5.x | Apache-2.0 | ✅ Yes | Dev/CI only |
| **BlackHole (referenced, not bundled)** | GPL-3.0 | ✅ Yes (link-only; user-driven install via vendor) | We DO NOT redistribute — open vendor URL only. GPL doesn't infect us via "system tool runtime use". |
| **VB-CABLE (potentially redistributed)** | Proprietary, free-for-personal use | ⚠️ YELLOW — verify EULA permits bundled redistribution | If EULA prohibits, fall back to detect-and-guide pattern (same as BlackHole). Plan-time license review required. |
| **Mixamo animations (asset license)** | Adobe license — free use including commercial | ✅ Yes per Adobe Mixamo ToS | Animations are royalty-free for commercial use; provenance documented in `mocks/MASCOT-ASSETS.md` or similar |

**No new dep is RED.** Two YELLOW items:
1. **VB-CABLE redistribution** — needs plan-time EULA verification before silent-install bundling.
2. **`tauri-plugin-playwright` maturity (0.1.0)** — not a license issue, an engineering risk; flag for spike.

---

## V. One-Click-Install Impact Table (per memory `project_one_click_install_hard_req`)

| New Item | Rating | Bundle Size Delta | Install-Time User Action | Why |
|---|---|---|---|---|
| Installer wizard CTA cards (BlackHole/VB-CABLE) | 🟢 GREEN | +~5 KB HTML/TS | Click "Install BlackHole" → vendor opens → ≤3 clicks total | UX polish only |
| Inno Setup `[Run]` VB-CABLE bundled | 🟢 GREEN | +~6 MB (VB-CABLE installer) | None (silent `/S` flag) | Bundled silent install; user-invisible |
| `msi` Tauri bundle target | 🟢 GREEN | +0 (alternative artifact) | None | User picks DMG/EXE/MSI from Releases |
| `uv` Python lockfile | 🟢 GREEN | +0 (dev only) | None | CI/dev only |
| CycloneDX SBOM | 🟢 GREEN | +0 (release asset, not bundled) | None | CI only |
| `pinact` SHA pinning | 🟢 GREEN | +0 | None | CI only |
| `cargo-deny` license allowlist | 🟢 GREEN | +0 | None | CI only |
| `tauri-plugin-playwright` dev-dep | 🟢 GREEN | +0 (gated under `[features] test`) | None | CI/test only |
| Playwright + visual baselines | 🟢 GREEN | +0 | None | CI/test only |
| 5 real prep_*.glb mascot clips | 🟢 GREEN | +~4 MB | None | Asset replace |
| MacBook pass test harness | 🟢 GREEN | +0 (test-only) | None | CI/test only |

**Bundle size projection:**
- v3.0 baseline (after Phase 31 + 40-44 polish): ~270-290 MB (Mac), ~290-310 MB (Win)
- v3.1 additions: +~4 MB (mascot real GLBs) on both; +~6 MB VB-CABLE bundle (Win only)
- **v3.1 shipping size: ~274-294 MB (Mac), ~300-320 MB (Win)** — comfortably under 350 MB hard cap

**Zero new user install actions on Windows. One additional user action on Mac (the BlackHole vendor `.pkg`), wrapped in a guided wizard step.** This is the closest achievable to "true one-click" given Apple's system-extension policy.

---

## VI. Installation Manifest (v3.1 delta)

```toml
# pyproject.toml — additions to [project.optional-dependencies.dev]
[project.optional-dependencies]
dev = [
  # ... v3.0 baseline ...
  "cyclonedx-python==7.3.0",     # SBOM CycloneDX generator (CI)
]
# Note: uv itself is invoked via `pipx install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`
# — not a Python package dependency in pyproject.toml.
```

```bash
# uv lockfile generation (one-time setup, then `uv sync --locked` in CI)
pipx install uv  # or curl install
uv lock                                    # Creates uv.lock
uv sync --locked                           # CI step: fails if lock out-of-sync
uv lock --upgrade-package livekit-agents   # Bump one dep
```

```yaml
# .github/workflows/python-cve.yml — add uv-sync step before pip-audit
- uses: astral-sh/setup-uv@v3      # pinact will SHA-pin this
  with:
    version: "0.11.14"
- run: uv sync --locked --extra dev
```

```toml
# tauri/src-tauri/deny.toml — NEW FILE (cargo-deny license gate)
[licenses]
allow = ["Apache-2.0", "MIT", "BSD-2-Clause", "BSD-3-Clause", "ISC", "Unicode-DFS-2016", "MPL-2.0"]
deny  = ["GPL-2.0", "GPL-3.0", "AGPL-3.0", "LGPL-3.0"]
confidence-threshold = 0.93
[bans]
multiple-versions = "warn"
```

```toml
# tauri/src-tauri/Cargo.toml — add dev-only test plugin
[features]
test = ["dep:tauri-plugin-playwright"]

[dependencies]
# ... v3.0 baseline ...
tauri-plugin-playwright = { version = "0.1.0", optional = true }
```

```json
// tauri/ui/package.json — add Playwright dev deps
{
  "devDependencies": {
    "@playwright/test": "^1.50.0",
    "pixelmatch": "^7.1.0",
    "pytest-playwright": "^0.5.0"  // via npm-managed Python venv hook OR pyproject.toml
  }
}
```

```iss
; installer/windows/vibemix-installer.iss — add VB-CABLE bundled-silent step (after EULA verification at plan time)
[Files]
Source: "vendor\vb-cable-installer.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Run]
Filename: "{tmp}\vb-cable-installer.exe"; \
  Parameters: "/S"; \
  Flags: shellexec waituntilterminated; \
  StatusMsg: "Installing VB-CABLE virtual audio driver..."
```

```bash
# Tauri bundle.targets update (tauri.conf.json5)
# Mac: ["app", "dmg"]  (already)
# Win: ["nsis", "msi"]  (currently just inferred; add explicit MSI for parity)
```

---

## VII. Version Compatibility Matrix (v3.1 additions only)

| Package A | Compatible With | Notes |
|---|---|---|
| `uv==0.11.14` | Python 3.8+ (resolves any 3.x); ours 3.12 ✅ | Cross-platform universal lockfile per docs |
| `cyclonedx-python==7.3.0` | Python 3.9+; ours 3.12 ✅ | CycloneDX spec 1.6 by default; compatible with `cyclonedx` viewers |
| `cargo-deny==0.18.x` | Rust 1.77+; ours 1.77 ✅ | Already verified in `rust-cve.yml` |
| `@playwright/test==1.50.x` | Node 18+; ours 20 ✅ | Latest stable as of research date |
| `tauri-plugin-playwright==0.1.0` | Tauri 2.x; ours 2.11 ✅ | Early-stage; spike at plan time |
| `pixelmatch==7.1.0` | Node 10+; transitive of Playwright | No explicit pin needed |
| `Inno Setup` 6.x with bundled NSIS `/S` | Tested on Win 10/11 | Verify VB-CABLE installer is NSIS-built (it is per VB-Audio reference) |
| Tauri MSI target | Tauri 2.11 + WiX built-in | Already supported via `bundle.targets: ["msi"]` |
| Mixamo character.glb skeleton | `@gltf-transform/cli^4.0.0` retarget | Already validated in Phase 43-05 |

---

## VIII. Alternatives Considered (and rejected)

| Recommended | Alternative | Why Not |
|---|---|---|
| **`uv` for Python lockfile** | `poetry` (1.8+) | uv is significantly faster (10-100×); single tool replaces pip+pip-tools+virtualenv. Poetry's lockfile is platform-specific by default; uv's is universal. |
| **`uv` for Python lockfile** | `pip-tools` (`pip-compile`) | uv supersedes pip-tools; same interface but cross-platform universal; pip-tools is in "maintenance mode" relative to uv pace |
| **`uv` for Python lockfile** | `pipenv` | Pipenv has slower resolver; weaker reproducibility guarantees; project less actively maintained |
| **`cyclonedx-python`** | Continue with only syft (SPDX) | CycloneDX is more common in Python ecosystem per 2026 PyPI analysis (1.58% adoption all CycloneDX, zero SPDX); shipping both formats covers more downstream SBOM consumers |
| **`tauri-plugin-playwright`** | `tauri-driver` (WebDriver) | `tauri-driver` is "pre-alpha" per Tauri 2 docs; macOS has no desktop WebDriver client. `tauri-plugin-playwright` is 0.1.0 but uses the native webview directly — strictly newer + targets the gap. Fallback to tauri-driver if 0.1.0 fails plan-time spike. |
| **`tauri-plugin-playwright`** | `testdriver.ai` | Commercial SaaS; "screenshot + LLM-classifier" approach is opaque, can't run hermetically in CI; we want Playwright's deterministic locator-based assertions |
| **`@playwright/test`** | `WebdriverIO` | Documented as Tauri's official test approach BUT same "pre-alpha tauri-driver" caveat applies; Playwright is more widely-used + better tooling |
| **Mixamo + Adobe auto-rigger** | Ready Player Me API | Art style mismatch (ARKit blendshapes vs. additive Mixamo skeleton); commercial use requires paid tier (Bravoh IS commercial); would force `character.glb` regression |
| **Mixamo + Adobe auto-rigger** | Auto-Rig Pro (Blender) | Paid ($40) + manual rigging; Mixamo + auto-rigger achieves same surface for free; Phase 43-05 already scaffolded |
| **Mixamo + Adobe auto-rigger** | AccuRIG 2.0 (Reallusion) | FBX/USD only; adds Blender-USD conversion step; new tool chain to learn |
| **Mixamo + Adobe auto-rigger** | Meshy/Hunyuan3D + Mixamo | Generative path is for character creation, not retargeting our existing rig; useful for `/hatch` v2.x stretch (per memory `project_mascot_as_vtuber_personality_surface`) |
| **`pinact` SHA pinning** | Manual SHA pinning via dependabot | Dependabot pins SHAs but doesn't enforce in PRs that bypass it; `pinact` is a pre-commit + CI gate that enforces |
| **VB-CABLE silent install** | Voicemeeter Banana bundle | Banana has more mixers but is donationware; VB-CABLE is simpler + freer; document Banana as advanced-user upgrade path in wizard |
| **VB-CABLE detect-and-guide (Mac-pattern fallback)** | Bundle BlackHole `.pkg` | ExistentialAudio EULA permits redistribution but the system-extension approval is Apple-mandated user-driven; detect-and-guide is the same UX |
| **Tauri MSI built-in target** | Wix Toolset standalone | Tauri 2.x WiX integration handles MSI generation; no need for separate WiX install |
| **`tart` install-VM matrix (existing)** | GitHub Actions `macos-latest` runners for full e2e | `macos-latest` is shared/non-deterministic; doesn't have BlackHole pre-installed; `tart` lets us pre-bake VM images with BlackHole + VB-CABLE for reproducible runs |
| **`pixelmatch` (built-in via Playwright)** | `resemblejs` / `looks-same` | pixelmatch is Playwright's built-in; using anything else means double image-diff stack |

---

## IX. What NOT to Add (v3.1 anti-list)

Per memory `feedback_no_scope_creep_clean_utility.md` + `feedback_no_clap_use_gemini_embedding.md`:

| Avoid | Why |
|---|---|
| **Any new AI provider beyond Gemini** | Memory locked: Gemini-only. No OpenAI fallback, no Claude, no local LLMs. Cull `livekit-plugins-openai` if non-transitive (verify uv pip tree first). |
| **CLAP / LAION-CLAP / MERT / OpenL3** | Memory locked: Gemini Embedding 2 is the embedding model. |
| **Stem separation (Demucs, Spleeter)** | Memory locked: deferred. ~500MB model bundle violates one-click install. |
| **Pioneer ProDJ Link / cdj-link-py / prodj-link Java** | Memory locked. Wrong market. Adds Java runtime + LAN config + admin permissions. |
| **Loopback Audio (Rogue Amoeba)** | Commercial $99; BlackHole free covers same. |
| **Dante Via (Audinate)** | Commercial $60; BlackHole free covers same. |
| **Soundflower** | Abandonware, unsigned, supplanted by BlackHole. |
| **Mixxx OSC adapter (PR #14388)** | DEFER to v3.x candidate scope — upstream still unmerged. |
| **`/hatch` user-gen mascot (Meshy/Hunyuan3D)** | v2.x stretch per memory `project_mascot_as_vtuber_personality_surface`. |
| **OBS browser source / `obs-websocket-py` uplink** | Backlog per PROJECT.md line 232. |
| **Beat This! Rust sidecar** | Backlog per PROJECT.md line 234; non-Gemini beat-grid (gates on install-size budget). |
| **Linux support** | Hard exclusion. |
| **`testdriver.ai` / commercial e2e SaaS** | Opaque LLM-classifier; can't run hermetically. |
| **Poetry as Python lockfile** | Slower than uv; platform-specific lockfile by default. |
| **Pipenv** | Slower resolver; weaker reproducibility. |
| **WebdriverIO over Playwright** | Tauri-driver pre-alpha is the limiting factor; tauri-plugin-playwright is the post-2026 workaround. |
| **DAW integration (Logic / Ableton / FL Studio)** | Out of scope per PROJECT.md. |
| **Mobile / iPad / iOS app** | Out of scope per PROJECT.md. |
| **Custom voice cloning** | Out of scope (Gemini TTS prebuilt voices only). |
| **Track recommendation AI** | Out of scope per PROJECT.md (file-watcher exists; AI-suggests defers to v1.1). |
| **Real-time Twitch/YouTube hook** | Out of scope. |

---

## X. Plan-Checker Verification Checklist

Items the gsd-roadmapper / gsd-planner MUST verify when decomposing v3.1 phases:

- [ ] `uv==0.11.14` lockfile generation succeeds with universal resolution (Mac arm64 + x64 + Win amd64 unified)
- [ ] `uv sync --locked` step added to `python-cve.yml` BEFORE `pip-audit` (fail-fast on lock drift)
- [ ] CycloneDX SBOM (`sbom.cdx.json`) uploaded alongside existing SPDX (`sbom.spdx.json`) in `sbom.yml`
- [ ] `pinact` SHA-pins all `@v*` refs in `.github/workflows/*.yml`; pre-commit hook installed in `.pre-commit-config.yaml`
- [ ] `tauri/src-tauri/deny.toml` shipped with license allowlist + GPL denial; `rust-cve.yml` runs `cargo-deny check`
- [ ] `livekit-plugins-openai` cull decision: keep if transitive of livekit-agents 1.5.8, remove if not (verify `uv pip tree`)
- [ ] `tauri-plugin-playwright==0.1.0` spike: 1-day verification that it drives WKWebView + WebView2 reliably; fallback path is `tauri-driver` if spike fails
- [ ] `@playwright/test==1.50.x` + `pixelmatch==7.1.0` + visual baselines under `tests/e2e/baselines/`; baseline update flow requires `--update-snapshots` PR
- [ ] VB-CABLE EULA permits bundled redistribution — if not, fall back to Mac-pattern detect-and-guide wizard step
- [ ] Inno Setup `[Run]` step uses `/S` (uppercase) NSIS silent flag for VB-CABLE; not `/s`
- [ ] BlackHole `.pkg` is NOT bundled — only the vendor URL `https://existential.audio/blackhole/` opened in wizard step
- [ ] `tart` install-VM matrix in `mac_vm_setup.sh` adds macOS 16 if released before v3.1 ship; Win11 24H2 added to `win_vm_setup.ps1`
- [ ] Tauri `bundle.targets` adds `"msi"` to Windows for MSI parity alongside Inno Setup EXE
- [ ] 5 prep_*.glb retargets shipped via Mixamo + Adobe auto-rigger pipeline (`scripts/mascot/` CLI from Phase 43-05); two-tier bundle-gate flips to exit-0
- [ ] MacBook pass test harness (`scripts/macbook_pass/run.sh`) emits `eval/macbook-pass/<UTC>/report.html` covering all 5 dimensions (functional / visual / aesthetic / usability / hallucination)
- [ ] MacBook pass runs nightly on `macos-14`, NOT per-PR (CI cost; ~20 min/run)
- [ ] Bundle size budget verified post-additions: ≤320 MB Win, ≤294 MB Mac (under 350 MB cap)
- [ ] `cargo-deny` `[bans] multiple-versions = "warn"` (not error) — many transitive deps legitimately ship multiple versions
- [ ] Bundle ID `world.bravoh.vibemix` stays locked (any change invalidates user TCC grants for AX + screen + microphone permissions)
- [ ] Mixamo Animation provenance documented in `mocks/MASCOT-ASSETS.md` per Adobe ToS attribution requirements
- [ ] `tauri-plugin-playwright` gated under `[features] test` so production builds don't ship the test bridge

---

## XI. Sources

### Primary (HIGH confidence — direct verification 2026-05-17)

- **uv v0.11.14** — [PyPI](https://pypi.org/project/uv/), [uv docs](https://docs.astral.sh/uv/), [uv lock concepts](https://docs.astral.sh/uv/concepts/resolution/) — universal lockfile; cross-platform reproducibility verified
- **Tauri 2.11.x** — [crates.io](https://crates.io/crates/tauri), [Tauri 2 docs](https://v2.tauri.app/develop/configuration-files/) — current shipped version per release notes
- **cyclonedx-python 7.3.0** — [cyclonedx-bom-tool docs](https://cyclonedx-bom-tool.readthedocs.io/) — most accurate Python SBOM generator
- **cargo-deny + cargo-audit** — [crates.io cargo-audit](https://crates.io/crates/cargo-audit), [RustSec](https://rustsec.org/) — already integrated in v3.0 CI
- **Playwright Tauri integration** — [Tauri WebDriver docs](https://v2.tauri.app/develop/tests/webdriver/), [tauri-plugin-playwright](https://crates.io/crates/tauri-plugin-playwright/0.1.0), [zudo-tauri Playwright Engine Pitfall](https://takazudomodular.com/pj/zudo-tauri/docs/frontend/playwright-engine-pitfall/) — confirms Tauri-WKWebView Playwright gap + 2026 plugin workaround
- **pixelmatch + Playwright visual** — [Playwright docs visual comparisons](https://playwright.dev/docs/test-snapshots), [Bug0 Playwright VRT 2026 guide](https://bug0.com/knowledge-base/playwright-visual-regression-testing) — built-in API + thresholds
- **Inno Setup silent flags** — [Inno Setup Silent Install reference](https://www.advancedinstaller.com/innosetup-silent-install-uninstall-paramaters.html) — `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART`
- **NSIS silent flags** — [NSIS Silent Install reference](https://silentinstallhq.com/nsis-silent-install-parameters-reference-guide/) — `/S` (uppercase only)
- **BlackHole installation** — [BlackHole GitHub](https://github.com/ExistentialAudio/BlackHole), [BlackHole Wiki Installation](https://github.com/ExistentialAudio/BlackHole/wiki/Installation) — confirms system-extension approval is user-driven
- **Mixamo retarget pipeline** — [MoCap Online Mixamo Alternatives](https://mocaponline.com/blogs/mocap-news/mixamo-alternatives), [Tripo3D Mixamo Alternative 2026](https://www.tripo3d.ai/content/en/guide/the-best-auto-rig-mixamo-alternative-tools) — confirms Mixamo + Adobe auto-rigger is the free production path
- **Ready Player Me API** — [RPM docs avatar API](https://docs.readyplayer.me/ready-player-me/api-reference/rest-api/avatars/get-3d-avatars) — confirms ARKit blendshape style mismatch with Mixamo skeleton
- **gltf-transform Draco compression** — [Draco optimization guide](https://compress-glb.com/blog/draco-compression/), [Three.js DRACOLoader](https://threejs.org/docs/pages/DRACOLoader.html) — already wired in our pipeline

### Secondary (MEDIUM confidence — research artifacts)

- `.planning/research/v3-shipped/STACK.md` — v3.0 baseline anchor
- `.planning/research/v3-buckets/A-external-world.md` — external-world dep map at v3.0 planning time
- `.planning/research/v2-buckets/B-followup-1-v11-integration-spec.md` — v11 integration spec
- v3.0 `release.yml` source — release pipeline anchor
- v3.0 `Cargo.toml` source — Tauri 2.11 + plugin pin verification
- v3.0 `pyproject.toml` source — runtime baseline

### Tertiary (LOW confidence — flag for plan-time validation)

- `tauri-plugin-playwright==0.1.0` production stability (early-stage; not yet at 1.0)
- VB-CABLE EULA bundled-redistribution clause (vendor `vb-audio.com` terms; verify at plan time)
- macOS 16 release date relative to v3.1 ship (affects install-VM matrix)
- Mixamo Adobe-account-gated download workflow (Kaan-action; tracked in §VIS-04 KAAN-ACTION-LEGAL)

### Memory anchors (locked decisions — cite in plan-checker)

- `project_one_click_install_hard_req.md` — every new dep rated green/yellow/red
- `feedback_no_clap_use_gemini_embedding.md` — Gemini-only embedding stack
- `feedback_no_scope_creep_clean_utility.md` — Gemini-only, no multi-provider, no enterprise features
- `project_mascot_as_vtuber_personality_surface.md` — single VTuber 3D char; `/hatch` v2.x stretch
- `project_visual_direction_cdj_whisper.md` — visual baseline + design system
- `project_v2_open_candidates.md` — confirmed-deferred-backlog inventory (informs Bucket 3)
- `feedback_autonomous_no_grey_area_pause.md` — autonomous discharge mode; Kaan-action carveouts only
- `feedback_privacy_scope_narrow.md` — privacy rule is narrow (off-limits paths only)
- `feedback_worktree_must_sync_main_first.md` — Phase 40 worktree-isolation learning

---

## XII. Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | `uv==0.11.14` lockfile resolves cleanly across Mac arm64 + x64 + Win amd64 without per-platform deps | §II.B2 | If platform-specific markers required, fall back to multi-lockfile pattern (Mac vs Win) — adds complexity but doesn't block |
| A2 | `tauri-plugin-playwright==0.1.0` drives WKWebView reliably enough for our 7 critical flow assertions | §II.B4 | If 0.1.0 spike fails: fall back to `tauri-driver` (pre-alpha) — flaky, but documented Tauri path; OR run e2e only on WebView2 Win until plugin matures |
| A3 | VB-CABLE EULA permits bundled silent-install redistribution inside our Inno Setup | §II.B1, §IV | If not: fall back to Mac-pattern detect-and-guide; user clicks one extra time. Not a blocker. |
| A4 | Mixamo + Adobe auto-rigger produces clips that visually + temporally match Phase 31 4-layer additive state machine | §II.B5 | If clips don't match additive blending expectations, run `AnimationUtils.makeClipAdditive()` preprocessing (already known per A6 of v3.0 STACK assumptions) |
| A5 | Bundle size stays under 350 MB cap after VB-CABLE bundle (Win) + mascot real GLBs | §V | If exceeds: trim VB-CABLE to detect-and-guide path; or compress GLBs harder via gltf-transform draco level boost |
| A6 | `tart` install-VM image creation cost (~1 hr per OS) fits Kaan-action discharge in §SHIP-04 INSTALL-VM-RUN | §III, §X | If image-creation infra is harder than planned, document the prerequisite + defer real-VM-run to v3.2; engineering scaffold (current Phase 33-08) stays green |
| A7 | `pinact` SHA-pin transform doesn't break any v3.0 CI workflow due to action-version constraints | §II.B2 | If any pinned SHA references a version with breaking changes, unpin selectively + document in v3.1 STATE.md |
| A8 | E2E MacBook pass test harness's audio-loopback fixture (BlackHole + recorded WAV) reliably reproduces a real DJ session within 5-min run window | §II.B4 | If timing-sensitive event detection doesn't fire deterministically with a recorded WAV, fall back to PIE (playback-in-environment) on Kaan's actual rig — but that defeats automation. Spike at plan time. |

---

## XIII. Cross-Reference to v3.1 Goals

| v3.1 Goal (per PROJECT.md line 17-22) | Bucket | Stack Items |
|---|---|---|
| One-click install scripts (Win + Mac) | Bucket 1 | Inno Setup VB-CABLE bundle + Tauri MSI target + wizard CTA cards |
| System requirements + dep audit/pin | Bucket 2 | uv lockfile + cyclonedx SBOM + pinact + cargo-deny |
| New dep + integration opportunity scan | Bucket 3 | Audited list — zero new packages confirmed; documented anti-list |
| End-to-end MacBook pass | Bucket 4 | tauri-plugin-playwright + Playwright + pixelmatch + audio loopback fixture |
| Mascot fully visible with all emotions wired | Bucket 5 | 5 prep_*.glb retargets via Phase 43-05 Mixamo CLI (zero new tooling) |

---

*Stack research for: v3.1 Distribution-Ready Pass — adds installer chain, dep audit/lockfile/SBOM, e2e MacBook test harness, real mascot GLBs to the v3.0 baseline. Zero new runtime deps. CI/dev/test-only additions. Bundle stays under 350 MB. Confidence: HIGH on lockfile/SBOM/installer; MEDIUM on Playwright-Tauri integration (0.1.0 plugin maturity); MEDIUM on Mixamo asset selection.*

*Researched: 2026-05-17 by gsd-researcher.*

*Word count: ~5,800.*
