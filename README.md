<p align="center">
  <img src="docs/assets/hero.png" alt="vibemix — AI co-host for your DJ set" width="100%" />
</p>

<h1 align="center">vibemix</h1>

<p align="center"><em>the only AI co-host that actually listens to your set</em></p>

<!-- vibemix:hero-start sha256=PLACEHOLDER path=docs/assets/demo.mp4 -->
<!-- Phase 35 ASSETS-07 + Phase 39 SHIP-02: the 30s demo film lands at
     docs/assets/demo.mp4 via Kaan-action (KAAN-ACTION-LEGAL.md
     ASSETS-DEMO-CUT). The <video> tag below points at it; until the
     asset ships, the <img> fallback GIF + the sha256=PLACEHOLDER
     sentinel keep scripts/check_readme_hero_hash.py green. When the
     real asset lands, swap the sentinel for the actual SHA256. -->
<p align="center">
  <video src="docs/assets/demo.mp4" controls muted playsinline width="720" poster="docs/assets/demo-placeholder.gif">
    <img src="docs/assets/demo-placeholder.gif" alt="vibemix demo (placeholder — real demo coming)" width="720" />
  </video>
</p>
<!-- vibemix:hero-end -->

## No AI slop

vibemix is a real DJ friend in your ear. It reacts to the actual audio coming out of your master, what's on your DJ software's screen right now, and the controller move you just made — not a generic "AI assistant" voice riffing on the word "drop". If a hype-man can't tell you that the kick came in two bars early, you don't want it talking over your set.

Built by DJs. The reactions are tuned against real sessions on rekordbox, Serato, Traktor, and djay Pro — not against a benchmark. Cuts that land late, hallucinated track names, and small-talk filler all fail the grading bar before any release ships.

Your audio doesn't leave your machine without you knowing. vibemix is open source under Apache 2.0, runs on Mac + Windows, and the only network calls go to Bravoh's Gemini proxy at `api.altidus.world` — analyzed in flight, never stored. Recordings stay local under `recordings/<session>/` with a 7-day default retention you can change in Settings. Read the FAQ for the long version.

<p align="center">
  <img alt="release" src="https://img.shields.io/github/v/release/bravoh/vibemix?style=flat-square&color=ff8a3d" />
  <img alt="build" src="https://img.shields.io/github/actions/workflow/status/bravoh/vibemix/release.yml?branch=main&style=flat-square" />
  <img alt="license" src="https://img.shields.io/badge/license-Apache%202.0-blue?style=flat-square" />
  <img alt="platforms" src="https://img.shields.io/badge/platforms-macOS%20%7C%20Windows-lightgrey?style=flat-square" />
  <img alt="stars" src="https://img.shields.io/github/stars/bravoh/vibemix?style=flat-square" />
</p>

<p align="center">
  <a href="https://github.com/bravoh/vibemix/actions/workflows/dep-audit.yml"><img alt="uv lock status" src="https://img.shields.io/github/actions/workflow/status/bravoh/vibemix/dep-audit.yml?label=uv%20lock&branch=main&style=flat-square" /></a>
  <a href="https://github.com/bravoh/vibemix/actions/workflows/dep-audit.yml"><img alt="cargo-deny" src="https://img.shields.io/github/actions/workflow/status/bravoh/vibemix/dep-audit.yml?label=cargo-deny&branch=main&event=push&style=flat-square" /></a>
  <a href="https://github.com/bravoh/vibemix/actions/workflows/dep-audit.yml"><img alt="npm-audit" src="https://img.shields.io/github/actions/workflow/status/bravoh/vibemix/dep-audit.yml?label=npm-audit&branch=main&event=push&style=flat-square" /></a>
  <a href="https://github.com/bravoh/vibemix/actions/workflows/sbom.yml"><img alt="CycloneDX SBOM" src="https://img.shields.io/github/actions/workflow/status/bravoh/vibemix/sbom.yml?label=CycloneDX%20SBOM&branch=main&style=flat-square" /></a>
</p>

---

