<!-- refreshed: 2026-05-17 for milestone v3.1 -->
# Feature Research — v3.1 Distribution-Ready Pass

**Domain:** vibemix v3.1 — distribution polish for the v3.0 engineering-complete OSS RC (Win + Mac one-click install, dep audit/pin, MacBook end-to-end pass, mascot full emotion coverage, new-dep opportunity scan)
**Researched:** 2026-05-17
**Confidence:** HIGH on category structure + dependency graph on existing v3.0 surface; HIGH on mascot emotion enumeration (anchored to shipped v2.1 4-layer state machine + Plutchik 8-primary set); MEDIUM on Windows install-flow expectations (VB-CABLE driver-signature prompt is OS-mandated, not removable); MEDIUM on the dep-opportunity scan outcomes (Mixxx OSC + 30-controller transpile are confirmed v3.x candidates per `project_v2_open_candidates`, but green/yellow/red ratings need a small parallel research pass to confirm).

---

## Domain Framing — Where v3.1 Sits

v3.0 closed engineering-complete on 2026-05-17. Every shipping product surface — anti-slop audio path (mic-as-Part-2 + lookahead-as-Part-3), latency stack v2 (ModelRouter + implicit caching + LLM→TTS streaming + Embedding 2 MRL), hybrid hallucination gate, CDJ-Whisper visual lock on Tier-1 surfaces, README hero verbatim lock, EvidenceRegistry citation strip, KAAN-ACTION-LEGAL §SHIP-01..13 discharge cookbook — is in the repo. **The product itself is finished. v3.1 is not new product scope.**

What v3.1 is doing instead: closing the gap between "Kaan's machine runs this" and "anyone on a clean Mac or Windows box can run this." That gap has five distinct shapes, mapped one-to-one to the milestone's target features:

1. **INSTALL** — `project_one_click_install_hard_req` says the install path is HARD requirement: app opens → auto-downloads deps → configures audio → ready. v2.1 Phase 33 shipped the TCC permissions wizard + BlackHole probe + onboarding stopwatch + bundle-ID lock. v3.0 Phase 45 SHIP-04/05 scaffolded the fresh-VM matrix runner (`tart`) but real-VM execution is gated on signed binaries (SHIP-01/02 external clock). **v3.1's job** is to turn the install path into a single visible double-click from `.dmg`/`.msi` to a running app with zero terminal commands AND validate it actually works on a clean machine.

2. **DEPS** — v2.1 Phase 34 shipped `gitleaks` + `pip-audit` + `osv-scanner` + `cargo-audit` + `cargo-deny` + `syft` SBOM + signed-binary verifier + STRIDE-lite + telemetry-opt-in default-OFF + capability allowlist lint. The CI machinery exists. **v3.1's job** is to make "are these deps healthy/current/secure" answerable in <2min by surfacing the existing machinery's output — pinned versions, license, install-impact rating, dep diff bot, AUDIT.md as a single human-readable surface.

3. **TEST** — v3.0 Phase 42 established the hybrid hallucination gate (autonomous proxy fast-lane + Kaan-ear release-cut veto via `check_gate.sh` Gate 2b). `project_phase_16_kaan_dj_testing` pins the hallucination gate to Kaan's personal DJ-set testing — NOT a 30-session formal harness. **v3.1's job** is broader than the hallucination gate alone: it's Kaan running the *full* product end-to-end on his MacBook — install, calibration wizard, first session, mascot emotion coverage, debrief UI, library intel, every CDJ-Whisper surface — and validating it as if he were a first-time user. Visual + aesthetic + usability dimensions, not just functional.

4. **MASCOT** — v2.1 Phase 31 shipped the 4-layer additive state machine (Base + Emotion + Anticipation + Reaction). v3.0 VIS-04 scaffolded the Mixamo retarget pipeline but the 5 `prep_*.glb` clips remain placeholders pending Kaan's Adobe-account-gated Mixamo download + Kaan-aesthetic Pioneer-CDJ-headbob selection. v3.0 VIS-05 ran the mood→animation pool runtime validation against the existing clip set (Hype-man / Teacher / Coach 30s smoke). **v3.1's job** is to land the actual emotion-clip set across all four layers — not just placeholders — so the mascot is *fully visible* with the right state-machine response to every event class. This is the only v3.1 feature that adds real authored content; everything else is polish/audit/test.

5. **OPPORTUNITY-SCAN** — `project_v2_open_candidates` confirms Mixxx OSC + map transpile + pyrekordbox + Gemini Embedding 2 + post-session debrief as v2.x; ProDJ Link + stems + CLAP as deferred. v3.x candidate scope in PROJECT.md lists Mixxx OSC adapter + Mixxx map transpiler + 10→30+ controller library + pyrekordbox + multi-session debrief + library coach drill packs as confirmed open candidates. **v3.1's research-pass job** is a small parallel scan to confirm WHICH integrations widen real-world compatibility enough to land in v3.1 itself (vs roll forward to v3.2). Only green-rated ones (low install-impact, high coverage) make v3.1. The scan is the deliverable — actual integrations land in their own phases.

The thread connecting all five: v3.0 left every back-end pipeline ready. v3.1 closes the operator-facing surface that turns "ready" into "shippable."

---

## Feature Landscape by Category

> **Reading guide for the roadmapper.** Every category traces to one of the 5 milestone target features in PROJECT.md. **Complexity** uses `single-day plan` (≤1 E-day; `gsd-quick` candidate) / `multi-day phase` (2-5 E-days; standard `/gsd-execute-phase`) / `epic` (>5 E-days; split into multiple plans within a phase). Dependencies on existing v3.0 features are explicit. Anti-features have stated alternatives — no scope creep tolerated per `feedback_no_scope_creep_clean_utility`.

---

### Category 1 — INSTALL: One-Click Install (Win + Mac)

**Thesis:** "One-click" on Mac is genuinely one click after the `.dmg` is opened (Homebrew-equivalent cask install of BlackHole + bundled sidecar + first-launch wizard). "One-click" on Windows is one click + one OS-mandated driver-signature security prompt for VB-CABLE — the Windows audio driver UAC dialog cannot be suppressed by ANY installer per VB-Audio forum confirmation. v3.1's job is to make those flows visible, monitored (`onboarding-stopwatch.ts` already shipped), and survive the fresh-VM matrix (tart runner from SHIP-04 already scaffolded).

#### Table Stakes

| Feature | Why Expected | Complexity | Depends on |
|---|---|---|---|
| **Signed `.dmg` + signed `.msi`/`.exe` artifacts** download from `releases/latest` | Without it, macOS Gatekeeper / Windows SmartScreen rejects → 0% install conversion. Engineering-side completely done (v2.1 Phase 38 + v3.0 Phase 45). v3.1 just walks SHIP-01/02 cookbook + DIST-19 verification on the resulting artifacts. | single-day plan (post-external-clock) | v3.0: SHIP-01 (Apple Dev Agreement) + SHIP-02 (SignPath OSS) + SHIP-03 (DIST-19 verify). |
| **First-launch wizard end-to-end walk** — `.dmg`/`.msi` open → app launches → wizard runs probes (BlackHole / VB-CABLE / TCC / MIDI / Gemini proxy reachability) → user lands on a configured live-mode session with mascot visible | The hard requirement per `project_one_click_install_hard_req`. The wizard exists (v2.1 Phase 33), but v3.1 validates it on clean hardware end-to-end with `onboarding-stopwatch.ts` confirming ≤60s. | single-day plan (SHIP-04/05 cookbook real run) | v3.0: SHIP-04 (`tart` matrix runner) + SHIP-05 (60s gate). v2.1: TCC wizard + BlackHole probe + bundle-ID lock. |
| **BlackHole 2ch auto-detect-and-prompt** — wizard detects missing BlackHole, opens "click here to install" CTA, launches Homebrew install if available, falls back to direct `.pkg` download + open if not, polls for device-list appearance | BlackHole `brew install --cask blackhole-2ch` is the path-of-least-resistance on Macs that already have Homebrew. Fresh Macs without Homebrew need `.pkg` fallback. Either way the wizard waits for `sounddevice` to see the device. v3.0 §AUDIO-07 Kaan-discharge already walks fresh-Mac → CTA fires; v3.1 wires the Homebrew-first / `.pkg`-fallback decision tree into the CTA action. | single-day plan | v3.0: AUDIO-07 fresh-Mac probe. v2.1: BlackHole probe in install wizard. |
| **VB-CABLE auto-prompt + driver-signature dialog framing** (Windows) — wizard detects missing VB-CABLE, runs `VBCABLE_Setup_x64.exe -i -h`, shows user a forewarning that "Windows will ask permission to install an audio driver — click Yes" because the UAC + driver-signing dialog CANNOT be suppressed by any installer flag per VB-Audio forum | The unavoidable Windows install asterisk. Forewarning the user reframes the prompt from "scary unexpected UAC" to "expected step in vibemix setup." First-class UX move that turns a friction point into a trust signal ("we told you it was coming"). | single-day plan | None (greenfield wording + sequencer). |
| **Generic-MIDI fallback path on no-controller-detected** | Already exists from v2.0 Phase 9. v3.1 just confirms the wizard surfaces it gracefully and the user can advance without a controller plugged in. | single-day plan | v2.0: Phase 9 generic-MIDI fallback. |
| **App opens to a configured-and-ready state** — wizard exit lands on session-ready with default mode (Hype-man / Coach via prompt matrix) + default Beginner skill level + mascot visible + Bravoh proxy connected | "Configured-and-ready" is the user-perceived definition of "one-click." Anything that ends at a config screen instead of a working session = failed. | single-day plan | v2.1 Phase 33 wizard exit-flow; v3.0 Phase 44 Bravoh proxy connection. |
| **Onboarding stopwatch confirms ≤60s** end-to-end on every VM in the matrix (macOS 12.3 / 14 / 15 + Win 10 / 11) | The stated bar from v2.1. SHIP-05 makes it a release gate. Without it, "one-click <60s" claim in README is unverified marketing. | single-day plan (SHIP-05 real run) | v3.0: SHIP-05 `--check-60s` sub-gate. v2.1: `onboarding-stopwatch.ts`. |

