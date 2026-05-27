# INTEL-23: research-backed musical intelligence bet map

**Date:** 2026-05-27
**Lane:** intelligence excellence / musical context / agentic engine / data strategy
**Depends on:** INTEL-01 through INTEL-22
**Status:** source-backed strategy map; no product code touched

## Purpose

The INTEL stack already defines the system we want:

```text
ANLZ structure
  -> section objects
  -> section vectors
  -> transition slates
  -> bounded context packets
  -> claim-validated agent decisions
```

This file answers a sharper question:

```text
Which intelligence bets are supported by outside evidence, where is vibemix
different from existing DJ software, and what must be proven before each bet
becomes product behavior?
```

It is a map for excellence, not scope creep. If a future builder wants to add a
model, live analyzer, cue system, or context feature, this file says whether it
supports the core thesis or distracts from it.

## Source-backed facts

### Real DJ mixes support section-aware, phrase-aware cueing

Kim et al. (ISMIR 2020) analyzed 1,557 matched real-world DJ mixes from
1001Tracklists, with 13,728 unique tracks and 20,765 transitions. Their
mix-to-track subsequence alignment extracts cue points, transition length, and
mix segmentation from real DJ practice.

Sources:

- https://arxiv.org/abs/2008.10267
- https://mir-aidj.github.io/djmix-analysis/

Product implications:

- Cue points are not arbitrary timestamps. They cluster around shared musical
  structure.
- Phrase-level timing matters. Their transition-length histogram peaks around
  phrase multiples, and the project page calls out 32-beat phrase structure.
- Real DJs usually do not warp tracks wildly: their summary reports 86.1% of
  tempo adjustments below 5%, 94.5% below 10%, and key transposition on only
  2.5% of played tracks.
- Therefore, vibemix can treat ANLZ beatgrids and section boundaries as a strong
  offline floor. The live engine should spend its complexity budget on alignment
  confidence and transition utility, not on assuming every track is heavily
  transformed.

INTEL consequence:

- INTEL-01/06 are correct: use beatgrid/phrase structure first, live confidence
  gates second.
- INTEL-18/19 are correct: smart cues must be evaluated as transition utility,
  not "pretty cue labels."
- INTEL-15 labels should include cue agreement and phrase usefulness, because
  that matches how real DJ behavior can be measured.

### Automatic DJ research supports a hybrid deterministic engine

Vande Veire and De Bie (EURASIP 2018) built an open automatic DJ system for Drum
and Bass. It combines beat/downbeat tracking, structural segmentation, cue point
selection, harmonic/style compatibility, crossfade behavior, and genre-specific
assumptions. The paper reports 91% fully correct annotations on the evaluated
corpus for tempo, beats, downbeats, and structure.

Source:

- https://link.springer.com/article/10.1186/s13636-018-0134-8

Product implications:

- The winning architecture is not "ask an LLM to listen." It is MIR features +
  structure + rules + selection policy.
- Genre-specific assumptions are a strength in dance music, not an
  embarrassment.
- Harmonic, rhythmic, timbral, and structural compatibility all matter; no single
  embedding should own the decision.
- The research goal is full automated mixing. vibemix's product goal is
  different: assist the DJ, expose grounded choices, keep the human in control.

INTEL consequence:

- INTEL-07 genre-aware transition grammar is a core primitive.
- INTEL-11 component scoring should stay explicit instead of becoming an opaque
  learned ranker too early.
- INTEL-20 should keep deterministic live pill behavior as v1 and use the model
  mainly for prep/chat explanations until eval proves otherwise.

### Rekordbox already competes on automatic cue preparation

rekordbox 7 has Intelligent Cue Creation. Official docs say it can set Hot Cues
or memory cues during analysis, can use Auto or Manual cue analysis modes, can
learn from an overall cue trend and a personal cue trend, and can set up to 16
Hot Cues and 10 memory cues. The overview frames it as learning a DJ's cue point
preferences from tracks registered in a cue-analysis playlist.

