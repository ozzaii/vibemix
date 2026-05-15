# vibemix — AI DJ Co-Host

## What This Is

A free, open-source AI co-host for live DJ sets. Runs locally on macOS or Windows: listens to your master output, watches your DJ software's screen, ingests your controller actions over MIDI, and talks back into your headphones or speakers as either a hype-man (party mode) or a coach (feedback mode). Three user levels — Beginner / Intermediate / Pro — with prompt templates tuned to each, plus a curated library of ~10 popular MIDI controllers mapped out of the box.

Bravoh's first open-source release. Built as a polished, narrow-scope utility that warms an audience converting into Bravoh's waitlist.

## Core Value

The AI reacts to your set in a way that feels alive and grounded — never hallucinating, never breaking the flow, never sounding like generic AI slop. If reactions feel forced, late, fake, or scripted, the product fails. The bar is "real DJ friend in your ear", not "voice assistant doing music commentary".

## Current State

**Last shipped:** v2.1 "The Unified Cut" — 2026-05-16 (status: `tech_debt` accepted per `gsd-autonomous fully` mode).

**Next milestone:** _none active_ — run `/gsd:new-milestone` to scaffold v2.2.

**Phase numbering** continues from Phase 40 in the next milestone (default; no `--reset-phase-numbers`).

**Critical path to public ship:** KAAN-ACTION-LEGAL discharge — Apple Developer Program Agreement update (Francesco, P46) + SignPath OSS Foundation application (Kaan, ~1-week SLA, P46) gate the RC publish. Phase 39 §SHIP customer-facing publishes + §POST-RC-CLEANUP NEVER autonomously discharged. Engineering is shippable; the external clock is the bottleneck.

<details>
<summary>📦 v2.1 The Unified Cut (shipped 2026-05-16, status <code>tech_debt</code>) — archived narrative</summary>

13 phases shipped engineering-green under `gsd-autonomous fully` mode. 96 plans, 633 phase-scope tests added on top of v2.0 baseline, 225 commits since `v2.0` tag, net ~+45k LOC. 105 / 105 v2.1 REQ-IDs engineering-satisfied. 15 carveouts deferred to KAAN-ACTION-LEGAL (legal capacity + customer-facing publish + real-hardware + real-asset + post-approval). All 5 cross-phase integration seams audited WIRED.

**Highlights:**