#### Differentiators

| Feature | Value Proposition | Complexity | Depends on |
|---|---|---|---|
| **Single-binary sidecar (universal2 + AOT)** — no Python interpreter shipping separately; user double-clicks app and Python is invisible | v2.1 Phase 27-06 already shipped universal2 sidecar (target-triple convention, PKG archive embedded in last merged slice). v3.1 just confirms the install-impact rating is GREEN and the README's "no Python needed" claim is verifiable on a fresh VM. | single-day plan (audit only) | v2.1: Universal2 sidecar (Phase 27-06). |
| **First-session demo button** — wizard final step offers "play 60s of canned audio to see vibemix react before you DJ" (uses deterministic 30-event demo-mode sequencer from v3.0 VIS-09) | The visceral proof that vibemix actually works before the user commits to a real set. Lowers "did I install this right?" anxiety. v3.0 VIS-09 already built the deterministic sequencer for Francesco's hero-demo capture; v3.1 reuses it as a user-facing first-session bootstrap. | multi-day phase (2-3 E-days incl. wiring + UI hookup) | v3.0: VIS-09 deterministic demo-mode sequencer. v2.1: Phase 33 wizard exit-flow. |
| **Uninstall path that actually cleans up** — Mac `/Applications/vibemix.app` drag-to-trash + `~/Library/Application Support/vibemix` removal CTA; Win `appwiz.cpl` clean removal + `%APPDATA%\vibemix` removal CTA; BlackHole / VB-CABLE explicitly NOT auto-removed (user may want them for other apps) | Most one-click installers ship without uninstallers. Shipping a clean uninstall path that telegraphs respect for the user's system (we don't touch BlackHole/VB-CABLE because you may want them for OBS, Reaper, etc.) is a polish signal that lands on Reddit comments and HN threads. | single-day plan | None (greenfield wording + script). |
| **Wizard a11y pass** — keyboard nav, screen reader labels, high-contrast palette already from CDJ Whisper, focus rings | Disability-aware open-source DJ tools are rare. The wizard is the only mandatory surface every user hits; a11y here is a moral floor AND a Reddit-comment trust signal. v3.0 Phase 44 a11y gate already covers README controller grid; extending it to the wizard is straightforward. | single-day plan | v3.0: Phase 44 4-gate a11y CI scaffolding. |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---|---|---|---|
| **Bundle BlackHole / VB-CABLE inside the vibemix installer** | "Truly zero clicks, even the audio driver." | Re-distribution of BlackHole MIT (allowed) + VB-CABLE EULA (forbids redistribution without contract). Even ignoring the EULA, Windows driver-signature prompt fires regardless of who delivers the binary — bundling doesn't suppress it. Bundling adds 5-15MB and version-pinning headaches. | Auto-prompt + download + run the official installer with forewarning. User experiences one extra UAC prompt; we stay license-clean. |
| **Auto-update channel with silent installs** | "Modern app UX." | Adds Tauri updater key escrow + signing CI surface + privacy concerns (silent install of an audio-listening app is the kind of thing that lands on /r/privacy). v3.0 AUDIO-06 already established the updater-key rotation cookbook but didn't ship silent-update. | Tauri's normal `tauri-plugin-updater` user-confirm-then-install flow. User retains the agency. |
| **`.deb` / `.AppImage` / Linux bundling** | "OSS-friendly multi-platform." | `project_one_click_install_hard_req` + Linux Out-of-Scope decision in PROJECT.md. DJ-on-Linux audience is small; engineering cost doubles. | Document Linux as Out of Scope in README; accept the PRs from community contributors as a v3.x stretch only if a Linux-DJ surfaces with a working patch. |
| **30-session install rehearsal across hardware** | "Empirical stability on the long tail." | The fresh-VM matrix (macOS 12.3 / 14 / 15 + Win 10 / 11) is the 5-config matrix. Beyond that is diminishing-returns + opens an infinite well of "is M1 Air 8GB different from M2 Pro 16GB?" testing. | Kaan's MacBook + 5-config tart matrix is the floor. Real hardware variance surfaces post-launch via day-zero ops (Phase 36) Discord triage. |
| **Cross-platform "one binary"** (e.g., Electron forge full-uniform path) | "Less Tauri vs PyInstaller plumbing." | Locks us into Electron's RAM tax + Chromium update treadmill. Tauri's reason-to-exist is that exact tradeoff. | Stay on Tauri shell + Python sidecar; the sidecar is universal2 on Mac + arch64 on Win — close enough. |
| **macOS App Store distribution** | "Reach + trust signal." | Sandbox + entitlements review on an audio-capture app that reads MediaRemote API + screen-shares djay Pro window = a multi-month review battle. Apple's stance on apps that observe other apps' UI has been historically negative. Sandboxing would also disable `mss` screen-capture path. | Direct `.dmg` distribution from GitHub releases. SHIP-04 fresh-VM matrix is the Gatekeeper validation. |