Sources:

- https://rekordbox.com/en/feature/overview/
- https://cdn.rekordbox.com/files/20260409151936/rekordbox7.214_manual_EN.pdf

Product implications:

- "Automatically place hot cues per track" is no longer enough as a moat.
- vibemix should not win by pretending rekordbox cueing does not exist.
- vibemix can win on set-aware, explanation-aware, grounded cueing:
  - cue slots chosen for an intended transition;
  - section-to-section compatibility explained;
  - review-first exports;
  - evidence and claims attached to each suggestion;
  - privacy-safe local fixture/eval story.

INTEL consequence:

- INTEL-18 must stay set-aware. Slot policy is not just per-track decoration.
- INTEL-19 baseline comparison is mandatory before marketing this as better.
- Product copy should say "transition-aware cue prep" or "set-aware cueing,"
  not generic "AI hot cues."

### BeatNet is a viable live-awareness candidate, but not PR 1

BeatNet exposes real-time and offline joint beat, downbeat, tempo, and meter
tracking with CRNN plus particle filtering. It can read streaming audio and emit
beat/downbeat arrays.

Sources:

- https://github.com/mjhydri/BeatNet
- https://arxiv.org/abs/2108.03576

Product implications:

- Live playhead from captured audio is technically plausible without rekordbox
  process memory, screen vision, or PRO DJ LINK.
- Beat/downbeat tracking should be optional and confidence-gated, not a hidden
  hard dependency in the first section-intelligence PR.
- Live beat/downbeat claims must degrade under blend, low confidence, or missing
  identity.

INTEL consequence:

- INTEL-06 is right to isolate live awareness into a snapshot holder.
- INTEL-20 is right to suppress exact timing below the floor.
- INTEL-16 should keep BeatNet out of PR 1-4 unless a focused spike proves
  latency and packaging on the target Mac.

### Fingerprinting is a fallback identity tool, not the main brain

Panako is designed for acoustic fingerprinting under pitch shifting, time
stretching, and tempo changes, and its publication reports reliability on
queries with time/pitch modifications up to 10%.

Source:

- https://biblio.ugent.be/publication/5754913

Product implications:

- Fingerprinting is valuable when now-playing/title identity fails.
- It is too indirect to be the primary live transition engine during blends.
- Its best role is "confirm or recover track identity," then let ANLZ/section
  maps and live alignment do the musical work.

INTEL consequence:

- INTEL-06 identity ladder should stay:
  - known deck/now-playing identity first;
  - fingerprint fallback second;
  - no invented identity ever.
- INTEL-21 `track_identity` claims should distinguish library resolution from
  fingerprint recovery.

### Music foundation models are a benchmark lane, not a product rewrite

Current and recent music/audio representation sources:

- LAION `larger_clap_music_and_speech` is a CLAP checkpoint trained on music and
  speech, useful for extracting audio/text features:
  https://huggingface.co/laion/larger_clap_music_and_speech
- MuLan is a music audio/text joint embedding trained on 44M music recordings
  and free-form text annotations:
  https://arxiv.org/abs/2208.12415
- MERT is a large-scale self-supervised acoustic music understanding model,
  accepted at ICLR 2024, with reported strength across 14 music understanding
  tasks:
  https://arxiv.org/abs/2306.00107
- MuQ and MuQ-MuLan are recent music representation / music-text embedding
  models with open code/checkpoints:
  https://arxiv.org/abs/2501.01108

Product implications:

- The first excellence move is not replacing CLAP. It is changing the data unit
  from track to section.
- New models should compete only through INTEL-14 benchmark contracts.
- No model gets to own BPM, key, beatgrid, cue timing, or claim truth.
- A stronger embedding can improve semantic/timbre scores, but it cannot replace
  the deterministic scorer.

INTEL consequence:

- INTEL-10 section rows and INTEL-14 representation bake-offs are the right
  abstraction.