- **Autonomous hallucination-proxy gate (Phase 27)** — replay harness + 2-judge cross-check (Gemini 3 Pro + Flash) + corpus diversity + substance + cited-relevance filter. Substitutes for Kaan's Phase 16 ear-test for v2.1 only (override expires post-v2.1 per P85).
- **Library intelligence v1 (Phase 28)** — Gemini Embedding 2 + sqlite-vec (Mac) / numpy (Win) with bit-identical top-K parity + vibe-search NL CLI + drag-drop UX + 30-day staleness nudge + €50/month CI cost gate.
- **Post-session debrief MVP UI (Phase 29)** — chaptered review + 60-90s voiced TL;DR + 3 drills + WaveSurfer.js clickable timeline + cited-critique strip. Second Tauri WebviewWindow docks into v2.0 sidecar slot via port 8766.
- **4-layer mascot full additive state machine (Phase 31)** — Base + Emotion + Anticipation + Reaction with priority-stacked crossfades; v2.0 mascot tests port verbatim (P47); GLB bundle 21.67/25 MB.
- **Long-term DJ profile (Phase 32)** — ~2KB allowlist-only JSON cache-side injected into `GeminiContextCache` (P60 preserved); `additionalProperties: false`; default-OFF consent; ≥ 2 citations per tendency.
- **One-click install hardening (Phase 33)** — TCC permissions wizard (macOS 12.3 / 14 / 15 fallback ladder) + BlackHole probe + onboarding stopwatch + bundle-ID lock + no-API-key-surface assertion.
- **Open-source security pass (Phase 34)** — gitleaks + pip-audit + osv-scanner + cargo-audit + cargo-deny + syft SBOM + signed-binary verifier + STRIDE-lite threat model + SECURITY.md + telemetry opt-in default-OFF + capability allowlist lint.
- **Signing pipeline real execution (Phase 38)** — Apple notarytool + SignPath GH Action wired into `release.yml` + post-sign verifier release-publish gate + PowerShell local-rehearsal + P46 audit (Bash + PowerShell mirror).
- **Cross-phase integration audit (Phase 37)** — 5 critical seams (P18→P20, P19→agent, P25→P28, P27→eval-gate, P31→ws_bus) all WIRED with green e2e tests + orphan inventory CI gate + grey-area decision log (P87) + POC immutability gate against v2.0 git tag.
- **Day-zero ops automation (Phase 36) + Public RC cut scaffold (Phase 39)** — Discord auto-provision + 100 RPS load test + healthz watchdog + aligned-community star-seeding + T-30/T+0/T+5/T+24h launch trigger + 5-channel social publisher with NACK + `cut_release.sh` 6-gate pre-flight (NEVER calls `gh release create` autonomously).
- **2 Hard Tek detectors (Phase 30)** — `DISTORTION_CLIMB` + `ACID_LINE_ENTRY` complete v2.0's 6-detector taxonomy; GenreRouter `MappingProxyType` atomic-swap regression test (8 readers × 1000 swaps, no race).
- **Universal2 sidecar (Phase 27-06)** — research-corrected from lipo-merge to target-triple convention (PyInstaller PKG archive embeds only in last merged slice). Eliminates Rosetta prompt on Apple Silicon. WASAPI `IMMNotificationClient` subscription handles mid-session default-device-change on Windows.

Full archive: `.planning/milestones/v2.1-ROADMAP.md` · Requirements: `.planning/milestones/v2.1-REQUIREMENTS.md` · Audit: `.planning/milestones/v2.1-MILESTONE-AUDIT.md`.

</details>

<details>
<summary>📦 v2.0 Research-Driven Ship (shipped 2026-05-14, status <code>tech_debt</code>) — archived narrative</summary>

12 phases shipped Claude-side end-to-end + 2 deferred-to-Kaan (Phase 15 Plan 04 UAT + Phase 16 ear-test). 1961 passing tests · 0 v2.0 regressions · 220 commits since `v0.1.0-rc1`.

**Highlights:**

- Anti-slop contract LIVE — every Gemini reaction citation-validated against `EvidenceRegistry`; un-cited responses strip to 40-OPUS ack-bank fallback. Phase 18 + Phase 20.
- 6 cross-genre event detectors (`KICK_SWAP`, `SUB_LAYER_ARRIVAL`, `BREAKDOWN_KICK_KILL`, `REENTRY_KICK_LAND`, `KICK_DENSITY_SHIFT`, `PHRASE_BOUNDARY`) + `GenreRouter` atomic dispatch. Phase 17.
- Latency Stack v1 — 40-OPUS `AckBank` + `GeminiContextCache` (1024-token floor / 4min refresh) + `CancelGate` (8s hard / 30 soft) + `TTFTMeter` + prompt diet. Phase 19.
- 10-SKU MIDI library + `MidiMapLoader`. Phase 23.
- djay Pro Mac overlay — Rust-parent AX bridge + second WebviewWindow + Canvas 2D amber ring. Phase 24.
- Mascot anticipation layer — `AdditiveLayer` + 5 `prep_*` GLB stubs + 30Hz ws_bus + cancel-aware crossfades. Phase 22.
- Pyrekordbox XML import + DEBRIEF architectural slot (sidecar `--debrief` flag + port 8766 + 3 IPC reservations). Phase 25.
- Recording browser + retention sweep. Phase 15.
- Sign + release CI scaffold (`release.yml` 4-target matrix + Pitfall-7 audit). Phase 21.
- README anti-slop hook + `BRANDING.md` + 4-channel post drafts + day-zero ops scripts. Phase 26.