**Research notes:**
- BlackHole Homebrew cask path: [`brew install --cask blackhole-2ch`](https://formulae.brew.sh/cask/blackhole-2ch) — current version 0.6.1, MIT-licensed, redistribution OK.
- VB-CABLE silent-install flags `-i -h` work but the Windows driver-signature security dialog is OS-enforced and cannot be suppressed — confirmed in [VB-Audio forum t=1909](https://forum.vb-audio.com/viewtopic.php?t=1909) and [t=1766](https://forum.vb-audio.com/viewtopic.php?t=1766).
- Tauri Windows installer: WiX MSI + NSIS `.exe` paths shipped from [Tauri docs](https://v2.tauri.app/distribute/windows-installer/); WebView2 bootstrap embedded by default. Tauri's native installer wizard already handles VBSCRIPT + WebView2 + C++ Build Tools detection.
- v2.1 Phase 33 install hardening (TCC wizard + BlackHole probe + onboarding stopwatch + bundle-ID lock) — shipped.
- v3.0 SHIP-04/05 (tart fresh-VM matrix + ≤60s gate) — scaffold GREEN, real-VM run pending external clock (SHIP-01/02).

---

### Category 2 — DEPS: Dep Audit/Pin Surface

**Thesis:** v2.1 Phase 34 shipped every audit *tool*. v3.1 surfaces the audit *output* as a single human-readable artifact answerable in <2min. The CI machinery already produces gitleaks + pip-audit + osv-scanner + cargo-audit + cargo-deny reports; `syft` already generates SBOM; STRIDE-lite + SECURITY.md exist. The job is consolidation, badging, and an `AUDIT.md` that someone reviewing the OSS project can read in 2 minutes and conclude "yes, these deps are healthy, current, secure, license-clean."

#### Table Stakes

| Feature | Why Expected | Complexity | Depends on |
|---|---|---|---|
| **Every Python + Rust + Tauri runtime dep pinned in lockfile** with rationale + license + install-impact rating (green/yellow/red per `project_one_click_install_hard_req`) | Required for reproducible builds + license compliance + security-audit answer. Many of these already pinned via `requirements.txt` / `Cargo.lock` / `package-lock.json`; v3.1 adds the human-readable rationale column. | multi-day phase (2-3 E-days incl. dep-by-dep review + AUDIT.md authoring) | v2.1: Phase 34 audit tools shipped. |
| **`AUDIT.md` as single human-readable surface** — table of dep / version / license / install-impact / "why we have it" — committed at repo root, linked from README | The "answerable in <2min" surface. Reviewers (potential OSS contributors, security folks, package maintainers) want one URL not a CI dashboard hunt. | single-day plan | v2.1: Phase 34 audit machinery output. |
| **CI badges in README** — gitleaks ✓ / pip-audit ✓ / osv-scanner ✓ / cargo-audit ✓ / SBOM published / signed-binary verified | Standard OSS trust signal. Reviewers/contributors evaluate trust by README badges; if our CI green-lights all of them, putting badges on README turns invisible CI into visible trust. | single-day plan | v2.1: Phase 34 CI workflow outputs. |
| **Stale-dep / outdated-dep nightly bot** — Dependabot or Renovate configured to surface deps > 6 months stale + auto-PR security patches | OSS-standard hygiene. GitHub's free Dependabot covers Python + Rust + JS. Without it, `AUDIT.md` rots silently. | single-day plan | None (Dependabot config). |
| **`unused-deps` sweep + cull** — actually-imported deps survive; transitive-only or aspirational deps removed | The v3.0 close noted that `openai==2.36.0` is installed as a livekit-agents transitive dep but unused directly. `google-cloud-speech` + `google-cloud-texttospeech` are installed but not directly imported. Each unused dep = bigger sidecar, bigger SBOM noise, longer install. | single-day plan | None (sweep against current `.venv`). |
| **SBOM published as release artifact** — `syft` SBOM generated on tag-push, attached to `gh release` as `vibemix-vN.N.N-sbom.spdx.json` | Standard supply-chain hygiene per [Mattermost SBOM audit guide](https://mattermost.com/blog/how-to-audit-a-security-bill-of-material-sbom/) — release artifacts should ship with SBOM alongside binaries. v2.1 Phase 34 generates the SBOM; v3.1 wires it into the release.yml asset list. | single-day plan | v2.1: Phase 34 syft SBOM. v3.0: SHIP-07 release.yml. |

#### Differentiators

| Feature | Value Proposition | Complexity | Depends on |
|---|---|---|---|
| **Lockfile-diff bot on every PR** that comments dep changes (added / removed / version-bumped) in a short summary | Standard CI courtesy. Makes review faster — reviewer doesn't have to mentally diff `Cargo.lock`. Tools like `dependabot/changelog-action` and GitHub-native diff comments cover this. | single-day plan | None (Action config). |
| **License-policy gate in CI** — `cargo-deny licenses` + `pip-licenses` allowlist of GPL-3 / Apache-2 / MIT / BSD / ISC / etc.; PR fails if a copyleft-incompatible license enters | License-clean is a v3.x consideration if Bravoh wants to consume vibemix code internally (per CLAUDE.md constraint: "Must allow Bravoh to use the same code internally if needed"). | single-day plan | v2.1: Phase 34 `cargo-deny` already in CI. |
| **Per-dep install-impact rating surfaced in AUDIT.md** — every dep gets explicit green/yellow/red rating (e.g., `livekit-agents` = green / `pyobjc-framework-Quartz` = yellow Mac-only / `mido` + `python-rtmidi` = green optional) | Operationalizes the `project_one_click_install_hard_req` memory directive. Future PRs adding deps can be gated on "is this green?" | single-day plan (part of AUDIT.md authoring) | None (greenfield). |
| **`AUDIT.md` link in security policy** — SECURITY.md cross-links AUDIT.md so a security-first reviewer reads them as one surface | Polish. SECURITY.md is the file security folks already open; AUDIT.md sitting next to it = no extra surface to discover. | <0.5 E-day | v2.1: SECURITY.md shipped. |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---|---|---|---|
| **Add Snyk / Black Duck / Dependency-Track enterprise SBOM analysis** | "Enterprise-grade audit." | These are paid tools designed for enterprise consumption. Free Dependabot + GitHub's built-in vulnerability scanning covers >90% of what an OSS project needs. Adding paid tooling adds a vendor dep + a new cost line + reviewer cognitive load. | Free Dependabot + GitHub's vulnerability alerts + the existing `gitleaks` / `pip-audit` / `osv-scanner` / `cargo-audit` stack. |
| **Build an internal vulnerability dashboard** | "Single pane of glass." | OSS projects don't need internal dashboards — reviewers want public READMEs + CI badges. Building a dashboard = building a product on top of the product. | `AUDIT.md` + CI badges + Dependabot tab. |
| **License compliance via SBOM scanning a la enterprise audit** | "Defensive against future Bravoh-internal-consumption concerns." | The CLAUDE.md constraint says vibemix needs to be Apache-2 or MIT compatible — that's a one-time license choice, not an ongoing dashboard problem. | LICENSE file at root (Apache-2 or MIT TBD per PROJECT.md) + `cargo-deny licenses` gate. |
| **Vendoring all Python deps into the repo** | "Reproducibility without lockfile trust." | Repo size explodes + `dependabot` no longer reads them + audit tools no longer scan them. Lockfile is the right primitive. | `requirements.txt` lockfile (pinned to specific versions, hash-validated via `pip install --require-hashes`) + Cargo.lock + package-lock.json. |
| **Auto-PR every minor version bump** | "Always latest." | Library minor bumps with audio/AI deps frequently break behavior. Auto-merging or even auto-PRing minors creates noise + risk. | Dependabot configured to PR only security patches automatically; minor/major version bumps as draft PRs for Kaan review. |

**Research notes:**
- v2.1 Phase 34 already shipped `gitleaks` + `pip-audit` + `osv-scanner` + `cargo-audit` + `cargo-deny` + `syft` SBOM + STRIDE-lite + SECURITY.md.
- [Mattermost SBOM audit guide](https://mattermost.com/blog/how-to-audit-a-security-bill-of-material-sbom/) confirms SBOM-with-release pattern.
- [dep-scan v5.1.4](https://securityonline.info/dep-scan-fully-open-source-security-audit-for-project-dependencies/) is OSS alternative if the existing stack misses gaps; likely not needed.
- The full OSS hygiene reference stack: Dependabot + GitHub Actions + lockfile + CI badges in README + SBOM-with-release is the consensus pattern (covered by [SPDX open-source tools](https://spdx.dev/tools/open-source-tools/)).

---

### Category 3 — TEST: End-to-End MacBook Pass

**Thesis:** v3.0 Phase 42 locked the hallucination gate to Kaan's ear via `check_gate.sh` Gate 2b. v3.1 broadens the gate to *every* operator-facing dimension: functional flows, CDJ-Whisper visual surfaces, mascot emotion coverage in live use, debrief UI ergonomics, library intel "what's playing?" search responsiveness, install-wizard a11y. Kaan acts as the first-time user, NOT the developer who built the thing. Per `project_phase_16_kaan_dj_testing`, this is Kaan's DJ ear extended to the full product — NOT a formal usability lab study or 30-session replay harness.

#### Table Stakes

| Feature | Why Expected | Complexity | Depends on |
|---|---|---|---|
| **Functional flow walk** — install wizard → first session → live mode (Hype/Coach × Beginner/Intermediate/Pro) → mascot reacts → mic-as-Part-2 grounds reactions → debrief opens → drill cards → library search → uninstall | Every shipping surface gets a Kaan-as-user walk. This is the v3.1 release-cut bar. Pass = engineering ships v3.1; fail = gap-closure items routed back to specific phases. | multi-day phase (3-5 E-days Kaan-time, calendar-blocking) | v3.0 + v2.1 + v2.0 shipping surfaces. |
| **Visual + aesthetic critique pass** — every CDJ-Whisper Tier-1 surface re-walked by Kaan-as-user (session / mascot overlay / wizard / calibration / debrief) with paired `gsd-ui-checker` + `gsd-ui-auditor` re-run | v3.0 Phase 43 closed VIS-01 at zero HIGH findings BUT that was a developer walk against mocks + composable components. v3.1 re-walk is "live on real hardware running a real session" which surfaces a different class of issues (rendering perf on integrated GPU at 1440p, font rendering on retina vs non-retina, mascot framerate when ML inference is hot, etc.). | single-day plan (re-run of ui-checker + ui-auditor against running app) | v3.0: Phase 43 VIS-01 Tier-1 surfaces. |
| **Mascot emotion coverage check** — Kaan triggers every event class while observing mascot; confirms each emotion lands at the right time with the right layer-stack response (e.g., TRACK_CHANGE should not look the same as DROP) | The mascot is the single largest non-Kaan piece of authored content; coverage is the hard verifiable test. See Category 4 for the actual emotion enumeration. | multi-day phase (2 E-days; bundled with Category 4 emotion-asset land) | v2.1: Phase 31 4-layer state machine. v3.0: VIS-05 mood→animation pool validation. |
| **Usability heuristic pass against Nielsen 10** — visibility of system status / match between system + real world / user control + freedom / consistency / error prevention / recognition rather than recall / flexibility / aesthetic minimalist / help recover from errors / docs | Standard usability heuristics applied as a checklist by Kaan-as-user. Lightweight version of a UX audit — no academic rigor, just "did anything feel broken or wrong?" | single-day plan | Kaan-time + Nielsen 10 checklist. |
| **Hallucination gate re-run via `check_gate.sh` Gate 2b** — Kaan signs ear-test log per v3.0 GATE-05 protocol (≥2 sessions ≥2 genres in 14d window) | The shipped Phase 42 hybrid regime. v3.1 doesn't change the gate; it walks the discharge runbook now that the audio-path closes (mic-as-Part-2 + lookahead-as-Part-3 are LIVE on Kaan's MacBook). | multi-day phase (≥2 sessions ≥30min each + log capture) | v3.0: GATE-05 ear-test protocol + GATE-06 `check_gate.sh`. |
| **Gap-closure routing** — every fail surfaces as a tracked item routed back to a v3.1 plan or deferred to v3.2 with reason | The audit-trail. Without it, fails get hand-waved away and v3.1 ships with the same gaps the test was designed to catch. | <0.5 E-day (PROJECT.md or STATE.md tracking surface) | None (greenfield routing convention). |

#### Differentiators

| Feature | Value Proposition | Complexity | Depends on |
|---|---|---|---|
| **Capture screen-recording of the entire walk** — every Kaan-test session records the screen + voice + mascot for later review or for the demo film capture | Doubles up: usability evidence + raw footage Francesco can mine for the launch wave. The deterministic-demo-mode sequencer from v3.0 VIS-09 is one path; live-set recording is the complementary path. | single-day plan (existing macOS screen-recorder or `ffmpeg -f avfoundation`) | None (greenfield). |
| **"First-time user" framing checklist** — before each walk, Kaan sets cognitive frame to "I just downloaded this; I don't know how it works" to surface affordance gaps | The hardest part of a maintainer's own usability test is escaping the curse-of-knowledge. A pre-walk frame-set checklist (acknowledge "I built this; I know where everything is; pretend I don't") shifts what gets flagged. | <0.5 E-day | None (greenfield convention). |
| **Compare-to-mocks pass** — every Tier-1 surface compared side-by-side against `mocks/vibemix-app-ui.html` + `mocks/vibemix-cinematic-storyboard.html` for visual drift | The mocks are the design contract. v3.0 Phase 43 closed against them, but live-running pixel exact alignment vs developer-tool inspection are different signals. | single-day plan | v3.0: Phase 43 mocks-as-contract. |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---|---|---|---|
| **Formal 30-session DJ replay harness with LLM scorer** | Standard ML eval discipline. | Per `project_phase_16_kaan_dj_testing` + v3.0 GATE-08 (P85 override RETIRED), Phase 16 is Kaan's DJ ear, NOT a formal suite. v3.1 broadens to full-product, not just hallucination — even more reason NOT to formalize. | Kaan's MacBook + Nielsen 10 heuristic checklist + GATE-05 ear-test protocol. |
| **Recruit external usability testers (5-7 DJs)** | "Standard usability test sample size." | The Bravoh public launch wave window opens once SHIP-01/02 land; spending 2-3 weeks recruiting + scheduling DJs slips the wave. Post-launch via day-zero ops Discord gives this for free. | Kaan + post-launch Discord triage. External tester onboarding is a v3.2+ consideration. |
| **A/B test multiple onboarding flows** | "Optimize conversion." | No baseline traffic yet (RC not public). A/B testing needs a denominator. | Ship one flow, measure post-launch via day-zero ops dashboard. |
| **Quantified usability metrics (SUS / NASA-TLX / time-on-task)** | "Defensible against design critique." | Adds measurement overhead to Kaan's walk. Kaan's gut signal + Nielsen 10 + heuristic checklist gives 80% of the value with 10% of the overhead. | Heuristic checklist only. |
| **Test on every macOS version** | "Coverage." | tart fresh-VM matrix already covers 12.3 / 14 / 15 in SHIP-04. Beyond that = diminishing returns. Kaan's MacBook is the *operator-experience* test, not the *compat matrix* test. | Kaan's MacBook (current macOS) + tart matrix (3 versions). |
| **Test on a borrowed Windows machine alongside MacBook** | "Cross-platform parity." | v3.1's MacBook end-to-end pass is specifically the MacBook walk. Windows is covered by SHIP-04 tart fresh-VM matrix (Win 10 / 11) automated; live operator walk on Windows is a v3.2 candidate if SHIP-04 surfaces real friction. | tart fresh-VM matrix handles Windows; defer live-Win operator walk to v3.2. |

**Research notes:**
- v3.0 GATE-05 ear-test protocol + JSON Schema + debrief capture surface (Phase 42-03) — ready for re-use.
- v3.0 Phase 43 VIS-01 paired `gsd-ui-checker` + `gsd-ui-auditor` walk on Tier-1 surfaces — re-usable.
- Nielsen 10 heuristics — public, no source needed.
- `project_phase_16_kaan_dj_testing` memory locks the "Kaan's ear, not formal suite" rule.

---

### Category 4 — MASCOT: Full Emotion Coverage With Real GLBs

**Thesis:** v2.1 Phase 31 shipped the 4-layer additive state machine; v3.0 VIS-04 scaffolded the Mixamo retarget pipeline; v3.0 VIS-05 validated the mood→animation pool runtime against placeholder clips. **The clips themselves are still placeholders.** v3.1's job is to land the actual emotion-clip set per layer so the mascot is fully visible across every event class. Per `project_mascot_as_vtuber_personality_surface`: single VTuber-style 3D character ("Neon Rebel"), mood variation on the same rig — NOT multi-character `/hatch`.

The shipped 4-layer architecture has fixed slot names (Base / Emotion / Anticipation / Reaction). v3.1 enumerates the specific emotions that get GLB assets per layer. Anchored to Plutchik's 8-primary-emotion set adapted for DJ-context (joy / anticipation are over-represented; sadness / fear / disgust are under-represented because DJing is performative, not emotional in the negative-valence sense), modulated by the existing v2.1 Hype-man / Teacher / Coach persona pools.

#### Table Stakes — The Emotion Enumeration (must land in v3.1)

The mascot is "fully visible" when these specific clips exist as real GLBs and the state machine resolves to them on the right event class. Numbers prefixed with the layer name.

**Layer 1 — BASE / IDLE** (always playing; mood-coupled hip-bob from BPM + RMS)
- `base_idle_calm` — pre-set, between-track, head bobbing at ~30% intensity (default startup state)
- `base_idle_groove` — in-set, music playing, bobbing at ~70% intensity (most common live state)
- `base_idle_peak` — drop / energy peak, full body movement at 100% intensity (the "lit" state)

**Layer 2 — EMOTION / MOOD** (long-duration; 30s-2min cycles; persona-pool-resolved)
- `emo_hype` — Hype-man persona, high-arousal positive (joy + anticipation Plutchik combo = optimism)
- `emo_neutral_teach` — Teacher persona, calm-attentive (trust)
- `emo_coach` — Coach persona, focused-analytical (anticipation)
- `emo_focused` — high-attention listening pose, used when KAAN_SPOKE fires (mirrors the mic-as-Part-2 grounding contract — mascot LOOKS like it's listening)
- `emo_neutral_silent` — silent-RMS state, low-stim idle (the v3.0 Beat C "AI shuts up when there's nothing to say" visual)

**Layer 3 — ANTICIPATION** (short-duration; fires on event-detect at T+50ms; covers the 400-1200ms Gemini TTFT window) — These are the existing 5 `prep_*.glb` slots from v3.0 VIS-04, awaiting Kaan-aesthetic Pioneer-CDJ-headbob selection from Mixamo
- `prep_lean_in_hyped` — DROP / PEAK predicted, body leans forward + head turns toward decks
- `prep_lean_in_neutral` — PHASE / LAYER_ARRIVAL predicted, mild lean + attentive pose
- `prep_head_turn` — TRACK_CHANGE predicted, head-turn-toward-deck-of-incoming-track (cross-references audible-deck detection)
- `prep_listen_focus` — KAAN_SPOKE predicted (mic onset), turns head toward Kaan + cups ear stylized
- `prep_breath` — pre-MIX_MOVE breathing pose, used when controller-significance crosses threshold but the move hasn't completed

**Layer 4 — REACTION** (short-duration; fires at TTS-start; modulated by inline emote tags from Gemini per v2.1 emote-tag vocab if shipped)
- `react_nod_yes` — affirming feedback, "you nailed that" or "yeah that's the move"
- `react_surprise` — DROP landed, eyebrows-up open-mouth pose
- `react_laugh` — Hype-man mode, joy-amplified
- `react_point_deck_a` — gesture at deck A (cross-references audible-deck = A)
- `react_point_deck_b` — gesture at deck B
- `react_facepalm` — Coach mode, mistake-acknowledged (gentle, not mocking — Coach persona is supportive)
- `react_shrug` — Coach mode, "I don't know, your call"
- `react_eyes_closed_feel` — energy-peak feel-the-music pose, used when AI is silent but the music is sub-bass peaking
- `react_chill` — low-energy moment, sip-from-cup type pose
- `react_silent` — explicit "no reaction" gesture (subtle stillness), used to underscore the anti-slop principle that the mascot can BE silent

**Total v3.1 emotion-clip target:** 3 Base + 5 Emotion + 5 Anticipation + 10 Reaction = **23 GLB clips**.

| Feature | Why Expected | Complexity | Depends on |
|---|---|---|---|
| **23-clip mascot emotion set with real GLBs (not placeholders)** | The mascot is "fully visible" criterion. Without these, the 4-layer state machine has nothing to resolve to. | epic (>5 E-days; gated on Kaan-aesthetic selection per `project_mascot_as_vtuber_personality_surface` + Adobe-account Mixamo download per KAAN-ACTION-LEGAL §VIS-04) | v2.1: Phase 31 4-layer state machine + AnimationUtils.makeClipAdditive. v3.0: VIS-04 retarget pipeline + bundle-size gate ≤25MB. |
| **MANIFEST update wiring every clip to the right event class** — `react_nod_yes` → `KICK_SWAP` praise reaction; `react_point_deck_a` → audible-deck=A `MIX_MOVE`; `prep_head_turn` → predicted `TRACK_CHANGE`; etc. | The actual emotion-to-event mapping. Phase 31 supports it architecturally; v3.1 fills the mapping table. | multi-day phase | v2.1: Phase 31 MANIFEST schema. v3.0: VIS-05 mood→animation pool. |
| **Bundle size ≤25MB enforced via `check_bundle_size.sh`** | v3.0 VIS-04 already shipped the two-tier gate (per-clip 400KB-1.2MB / total ≤25MB). v3.1 just confirms 23 real clips fit the envelope. | <0.5 E-day | v3.0: VIS-04 bundle-size gate. |
| **Mascot visible on every supported window/screen-share path** — mascot overlay window survives djay Pro full-screen, second-monitor extend, OBS browser-source `ws://127.0.0.1:8765` path, mascot.html standalone | The "fully visible" sub-criterion covers paths-of-display not just emotional states. v2.1 mascot overlay window already shipped; v3.1 confirms all paths still work with the full clip set loaded. | single-day plan (verification only) | v2.1: mascot overlay window. v2.0: `ws://127.0.0.1:8765` bus. |
| **30s smoke test per persona** — Hype-man / Teacher / Coach 30s walk with the full clip set; bone-level "idle-zero" contract test passes | v3.0 VIS-05 ran this against placeholder clips. v3.1 re-runs with real clips. | single-day plan | v3.0: VIS-05 mood→animation pool runtime validation. |

#### Differentiators

| Feature | Value Proposition | Complexity | Depends on |
|---|---|---|---|
| **Inline emote-tag vocabulary integration** (per v2.1 v2 deferred feature) — Gemini emits `[nod_yes]` / `[shrug]` / `[point_deck_a]` etc. in TTS text channel, parsed before TTS speak, mapped to reaction-layer clips | v2.1 deferred the emote-tag vocab; v3.1 with 10 reaction clips now has the inventory for it. BUT it's gated on the v2.x Gemini text-channel-timing spike (D-bucket A3 risk). If the spike doesn't land in v3.1, defer to v3.2. | multi-day phase (2 E-days incl. spike + parser + tag→clip dispatch) | v2.1 v2 emote-tag vocab; Gemini text-channel timing spike. |
| **Mascot per-persona timing tuning** — Hype-man reacts faster (T+30ms), Teacher delays (T+200ms for "thinking face" affordance), Coach is paced (T+150ms) | Polish that telegraphs persona-specific personality. Cheap to implement once clip set lands. | single-day plan | v2.1: Phase 31 4-layer state machine. |
| **Mascot "fully visible" in the README hero asset** — render a still of the mascot from the v3.1 clip set as the README banner alongside the verbatim-locked "the only AI co-host that actually listens to your set" hero text | Brand surface tied to the hero copy. The mascot becomes recognizable. | single-day plan (post-clip-set-land) | v3.0: LAUNCH-01 hero text. |
| **Mascot-only OBS-browser-source easter-egg path documented** — README 2-line callout that `mascot.html` works as a standalone OBS scene element | Already supported by v2.0 `ws://127.0.0.1:8765` bus + v2.1 mascot.html keeping the bus contract. Just documentation. | <0.5 E-day | v2.0: ws bus. v2.1: mascot.html. |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---|---|---|---|
| **`/hatch` user-generated mascots in v3.1** | "Engagement / retention play." | Explicitly v3.x stretch per memory `project_mascot_as_vtuber_personality_surface` + v3.0 Out-of-Scope. Adds asset-pipeline + safety/moderation + Imagen-or-Hunyuan3D dep. | Single mascot + mood variation on same rig (the v3.1 23-clip set). |
| **Re-rolling Neon Rebel mascot** | "Mascot doesn't feel right yet." | v3.0 Out-of-Scope lists this explicitly. Re-rolling is a v3.x refresh if Hunyuan3D + AccuRIG 2 + Kaan's gut decide. Re-rolling mid-v3.1 = restart the entire 4-layer animation work. | Ship as-is; v3.x refresh is a future consideration. |
| **More than 23 clips in v3.1** | "Richer emotion vocabulary." | 23 is already calibrated against bundle-size ≤25MB. Going to 30+ requires re-tier of per-clip target or longer download. | Cap at 23 for v3.1; v3.2 expansion candidates are micro-expressions (eye darts, eyebrow-only reactions) that fit in smaller per-clip budgets. |
| **Procedural lip-sync via AudioAnalyser jaw-bone rotation** | "Cheap lip-sync." | Per v2.0 Category 3 anti-feature: reads as "puppet flapping jaw" — generic, not stylised. Defer to v2.x polish layer per existing decision. | Amplitude-banded talk variants (3 clips); already part of v2.1 design. |
| **ARKit blendshape lip-sync** | "Realistic mouth motion." | Mixamo strip blendshapes constraint per v2.1 anti-feature; re-rigging is 2-3 weeks + uncanny-valley risk. | Body-language-first stylised rig (current direction). |
| **2D Live2D version for "lighter weight"** | "Smaller bundle / wider compat." | Locks demographic + abandons the stylised-3D approach + adds a parallel render pipeline. | Stay on Three.js 3D rig; ≤25MB bundle is fine. |
| **Mascot speaks instead of (or in addition to) the AI voice** | "More mascot presence." | The AI voice IS the mascot's voice. Adding a second voice channel breaks the audio contract + privacy guarantees (only one voice in the room). | Mascot is silent visual; voice stays Gemini TTS. |

**Research notes:**
- v2.1 Phase 31 4-layer additive state machine (Base + Emotion + Anticipation + Reaction) — shipped.
- v3.0 VIS-04 Mixamo retarget pipeline scaffolded; KAAN-ACTION-LEGAL §VIS-04 awaiting Kaan Adobe-account Mixamo download + aesthetic selection.
- v3.0 VIS-05 mood→animation pool runtime validation against placeholder clips — passed; will re-pass with real clips.
- Plutchik 8-primary emotions (joy / trust / fear / surprise / sadness / disgust / anger / anticipation) anchored from [Plutchik's Wheel reference](https://www.6seconds.org/2025/02/06/plutchik-wheel-emotions/) — used selectively (joy / trust / surprise / anticipation are DJ-appropriate; sadness / fear / disgust / anger are minimized or omitted because DJing is performative not negative-valence).
- VTuber expression patterns from [VTubeStudio Expressions wiki](https://github.com/DenchiSoft/VTubeStudio/wiki/Expressions-(a.k.a.-Stickers-or-Emotes)) and [11 VTuber Expressions](https://vtuberart.com/11-amazing-vtuber-expressions-a-must-have-for-your-model/) — body-language equivalents adopted.
- `project_mascot_as_vtuber_personality_surface` memory: single VTuber-style 3D character ("Neon Rebel"), mood variation on the same rig. `/hatch` user-gen explicitly deferred.

---

### Category 5 — OPPORTUNITY-SCAN: New Dep/Integration Opportunities

**Thesis:** This is a research-pass output, not an engineering category. v3.1's deliverable is a green/yellow/red rating across confirmed v3.x candidates + a small set of new candidates surfaced by the install-readiness review. Only GREEN-rated integrations actually land in v3.1; YELLOW + RED defer to v3.2 or backlog with explicit reasons.

The confirmed candidates from `project_v2_open_candidates` + PROJECT.md `Active` section already form the universe. v3.1's scan rates them on the `project_one_click_install_hard_req` install-impact axis (does adding this break or threaten one-click?) and on adoption-impact (does this widen real-world compatibility meaningfully?).

#### Table Stakes — What MUST be in the scan output

| Item | Why Expected | Complexity | Depends on |
|---|---|---|---|
| **Mixxx OSC adapter rating** — UDP `:7777` subscribe, maps to existing `MusicState` schema, GPL-2 IPC-only (no GPL-2 linkage = no license contamination), gated on Mixxx PR #14388 status | Mixxx is the only DJ app with a real-time deck-state surface, AND the free-software DJ community is the right cultural audience for OSS vibemix. Rating likely GREEN if PR merged or YELLOW if still feature-flagged. | single-day plan (rating only) | None (research output). |
| **10→30+ controller library via Mixxx map transpile rating** — offline build-time XML+JS → vibemix semantic event JSON; separate `vibemix-maps` GPL-2 repo; core consumes as data (no license contamination) | Closes the "10 controllers" promise; unlocks ~80% of OSS DJ TAM. Rating likely GREEN-with-caveat — transpiler is a one-time build job, end-user impact is zero. | single-day plan | None (research output). |
| **pyrekordbox integration rating** — beyond the v2.0 XML-import already shipped, what about reading Rekordbox cache for "what's hot in your library this week" priors? | The library-side grounding hasn't been pushed beyond import. Adding read-only Rekordbox cue/loop/grid-marker priors would let Gemini cite "you set a cue at this exact point yesterday." | single-day plan | v2.0: pyrekordbox XML import. |
| **DJ software coverage scan** — for the canonical 10 controllers + 6 DJ apps in LAUNCH-04, what's the actual coverage gap? Which DJ apps don't yet have any vibemix surface? | Surface the gap so we know where to push v3.2 or v3.x. Likely Rekordbox + Serato Studio + Traktor are gaps. | single-day plan | v3.0: LAUNCH-04 controllers + DJ-app grids. |
| **OS edge-case scan** — macOS 12.3 still supported? Win 10 EOL implications? ARM-only Mac install path? | Operational scope check. Apple drops 12.3 support sometime in 2026-2027 per typical EOL; vibemix should know the runway. | single-day plan | v3.0: SHIP-04 fresh-VM matrix. |
| **Hardware coverage scan** — Pioneer DDJ-FLX4 / FLX6 / FLX10 / SX3 / 400 / 1000 / XDJ-RX3 / Numark Party Mix Live / Mixstream Pro+ / Hercules Inpulse 300 + 500. What's missing? Denon Engine DJ controllers? Reloop? | The shipped MIDI library (LAUNCH-04) is canonical 10. Reloop + Denon are notable gaps for European + US prosumer DJs respectively. Rating each as GREEN (Mixxx map exists → transpile path) / YELLOW (proprietary mapping only) / RED (no public mapping). | single-day plan | v3.0: LAUNCH-04 canonical 10. |
| **Final v3.1 dep-add list (GREEN-only)** — explicitly enumerated, with green rating rationale per dep | Anti-creep guardrail. Without an explicit final list, v3.1 implementation could pull in YELLOW deps under "but it's also good for users." | <0.5 E-day | All above. |

#### Differentiators

| Feature | Value Proposition | Complexity | Depends on |
|---|---|---|---|
| **OBS browser-source integration callout** (mascot path) — README + docs/integrations.md two-paragraph "use mascot.html as an OBS browser source for streaming overlay" | Free differentiator. The infrastructure exists (v2.0 `ws://127.0.0.1:8765` bus + v2.1 mascot.html preservation). Zero engineering, pure docs. | <0.5 E-day | v2.0: ws bus. v2.1: mascot.html. |
| **`obs-websocket-py` uplink rating** — backlog item in PROJECT.md; would let vibemix events trigger OBS scene switches / lower-third subtitles | Rating only in v3.1; if GREEN it lands in v3.2. Streamer-DJ audience (the IG/Twitch crossover demographic) is a real differentiator wedge. | single-day plan (rating only) | None (research output). |
| **Beat This! Rust sidecar rating** — backlog item in PROJECT.md; non-Gemini beat-grid, closes "AI reacts off-beat" hallucination class; gated on install-size budget | If install-size budget allows (Rust sidecar likely 10-20MB), the off-beat hallucination class is the next-after-mic-as-Part-2 grounding lift. | single-day plan (rating only) | None (research output). |
| **Curriculum-mode lesson packs rating** — per user level (Beginner / Intermediate / Pro); coach drill packs | Already a v3.x candidate. The scan confirms it's coherent with the v3.1 install-readiness theme or defers explicitly. Likely defers (not install-related). | single-day plan | None (research output). |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---|---|---|---|
| **Add ProDJ Link in v3.1** | "Pro/touring DJ coverage." | Already RED per v3.0 Out-of-Scope: 80-200MB install bloat + Pioneer CDJ hardware requirement + JVM bridge. The opportunity-scan output should re-affirm RED. | Skip entirely. v3.2+ only if a CDJ-Pro SKU emerges with real demand. |
| **Add stem separation (Demucs / Spleeter)** | "Per-stem grounding." | Already RED per v3.0 Out-of-Scope: install bloat + compute-heavy + explicit anti-scope-creep decision. The opportunity-scan output should re-affirm RED. | Skip entirely. |
| **Add CLAP / MERT / OpenL3** | "Better music embedding." | Already RED per `feedback_no_clap_use_gemini_embedding`. The opportunity-scan output should re-affirm RED. | Skip entirely; Gemini Embedding 2 covers it. |
| **Add a second LLM provider as fallback** | "Multi-provider resilience." | Already RED per `feedback_no_scope_creep_clean_utility` + Bravoh-is-Gemini-only constraint. Adding OpenAI/Anthropic SDK doubles maintenance surface + breaks the cost model. | Stay Gemini-only; the OpenRouter TTS fallback chain already in v4 POC is the only non-Gemini path and it's TTS-only. |
| **Add DAW integration (Logic / Ableton / FL)** | "Next conquest beyond DJ software." | Already RED per v3.0 Out-of-Scope. v3.2+ deliberate decision, not v3.1 scope-creep. | Skip entirely; defer to milestone-after-v3.1 if at all. |
| **Add mobile companion app** | "Multi-surface UX." | Desktop-only constraint in PROJECT.md. | Skip entirely. |
| **Add real-time stream-to-Twitch hook** | "Streamer-DJ wedge." | Already RED per v3.0 Out-of-Scope. The OBS browser-source path covers the streamer use-case without engineering cost. | OBS browser-source path (differentiator above). |

**Research notes:**
- `project_v2_open_candidates` memory: confirmed Mixxx OSC + map transpile + pyrekordbox + Gemini Embedding 2 + post-session debrief; deferred ProDJ Link + stems + CLAP; backlog OBS / Sonic Pi / ai-remixmate / `/hatch`.
- PROJECT.md `Active` section: v3.x candidate scope already enumerated.
- v3.0 LAUNCH-03 + LAUNCH-04: canonical 10 controllers + 6 DJ-software grid established baseline.
- Confidence on the actual GREEN/YELLOW/RED ratings is MEDIUM until the small parallel scan runs — this category outputs the *framework* + *target list*, not the final ratings. The ratings themselves are a single-day plan in v3.1 itself.

---

## Cross-Category Dependency Graph

```
Category 1: INSTALL
    Signed artifacts (SHIP-01/02 + DIST-19)
        └──gates──> Category 1 fresh-VM matrix run (SHIP-04/05)
        └──gates──> Category 3 MacBook end-to-end pass (need a real installable artifact to test)
    BlackHole auto-prompt + Homebrew fallback
        └──extends──> v2.1 Phase 33 install wizard
    VB-CABLE auto-prompt + driver-prompt forewarning
        └──extends──> v2.1 Phase 33 install wizard
    First-launch wizard end-to-end + ≤60s gate
        └──requires──> All install prereqs landing (signed binaries + virtual audio path + TCC + MIDI fallback)
        └──provides──> Category 3 functional flow walk starting state
    Onboarding-stopwatch ≤60s gate
        └──provides──> README "<60s install" claim verification

Category 2: DEPS
    AUDIT.md authoring
        └──consumes──> v2.1 Phase 34 audit machinery (existing CI output)
        └──provides──> Category 1 install-impact rating evidence
    CI badges in README
        └──extends──> v3.0 LAUNCH-01 README
    SBOM-with-release
        └──extends──> v3.0 SHIP-07 release.yml
    Lockfile-diff bot + Dependabot
        └──parallel──> independent CI surfaces

Category 3: TEST
    Functional flow walk
        └──requires──> Category 1 first-launch wizard end-to-end + Category 4 mascot emotion set landed
        └──gates──> v3.1 release-cut
    Visual + aesthetic critique
        └──reuses──> v3.0 Phase 43 paired ui-checker + ui-auditor
    Mascot emotion coverage check
        └──requires──> Category 4 23-clip emotion set landed
    Usability heuristic pass (Nielsen 10)
        └──parallel──> independent Kaan-time pass
    Hallucination gate re-run (check_gate.sh Gate 2b)
        └──reuses──> v3.0 Phase 42 GATE-05/06 protocol + script
    Gap-closure routing
        └──output-of──> All above; feeds back to v3.1 plan-list or v3.2 scope

Category 4: MASCOT
    23-clip emotion set
        └──requires──> Kaan-aesthetic Mixamo selection (KAAN-ACTION-LEGAL §VIS-04 discharge)
        └──requires──> v2.1 Phase 31 4-layer state machine (existing)
        └──requires──> v3.0 VIS-04 retarget pipeline + bundle-size gate (existing)
        └──provides──> Category 3 mascot emotion coverage test surface
    MANIFEST update wiring
        └──requires──> 23-clip set landed
        └──extends──> v2.1 Phase 31 MANIFEST schema
    Inline emote-tag vocab integration (differentiator)
        └──requires──> 23-clip set + Gemini text-channel-timing spike
        └──gates-on──> spike landing in v3.1 vs deferring to v3.2

Category 5: OPPORTUNITY-SCAN
    Mixxx OSC + map transpile + pyrekordbox + Beat This! + curriculum-mode ratings
        └──output-of──> v3.1 research pass; informs v3.2 milestone scope
    OBS browser-source callout
        └──reuses──> v2.0 ws bus + v2.1 mascot.html preservation
    Final GREEN-only v3.1 dep-add list
        └──output-of──> All above; gates what actually lands in v3.1 phases
```

### Cross-Category Conflicts

- **Category 4 mascot clip-set land × Category 3 MacBook test**: Category 3's mascot emotion coverage check requires Category 4's clips landed first. Phase ordering must put Category 4 before Category 3's mascot section (functional flow walk + visual critique can run in parallel with mascot clip-land; only the mascot-specific test gates).
- **Category 1 signed artifacts × Category 3 functional flow walk**: Category 3 needs a real installable to test. Without SHIP-01/02 (external clock), Category 3 can run on a *dev build* but the v3.1 release-cut gate stays open until signed-binary Category 3 walk passes. Recommended: Category 3 dev-build walk happens in v3.1 phases; signed-binary walk happens as part of SHIP-04 discharge cookbook execution (post-external-clock).
- **Category 4 emote-tag vocab integration × Gemini Live spike timing**: The v2.1-deferred emote-tag vocab depends on Gemini text-channel timing behavior (Bucket D A3 risk). v3.1 should NOT block on the spike — ship 23 clips as table stakes; emote-tag integration is a differentiator that lands only if the spike succeeds early.
- **Category 5 dep-add list × `feedback_no_scope_creep_clean_utility`**: The scan output MUST default to RED for anything that violates one-click-install or adds non-Gemini AI providers. Even if a dep looks "good" on adoption-impact, install-impact veto wins.

---

## v3.1 Cut Recommendation

### Launch With (v3.1)

Ruthless minimum that turns engineering-complete v3.0 into shippable v3.1.

- [ ] **INSTALL: Signed `.dmg` + `.msi` discharged via SHIP-01/02 cookbook** — post-external-clock walk
- [ ] **INSTALL: First-launch wizard end-to-end with BlackHole / VB-CABLE auto-prompts** — Homebrew-first + `.pkg` fallback on Mac; `-i -h` + forewarning on Win
- [ ] **INSTALL: Onboarding-stopwatch ≤60s** confirmed on tart matrix (macOS 12.3 / 14 / 15 + Win 10 / 11)
- [ ] **INSTALL: First-session demo button** (differentiator that lifts user confidence; reuses VIS-09 deterministic sequencer)
- [ ] **DEPS: AUDIT.md at repo root** with full pinned-dep table + license + install-impact rating + rationale
- [ ] **DEPS: CI badges in README** (gitleaks / pip-audit / osv-scanner / cargo-audit / SBOM / signed-binary)
- [ ] **DEPS: SBOM-with-release** attached as `gh release` asset
- [ ] **DEPS: Dependabot configured** for security patches auto-PR; minor/major draft only
- [ ] **DEPS: Unused-dep cull** (drop `openai`, `google-cloud-speech`, `google-cloud-texttospeech` if unused after audit)
- [ ] **TEST: Kaan functional flow walk** (install wizard → first session → all 6 prompt-matrix cells → debrief → library search → uninstall)
- [ ] **TEST: Visual + aesthetic critique pass** (paired ui-checker + ui-auditor on running app)
- [ ] **TEST: Mascot emotion coverage check** (per Category 4 23-clip set)
- [ ] **TEST: Nielsen 10 usability heuristic pass**
- [ ] **TEST: Hallucination gate re-run via check_gate.sh Gate 2b** (≥2 sessions ≥2 genres in 14d window per GATE-05)
- [ ] **TEST: Gap-closure routing** for every fail
- [ ] **MASCOT: 23-clip emotion set landed** (3 Base + 5 Emotion + 5 Anticipation + 10 Reaction)
- [ ] **MASCOT: MANIFEST update wiring** every clip to its event class
- [ ] **MASCOT: bundle-size ≤25MB** confirmed
- [ ] **MASCOT: visible on every supported window/screen-share path** (overlay window, OBS browser-source, standalone mascot.html)
- [ ] **OPPORTUNITY-SCAN: Mixxx OSC + map transpile + pyrekordbox + Beat This! + curriculum-mode** ratings
- [ ] **OPPORTUNITY-SCAN: DJ-software + OS + hardware coverage gap rating**
- [ ] **OPPORTUNITY-SCAN: Final GREEN-only v3.1 dep-add list** (with explicit anti-creep RED reaffirmations)
- [ ] **OPPORTUNITY-SCAN: OBS browser-source callout** docs/README

### Add After v3.1 (v3.2 fast-follow candidates)

Features explicitly out of v3.1 but on the immediate runway.

- [ ] **Inline emote-tag vocab integration** — if Gemini text-channel-timing spike lands clean; reaction-layer clips already in v3.1
- [ ] **Mixxx OSC adapter implementation** — if scan rates GREEN
- [ ] **Mixxx map transpile → 30+ controllers** — if scan rates GREEN-with-caveat
- [ ] **Beat This! Rust sidecar** — if install-size budget allows + scan rates GREEN
- [ ] **Live operator-walk on Windows** — if SHIP-04 tart matrix surfaces real friction
- [ ] **pyrekordbox deeper integration** (cue/loop/grid priors) — beyond v2.0 XML import
- [ ] **Curriculum-mode lesson packs**
- [ ] **`obs-websocket-py` uplink** — if streamer-DJ demand emerges

### Future Consideration (v3.3+)

Features that need infrastructure or signal beyond v3.1/v3.2 ship.

- [ ] **`/hatch` user-gen mascot pipeline** — v2.x stretch per memory
- [ ] **`v1.0.0` cut** — gated on T+30 SHIP-V1-DECISION audit
- [ ] **Re-rolling Neon Rebel mascot** — v3.x refresh if Hunyuan3D + AccuRIG 2 + Kaan's gut decide
- [ ] **External usability tester recruit** — 5-7 DJs post-launch via Discord
- [ ] **Multi-language UI** — defer; English-only in v1.x

---

## Feature Prioritization Matrix (v3.1 in-scope only)

| Feature | User Value | Implementation Cost | Priority |
|---|---|---|---|
| INSTALL: Signed artifacts + first-launch wizard end-to-end | HIGH (zero-install conversion otherwise) | LOW (post-external-clock walk only) | P1 |
| INSTALL: BlackHole / VB-CABLE auto-prompt + forewarning | HIGH (avoids "scary UAC" friction) | LOW (~1d sequencer + copy) | P1 |
| INSTALL: ≤60s onboarding-stopwatch gate | HIGH (README claim verification) | LOW (real-VM run + assertion) | P1 |
| INSTALL: First-session demo button | MEDIUM (lowers anxiety, reuses VIS-09) | MEDIUM (~2-3d wiring) | P1 |
| DEPS: AUDIT.md + CI badges + SBOM-with-release | HIGH (trust signal + reviewer surface) | LOW (~2-3d consolidation) | P1 |
| DEPS: Unused-dep cull | MEDIUM (smaller install + cleaner SBOM) | LOW (~0.5d sweep) | P1 |
| DEPS: Lockfile-diff bot + Dependabot | MEDIUM (review velocity) | LOW (~1d config) | P2 |
| TEST: Functional flow walk | HIGH (release-cut gate) | MEDIUM (~3-5d Kaan-time) | P1 |
| TEST: Visual + aesthetic critique | HIGH (catches live-rendering issues) | LOW (~1d re-run) | P1 |
| TEST: Mascot emotion coverage check | HIGH (gates "fully visible" claim) | LOW (~1d if clip-set ready) | P1 |
| TEST: Nielsen 10 heuristic pass | MEDIUM (UX gap detection) | LOW (~0.5d checklist) | P1 |
| TEST: Hallucination gate re-run | HIGH (ship gate per Phase 42) | MEDIUM (≥2 sessions calendar-blocking) | P1 |
| MASCOT: 23-clip emotion set landed | HIGH (the v3.1 hard authored-content lift) | HIGH (>5d epic; Mixamo + Kaan-aesthetic gate) | P1 |
| MASCOT: MANIFEST update + bundle-size gate | HIGH (state machine wiring) | LOW (~1d post-clip-set) | P1 |
| MASCOT: Per-persona timing tuning | LOW (polish) | LOW (~0.5d) | P2 |
| MASCOT: README hero asset render | MEDIUM (brand surface) | LOW (~0.5d post-clip-set) | P2 |
| OPPORTUNITY-SCAN: GREEN/YELLOW/RED ratings on confirmed candidates | HIGH (v3.2 scope-setting) | LOW (~2d research pass) | P1 |
| OPPORTUNITY-SCAN: OBS browser-source callout | LOW (free differentiator via docs) | LOW (<0.5d docs) | P2 |
| OPPORTUNITY-SCAN: Final GREEN-only dep-add list | HIGH (anti-creep guardrail) | LOW (<0.5d output) | P1 |

**Priority key:**
- **P1**: Must have for v3.1 ship — every milestone target feature has at least one P1 representative.
- **P2**: Should have, ship if schedule allows — polish + differentiators.
- **P3**: Defer to v3.2+ — explicitly enumerated in "Add After v3.1" above.

---

## Sources

### Project state (already-shipped baseline)

- [`.planning/PROJECT.md`](../PROJECT.md) — v3.1 milestone definition, 5 target features
- [`.planning/research/v3-shipped/FEATURES.md`](v3-shipped/FEATURES.md) — v2.0 feature research; anti-features inherited
- [`.planning/milestones/v3.0-REQUIREMENTS.md`](../milestones/v3.0-REQUIREMENTS.md) — REQ-ID closure; v3.1 builds on AUDIO/LAT/GATE/VIS/LAUNCH/SHIP-* completion
- `cohost_v4.py` — canonical v4 baseline (POC reference per memory `project_v4_canonical_baseline`)
- Mocks: `mocks/vibemix-app-ui.html`, `mocks/vibemix-cinematic-storyboard.html`, `mocks/vibemix-direction-final.html`

### Memory directives (constraints driving anti-features)

- `project_one_click_install_hard_req` — install path is HARD requirement; every dep choice rated green/yellow/red
- `feedback_no_scope_creep_clean_utility` — OUT: stem separation, CLAP, multi-provider AI, enterprise features
- `project_mascot_as_vtuber_personality_surface` — single VTuber-style 3D character "Neon Rebel"; `/hatch` deferred
- `project_phase_16_kaan_dj_testing` — Kaan's DJ ear, NOT formal harness
- `feedback_no_clap_use_gemini_embedding` — Gemini Embedding 2 only
- `project_v2_open_candidates` — v3.x candidate inventory + confirmed/deferred/backlog ratings
- `project_anti_slop_grounded_gemini_thesis` — central product principle preserved
- `project_visual_direction_cdj_whisper` — CDJ-Whisper UI direction held through v3.1

### External research

- BlackHole Homebrew cask: [`brew install --cask blackhole-2ch`](https://formulae.brew.sh/cask/blackhole-2ch) — 0.6.1 current, MIT-licensed
- BlackHole upstream: [GitHub ExistentialAudio/BlackHole](https://github.com/existentialaudio/blackhole)
- VB-CABLE silent install: [VB-Audio forum t=1909](https://forum.vb-audio.com/viewtopic.php?t=1909), [t=1766](https://forum.vb-audio.com/viewtopic.php?t=1766), [VB-Audio cable product page](https://vb-audio.com/Cable/) — `-i -h` flags work; Windows driver-signature prompt is OS-mandated
- Tauri Windows installer: [Tauri v2 docs Windows Installer](https://v2.tauri.app/distribute/windows-installer/) — WiX MSI + NSIS, WebView2 bootstrap embedded
- Tauri v2 prerequisites: [Tauri v2 prerequisites](https://v2.tauri.app/start/prerequisites/)
- SBOM audit practice: [Mattermost SBOM audit guide](https://mattermost.com/blog/how-to-audit-a-security-bill-of-material-sbom/), [SPDX open-source tools](https://spdx.dev/tools/open-source-tools/)
- Plutchik 8-emotion wheel: [Six Seconds Plutchik's Wheel](https://www.6seconds.org/2025/02/06/plutchik-wheel-emotions/), [Positive Psychology Emotion Wheel](https://positivepsychology.com/emotion-wheel/)
- VTuber expression conventions: [VTubeStudio Expressions wiki](https://github.com/DenchiSoft/VTubeStudio/wiki/Expressions-(a.k.a.-Stickers-or-Emotes)), [11 VTuber Expressions](https://vtuberart.com/11-amazing-vtuber-expressions-a-must-have-for-your-model/)

---

*Feature research for: vibemix v3.1 Distribution-Ready Pass milestone*
*Researched: 2026-05-17*
*Confidence: HIGH on category structure + dependency graph + mascot emotion enumeration; MEDIUM on Windows install-flow framing (driver-signature prompt is OS-mandated) and on opportunity-scan rating outcomes (final ratings produced by the scan itself in v3.1, not pre-determined here).*