**A real DJ friend in your ear — no AI slop.** vibemix listens to your master output, watches your DJ software's screen, ingests your controller, and talks back into your headphones in a way that's grounded in what you actually just did. Not generic "AI assistant" commentary. Not hallucinated track names. Not late reactions to events that already passed. Built by [Bravoh](https://altidus.world) and released open-source as the warm-up for our main launch.

> **Audio privacy in one line:** your audio is streamed to Bravoh's Gemini proxy for analysis. Recordings stay on your machine. See [FAQ](#faq) for the long version.

> **Found a vulnerability?** Please email **security@bravoh.com** (PGP key in repo root). Full disclosure policy in [SECURITY.md](SECURITY.md). Do not open a public issue.

---

## Works alongside whatever DJ app you already use

vibemix doesn't care which DJ app you run — it listens to the master output, watches the screen, and reads your controller. Confirmed working with:

<table>
  <tr>
    <td align="center"><img src="docs/assets/dj-software/rekordbox.svg" alt="rekordbox logo" width="160" /><br/><sub>rekordbox</sub></td>
    <td align="center"><img src="docs/assets/dj-software/serato.svg" alt="Serato logo" width="160" /><br/><sub>Serato</sub></td>
    <td align="center"><img src="docs/assets/dj-software/traktor.svg" alt="Traktor logo" width="160" /><br/><sub>Traktor</sub></td>
  </tr>
  <tr>
    <td align="center"><img src="docs/assets/dj-software/djay-pro.svg" alt="djay Pro logo" width="160" /><br/><sub>djay Pro</sub></td>
    <td align="center"><img src="docs/assets/dj-software/virtualdj.svg" alt="VirtualDJ logo" width="160" /><br/><sub>VirtualDJ</sub></td>
    <td align="center"><img src="docs/assets/dj-software/mixxx.svg" alt="Mixxx logo" width="160" /><br/><sub>Mixxx</sub></td>
  </tr>
</table>

Don't see your app? vibemix listens to the audio coming out of your machine — anything routed through BlackHole (Mac) or WASAPI loopback (Windows) is fair game. The grounding stack (audio + screen + MIDI) is app-agnostic.

<!-- Logos are placeholder wordmarks per KAAN-ACTION-LEGAL.md §LAUNCH-03 — real trademark-compliant logos land via Kaan-discharge before public launch. -->

---

## Install

| OS | Download |
|----|----------|
| macOS (Apple Silicon) | [vibemix.dmg](https://github.com/bravoh/vibemix/releases/latest) |
| Windows 11 | [vibemix-installer.msi](https://github.com/bravoh/vibemix/releases/latest) |

<!-- TBD(launch): Install URLs go live with the first signed release (Phase 21 deliverable). Verify the `bravoh/vibemix` org/repo slug matches the final GitHub home before public launch. -->
<!-- TODO: drop install GIFs (clone-to-running in <60s) into docs/assets/install/ -->

Builds are signed (Apple Developer ID on macOS, SignPath OSS cert on Windows) and notarized. Auto-update is on by default; opt out in Settings.

---

## Feature matrix

vibemix has 3 skill levels × 2 modes. Pick one before each set.

|              | **Hype-man** (party-mode energy)                                                                                       | **Coach** (post-cue critique)                                                                                          |
|--------------|------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------|
| **Beginner**     | > "Nice. You held the EQ steady through that intro." <br/> > "Yo, the crowd just got loud."                                  | > "That cut was a beat off. Try waiting for the downbeat next time." <br/> > "Filter was riding low for like a minute — bring it back up."   |
| **Intermediate** | > "Clean swap. Bassline locked." <br/> > "You let that build run an extra 8 bars. Risky."                                       | > "You're filtering on every transition. Mix it up — let one through dry."                                            |
| **Pro**          | > "That was a stack and a hot-cue trigger inside one bar. Disgusting." <br/> > "BPM jump was tight. Sub stayed in the pocket." | > "You're hitting the same loop tool four tracks in a row. Crowd's reading it." |

Each cell speaks a different vocabulary on purpose. Beginner is encouragement-heavy; Pro assumes you know the language. Coach mode is always past-tense — vibemix won't talk while you're working.

### What's shipped in v2.1

<!-- AUTO-GEN: feature-matrix START — auto-populated by scripts/launch/sync_feature_matrix.py -->

| Phase | Surface | What shipped |
|---|---|---|
| 27 | Eval Harness + v2.0 Carry-Forward Close-Out (9/9 plans, 140 tests) | completed 2026-05-15 |
| 28 | Library Intelligence v1 (9/9 plans, 258 tests) | completed 2026-05-15 |
| 29 | Post-Session Debrief MVP UI (9/9 plans) | completed 2026-05-15 |
| 30 | 2 Hard Tek Detectors (4/4 plans, 45 tests) | completed 2026-05-15 |
| 31 | 4-Layer Mascot Full Additive State Machine (8/8 plans, 17 mascot tests, GLB 21.67/25 MB) | completed 2026-05-15 |
| 32 | Long-Term DJ Profile ~2KB JSON (6/6 plans, 67 tests, P51/P53/P60 enforced) | completed 2026-05-15 |
| 33 | One-Click Install Hardening (9/9 plans, 50 tests; INSTALL-VM-RUN = KAAN-ACTION-LEGAL) | completed 2026-05-15 |
| 34 | Open-Source Security Pass (10/10 plans, 63 tests) | completed 2026-05-15 |
| 35 | Real GLBs + 30s Viral Demo Film (6/6 plans, 35 tests; real assets = KAAN-ACTION-LEGAL) | completed 2026-05-15 |
| 36 | Day-Zero Operations Automation (6/6 plans, 36 tests; 6 real-execution items = KAAN-ACTION-LEGAL) | completed 2026-05-15 |
| 37 | Cross-Phase Integration Audit Gate (6/6 plans, 42 tests; 5/5 seams WIRED) | completed 2026-05-15 |
| 38 | Signing Pipeline Real Execution (6/6 plans, 58 tests; DIST-09 + DIST-11 = P46 legal-capacity carveouts) | completed 2026-05-15 |
| 39 | Public RC Cut + Ship (8/8 plans, 91 tests; §SHIP × 6 + §POST-RC-CLEANUP × 3 = KAAN-ACTION-LEGAL) | completed 2026-05-15 |
| 40 | Anti-Slop Audio Port (6/6 plans) | completed 2026-05-16 (AUDIO-01..04 GREEN; AUDIO-05/06/07 = KAAN-ACTION-LEGAL) |
| 41 | Gemini SKU Upgrade + Latency Stack v2 (7/7 plans) | completed 2026-05-16 (LAT-01..08 GREEN; LAT-09 spike = KAAN-ACTION-PROXY) |
| 42 | Hallucination Gate v3 | Hybrid (6/6 plans) — completed 2026-05-16 (GATE-05..09 GREEN; GATE-01/02/03/04 corpus = KAAN-ACTION-LEGAL) |
| 43 | Visual Ship Lock (9/9 plans) | completed 2026-05-16 (VIS-01..09 GREEN; VIS-04 Mixamo retargets = KAAN-ACTION-LEGAL) |
| 44 | Launch Positioning + Pre-stage (7/7 plans) | completed 2026-05-17 (LAUNCH-01..10 GREEN; LAUNCH-03/04/06/07/08 = KAAN-ACTION-LEGAL) |
| 45 | External Discharge + Public RC Publish (6/6 plans) | completed 2026-05-17 (SHIP-08/11/13 engineering GREEN; SHIP-01..13 cookbook in KAAN-ACTION-LEGAL) |
| 46 | Dependency Audit + Lockfile + AUDIT.md (6/6 plans, 45 tests + 1 xfail; DEPS-01..06 + DEPS-09/10 GREEN; DEPS-07 pinact + DEPS-08 cull-blocked documented in AUDIT.md § Decisions) | completed 2026-05-18 |
| 47 | Mascot Real GLB Land + Full Emotion Coverage (8/8 plans, 63 python + 177 ts tests; MASCOT-01..08 GREEN; §VIS-04 + §VIS-05 Mixamo discharge = KAAN-ACTION) | completed 2026-05-18 |
| 48 | New-Dep + Integration Opportunity Scan (6/6 plans, 19 tests; OPP-01..06 GREEN; 24 candidates rated 1G/8Y/9R-constraint/6R-risk; OBS adopted docs-only) | completed 2026-05-18 |
| 49 | Win + Mac One-Click Installer Chain (6/6 plans, 68 passing + 1 skip; INSTALL-01..10 GREEN; §INSTALL-COMPANION-SIGN + §INSTALL-VM-RUN + §SHIP-CONTACT-VBAUDIO = KAAN-ACTION; median 41,000 ms / 60,000 ms budget) | completed 2026-05-18 |
| 50 | End-to-End MacBook + OS-Matrix Pass (6/6 plans, 16 passing + 5 CI-tolerant skips; E2E-01..10 GREEN; §E2E-50A-WALK + §INSTALL-VM-RUN downstream = KAAN-ACTION; Gate 6b wired into cut_release.sh) | completed 2026-05-18 |

<!-- AUTO-GEN: feature-matrix END -->

---

## Supported controllers

Out-of-the-box mappings for 10 controllers, sourced verbatim from [`src/vibemix/midi/controllers/`](src/vibemix/midi/controllers/). Anything else uses the generic positional fallback — see [docs/midi-mapping.md](docs/midi-mapping.md) to calibrate or contribute a mapping.

<table>
  <tr>
    <td align="center"><img src="docs/assets/controllers/ddj-200.svg" alt="Pioneer DDJ-200" width="180" /><br/><sub><b>Pioneer DDJ-200</b></sub></td>
    <td align="center"><img src="docs/assets/controllers/ddj-400.svg" alt="Pioneer DDJ-400" width="180" /><br/><sub><b>Pioneer DDJ-400</b></sub></td>
    <td align="center"><img src="docs/assets/controllers/ddj-flx4.svg" alt="Pioneer DDJ-FLX4" width="180" /><br/><sub><b>Pioneer DDJ-FLX4</b></sub></td>
    <td align="center"><img src="docs/assets/controllers/ddj-rev1.svg" alt="Pioneer DDJ-REV1" width="180" /><br/><sub><b>Pioneer DDJ-REV1</b></sub></td>
    <td align="center"><img src="docs/assets/controllers/kontrol-s2.svg" alt="Native Instruments Traktor Kontrol S2" width="180" /><br/><sub><b>NI Traktor Kontrol S2</b></sub></td>
  </tr>
  <tr>
    <td align="center"><img src="docs/assets/controllers/kontrol-s4.svg" alt="Native Instruments Traktor Kontrol S4" width="180" /><br/><sub><b>NI Traktor Kontrol S4</b></sub></td>
    <td align="center"><img src="docs/assets/controllers/mc-6000.svg" alt="Denon DJ MC6000" width="180" /><br/><sub><b>Denon DJ MC6000</b></sub></td>
    <td align="center"><img src="docs/assets/controllers/mc-7000.svg" alt="Denon DJ MC7000" width="180" /><br/><sub><b>Denon DJ MC7000</b></sub></td>
    <td align="center"><img src="docs/assets/controllers/mixtrack-platinum-fx.svg" alt="Numark Mixtrack Platinum FX" width="180" /><br/><sub><b>Numark Mixtrack Platinum FX</b></sub></td>
    <td align="center"><img src="docs/assets/controllers/mixtrack-pro-fx.svg" alt="Numark Mixtrack Pro FX" width="180" /><br/><sub><b>Numark Mixtrack Pro FX</b></sub></td>
  </tr>
</table>

Calibrate any other controller — see [docs/midi-mapping.md](docs/midi-mapping.md).

<!-- Controller logos are placeholder wordmarks per KAAN-ACTION-LEGAL.md §LAUNCH-04 — real trademark-compliant logos land via Kaan-discharge before public launch. The canonical 10 controller set is locked against `src/vibemix/midi/controllers/*.json`; any drift between this grid and that JSON profile set fails `scripts/launch/check_readme_grids_a11y.py`. -->


### Don't see your controller?

Two ways to add it:

1. **File a request** — open a [new-controller issue](https://github.com/bravoh/vibemix/issues/new?template=new_controller.yml) and we'll triage. <!-- TBD: confirm org slug `bravoh/vibemix` matches the final repo name before launch -->
2. **Send a PR** — run `python3 scripts/sniff_controller.py` to capture your controller's MIDI shape, then drop a JSON profile under `src/vibemix/midi/profiles/` per [CONTRIBUTING.md](CONTRIBUTING.md#2-new-controller-mapping). CI auto-merges clean profile additions.

---

## Screenshots

<!-- TODO: drop final PNGs into docs/assets/screenshots/ once UI surfaces stabilize. -->

| Surface | Image |
|---------|-------|
| Calibration wizard | <img src="docs/assets/screenshots/wizard.png" width="500" /> |
| Mode picker | <img src="docs/assets/screenshots/mode-picker.png" width="500" /> |
| Voice picker | <img src="docs/assets/screenshots/voice-picker.png" width="500" /> |
| Live session UI | <img src="docs/assets/screenshots/session.png" width="500" /> |
| Recording browser | <img src="docs/assets/screenshots/recordings.png" width="500" /> |

---

## How it works

<p align="center">
  <img src="docs/assets/architecture.svg" alt="vibemix architecture diagram" width="100%" />
</p>

vibemix runs entirely on your machine. The only network calls go to Bravoh's proxy at `api.altidus.world`, which forwards to Google Gemini. Your audio + screen frames + MIDI events are streamed through; nothing is stored on Bravoh's end. The reaction comes back as a Gemini-TTS-streamed voice into your headphones.

---

## Streaming integrations

**OBS Studio (browser-source).** vibemix's mascot canvas can render directly inside an OBS scene as a transparent overlay. Point the OBS Browser source at the local mascot route and the mascot reacts to your live session in real time. Full setup steps live in [docs/integrations/obs-browser-source.md](docs/integrations/obs-browser-source.md).

---

## FAQ

### 1. What is vibemix?

An AI co-host for live DJ sets. It listens to your master output, watches your DJ software's screen, ingests your controller actions over MIDI, and talks back into your headphones — either as a hype-man during the set, or as a coach pointing out where you cut a beat early. Open source. Mac + Windows.

### 2. Is my audio sent to the cloud?

Yes. Audio chunks are streamed to Bravoh's proxy at `api.altidus.world`, which forwards to Google Gemini for analysis. **No raw audio is stored on Bravoh's servers.** Your recordings (in `recordings/<session>/`) stay on your machine. Default retention is 7 days, configurable in Settings.

### 3. Is this free?

Yes for v1. The ~50 €/month Gemini API cost is absorbed by Bravoh as part of the launch wedge. We may revisit this if usage scales past what we projected; if so, we'll announce before changing anything.

### 4. Why no Linux?

Three reasons: djay Pro is Mac/Win only and that's our primary integration target; the loopback audio stack on Linux (PulseAudio / PipeWire) is different enough that the OS-platform layer triples in maintenance; and Bravoh's first OSS release optimizes for narrow scope. We'd consider it for v2 if there's community signal (a PR with the platform port already in shape).

### 5. Why Gemini and not GPT / Claude / Llama?

Bravoh's main product is Gemini-only. vibemix shares the brain. The proxy could route elsewhere in principle, but it isn't designed to — you'd be running a different product.

### 6. Is the AI actually listening to my music?

Yes. It listens to your master output via virtual audio (BlackHole on Mac, WASAPI loopback on Windows), watches your DJ software's window via screen capture, and reads your MIDI controller. The "real friend" feel comes from grounding the reaction in all three sources simultaneously, not from clever prompting alone.

### 7. Can it hallucinate?

Phase 16's hallucination verification gate enforces ≥95% grounded reactions before any release ships. The anti-slop stack — negative dictionary, describe-before-infer, past-tense framing, `<silence/>` short-circuit token, per-session anti-repetition ring — exists to keep the AI from making things up. The reaction-reel grading gate (Phase 17, ≥4.0 average with zero 1-2 ratings) is the human-judged final gate before any binary ships.

### 8. What's open-source and what isn't?

The vibemix client (this repo) is Apache 2.0. The Bravoh proxy and Bravoh's main product are closed. Gemini is Google's. The Apache 2.0 license means you can fork the client and point it at your own Gemini API key if you want to skip the Bravoh proxy entirely.

### 9. Why a Bravoh-managed proxy instead of bring-your-own-key?

UX and ops: most DJs don't want to manage an API key, billing, or rate limits. Centralising those at Bravoh is part of the launch wedge. If you'd rather BYO, see CONTRIBUTING — there's an env-var path to point vibemix at your own Gemini endpoint.

### 10. Will my recordings be uploaded anywhere?

No. Recordings live under `recordings/<session>/` on your machine. Default retention is 7 days; the Settings drawer lets you change it (anything from 1 day to ∞). vibemix never uploads them.

### 11. What about Mixxx? Rekordbox?

Candidates for v2. v1 ships djay-Pro-first because that's what Kaan + Francesco use daily and where we can verify the live experience. Mixxx OSC + rekordbox parsing are tracked in the v2 inventory.

### 12. How do I contribute?

See [CONTRIBUTING.md](CONTRIBUTING.md). Three paths: bug fixes (standard PR with DCO sign-off), new controller mappings (drop a JSON in `src/vibemix/midi/profiles/`), and new prompt templates (manual review by maintainers — anti-slop dictionary applies).

---

## Built by [Bravoh](https://altidus.world)

vibemix is Bravoh's first open-source release — a warm-up for our main product. If you like the energy here, the AI creative team for music artists is over there:

[**altidus.world →**](https://altidus.world/vibemix?utm_source=github&utm_medium=oss&utm_campaign=vibemix_launch)

Apache 2.0 · ([LICENSE](LICENSE)) · ([SECURITY](SECURITY.md)) · ([CONTRIBUTING](CONTRIBUTING.md)) · ([CODE_OF_CONDUCT](CODE_OF_CONDUCT.md))

<!-- TODO(kaan, pre-tag-v0.1.0): replace TBD with the real Bravoh-managed vibemix Discord invite. -->
Discord: **TBD** — invite link goes live before the v0.1.0 tag.