Full archive: `.planning/milestones/v2.0-ROADMAP.md` · Requirements: `.planning/milestones/v2.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v2.0-MILESTONE-AUDIT.md`.

</details>

<details>
<summary>📦 v2.0 milestone target features (archived — see <code>.planning/milestones/v2.0-ROADMAP.md</code>)</summary>

**Goal (v2.0):** Ship a public open-source AI DJ co-host that reacts in-bar, never hallucinates, with a viral demo arsenal earning 1000+ GitHub stars.

**Absorbed:** Outstanding v0.1.0 work (Phases 15-20 — recording, UAT, sign, release, day-zero ops) folded into a single bulky milestone alongside the research-driven feature set from the v2-bucket research swarm (`.planning/research/v2-buckets/SYNTHESIS.md` + 11 supporting artifacts).

**Target features (12 buckets — shipped):**

1. Ship infrastructure (absorb v0.1.0 outstanding) — recording browser + retention enforcement, UAT, Apple Developer ID sign + notarize + DMG, SignPath Windows MSI, GitHub release matrix, day-zero ops
2. Generalized event detector v1 — 6 cross-genre detectors
3. Latency stack — Gemini prompt diet + context caching + 40-OPUS ack bank + cancel-and-refire
4. Mascot 4-layer additive state machine (simplified for v2.0)
5. Citation linter — anti-slop tech impl
6. djay Pro Mac overlay highlight — viral demo Beat A anchor
7. Pyrekordbox XML one-shot library import
8. 10-SKU MIDI controller library
9. Post-session debrief — architectural slot only in v2.0
10. Library intelligence — deferred to v2.1
11. Cross-mode citation enforcement — live mode only in v2.0
12. Viral demo film + post arsenal

**v2.0 source-of-truth artifacts:**

- `.planning/research/v2-buckets/SYNTHESIS.md` — integration layer + priority matrix
- `.planning/research/v2-buckets/A-latency.md` + `A-followup-1-cancel-and-caching.md`
- `.planning/research/v2-buckets/B-industry-integrations.md` + `B-followup-1-v11-integration-spec.md`
- `.planning/research/v2-buckets/C-ui-overlay.md`
- `.planning/research/v2-buckets/D-mascot-emotion.md`
- `.planning/research/v2-buckets/E-debrief-pedagogy.md` + `E-followup-1-citation-linter.md`
- `.planning/research/v2-buckets/F-library-intelligence.md`
- `.planning/research/v2-buckets/G-genre-taxonomy.md` + `G-followup-1-hard-tek-dsp.md`
- `.planning/research/v2-buckets/synthesis-viral-demo.md`

</details>

## Requirements

### Validated

<!-- Inferred from existing codebase (cohost.py / cohost_v2.py / cohost_lk.py). -->

- ✓ Real-time audio capture pipeline (48kHz stereo → 16kHz mono) — `cohost.py:AudioBuffer`
- ✓ Streaming audio level extraction (RMS, frequency bands, onset density, BPM) — `cohost_v2.py:MusicState`
- ✓ Phase detection (silent/low/groove/build/drop/peak/breakdown) — `cohost_v2.py:EventDetector`
- ✓ Audible-deck detection (A/B/mix/none) — `cohost_v2.py`
- ✓ DJ-app screen capture with window-cropping (Quartz on macOS) — `cohost_v2.py:ScreenBuffer`
- ✓ DDJ-FLX4 MIDI controller event ingestion — `cohost.py:ControllerState`
- ✓ Now-playing track detection via macOS MediaRemote — `cohost.py:TrackInfo` (via `nowplaying-cli`)
- ✓ Gemini 3 Flash multimodal inference path (audio + screenshot + history) — `cohost.py:run_one_turn`
- ✓ Gemini 3.1 TTS streaming → PCM playback queue — `cohost.py:PlaybackQueue`
- ✓ LiveKit `RealtimeModel` integration (Gemini Live Native Audio) — `cohost_lk.py`, `cohost_v2.py`
- ✓ Heuristic event detector with cooldown + in-flight locking — `cohost.py:trigger_loop`
- ✓ Session recording (input.wav + voice.wav + events.jsonl per session) — `recordings/`
- ✓ Mascot WebSocket bus (canvas sprite reacts to RMS at 30Hz) — `mascot.html`
- ✓ Voice-aware mic gating (mic muted during AI talk) — `MicBuffer`