- Product default remains local 512D CLAP until a benchmark proves better
  transition utility, migration cost, and packaging reliability.

## Vibemix moat

Existing tools cover pieces:

- rekordbox: library analysis, grids, phrases, cue prep, Intelligent Cue
  Creation.
- Mixed In Key style tools: key/energy/cue prep.
- automatic DJ research: full algorithmic mixing.
- general audio LLMs: language over audio, but weak grounding for exact musical
  claims.

vibemix's excellent lane is the intersection:

```text
local DJ library data
+ section-level representations
+ deterministic transition scoring
+ taste feedback
+ claim-validated agent explanations
+ review-first actions
+ live silence when confidence is weak
```

That is different from "auto DJ." The product is a grounded copilot:

- it proposes the next musical move;
- it tells which cue to use;
- it explains only evidence-backed reasons;
- it learns the DJ's taste without turning private history into prompt soup;
- it writes/export cues only through issued, reviewable proposals.

## Bet map

### Bet A: ANLZ structure floor

Status: no-regret.

Why:

- Local evidence shows ~91% PSSI phrase coverage with no parse failures.
- External DJ mix research supports structural cue/transition behavior.
- Existing product already has cue contracts and cue-anchored ingest seams.

Build:

- PR 1 ANLZ parser.
- PR 2 smart cue prep/audit.

Kill criteria:

- PSSI role boundaries fail human review on Kaan's main genres below 60%
  keep/maybe.
- ANLZ parsing creates brittle private-path or DB dependencies.

Graduate criteria:

- 20 reviewed tracks, >=70% keep/maybe, 0 overwritten DJ cues.
- INTEL-19 shows vibemix proposals beat naive ANLZ and are comparable or better
  than rekordbox Intelligent Cue Creation on transition utility.

### Bet B: section-level embeddings with current CLAP

Status: no-regret, ship first.

Why:

- Track-level embeddings collapse intro/build/drop/outro differences.
- Existing CLAP path already works locally.
- Section windows are the cheapest way to create musical moments.

Build:

- PR 3 section store/index.
- Keep whole-track search unchanged.
- Store vector refs, not raw vectors, in packets.

Kill criteria:

- Section search cannot beat track-level nearest neighbor on INTEL-03/14
  transition fixtures and private labels.

Graduate criteria:

- Section retrieval improves mixable-window hit@5 and transition nDCG without
  more grounding failures.

### Bet C: deterministic transition slate scorer

Status: core product brain.

Why:

- Research and DJ practice both support multi-factor compatibility:
  structure, beat/downbeat, phrase, harmony, rhythm/timbre, energy.
- LLMs should choose/explain among candidates, not free-rank the library.

Build:

- PR 4 transition scorer with explicit score components.

Kill criteria:

- Human labels show top deterministic candidates are usually unplayable and
  component weights cannot be tuned without overfitting.

Graduate criteria:

- INTEL-15 labels show accepted/maybe candidates outrank rejects.
- Risk flags predict actual review objections.

### Bet D: set-aware smart cueing

Status: moat candidate.

Why:

- Per-track cueing is now a platform feature in rekordbox 7.
- Set-aware cueing is less commoditized: "use this cue for this transition"
  is the real DJ utility.

Build:

- INTEL-18 policy plus INTEL-19 baseline comparison.
- Keep review-first export.

Kill criteria:

- Rekordbox Intelligent Cue Creation matches or beats vibemix on Kaan's reviewed
  set-aware transition utility with less operational friction.

Graduate criteria:

- Vibemix wins on at least one of:
  - cue usefulness for a planned transition;
  - explanation quality;
  - preserving DJ-authored cues;
  - genre-aware pad semantics.

### Bet E: live pill with audio-derived playhead

Status: second-wave, not first PR sequence.

Why:

- Laptop-only rekordbox does not expose rich live deck state without memory
  reads/vision/hardware.
