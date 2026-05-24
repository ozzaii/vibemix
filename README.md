<p align="center">
  <img src="docs/assets/hero.png" alt="vibemix — AI co-host for your DJ set" width="100%" />
</p>

<h1 align="center">vibemix</h1>

<p align="center"><em>the only AI co-host that actually listens to your set</em></p>

<!-- vibemix:hero-start sha256=PLACEHOLDER path=docs/assets/demo.mp4 -->
<!-- Phase 35 ASSETS-07 + Phase 39 SHIP-02 + Phase 70 GH-01: the 30s demo film
     lands at docs/assets/demo.mp4 via Kaan-action (KAAN-ACTION-LEGAL.md
     §ASSETS-DEMO-CUT). The <video> tag below points at it; until the
     asset ships, the source-generated docs/assets/demo-poster.png
     (CDJ-Whisper still, MANIFEST-pinned) carries the visual as the
     <video poster=> + the <img> fallback keeps it non-broken, while the
     sha256=PLACEHOLDER sentinel keeps scripts/check_readme_hero_hash.py
     green. When the real asset lands, swap the sentinel for the actual
     SHA256 (the §ASSETS-DEMO-CUT discharge does this). -->
<p align="center">
  <video src="docs/assets/demo.mp4" controls muted playsinline width="720" poster="docs/assets/demo-poster.png">
    <img src="docs/assets/demo-poster.png" alt="vibemix co-host live over a DJ set — the live session UI (demo film coming soon)" width="720" />
  </video>
</p>
<!-- vibemix:hero-end -->

<!-- OG / social card (GH-03): docs/assets/og-card.png is the 1200×630 source-generated
     social-unfurl image (rendered from docs/assets/sources/og-card.html, pinned by SHA-256
     in docs/assets/MANIFEST.yaml). On a Slack/Discord/Twitter unfurl it carries the brand.
     A raw <meta property="og:image"> does NOT render in GitHub-flavoured markdown, so the
     live <meta property="og:image" content=".../docs/assets/og-card.png"> tag lives in the
     Wave 2 GitHub Pages landing <head>. The repo's GitHub social-preview image (Settings →
     General → Social preview) is a manual repo-settings action → KAAN-ACTION-LEGAL.md
     §V7-LANDING; point it at docs/assets/og-card.png. -->

## No AI slop

vibemix is a real DJ friend in your ear. It reacts to the actual audio coming out of your master, what's on your DJ software's screen right now, and the controller move you just made — not a generic "AI assistant" voice riffing on the word "drop". If a hype-man can't tell you that the kick came in two bars early, you don't want it talking over your set.

Built by DJs. The reactions are tuned against real sessions on rekordbox, Serato, Traktor, and djay Pro — not against a benchmark. Cuts that land late, hallucinated track names, and small-talk filler all fail the grading bar before any release ships.

Your audio doesn't leave your machine without you knowing. vibemix is open source under Apache 2.0, runs on Mac + Windows, and the only network calls go to Bravoh's Gemini proxy at `api.altidus.world` — analyzed in flight, never stored. Recordings stay local under `recordings/<session>/` with a 7-day default retention you can change in Settings. Read the FAQ for the long version.

<p align="center">
  <img alt="release" src="https://img.shields.io/github/v/release/bravoh-ai/vibemix?style=flat-square&color=ff8a3d" />
  <img alt="build" src="https://img.shields.io/github/actions/workflow/status/bravoh-ai/vibemix/release.yml?branch=main&style=flat-square" />
  <img alt="license" src="https://img.shields.io/badge/license-Apache%202.0-blue?style=flat-square" />
  <img alt="platforms" src="https://img.shields.io/badge/platforms-macOS%20%7C%20Windows-lightgrey?style=flat-square" />
  <img alt="stars" src="https://img.shields.io/github/stars/bravoh-ai/vibemix?style=flat-square" />
</p>