### Active

<!-- v1 scope for the shipping open-source product. -->

**Architecture & Audio I/O**

- [ ] Consolidate three cohost variants into one shipping product (`cohost.py` / `cohost_v2.py` / `cohost_lk.py` → `vibemix`)
- [ ] LiveKit-pipelined architecture (rooms/agents/tracks) with **Gemini 3 Flash multimodal in + Gemini TTS streaming out** as the AI path (NOT Gemini Live Native Audio)
- [ ] Auto-detect master output device cross-platform (no hardcoded BlackHole assumption)
- [ ] Output destination picker — headphones (in-ear) or speakers
- [ ] Drop headphone-cue listening from the audio path (Gemini gets confused)

**Cross-platform**

- [ ] macOS audio capture via system loopback (BlackHole or equivalent virtual cable, auto-detected)
- [ ] Windows audio capture via WASAPI loopback
- [ ] macOS screen capture (Quartz/ScreenCaptureKit window picker)
- [ ] Windows screen capture (win32 window enumeration + capture)
- [ ] Cross-platform window picker UI (pick your DJ app from the running windows)
- [ ] Cross-platform MIDI via `mido` + `python-rtmidi`

**MIDI Controller Library**

- [ ] Curated controller mappings for ~10 popular models: DDJ-FLX4, DDJ-400, DDJ-FLX6, DDJ-FLX10, DDJ-1000, DDJ-SX3, XDJ-RX3, Numark Party Mix Live, Hercules DJControl Inpulse 300, Hercules DJControl Inpulse 500
- [ ] Each mapping: EQ low/mid/high knobs, channel faders, crossfader, play/cue/sync buttons, hotcue pads, filter knobs, tempo faders, jog wheel events
- [ ] Magnitude-aware EQ events (capture the *delta*, not just "user moved knob"), so prompts can convey "slight high boost" vs "kill the lows"
- [ ] Generic-MIDI fallback for unmapped controllers (works but with less semantic context)
- [ ] Controller auto-detection on app launch

**User Experience**

- [ ] Three user modes — Beginner / Intermediate / Pro — each with its own prompt template
- [ ] Two interaction modes — Hype-man (party energy) / Coach (feedback on mixes, EQ choices, transitions)
- [ ] Voice picker — male or female (Gemini TTS prebuilt voices)
- [ ] Genre picker at session start — electronic / techno / house / pop / etc. — used to calibrate phase-detection thresholds
- [ ] Genre-agnostic RMS calibration (research-backed approach that works across genres, not just acid/techno)
- [ ] Calibration wizard on first run (one-click setup, system finds devices, asks for permissions)

**Prompting & Grounding**

- [ ] Absolute set-timeline awareness in prompts ("you're at 2:44; drop happened at 2:33")
- [ ] Surrounding-data prompt strategy: feed Gemini the RMS values + recent events + timing, let *it* form the reaction. Don't tell it "DROP HAPPENED REACT!"
- [ ] Magnitude-aware EQ/fader context (small adjustment vs big push)
- [ ] Hallucination verification before open-source release — every shipped reaction grounded in real audio/MIDI/screen events

**Distribution & Branding**