- BeatNet/Panako/DTW-style alignment make audio-derived live awareness plausible.

Build:

- Start with coarse identity + ANLZ phrase map.
- Add BeatNet only behind a live-awareness confidence gate.
- Suppress exact timing during blends.

Kill criteria:

- On-device latency, packaging, or blend failure makes exact timing unreliable.

Graduate criteria:

- Offline replay shows playhead/section agreement above INTEL-06 floor.
- Live pill suppresses instead of lying in ambiguous windows.

### Bet F: model-assisted explanations

Status: prep/chat first, live later.

Why:

- The language model is valuable for tradeoff language and taste questions.
- It is not reliable as the primary musical truth source.

Build:

- PR 6 context compiler.
- PR 7 claim ledger.
- PR 8 decision runtime.

Kill criteria:

- Validator rejects too many outputs for live mode, or model-written copy adds
  unsupported claims even with a bounded packet.

Graduate criteria:

- Agent explanations pass claim validation.
- Unsupported musical claim rate stays below INTEL-21 gate.
- User labels prefer model explanations over deterministic templates in prep.

## What not to do

- Do not chase "Gemini can hear it" as a core product dependency.
- Do not replace the current embedding model before section rows exist.
- Do not market generic auto-hot-cueing without comparing against rekordbox.
- Do not use process-memory rekordbox hacks as the default live path.
- Do not let a model write cue positions, track IDs, BPM/key, or exact timing.
- Do not optimize for automatic playback. Optimize for grounded DJ agency.

## Evaluation map

Each bet must map to a current INTEL gate:

| Bet | Primary gate | Secondary gate |
|-----|--------------|----------------|
| ANLZ floor | INTEL-01 parser tests | INTEL-15 human review |
| Section embeddings | INTEL-10 store parity | INTEL-14 representation benchmark |
| Transition scorer | INTEL-11 score tests | INTEL-15 transition labels |
| Smart cueing | INTEL-18 policy tests | INTEL-19 baseline comparison |
| Live awareness | INTEL-06 replay | INTEL-20 suppression traces |
| Model explanations | INTEL-21 claim validation | INTEL-17 replay |
| Synthetic testability | INTEL-22 privacy fixture audit | INTEL-16 PR evidence bundle |

## Product language discipline

Use:

```text
set-aware cue prep
transition-aware cue suggestions
section-level musical context
grounded next-entry suggestions
claim-validated explanations
review-first rekordbox export
```

Avoid:

```text
AI hears your music
perfect hot cues
automatic DJ
beat-accurate live calls without confidence
better than rekordbox
```

The excellent claim is not that vibemix is omniscient. The excellent claim is
that it is honest, grounded, musically useful, and gets sharper with the DJ.

## Next research/build handoff

Immediate no-regret build order remains:

```text
PR 0 fixtures
PR 1 ANLZ structure
PR 2 smart cue audit/proposals
PR 3 section store/index
PR 4 transition scorer
PR 5 grounded tool surface
PR 6 context compiler
PR 7 claim ledger
PR 8 decision runtime
PR 9 labels/eval gates
```

Research tracks after the first build sequence:

1. BeatNet packaging/latency spike on the target Mac.
2. Rekordbox Intelligent Cue Creation baseline export/review on the same 20
   tracks used for INTEL-19.
3. MERT/MuQ/MuLan representation bake-off through INTEL-14, only after section
   rows make the benchmark meaningful.
4. Fingerprint fallback spike only if now-playing identity remains weak in real
   sessions.

## Success definition

This map is successful when future implementation choices can be judged quickly:

```text
Does this improve section-level transition utility?
Does it preserve deterministic grounding?
Does it beat or complement rekordbox where rekordbox already competes?
Can we prove the lift with INTEL-14/15/19/21/22 evidence?
Does live mode stay quiet when confidence is weak?
```

If the answer is no, it is probably not intelligence excellence. It is just a
shiny detour.