<p align="center">
  <a href="https://github.com/bravoh-ai/vibemix/actions/workflows/dep-audit.yml"><img alt="uv lock status" src="https://img.shields.io/github/actions/workflow/status/bravoh-ai/vibemix/dep-audit.yml?label=uv%20lock&branch=main&style=flat-square" /></a>
  <a href="https://github.com/bravoh-ai/vibemix/actions/workflows/dep-audit.yml"><img alt="cargo-deny" src="https://img.shields.io/github/actions/workflow/status/bravoh-ai/vibemix/dep-audit.yml?label=cargo-deny&branch=main&event=push&style=flat-square" /></a>
  <a href="https://github.com/bravoh-ai/vibemix/actions/workflows/dep-audit.yml"><img alt="npm-audit" src="https://img.shields.io/github/actions/workflow/status/bravoh-ai/vibemix/dep-audit.yml?label=npm-audit&branch=main&event=push&style=flat-square" /></a>
  <a href="https://github.com/bravoh-ai/vibemix/actions/workflows/sbom.yml"><img alt="CycloneDX SBOM" src="https://img.shields.io/github/actions/workflow/status/bravoh-ai/vibemix/sbom.yml?label=CycloneDX%20SBOM&branch=main&style=flat-square" /></a>
  <a href="https://github.com/bravoh-ai/vibemix/actions/workflows/full-test-matrix.yml"><img alt="full test matrix" src="https://img.shields.io/github/actions/workflow/status/bravoh-ai/vibemix/full-test-matrix.yml?label=tests&branch=main&style=flat-square" /></a>
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
| macOS (Apple Silicon) | [vibemix.dmg](https://github.com/bravoh-ai/vibemix/releases/latest) |
| Windows 11 | [vibemix-installer.msi](https://github.com/bravoh-ai/vibemix/releases/latest) |

<!-- TBD(launch): Install URLs go live with the first signed release (Phase 21 deliverable). Verify the `bravoh-ai/vibemix` org/repo slug matches the final GitHub home before public launch. -->
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
| 67 | All Tests Pass (5/5 plans) | 2026-05-23 (TEST-01..04; default `pytest -q` 0-red, 21-job `full-test-matrix.yml` CI, static skip/flake gates, 10× flake-hunt baseline) |
| 68 | All Devices Ready (5/5 plans) | 2026-05-23 (DEV-01..05; 10 profile contracts + synthetic-MIDI smokes, catalog reconciled to single `profiles/` source, hot-plug + audio-backend matrices, contributor recipe) |
| 69 | OSS Fully Integrated (5/5 plans) | 2026-05-24 (OSS-01..05; 4 OSS docs + presence test, client-side proxy fallback "Co-host unavailable this session", BYO-key doc, Homebrew+Scoop scaffolds, §SHIP-V4 publish pre-staged) |
| 70 | GitHub Sexified, Generated, Tested (5/5 plans) | 2026-05-24 (GH-01..05; asset reproducibility pipeline + auto-gen og-card, CDJ-Whisper Pages landing, demo poster, one-stop `test_github_presence.py`) |
| 63 | Memory Store (3/3 plans) | 2026-05-22 (STORE-01..04 GREEN; 19/19 tests/memory/) |
| 64 | Session Ingest (3/3 plans) | 2026-05-22 (INGEST-01..03 GREEN; one v1 moment kind = `coach_line`; `moment` cut, `audio_moment` deferred) |
| 65 | Memory Retrieval Seam | ANTI-SLOP RELEASE GATE (4/4 plans) — 2026-05-22 (RECALL-01..04 GREEN; existence-only `recall` source à la P59 `key:`, fabricated `[recall:<id>]` strips whole turn) |
| 66 | Visible Copilot Move (2/2 plans) | 2026-05-22 (COPILOT-01..03 GREEN; transition-shape + vocabulary callbacks; ships behind `VIBEMIX_RECALL_ENABLED=0` until §RECALL-EAR Kaan-ear pass) |
| 59 | Full Deck Awareness + Grounding (5/5 plans) | 2026-05-21 |
| 60 | Harmonic-Feedback Confidence Gate (4/4 plans) | 2026-05-21 (detector default-OFF until the Kaan-ear veto flip) |
| 61 | Actionable-Not-Hype Coach Persona (2/2 plans) | 2026-05-21 |
| 62 | Floating Pill UI (5/5 plans) | 2026-05-22 |
| 51 | Real-Hardware Bring-Up (3/3 plans) | 2026-05-21 |
| 52 | Audio Path + Feature Grounding (4/4 plans) | 2026-05-21 |
| 53 | Controller Live + Graceful Fallback (2/2 plans) | 2026-05-21 |
| 54 | Hype Mode Live (4/4 plans) | 2026-05-20 |
| 55 | Feedback Mode Live + Citation Integrity (3/3 plans) | 2026-05-21 |
| 56 | Performance + Live Mascot (3/3 plans) | 2026-05-21 |
| 57 | Sexify Finish (3/3 plans) | 2026-05-21 |
| 58 | Ship Readiness (4/4 plans) | 2026-05-21 (`cut_release.sh --dry-run v0.1.0-rc1` GREEN; publish hard-guard regression-pinned) |

<!-- AUTO-GEN: feature-matrix END -->

---

## Supported controllers

Out-of-the-box mappings for 10 controllers, sourced verbatim from [`src/vibemix/midi/profiles/`](src/vibemix/midi/profiles/). Anything else uses the generic positional fallback — see [docs/midi-mapping.md](docs/midi-mapping.md) to calibrate or contribute a mapping.

<table>
  <tr>
    <td align="center"><img src="docs/assets/controllers/pioneer-ddj-flx4.svg" alt="Pioneer DDJ-FLX4" width="180" /><br/><sub><b>Pioneer DDJ-FLX4</b></sub></td>
    <td align="center"><img src="docs/assets/controllers/pioneer-ddj-flx6.svg" alt="Pioneer DDJ-FLX6" width="180" /><br/><sub><b>Pioneer DDJ-FLX6</b></sub></td>
    <td align="center"><img src="docs/assets/controllers/pioneer-ddj-flx10.svg" alt="Pioneer DDJ-FLX10" width="180" /><br/><sub><b>Pioneer DDJ-FLX10</b></sub></td>
    <td align="center"><img src="docs/assets/controllers/pioneer-ddj-400.svg" alt="Pioneer DDJ-400" width="180" /><br/><sub><b>Pioneer DDJ-400</b></sub></td>
    <td align="center"><img src="docs/assets/controllers/pioneer-ddj-1000.svg" alt="Pioneer DDJ-1000" width="180" /><br/><sub><b>Pioneer DDJ-1000</b></sub></td>
  </tr>
  <tr>
    <td align="center"><img src="docs/assets/controllers/pioneer-ddj-sx3.svg" alt="Pioneer DDJ-SX3" width="180" /><br/><sub><b>Pioneer DDJ-SX3</b></sub></td>
    <td align="center"><img src="docs/assets/controllers/pioneer-xdj-rx3.svg" alt="Pioneer XDJ-RX3" width="180" /><br/><sub><b>Pioneer XDJ-RX3</b></sub></td>
    <td align="center"><img src="docs/assets/controllers/numark-party-mix-live.svg" alt="Numark Party Mix Live" width="180" /><br/><sub><b>Numark Party Mix Live</b></sub></td>
    <td align="center"><img src="docs/assets/controllers/hercules-inpulse-300.svg" alt="Hercules DJControl Inpulse 300" width="180" /><br/><sub><b>Hercules Inpulse 300</b></sub></td>
    <td align="center"><img src="docs/assets/controllers/hercules-inpulse-500.svg" alt="Hercules DJControl Inpulse 500" width="180" /><br/><sub><b>Hercules Inpulse 500</b></sub></td>
  </tr>
</table>

Calibrate any other controller — see [docs/midi-mapping.md](docs/midi-mapping.md).

<!-- Controller logos are placeholder wordmarks per KAAN-ACTION-LEGAL.md §LAUNCH-04 — real trademark-compliant logos land via Kaan-discharge before public launch. The canonical 10 controller set is locked against `src/vibemix/midi/profiles/*.json`; any drift between this grid and that JSON profile set fails `scripts/launch/check_readme_grids_a11y.py`. See `docs/contributing/midi-catalog.md` for the Phase 68 catalog-reconciliation note.

Canonical profile IDs (one per cell, mirrors `src/vibemix/midi/profiles/*.json`):
  pioneer_ddj_flx4 · pioneer_ddj_flx6 · pioneer_ddj_flx10 · pioneer_ddj_400 · pioneer_ddj_1000 ·
  pioneer_ddj_sx3 · pioneer_xdj_rx3 · numark_party_mix_live · hercules_inpulse_300 · hercules_inpulse_500
-->


### Don't see your controller?

Two ways to add it:

1. **File a request** — open a [new-controller issue](https://github.com/bravoh-ai/vibemix/issues/new?template=new_controller.yml) and we'll triage. <!-- TBD: confirm org slug `bravoh-ai/vibemix` matches the final repo name before launch -->
2. **Send a PR** — run `python3 scripts/sniff_controller.py` to capture your controller's MIDI shape, then drop a JSON profile under `src/vibemix/midi/profiles/` per [CONTRIBUTING.md](CONTRIBUTING.md#2-new-controller-mapping). CI auto-merges clean profile additions.

---

## Screenshots

<p align="center">
  <img src="docs/assets/screenshots/session.png" alt="vibemix live session — deck readout, polychrome master meter, set clock, and the AI co-host reacting in real time" width="100%" />
  <br/><sub><b>Live session.</b> Deck readout + polychrome master meter on the left, set clock and phase tape in the middle, the co-host reading the room on the right.</sub>
</p>

<table>
  <tr>
    <td width="50%"><img src="docs/assets/screenshots/wizard.png" alt="first-run permissions wizard" width="100%" /><br/><sub><b>First-run wizard.</b> Permissions, device, controller, profile, telemetry — five steps to ready.</sub></td>
    <td width="50%"><img src="docs/assets/screenshots/recordings.png" alt="recording browser in the settings drawer" width="100%" /><br/><sub><b>Recordings.</b> Every set stays local. Play back, browse, set your own retention.</sub></td>
  </tr>
  <tr>
    <td width="50%"><img src="docs/assets/screenshots/mode-picker.png" alt="skill level and hype/teach/coach mode picker" width="100%" /><br/><sub><b>Mode.</b> Beginner / Intermediate / Pro × Hype-man / Coach. Pick the energy before the set.</sub></td>
    <td width="50%"><img src="docs/assets/screenshots/voice-picker.png" alt="co-host voice picker" width="100%" /><br/><sub><b>Voice.</b> Three co-host voices — calm, warm, or gruff.</sub></td>
  </tr>
</table>

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

---

## Community

- **Contributing:** [CONTRIBUTING.md](CONTRIBUTING.md) — how to file bugs, add controller mappings, propose new prompt templates.
- **Code of Conduct:** [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) — community standards for contributors and maintainers.
- **Security:** [SECURITY.md](SECURITY.md) — how to report vulnerabilities privately.
- **Maintainers:** [MAINTAINERS.md](MAINTAINERS.md) — who maintains vibemix, decision process, release cadence.

---

Apache 2.0 · ([LICENSE](LICENSE)) · ([SECURITY](SECURITY.md)) · ([CONTRIBUTING](CONTRIBUTING.md)) · ([CODE_OF_CONDUCT](CODE_OF_CONDUCT.md))

<!-- TODO(kaan, pre-tag-v0.1.0): replace TBD with the real Bravoh-managed vibemix Discord invite. -->
Discord: **TBD** — invite link goes live before the v0.1.0 tag.