- [ ] One-click installer — macOS notarized DMG (Apple Developer account exists) + Windows signed installer
- [ ] Free for end users — Bravoh-managed Gemini API key in environment, no key entry required
- [ ] API-usage abuse protection (rate-limit, quota cap per anonymous client) so we don't get drained
- [ ] Polished UI/UX inside the app — calibration wizard, mode/voice/genre pickers, no AI-slop aesthetics
- [ ] **Reactive mascot (Avery) — first-class feature, not decoration.** Lives on screen, reacts physically to MIDI events: covers ears on bass-kill, squints on high-EQ slam, leans with crossfader, puffs up on bass-push, freezes on pause, bounces on the beat, zips mouth shut during vocal sections, punches air on hot-cue. Inspired by OpenAI Pets / Tamagotchi — a live indicator of what the system actually saw, so the user feels the system *listening*. Pose vocabulary documented and named (idle/alert/speaking/squint/cover-ears/puff-up/wavy/lean/punch/freeze/bounce/zipped/shocked/dancing/sleeping/winking).
- [ ] **Dedicated polish phase — FL-Studio-quality UI bar.** Not a final-week sweep; an explicit phase that lifts every surface to pro-audio-software realism (think FL Studio, Ableton, Bitwig, Native Instruments). Knob/fader physics, controller-grade hierarchy, dense data without overwhelm, no "looks like a web app" residue. Critique → execute → critique → execute loop within the phase, with `gsd-ui-checker` + `gsd-ui-auditor` runs between iterations until the bar is hit.

**GitHub Presence — "Maximum Sexification"**

The GitHub repo is the front door for 100% of organic discovery. It must read like a real product launch, not a code dump.

- [ ] Branded hero banner at top of README (custom artwork — vibemix wordmark + tagline + screen of the app in action; not a generic logo placeholder)
- [ ] One-paragraph value prop above the fold (clear, no jargon, hooks DJ at "co-host that actually reacts to your set")
- [ ] Hero demo video / GIF — 30-45s cinematic edit: real DJ playing → AI reacting in real-time over headphones (subtitled), drop/build/transition reactions visible on screen
- [ ] Installation section — one-click download buttons for macOS + Windows, install GIFs, "from clone to running in <60s" promise
- [ ] Feature matrix — beginner/intermediate/pro × hype-man/coach, with example reactions per cell
- [ ] Supported controllers grid — logos/photos of all 10 mapped controllers + "calibrate any other" callout
- [ ] Screenshots gallery — calibration wizard, mode picker, voice picker, in-session UI, recording browser
- [ ] "How it works" diagram — clean architecture sketch (audio in → events → Gemini → voice out), not Mermaid-default ugly
- [ ] FAQ — 8-12 questions: privacy, what data leaves your machine, cost, why no Linux, why no Gemini Live, etc.
- [ ] "Built by Bravoh" footer + link to the Bravoh waitlist (the funnel)
- [ ] Badges row — build status, latest release, license, platform, stars, Discord (optional)
- [ ] CONTRIBUTING.md — controller-mapping contribution path (the most likely external PR), prompt-template contribution path
- [ ] CODE_OF_CONDUCT.md, SECURITY.md, LICENSE — table-stakes OSS hygiene
- [ ] Issue templates — bug / feature / new-controller-request
- [ ] Releases page — every binary cut tagged with a real changelog, not auto-generated noise
- [ ] Social preview image — custom OG image that looks slick when shared on X/Discord/Slack
- [ ] Repo description + topics tags optimised for search (`dj`, `livekit`, `gemini`, `ai-assistant`, `audio`, `midi`, `pioneer-ddj`, `realtime-ai`)
- [ ] No "rough edges" visible in the public repo — no `_test_*.py` scratch files, no `.bak` files, no committed `.env`, no large binaries (mascot sprites move to release assets or get rebuilt cleanly)

**Launch Funnel**

- [ ] Marketing-ready demo cinematic (Kaan + Francesco DJ session, edited; vibemix doing transitions feedback; Gemini speaking over)
- [ ] Open-source release on `github.com/bravoh/vibemix` (GitHub Enterprise under bravoh org)
- [ ] Pre-launch seed: 15+ stars from friends/dev network on day 1 (Kaan, Francesco, Momo + dev contacts + ARRAY community)
- [ ] Organic content push (Instagram/X/TikTok reels — Francesco's cinematic shoot + Kaan's controller demos)
- [ ] 50-100 € IG/TikTok ads → drive to repo download
- [ ] Outreach to DJ network (Francesco's connections — alignment, label contacts) + DJ-software vendors (e.g. Algoriddim/djay Pro team)
- [ ] Email collector on download (Instagram lead magnet pattern: comment → DM with link → email capture → routes into Bravoh waitlist at public launch)

### Out of Scope

- **Gemini Live Native Audio modality** — Kaan tested it, doesn't generalize well enough for live music context. Code path stays in the repo but is not the default; future opt-in toggle possible.
- **Headphone cue listening** — Gemini conflates cue with master and produces wrong reactions.
- **User-supplied Gemini API keys** — friction kills virality; we eat the cost as marketing.
- **DAW integration** (Logic / Ableton / FL Studio) — mentioned as "the next conquest" after DJ software; defer entirely.
- **Mobile / iPad / iOS app** — desktop only.
- **Custom voice cloning** — Gemini TTS prebuilt voices only.
- **Linux support** — niche audience, doubles platform-engineering cost.
- **Multi-language UI** — English only in v1 (the AI itself can speak whatever Gemini supports, but the app chrome is English).
- **Track recommendation / library scanner AI feedback** — file-watcher exists in code but the "AI suggests your next track" feature defers to v1.1.
- **Mascot.html as a shipped UI** — kept as a fun easter egg / dev visualization, not part of the polished installer experience.
- **Real-time stream-to-Twitch/YouTube hook** — out of scope; recording for later sharing is enough.

## Context

**Where this comes from.** The codebase started as a personal Friday-night hobby experiment — Kaan wanted an AI co-host while DJing on his DDJ-FLX4. Three iterations explored different architectures: `cohost.py` (heuristic triggers + Gemini 3 Flash multimodal), `cohost_lk.py` (LiveKit + Gemini 2.5 Native Audio realtime), `cohost_v2.py` (single-source-of-truth `MusicState` + EventDetector + audible-deck detection). All run, all have rough edges. The Native Audio realtime path showed worse grounding than the explicit Flash + TTS path despite more architectural plumbing — hence the v1 architectural decision to keep LiveKit's *pipeline* (rooms/agents/tracks/streaming) but swap the brain to Flash + TTS.

**Why open-source now.** Bravoh (the AI Artist Operating System) has a 140k-view reel on the project's Instagram account and a Closed Beta running since March 1, 2026. The DJ co-host is a fast-shipping, narrowly-scoped, demo-able artefact that lives downstream of Bravoh's positioning ("we build cool AI for musicians, here's a free taste") — it is the marketing wedge that turns "interested" into "watching the Bravoh waitlist".

**Existing user.** Kaan, primarily — the codebase started as his Friday-night experiment. The open-source release expands to "any DJ with a controller + a DJ software running on mac or windows" — beginner curiosity to pro feedback-loop.

**Stack baseline.** Python 3.12+ (current `.venv` is 3.14), LiveKit Agents framework, `google-genai`, `sounddevice` (mac) / WASAPI bindings (Windows), `mido` + `python-rtmidi`, `numpy` + `scipy` for DSP, `mss` / Quartz / win32 for screen capture. Heavy reliance on Gemini 3 family (Flash for inference, TTS for voice).

## Constraints

- **Timeline**: No hard calendar target — ship-when-ready per `gsd-autonomous fully` mode. External Apple Developer Program Agreement + SignPath OSS approvals are the critical path; engineering parallelizes around the external clock.
- **Quality bar**: "Real DJ friend in your ear, no AI slop" — Kaan will block release if reactions feel scripted, late, hallucinated, or generic.
- **Budget**: 150-200 € launch marketing (IG ads, paid posts), ~50 €/month ongoing Gemini API for end-user requests. Reassess if usage scales.
- **Tech stack**: Locked on LiveKit pipeline + Gemini 3 Flash + Gemini TTS streaming. No other LLM providers (Bravoh is Gemini-only).
- **Platforms**: macOS + Windows in v1. Linux explicitly excluded.
- **Team**: Kaan (engineering + product), Francesco (cofounder — product/marketing/DJ network for outreach), Momo (Bravoh team). Bravoh main product takes priority — vibemix runs alongside.
- **Open-source license**: TBD (likely MIT or Apache 2.0). Must allow Bravoh to use the same code internally if needed.
- **Security**: API key embedded in distributed binary is the API-key-protection problem of the year — solve via Bravoh-side proxy with per-client rate limit, not by shipping a raw key.
- **Hallucination grounding**: No release until verification phase confirms reactions are tied to real events. This is a hard gate.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Product name = **vibemix**, repo = `bravoh/vibemix` | Distinct enough to be its own thing, "mix" hooks the DJ semantic, GitHub Enterprise being set up under bravoh org | — Pending |
| **macOS + Windows in v1**, no Linux | Doubles addressable market vs mac-only; Linux is small DJ audience and tripled platform-engineering cost | — Pending |
| **LiveKit pipeline + Gemini 3 Flash + Gemini TTS streaming** as default AI path | Kaan tested Gemini Live Native Audio (`cohost_v2.py`) — grounding was worse than explicit Flash + TTS (`cohost.py`) despite more plumbing. LiveKit architecture (rooms/agents/tracks/streaming) is loved; only the brain swaps. | — Pending |
| **Curated 10-controller MIDI library** + generic fallback | Covers the ~80% of mid-tier DJs (Pioneer DDJ family + Numark + Hercules) without forcing every user through a calibration wizard | — Pending |
| **Master-output-only audio**, no headphone cue | Gemini conflates cue with master and produces wrong reactions — Kaan confirmed | — Pending |
| **3 user modes × 2 interaction modes** (Beginner/Intermediate/Pro × Hype-man/Coach) | Wide audience coverage with a small prompt-template matrix | — Pending |
| **Bravoh-managed API key**, free for end users | Friction kills virality; we treat cost as marketing spend | — Pending |
| **Genre picker at session start** | Phase-detection (drop/build/breakdown) thresholds depend heavily on genre; "auto-detect genre" is research-grade and would block shipping | — Pending |
| **Open-source as Bravoh's first OSS** | Marketing wedge ahead of Bravoh public launch; gets attention, builds trust, funnels to waitlist | — Pending |
| **Workflow profile: Fine granularity, all Opus, all checkpoints on** | Kaan's directive: "do your deep research, don't go blind into coding, all checkpoints will be every agent will be Opus". Enforced via `models.*=opus` (all 6 phase types) + `model_overrides.<agent>=opus` (33 agents) in `.planning/config.json` — belt-and-braces, no agent can fall back to a smaller model. | — Pending |
| **Critique → execute → critique → execute loop per phase** | Kaan's directive: every phase runs a quality loop, not a one-shot. plan-checker before execute, verifier after execute, ui-checker/ui-auditor between polish iterations, code-reviewer on output. Continue iterating until the gate passes. Enforced via `workflow.plan_check=true`, `workflow.verifier=true`, `workflow.code_review=true`, `workflow.ui_safety_gate=true` already in config. | — Pending |
| **Reactive mascot as v1 feature, dedicated polish phase** | The mascot isn't just brand decoration — it's the visual feedback loop that telegraphs back what the system saw. Inspired by OpenAI Pets, lives in-app, reacts to MIDI/audio in real time. Polish to FL-Studio UI quality is its own phase, not a final-week sweep — a critique→execute loop runs until the realism bar is hit. | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state (users, feedback, metrics)

---
*Last updated: 2026-05-16 — milestone v2.1 "The Unified Cut" SHIPPED + archived via `/gsd:complete-milestone` (status: `tech_debt` accepted — KAAN-ACTION-LEGAL discharge pending public RC publish). Next: `/gsd:new-milestone` for v2.2.*
