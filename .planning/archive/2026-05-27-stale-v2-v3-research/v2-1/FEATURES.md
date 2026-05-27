# Feature Research — v2.1 "The Unified Cut"

**Domain:** AI live co-host for DJs — second milestone hardening pass (v2.0 shipped 2026-05-14, status `tech_debt`)
**Researched:** 2026-05-14
**Confidence:** HIGH on architectural patterns (Three.js additive blending, LLM-as-judge, Gemini Embedding 2, Tauri signing). MEDIUM on Hard-Tek DSP thresholds (no public reference dataset, library-tuned). LOW on day-zero ops timing (every launch is different — references are pattern, not playbook).

---

## Reading Guide

This file is the v2.1-only feature landscape. **It does NOT re-research the 6 cross-genre detectors, citation linter, latency stack v1, MIDI library, djay Pro overlay, mascot simplified subset, pyrekordbox + DEBRIEF slot, recording browser, sign+release scaffold, or README/branding work — those shipped in v2.0** (see `.planning/milestones/v2.0-MILESTONE-AUDIT.md` for shipped surfaces).

Every feature below either (a) closes a v2.0 orphan / Kaan-action gap autonomously, (b) extends a v2.0 architectural slot, or (c) is genuinely new scope. Each entry names the v2.0 surface it docks into so the roadmapper can sequence dependencies.

**Core anti-slop bar throughout:** "real DJ friend in your ear, no AI slop". Every feature is judged by the hallucination class it closes or the slop pattern it avoids. Anything that adds surface without closing a class is anti-feature.

**Core star-bait bar:** 1000+ GitHub stars. Every feature is judged by whether it's screenshottable / demo-worthy / "I'd star that" — or just engineering hygiene the user never sees. Engineering hygiene still ships (the audit gate, security pass) but doesn't compete for star budget.

---

## Top-Level Priority Matrix

| # | Feature | User Value | Star Bait | Anti-Slop Lever | Complexity | Priority |
|---|---------|------------|-----------|-----------------|------------|----------|
| 1 | Autonomous proxy hallucination gate | HIGH (release gate) | LOW (hidden) | **HIGH** — the gate itself | L | P1 |
| 2 | Embedding library intelligence v1 | HIGH | HIGH (demo-worthy) | HIGH (closes track-name hallucination) | L | P1 |
| 3 | Post-session debrief UI | HIGH (re-positions to coach) | HIGH (chaptered scrub = screenshot) | MEDIUM (cited critique) | L | P1 |
| 4 | 4-layer mascot additive state machine | MEDIUM (already-shipped subset works) | HIGH (mascot = brand) | LOW (visual, not factual) | M | P2 |
| 5 | One-click install hardening | HIGH (every user touches) | MEDIUM (60s clone-to-run promise) | LOW | M | P1 |
| 6 | OSS security pass | LOW (invisible to users) | MEDIUM (SECURITY.md = trust signal) | LOW | M | P1 |
| 7 | Long-term DJ profile (~2KB JSON) | MEDIUM (kicks in session 2+) | LOW (invisible until you notice) | HIGH (next-session grounding) | S | P2 |
| 8 | Autonomous demo film generation | MEDIUM (one-shot use) | **VERY HIGH** (the viral wave) | HIGH (real session anti-slop tax) | M | P1 |
| 9 | Cross-phase integration audit gate | LOW (engineering hygiene) | LOW | MEDIUM (closes orphans) | S | P1 |
| 10 | Day-Zero ops live | HIGH (launch infra) | HIGH (the launch itself) | LOW | M | P1 |
| 11 | Public RC cut + ship | HIGH (it's the ship) | **VERY HIGH** (it IS the launch) | LOW | S | P1 |
| 12 | Real GLB mascot animations autonomously | MEDIUM (replaces stubs) | HIGH (mascot rig quality = brand) | LOW | M | P2 |
| 13 | 2 Hard Tek detectors (DISTORTION_CLIMB + ACID_LINE_ENTRY) | MEDIUM (Kaan's primary genre) | MEDIUM (Hard Tek subculture wedge) | HIGH (closes "synth/303" hallucinations) | S | P2 |

**Priority key:**
- P1: Blocks RC ship. Must land before public cut.
- P2: Lifts quality bar but doesn't block ship. Land in v2.1 if budget allows; defer to v2.2 if not.
- P3: Nice-to-have. None in v2.1 — every entry above is at least P2.

---

## v2.0 Surface Dependency Map

```
v2.1 Feature                          ──docks into──>  v2.0 Surface (Phase #)
─────────────────────────────────────────────────────────────────────────
1  Autonomous hallucination gate       ──>  P16 (deferred) + P17 detectors + P18 EvidenceRegistry
                                                + P19 AckBank + P20 CitationLinter + P22 anticipation
                                                + VoiceRecorder events.jsonl + recordings/ baseline
2  Library intelligence v1             ──>  P25 RekordboxLibrary + EvidenceRegistry.register_library
                                                (orphaned in v2.0) + P5 proxy
3  Post-session debrief UI             ──>  P25 DEBRIEF architectural slot (sidecar --debrief flag
                                                + port 8766 + 3 IPC reservations) + P14 settings
                                                drawer + P15 recording browser
4  4-layer mascot full state machine   ──>  P22 AdditiveLayer simplified subset
                                                (extends, not replaces) + 30Hz ws_bus
5  One-click install hardening         ──>  P21 sign+release scaffold + P15 recording UAT
                                                + Tauri shell sidecar bundle
6  OSS security pass                   ──>  P21 release.yml + Bravoh-side proxy + bundled secrets
7  Long-term DJ profile                ──>  P25 DEBRIEF IPC + P10 prompt matrix + VoiceRecorder
                                                events.jsonl
8  Autonomous demo film generation     ──>  P24 djay overlay + P22 mascot + P26 viral drafts
                                                + recordings/ session pipeline
9  Cross-phase integration audit gate  ──>  ALL v2.0 surfaces — register_library orphan, MASCOT-11
                                                stubs, DEBRIEF IPC consumers, OPS-* live
10 Day-Zero ops live                   ──>  P26 day-zero scripts + healthz endpoint + Bravoh proxy
11 Public RC cut + ship                ──>  P21 signed binaries + P26 social drafts + README hero
12 Real GLB mascot animations          ──>  P22 prep_* GLB stubs (artist task substitute)
13 2 Hard Tek detectors                ──>  P17 GenreRouter + Hard-Tek genre slot
```

**Orphan close-out tracker:**
- `EvidenceRegistry.register_library` (P25 → P18) — wired by Feature 2
- `MASCOT-11` real GLB stubs (P22) — wired by Feature 12
- `DEBRIEF-02` IPC consumers (P25) — wired by Feature 3
- 40 Achird-voice OPUS recordings (P19) — wired by Feature 1 (TTS render block) + voice-talent fallback
- 9-SKU controller verification (P23 MIDI-17) — wired by Feature 9 (community PR substitute)

---

## Feature 1: Autonomous Proxy Hallucination Verification Gate

**Reference products:**
- **DeepEval (Confident AI)** — pytest-native LLM eval framework; multimodal incl. audio first-class; LLM-as-judge with 50+ pre-built metrics. The closest off-the-shelf match for vibemix's gate. ([DeepEval](https://deepeval.com/), [LLM-as-judge guide](https://deepeval.com/guides/guides-llm-as-a-judge))
- **Anthropic's eval methodology** — three-tier: rules-based (linters/type-checkers), visual feedback (Playwright screenshots), LLM-as-judge subagent. Documented in [Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).
- **Arize AI golden-dataset templates** — calibrated against human graders to 70-90% precision; the canonical "lock the threshold" pattern. ([Arize LLM-as-Judge](https://arize.com/llm-as-a-judge/))
- **Braintrust** — production LLM eval platform; documents when LLM-as-judge wins vs deterministic evals. ([Braintrust article](https://www.braintrust.dev/articles/what-is-llm-as-a-judge))

**Table stakes (must include):**
- **Recorded-session replay harness** — feed `recordings/<session>/input.wav + voice.wav + events.jsonl + session.json` back through the pipeline deterministically. Already half-built: VoiceRecorder writes the artifacts (Phase 2), `tests/replay/` and `scripts/tune_detectors.py` (Phase 17) have the scaffold.
- **Pointwise LLM-judge scoring** — per Gemini reaction, one judge call: `{event, reaction_text, evidence_packet} → {grounded: bool, on_beat: bool, slop_score: 0-5, rationale: str}`. Single-prompt rubric, single-judge model (Gemini 3 Pro as judge; Flash as production).
- **Golden-set calibration** — 30-50 hand-labeled reactions across Kaan's recorded sessions become the calibration set. Judge agreement with Kaan ≥85% before the judge gets to score anything else. Without this, the judge is the slop.
- **F1 / precision / recall on detector fires** — for the 8 v2.0+v2.1 detectors, replay against labeled events and measure: did the detector fire when an event was present (recall), and was the fire correct when it fired (precision). Threshold-lock at the value Kaan signs off on, not at an arbitrary academic number.
- **CI gate** — `pytest tests/replay/test_gate.py` runs the harness on every commit; if F1 drops below locked threshold, build fails. Same gate runs on `main` nightly with the full session corpus.
- **Audit trail** — every gate run produces `replay/<timestamp>/{detector_metrics.csv, judge_verdicts.jsonl, regression_diff.md}`. Audit-able, scrubable, blameable.

**Differentiators (vibemix angle):**
- **Audio-first eval** — almost every production LLM eval today is text-only (RAGAS, Braintrust). vibemix's gate scores reactions against the *audio* + *MIDI* + *screen* triple — the same multimodal input the production agent sees. The judge gets the evidence packet, not the prompt.
- **Citation linter as preflight** — every reaction is already citation-checked at runtime (Phase 20). The replay harness can lean on the linter's citation parse for ground-truth event lookup — fast, deterministic, no LLM call needed for "did the cited event actually exist?".
- **"Real DJ friend" rubric, not "factually correct"** — judge prompt explicitly anchors on Kaan's tone bar: scripted? late? generic? hallucinated? Not "is this technically accurate" — DJ commentary has wide latitude for stylistic call.
- **Threshold-lock signed by Kaan in writing** — gate threshold isn't a Claude decision. Kaan listens to the calibration set, signs off, the F1/slop_score numbers it produces become the gate. No drift without Kaan re-signing.

**Anti-features (don't build):**
- **Real-time eval in production** — judge calls in the hot path = doubled cost, latency regression, and the judge itself becomes a slop source. Eval is an offline gate, not a live filter.
- **Multi-judge ensemble** — sounds rigorous, costs 3-5× per eval, adds variance without closing slop classes. One good judge with a tight rubric beats three mediocre judges.
- **Pretty dashboard for eval results** — Langfuse-style UI is engineering ego, not ship-value. Markdown report + CSV is enough. Build the dashboard only if Kaan asks for it.
- **Synthetic data generation** — "generate adversarial DJ sessions to test the gate" — synthetic audio sounds like AI slop, which is what we're trying to *not* be. Real session corpus only.
- **Gate "approval" via shipping rubrics from research papers (BLEU, ROUGE, semantic similarity)** — none of these measure "feels like a real DJ friend". They measure text overlap with a reference, which is the wrong primitive for live commentary.

**Complexity:** **L (Large, ~8-10 E-days)** — the harness scaffold exists, but: (a) golden-set labeling is 4-6 hours of Kaan focus, (b) judge prompt design + calibration iteration is 2-3 days, (c) CI wiring + report generation is 1-2 days, (d) per-detector F1 baseline establishment requires running against Kaan's full session corpus (recordings/ already accumulates these). Wall-clock dominated by golden-set labeling.

**v2.0 dependency:** P16 (deferred, fully replaces) + P17 detectors (scoring target) + P18 EvidenceRegistry (judge ground truth) + P19 AckBank (fallback to score) + P20 CitationLinter (preflight) + P22 anticipation (timing scoring) + `recordings/*/events.jsonl` (replay input) + `scripts/tune_detectors.py` (existing scaffold).

**Anti-slop watch:** The gate itself failing to detect slop. Pre-launch: hand-pick 5 known-slop reactions from past sessions (Kaan flags them), confirm judge rates them as slop. If judge misses 1 of 5, the rubric is wrong — fix before locking threshold.

---

## Feature 2: Embedding-Based Music Library Intelligence v1

**Reference products:**
- **Algoriddim djay Pro AI Neural Mix** — uses ML for stem separation in real-time; the closest "AI inside the DJ app" reference. Doesn't do embedding-based vibe search — it's stem-focused. ([Algoriddim djay](https://www.algoriddim.com/), [Neural Mix Pro](https://www.algoriddim.com/neural-mix-pro))
- **rekordbox 7 Cloud Library + SMART CUE** — auto-playlists by BPM/key/genre/artist; "find similar tracks" feature; AI vocal-position detection. Closest competitor for library intelligence in DJ tooling. ([rekordbox](https://rekordbox.com/en/feature/overview/))
- **Spotify DJ / Spotify-rekordbox integration** — AI-curated streaming queue; doesn't expose the embedding surface to user. ([Spotify in rekordbox](https://rekordbox.com/en/2025/09/rekordbox-for-mac-win-spotify-support/))
- **Mixed In Key** — Camelot-key based harmonic mixing; the table-stakes "key-aware library" pattern. ([Mixed In Key Harmonic Mixing Guide](https://mixedinkey.com/harmonic-mixing-guide/))
- **Bravoh's `app/services/embedding/service.py`** — 80% portable internal reference; Gemini Embedding 2 + L2-norm + pydub MP3 transcode + tenacity retry.

**Table stakes (must include):**
- **Rekordbox XML import** — already shipped in v2.0 (`RekordboxLibrary` Phase 25). v2.1 wires the orphaned `EvidenceRegistry.register_library` call so imported tracks become citation-eligible.
- **Embedding pipeline** — Gemini Embedding 2 (`gemini-embedding-2-preview`), 1536-dim, drop-chunk (60s peak) + breakdown-chunk (30s low) + centroid storage. ~$0.0144/track paid, free tier covers most users.
- **Local vector store** — sqlite-vec (7.6k stars, embedded, pip wheels Mac/Win); no Qdrant/Chroma server. One file on disk, ships with the Tauri sidecar.
- **"What's playing" grounding** — live 60s window of the master output gets embedded → kNN against library → top-1 if cosine ≥0.85 becomes the `[track:<id>]` evidence source. Closes the "Gemini guesses the track name" hallucination class.
- **Drag-drop import UI** — Settings → Library tab. Drop `collection.xml`, progress bar, "N tracks indexed, M failed." Phase 25 status: `human_needed` (LIBRARY-05). v2.1 ships the UI.
- **30-day staleness nudge** — `last_indexed` timestamp; if >30 days, in-app nudge "your library may be out of date, re-import?" Phase 25 LIBRARY-06.

**Differentiators (vibemix angle):**
- **Citations grounded in user's own library** — `[track:Camelot_8A→9A]` only emits if the track is *actually* in the user's imported library. No competing AI-for-DJ tool has this contract. Gemini can't hallucinate a track that's not in the registry.
- **Vibe search in plain English** — "show me my dark deep house tracks at 124 BPM" — Gemini Embedding 2 text query → kNN against library audio embeddings → results sorted by similarity, filtered by BPM/key metadata. Differentiator vs rekordbox's metadata-only filter.
- **No streaming-service lock-in** — works with the DJ's local files (m4a/aac transcoded via pydub at ingest). Rekordbox + Serato both push toward proprietary cloud sync; vibemix stays local.
- **Free tier covers virtually every user** — Gemini free tier RPM/TPM allow ~100k embed/day; 30k tracks finishes overnight on the user's own key. No proxy budget bottleneck at indexing.

**Anti-features (don't build):**
- **"AI suggests your next track" prescriptive recommender** — slop-prone. Users have taste. The cohost can drop a *soft suggestion* ("your library has a 124 BPM Bm track three spots back") but never a prescription. The user is the artist; AI is the friend.
- **CLAP / OpenL3 / MERT bundled** — Kaan rejected explicitly (memory `feedback_no_clap_use_gemini_embedding`). Bundling 50-200MB ML model breaks one-click install budget.
- **Vector DB server (Qdrant, Chroma, Weaviate)** — breaks one-click install (separate service). sqlite-vec is enough at 30k tracks.
- **Full-track embedding** — Gemini Embedding 2 caps at 180s (empirically 80s). Two-chunk strategy beats sliding-window 3× cost.
- **Pre-embedded library shipped in binary** — copyright-toxic. Users embed their own.
- **Real-time library scanner running in background** — battery + thermal cost on Mac, breaks the "vibemix runs lightweight alongside djay Pro" UX. Watchdog file-watcher is fine; full re-scan is user-triggered.
- **AI-curated playlists / smart crates** — feature creep into rekordbox's domain. Stay focused on grounding, not library management.

**Complexity:** **L (Large, ~7-9 E-days)** — Bravoh pipeline is 80% portable (lifts to ~2 days), sqlite-vec wiring + drag-drop UI + indexing progress bar + 30-day nudge is ~3 days, "what's playing" live grounding loop + citation registry hook is ~2 days, tuning + edge cases (m4a transcode failures, 80s cap retries) is ~2 days.

**v2.0 dependency:** Phase 25 RekordboxLibrary (extends — wires the dormant `register_library` seam) + Phase 25 `LIBRARY-03/04/05/06` (the v2.0-deferred UI slot now ships) + Phase 5 proxy (embed-call budget) + Phase 18 EvidenceRegistry (citation registration).

**Anti-slop watch:** "Vibe search" returning generic results because the embedding is dominated by drum patterns, not vibe. Mitigation: tune the chunk strategy with Kaan's library — verify "dark deep house" query returns dark deep house, not "any 120 BPM 4/4." If it fails, fall back to metadata-prefilter + embedding-rerank.

---

## Feature 3: Post-Session DJ Coaching Debrief UI

**Reference products:**
- **Strava activity recap** — chaptered card (map, splits, segments, kudos); each segment clickable, scrubs to map; ~30-90s read budget. The canonical "linear narrative with embedded metrics + interactive scrub" pattern. ([Strava Built for Mars](https://builtformars.com/case-studies/strava))
- **Whoop daily/monthly recovery report** — auto-detected, no user tagging; built on the trust that the system "saw" everything. ([Whoop UX eval](https://everydayindustries.com/whoop-wearable-health-fitness-user-experience-evaluation/))
- **HUDL Technique (formerly Coach's Eye)** — post-session video review for athletes; slow-mo + telestration + side-by-side comparison. Post-session-only model (not live coaching). ([Hudl Technique on golf](https://forum.practical-golf.com/t/hudl-technique-video-recording-app/805))
- **Synthesia (piano)** — replay-with-event-overlay; per-note scoring. ([Synthesia knowledge base](https://tools.aiformusic.org/knowledgebase/articles/synthesia-interactive-midi-based-piano-learning-and-practice-software))
- **rekordbox HISTORY tab** — flat list of played tracks per session; minimal — no critique, no chapters. The baseline DJ-software bar. ([rekordbox History tutorial](https://www.deejayplaza.com/en/articles/rekordbox-history))
- **Serato History panel** — adds play-time + deck per track. Slightly ahead of rekordbox; still no AI critique. ([Serato History](https://support.serato.com/hc/en-us/articles/223455687-History))

**Table stakes (must include):**
- **Auto-detected session boundaries** — open vibemix, hit play on djay Pro, AI tracks start/end of session from audio activity. No "tag your session" friction. (Whoop pattern.)
- **Chaptered review** — session split into ~5-10 chapters by phase change / track change / key event. Each chapter = title + 1-2 sentence critique + scrub-to-timestamp button. (Strava pattern.)
- **Clickable timeline** — horizontal timeline at top of debrief; click any event marker, scrubs the recorded `input.wav` + opens the corresponding chapter card.
- **60-90s voiced TL;DR** — Gemini TTS reads the executive summary (~150 words); plays at top of debrief; skippable.
- **3 drills for next session** — concrete prescriptions ("next session, pre-cue your reentry into a 4-bar phrase, not 2"). Capped at 3 — research-grounded (deliberate practice, ZPD scoped).
- **Citation-grounded critique** — every chapter card cites `[ev:KICK_SWAP@04:22]` / `[aud:peak_rms@04:22]` / `[track:<id>]`. Hover or tap citation = scrubs `input.wav` to that timestamp. Inherits Phase 20 citation linter wholesale.
- **Beginner / Intermediate / Pro skill-lens** — same session generates different critique based on user-level dial. Beginner = mechanical (beatmatch drift); Intermediate = phrasing + harmonic; Pro = micro-craft + arc.

**Differentiators (vibemix angle):**
- **First AI-grounded DJ debrief on the market** — every product surveyed (rekordbox History, Serato History, Mixed In Key) shows a *list of tracks*; none generates critique. vibemix turns the recording into a coach.
- **SBI + STAR-AR framing, not feedback sandwich** — research-backed (Radical Candor, Faculty Focus). "At 04:22 (situation), you mixed in over the breakdown of the outgoing track (behavior), which killed the build (impact). Next time, hold the incoming until the phrase boundary." Specific, cited, prescriptive.
- **No streaks, no gamification, no "Pro Tips of the Week"** — Pro DJs read patronising gamification as slop instantly. The debrief is a coach's note, not a Duolingo lesson.
- **Audio scrub on every citation** — Synthesia's "replay with overlay" pattern lifted to audio-first. The chapter card says "your filter sweep clipped the bass" → tap → hear it.
- **Bare-minimum surface, deliberate** — chapter cards + scrub + TL;DR + 3 drills. NOT a metrics dashboard. NOT a leaderboard. The temptation to ship 30 charts is the slop trap.

**Anti-features (don't build):**
- **Metrics dashboard with charts of "energy curve" / "harmonic balance"** — Garmin Connect old-school; high bounce, low learning value. Linear narrative beats charts.
- **Social/share/leaderboard hooks** — Bravoh's domain. vibemix's debrief is private. (Could expose "share TL;DR clip to Instagram" as a one-button v2.2 stretch — but not v2.1.)
- **Per-track scoring (✓/✗)** — DJ-ing is performative, not "correct/incorrect" (per memory `feedback_no_scope_creep_clean_utility` + bucket E research). Critique, don't score.
- **Long-form voiced playback** — users bail by minute 2. Voiced TL;DR is 60-90s cap; the rest is skimmable cards.
- **Interactive Q&A ("ask the coach about your set")** — turns debrief into a chat. Out of scope for v2.1. Single Gemini call generates the whole debrief; user reads it.
- **Cross-session aggregate ("you've improved 12% on harmonic mixing this month")** — fake-metric trap. Tendencies feed into the long-term profile (Feature 7), not "scores."
- **Auto-tagged "this transition was Train Wreck Level 3"** — slop labeling. Cite the event, name the failure mode, prescribe the fix. No badge system.

**Complexity:** **L (Large, ~8-10 E-days)** — DEBRIEF architectural slot exists in v2.0 (sidecar `--debrief` + port 8766 + 3 IPC schemas). UI is ~4-5 days (chaptered cards + timeline scrubber + TTS player). Single Gemini call orchestration + citation routing is ~2 days. Skill-lens prompt variants × 3 modes is ~1 day. Tying drills to next-session prompt is ~1 day. Edge cases (sessions <2min, missing events.jsonl, multi-day sessions) is ~1 day.

**v2.0 dependency:** Phase 25 DEBRIEF slot (the entire architectural skeleton — IPC + sidecar flag + port) + Phase 14 settings drawer (debrief lives there or in a new top-level tab) + Phase 15 recording browser (entry point: open recording → "view debrief") + Phase 20 citation linter (citations in debrief output) + Phase 18 EvidenceRegistry (resolve citations to timestamps).

**Anti-slop watch:** Gemini generating generic critique ("good energy, nice transitions") that cites nothing. Mitigation: linter strips uncited sentences in debrief mode (already designed in Phase 20). If too much gets stripped, debrief is short — fine. Short + cited beats long + generic.

---

## Feature 4: 4-Layer Mascot Full Additive State Machine

**Reference products:**
- **Live2D Cubism** — industry standard for VTuber 2D animation; expressions are layered blendshape combos. ([Live2D Cubism](https://www.live2d.com/en/cubism/about/))
- **Warudo** — 3D ARKit-blendshape-driven VTuber tool; expressions on layers (BlendShapeClips on layer 0, custom on layer 1+). The closest layered-3D reference. ([Warudo Character docs](https://docs.warudo.app/docs/assets/character))
- **VTube Studio** — 2D platform; fixed catalog of hotkey expressions (15-30 per model); LLM-plugin selects hotkey based on message content. ([VTubeStudio plugins](https://github.com/DenchiSoft/VTubeStudio/wiki/Plugins))
- **Open-LLM-VTuber** — closest existing analogue to vibemix (Live2D + LLM voice loop); inline emotion tags in LLM response, mapped via `emotionMap` config. ([Open-LLM-VTuber](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber))
- **Three.js AnimationMixer** — native multi-action additive blending + weight + crossFadeTo; the engine vibemix runs on. ([three.js AnimationMixer](https://threejs.org/docs/pages/AnimationMixer.html))

**Table stakes (must include):**
- **4 layers running simultaneously** — Mood (base, continuous), Anticipation (prep_*, fires on detect), Reaction (react_*, fires on Gemini reply), Effect (one-shot particles/flashes). Three.js handles natively via `AnimationAction.weight` + `additive = true`. Phase 22 already shipped the AdditiveLayer + 5 `prep_*` stubs.
- **Priority stack with cancel-aware crossfades** — higher-priority action pre-empts lower; crossFadeTo at 250-300ms hides the seam. Phase 22 already shipped cancel-aware fades.
- **Bone-subset additive overlays** — Reaction layer applies to upper body only; Mood layer keeps breathing/idle alive on lower body. Avoids "freezes mid-reaction" tell that screams "scripted."
- **Beat-coupled procedural idle bob** — Mood layer runs continuously, weighted by RMS + BPM from the WS bus (existing 30Hz feed). NO new asset needed; modulates existing idle clip.
- **Inline emote tag vocabulary** — Gemini text response tagged with `[emote:hyped]` / `[emote:settle]` / `[emote:focused]`; vibemix strips tags before TTS, routes to corresponding Reaction clip. Open-LLM-VTuber pattern.
- **Cancel cascades** — when Phase 19 `CancelGate` fires (interrupt + refire), Reaction layer crossfades back to Mood, Anticipation resets to neutral, Effect cancels. No "stuck" pose after a cancel.

**Differentiators (vibemix angle):**
- **Anticipation fires BEFORE Gemini responds** — Phase 22 already proved the pattern. v2.1 completes the full set: 5 prep clips (head turn, lean-in hyped, settle, lean-in neutral, freeze-shocked) tied to event class. The mascot moves at T=0; voice arrives at T=400-1200ms. Masks the LLM round-trip without hallucinating.
- **Mascot is a literal output of grounding** — every Reaction layer fire traces to a cited event (the same `[ev:...]` Gemini uses). The mascot is the "visible part" of the anti-slop contract — what the system saw, made visible.
- **Real VTuber-grade rig, not webapp-decoration** — per memory `project_mascot_as_vtuber_personality_surface`. Single character ("DJ bat" placeholder), Meshy/Hunyuan3D + Mixamo auto-rig, Three.js render. Feature 12 ships the actual rig.
- **Beat-locked, BPM-aware** — bob amplitude scales with kick RMS; bob frequency locks to detected BPM. The mascot is "in the pocket" with the music. No other VTuber tool does this — they sync to voice activity, not to the music the user is mixing.

**Anti-features (don't build):**
- **Procedural mouth shape / ARKit visemes** — Mixamo stopped exporting blendshapes in 2020; current rig has none. Adding visemes = re-rig the model = 2-3 week side quest + uncanny-valley risk. **Recommendation: 3 amplitude-banded talk clips (talk_calm / talk_normal / talk_energetic) modulated by TTS RMS** — 80% of the "alive mouth" feel at 10% the cost (per Bucket D research).
- **Multi-character mascot system** — per memory: SINGLE VTuber character. No team of characters. No selectable mascots in v2.1 (memory: `/hatch` user-gen is v2.x stretch).
- **Procedural eye-tracking on the user's webcam** — uncanny-valley trap; webcam permission ask is heavy; doesn't ground anything. Mascot looks at the music, not the user.
- **Mascot-as-feedback-form** ("did this reaction feel real? 👍/👎") — turns mascot from companion into instrument. The mascot is alive, not a survey.
- **30+ emote vocabulary** — Open-LLM-VTuber caps at 15-30 typically. vibemix targets 8-12: idle / hyped / settled / focused / surprised / shocked / dancing / zipped. Each one named, each one cited from an event class.
- **Mascot speaking lip-sync via TTS phoneme alignment** — Gemini TTS doesn't expose phonemes. Don't fake it; the amplitude-banded talk variants are the right answer.

**Complexity:** **M (Medium, ~5-7 E-days)** — Phase 22 shipped the additive subset (AdditiveLayer + 5 prep_* stubs + cancel-aware crossfade + 30Hz ws_bus). v2.1 adds: full 4-layer composition (~1 day), bone-subset additive (~1-2 days), inline emote tag parser + vocabulary (~1-2 days), beat-coupled procedural bob (~1 day), 3 amplitude-banded talk variants tied to TTS RMS (~1 day).

**v2.0 dependency:** Phase 22 simplified subset (extends — full state machine replaces the simplified subset) + Phase 19 CancelGate (cancel-aware crossfades) + Phase 17 EventDetector (anticipation triggers) + Phase 20 citation linter output (emote-tag stripping pipeline parallels) + Three.js renderer in Tauri webview.

**Anti-slop watch:** Reaction-layer clip firing when no real event happened (mascot "hyped" during silence). Mitigation: every Reaction fire is gated by the EventDetector having actually emitted an event in the last N ms. No event → mascot stays in Mood. This is the visual equivalent of the citation linter.

---

## Feature 5: One-Click Install + Auto-Permission Grant

**Reference products:**
- **Loom** — onboarding wizard requests camera + microphone + screen-recording in sequence; "allow each, click Continue." Industry-standard pattern. ([Loom Mac permissions](https://support.atlassian.com/loom/kb/mac-app-installation-reset-accessibility-permission/))
- **Raycast** — wizard requests Accessibility on first launch; further permissions on-demand when commands are run. ([Raycast onboarding](https://medium.com/@b6pzeusbc54tvhw5jgpyw8pwz2x6gs/using-raycast-001-introduction-installation-9dd58eea8836))
- **Notion / Linear / Cron** — minimal-permission desktop apps; demonstrate "look, we only ask for what we need" trust signal.
- **Tauri v2 installer guides** — DMG + notarized .app for Mac; MSI/NSIS for Windows; supports `externalBin` sidecar bundling with `TAURI_SKIP_SIDECAR_SIGNATURE_CHECK` for dev (do NOT skip in prod). ([Tauri Windows](https://v2.tauri.app/distribute/windows-installer/), [Tauri macOS signing](https://v2.tauri.app/distribute/sign/macos/))

**Table stakes (must include):**
- **Mac: signed + notarized DMG** — Apple Developer ID Application certificate, hardened runtime entitlements, `xcrun notarytool submit` + `stapler staple`. Phase 21 scaffold exists; v2.1 completes (Apple Developer Agreement = Francesco-pending external).
- **Windows: signed MSI/NSIS** — SignPath OSS sponsorship (free for open source); Phase 21 scaffold exists; v2.1 completes (SignPath OSS app pending ~1 week SLA).
- **Mac TCC pre-grant wizard** — first launch: 3 permissions to request in order: Microphone (for mic gating), Screen Recording (for djay window capture), Accessibility (for djay AX bridge). Each one: explain *why* in one sentence, button → triggers system prompt. Phase 14 wizard exists for v0.1.0 scope; v2.1 hardens.
- **Windows: UAC + Defender SmartScreen pre-empt** — code-signed binary clears SmartScreen automatically once trust is established; first few users may see the "unrecognized publisher" prompt — README addresses this with a screenshot.
- **Auto-detect BlackHole / virtual audio device** — if absent, in-app prompt with one-click `brew install blackhole-2ch` (Mac) or VB-Audio CABLE auto-fetcher (Windows). No manual terminal step.
- **nowplaying-cli auto-fetch** — Mac dependency; `brew install nowplaying-cli` triggered from app if absent. Detected on first launch.
- **Sidecar Python interpreter bundled** — `pyinstaller`-frozen 3.12 venv inside the Tauri bundle. User doesn't install Python. Phase 21 release.yml has the scaffold; v2.1 verifies fresh-VM end-to-end.
- **Fresh-VM rehearsal** — Phase 26 Wave 3 (deferred to Kaan in v2.0). v2.1 executes: fresh macOS VM + fresh Windows 11 VM, clean install path tested top-to-bottom, video captured.

**Differentiators (vibemix angle):**
- **"Icon tap → ready to mix" zero-friction onboarding** — most AI desktop apps require API key entry, model download, or external service signup. vibemix: download → install → permissions wizard → calibration → "go." Sub-60s clone-to-running (memory: `project_one_click_install_hard_req`).
- **"Why we need this" inline explanation** — most permission flows are "Allow microphone access" with no context. vibemix's wizard: "Microphone — so we can tell when YOU talk and shut up while you do." Trust signal + scope-narrowing.
- **No API key entry, ever** — Bravoh-side proxy handles Gemini API; user never sees a key. Removes the #1 friction point of every other AI desktop tool (Ollama, LM Studio, Continue.dev all require user to wire keys).
- **Calibration wizard finds the audio device** — Phase 14 shipped this; v2.1 verifies it works on fresh hardware. No "select BlackHole 2ch from the dropdown" — vibemix finds it.

**Anti-features (don't build):**
- **Bundled Homebrew installation** — too aggressive (manages user's whole package state). Detect + prompt with the one-line command + a "copy to clipboard" button; user clicks.
- **Bundled BlackHole installer payload (without consent)** — kext signing is fraught; BlackHole upstream handles the kext path; vibemix's job is to detect + prompt, not bundle.
- **Auto-grant permissions via TCC database manipulation** — security violation, breaks notarization, users hate it. Use the official prompt flow.
- **"Sign in with Google / Apple" for analytics opt-in** — adds account friction. Telemetry consent is a single checkbox in Settings, default OFF.
- **Always-on auto-update** — Sparkle/Squirrel-style; security-positive but breaks the "OSS, build-from-source" promise. Manual `vibemix upgrade` CLI + in-app "new version available" banner.
- **Linux installer path** — explicitly out of scope (memory + PROJECT.md).
- **"Run on startup" default-on** — invasive; user enables in Settings.

**Complexity:** **M (Medium, ~5-7 E-days)** — Phase 21 scaffold + Phase 14 wizard exist. v2.1 work: (a) complete signing once Apple/SignPath approvals land (~1 day each, blocking-external), (b) TCC pre-grant wizard polish (~1-2 days), (c) BlackHole auto-detect + one-click brew prompt (~1 day), (d) sidecar bundle verification on fresh VM (~1-2 days), (e) Windows WASAPI loopback auto-detect (~1-2 days, possibly more if API quirks).

**v2.0 dependency:** Phase 21 release matrix (extends — signing + notarization completes) + Phase 14 calibration wizard (extends — TCC wizard polish) + Phase 26 Wave 3 Fresh-VM rehearsals (executes the deferred work) + Tauri sidecar bundle.

**Anti-slop watch:** Permission wizard saying "we need microphone access to listen to your set" without explaining the mic gating. Clarity matters — wizard copy is a slop-vector. Run it past Kaan + Francesco; if it reads patronising or vague, rewrite.

---

## Feature 6: Open-Source Security Pass for Desktop AI Apps

**Reference products:**
- **Ollama** — MIT-licensed; recently hit by Out-of-Bounds Read CVE (2026-05); 175k Ollama servers exposed publicly (2026-01). Cautionary tale on default-bind. ([Ollama security](https://thehackernews.com/2026/05/ollama-out-of-bounds-read-vulnerability.html), [Exposed servers](https://thehackernews.com/2026/01/researchers-find-175000-publicly.html))
- **LM Studio** — visual local-LLM runner; ships with HF model index; doesn't bundle secrets (user brings own model files).
- **Cursor** — IDE with embedded AI; backend-routed requests (user doesn't see API key); `.cursorignore` for file exclusion. Pattern for "key never leaves server." ([Cursor local model setup](https://forum.cursor.com/t/ollama-lm-studio-support/5130))
- **Continue.dev** — open-source VS Code extension; user-provided keys; `.continueignore` for exclusion.
- **Codeium / Tabby** — self-hosted-friendly; emphasize "code never leaves your box." Trust-via-transparency.

**Table stakes (must include):**
- **No raw API keys in distributed binary** — Bravoh-side proxy with per-client rate limit; client gets an anonymous client_id + a signed token, not a raw Gemini key. Already designed (memory + constraint). v2.1 audits actual binary for accidental key leak.
- **`SECURITY.md`** — disclosure policy, vulnerability report email, expected response time. Table-stakes OSS hygiene; PROJECT.md already lists this in Active.
- **Secret scanner CI** — `gitleaks` / `trufflehog` on every commit; CI fails if a secret is committed. Catches accidental key paste.
- **Dependency CVE audit** — `pip-audit` + `cargo audit` + `npm audit` (for the Tauri renderer) running in CI; fails on HIGH/CRITICAL.
- **Signed binary verification** — Mac: stapled notarization ticket; Windows: SignPath signature; verifiable via `codesign --verify -v` + `Get-AuthenticodeSignature`. Phase 21 scaffold; v2.1 verifies live binaries.
- **Telemetry consent UX** — single Settings checkbox, default OFF, plain-English "what we collect, what we don't." If ON: anonymous session counts + crash reports only. NO prompt content. NO audio. NO MIDI. NO citations.
- **Permission least-scope** — Mac TCC: Mic + Screen Recording + Accessibility — not Camera, not Full Disk Access. README explains why each.
- **Threat model in SECURITY.md** — 4-5 named threats: key exfiltration (proxy), audio exfiltration (local-only), supply-chain (signed releases), MITM on proxy (TLS), session recording leak (Mac TCC + local-only).

**Differentiators (vibemix angle):**
- **Audio + MIDI + screen never leaves the user's machine** — except for Gemini API calls. Gemini sees ~6-12s audio windows + screen JPEGs *only during reaction generation*. This is the v2.1 SECURITY.md headliner: "we send what we need to react, nothing else."
- **Bravoh-proxy is the only network egress** — no telemetry endpoint, no analytics SDK, no crashlytics. Crash reports (if telemetry consented) go through the same proxy.
- **Open-source code = auditable claim** — "we say audio doesn't leave your machine; here's the code where it doesn't leave your machine." Trust-via-transparency is the OSS unfair advantage.
- **Recording browser is opt-in deletion** — Phase 15 already ships retention sweep; v2.1 SECURITY.md highlights this. User's recordings are local + auto-pruned + manually deletable.

**Anti-features (don't build):**
- **Per-user OAuth flow for Gemini access** — friction kills virality (PROJECT.md explicit). Proxy with rate limit is the design.
- **Defender SmartScreen reputation submission service** — too operational; signing is enough to clear over time.
- **Bug-bounty program** — too early; OSS first wave gets 0-50 reports; manual triage via SECURITY.md email is enough.
- **SOC 2 / ISO certification** — irrelevant for free OSS desktop app; signals "enterprise" wrong.
- **End-to-end encryption of recordings** — recordings are local-only; user owns the disk; encryption-at-rest is the OS's job.
- **Automated dependency-bumping (Dependabot full auto-merge)** — breaks too often. Dependabot opens PRs; human reviews. Don't auto-merge AI deps.
- **PII/sensitive content classifier on outgoing prompts** — over-engineering; audio + screen of a DJ set has no PII surface. Don't bolt on a classifier the product doesn't need.

**Complexity:** **M (Medium, ~4-6 E-days)** — secret-scanner CI + dependency audit CI is ~1 day. SECURITY.md + threat model is ~1 day (writing-heavy, not engineering). Binary verification scripts are ~1 day. Telemetry consent UX (Settings checkbox + plain-English copy) is ~1 day. Proxy rate-limit verification (load test) is ~1 day (Day-Zero ops overlap).

**v2.0 dependency:** Phase 21 release matrix (signed-binary verification) + Bravoh-side proxy (rate-limit verification) + Phase 14 Settings drawer (telemetry consent checkbox) + Phase 15 recording browser (retention claim).

**Anti-slop watch:** SECURITY.md being marketing copy instead of substance. Every claim must be code-traceable. If "audio never leaves your machine except for Gemini calls" — link the file + line where Gemini calls happen. Reviewer-traceable, not marketing-prose.

---

## Feature 7: Long-Term DJ Profile (~2KB JSON, Session-Regenerated)

**Reference products:**
- **ChatGPT memory** — "always inject" model; every stored fact rides along on every prompt; growing memory bloat over time. ([ChatGPT memory analysis](https://simonwillison.net/2025/Sep/12/claude-memory/))
- **Claude memory** — "model decides" / tool-call retrieval; refers to raw conversation history only; no AI-summarized profile. ([Claude memory](https://support.claude.com/en/articles/11817273-use-claude-s-chat-search-and-memory-to-build-on-previous-context))
- **Cursor `.cursorrules` / Zed `.rules` / Claude `AGENTS.md`** — user-editable, scoped, legible text files; the canonical "developer-controlled profile" pattern. ([Memory architecture analysis](https://manthanguptaa.in/posts/memory_is_a_mistake/))
- **Pi.ai memory** — short-form summarization; warm-conversation reference (limited public docs).
- **character.ai memory** — implicit world-state in long character sessions.

**Table stakes (must include):**
- **Structured JSON, ~2KB cap** — fields: `user_level` (Beg/Int/Pro), `preferred_genres` (top 3), `tendencies` (8-12 short prose lines: "tends to mix in early on phrase 5 instead of 1", "consistent harmonic mixing", "favors filter sweeps over EQ kills"), `drills_outstanding` (3 from last debrief), `last_updated`.
- **Regenerated each session post-debrief** — single Gemini call: feed last 5 sessions' debrief outputs → emit new JSON. Idempotent, overwriting. No append-only growth.
- **Injected verbatim into next session's prompt** — system prompt section: "Your DJ's profile: <JSON>". Gemini reads, doesn't re-emit. 2KB ≈ 500 tokens; fits comfortably in caching prefix (Phase 19 1024-token floor).
- **User-editable + viewable** — Settings → Profile tab shows the JSON in a readable rendered form ("Your style:" sections); user can edit / remove tendencies they disagree with. Cursor `.cursorrules` legibility.
- **Privacy-respectful** — JSON stored locally only; never sent except as part of the system prompt (which goes through Bravoh proxy → Gemini); user can delete with one button.

**Differentiators (vibemix angle):**
- **NOT a vector DB / mem0 / retrieval system** — Kaan rejected explicitly (memory + Bucket E research). DJ tendencies fit in a tweet, not a search index. Vector retrieval over 30 past sessions is the wrong primitive.
- **"Always inject" model, like ChatGPT, NOT "model decides," like Claude** — for live reaction, the LLM doesn't have time to decide to retrieve. The profile lives in the cached system-prompt prefix; it's free.
- **8-12 cap is brutal — forces summarization quality** — Gemini gets only 12 slots; the regeneration prompt forces "the 12 most-load-bearing observations about this DJ." No bloat. No drift. (Bucket E research.)
- **First DJ tool that learns the DJ's style across sessions** — rekordbox + Serato have History; neither produces a learned profile. The next-session "I noticed you tend to..." opening line is a "wait, it remembers?" moment.
- **Tied to drills from last debrief** — debrief prescribes 3 drills (Feature 3); profile carries them forward; next session's prompt knows the drill targets; mascot anticipation could even fire on "you nailed the drill" moments.

**Anti-features (don't build):**
- **Vector DB / Qdrant / Chroma / mem0** — breaks one-click install (separate service); wrong primitive (per Bucket E).
- **Append-only growth** — profile balloons over weeks. Cap at 2KB; older tendencies fade out.
- **Cross-user profile sharing** — privacy nightmare, not useful (every DJ's style is personal).
- **Auto-shared "your profile" leaderboard** — Bravoh's domain; vibemix profile is private.
- **AI-generated nicknames or "style names"** ("you're a Deep House Dreamer") — slop trap, patronising. Tendencies are observations, not labels.
- **Profile editing UI with rich text / sliders / per-tendency confidence** — over-engineering. JSON view + delete-line + "regenerate from sessions" button is enough.
- **Profile injected as multi-turn history** — wastes context window. Single system-prompt block; cached. (Phase 19 cache benefits.)

**Complexity:** **S (Small, ~3-4 E-days)** — JSON schema + storage + Settings view = ~1 day. Regeneration prompt + post-debrief hook = ~1 day. Live-session prompt injection = ~0.5 day. User-edit UI + delete button = ~1 day. Edge cases (first-ever session no profile, 2KB cap trim, JSON parse error fallback) = ~0.5 day.

**v2.0 dependency:** Phase 25 DEBRIEF slot (regeneration hook is post-debrief) + Phase 10 prompt matrix (injection point) + Phase 14 Settings drawer (user-edit UI) + VoiceRecorder events.jsonl (source data for first-ever profile).

**Anti-slop watch:** Profile tendencies being generic ("good DJ"). Mitigation: regeneration prompt explicitly requires each tendency to cite ≥2 sessions; un-cited tendencies are stripped (Phase 20 linter pattern lifts). User reads the profile; if it's vague, they delete the line.

---

## Feature 8: Autonomous Demo Film Generation

**Reference products:**
- **Loom AI screen recorder** — auto-generates titles + chapters + summaries from screen capture + voice. ([Loom AI](https://www.loom.com/products/ai-screen-recorder))
- **Descript** — record screen + AI co-editor "Underlord" edits + adds voiceover from plain-text instructions. ([Descript Video Editing](https://www.descript.com/video-editing))
- **Tella** — 30+ layouts, post-prod-free recordings ready for share.
- **DemoPolish** — upload screen recording → AI rewrites narration + adds professional voiceover in ~60s. ([DemoPolish](https://demopolish.com/alternatives/loom/))
- **Vibrantsnap** — auto silence-removal + smart zoom on cursor + auto-captions. ([Loom alternatives](https://www.vibrantsnap.com/blog/10-alternatives-to-loom))
- **RunwayML / Pika** — generative AI video (not screen-based; for B-roll).

**Table stakes (must include):**
- **Screen capture pipeline** — Phase 24 djay overlay + Phase 22 mascot canvas + Phase 14 vibemix UI all renderable; macOS `ScreenCaptureKit` or sidecar `ffmpeg` capture at 30 fps. Already used in v2.0 demo storyboard mocks (`mocks/vibemix-cinematic-storyboard.html`).
- **Real DJ session as source material** — NOT synthetic. Per Core Value: "real reactions, no AI slop." Kaan or Francesco DJs a 60-90s segment; vibemix records audio + screen + mascot; demo film cuts FROM that recording.
- **Auto-edit pass** — silence removal (drop dead air between reactions), smart zoom on djay UI when Phase 24 overlay fires, mascot crop-in when anticipation lean-in fires, captions for the AI's voice line.
- **30s target cut** — synthesis-viral-demo.md storyboard already specifies the 3-beat structure: Beat A (djay overlay amber ring + AI calls the mids), Beat B (mascot anticipation lean-in BEFORE voice arrives), Beat C (anti-slop silence beat at 0:22-0:25).
- **AI voiceover for narration on top of the DJ audio** — Gemini TTS (Achird voice) reads a short narrator track ("this is vibemix. it listens. it sees. it reacts in-bar") over the music intro/outro.
- **4-channel export** — 9:16 (IG Reels / TikTok), 16:9 (X / YouTube), 1:1 (X profile), 4:5 (Instagram feed). All from one master cut.

**Differentiators (vibemix angle):**
- **Anti-slop tax in the demo** — most AI-product demos are 100% scripted, every line rehearsed. vibemix's demo MUST showcase a *real* in-bar reaction to an unscripted moment. If the demo cuts feel scripted, the demo is slop. Beat C's silence (the AI not talking when it shouldn't) is the proof-of-grounding moment.
- **Citation overlay during demo** — small `[ev:KICK_SWAP@04:22]` text appears on screen as the AI speaks the line tied to it. Proves the citation contract live. No competing AI-demo does this; for vibemix's audience (developers + DJs) it's a credibility flex.
- **Mascot anticipation lean-in is the screenshot moment** — Beat B's lean-in BEFORE voice = "the AI is predictive, not reactive." This is the Twitter card.
- **One filmable take, three platforms** — the storyboard locks the 30s structure; the auto-edit picks the takes; no human editor needed for the master cut. Human approval gate before publishing.

**Anti-features (don't build):**
- **Fully AI-generated B-roll (Pika / Runway)** — synthetic video reads as slop; competes with the realness claim. Live screen capture only.
- **Voice cloning of Kaan or Francesco** — uncanny, ethical risk, defeats "Gemini TTS is the voice" claim. Use the Achird voice.
- **AI-generated music underscore** — there's already music (the DJ set). Don't double-stack.
- **"AI directed the entire shoot"** — false marketing. Auto-edit + auto-voiceover is honest; "AI directed the demo" is hype.
- **Auto-publishing to social platforms** — review gate is non-optional. AI generates the master cut + 4 platform variants + post drafts; human (Kaan + Francesco) approves before publish.
- **Multiple demo films generated, A/B-tested** — 30s is the one shot. A/B testing demos is post-launch optimization.
- **Bundled "make your own demo" feature shipped to users** — feature creep. The autonomous demo is for launch; user-generated demos are v2.x.

**Complexity:** **M (Medium, ~5-7 E-days)** — Phase 24 + Phase 22 already produce the screen-worthy beats. v2.1: (a) capture pipeline (ffmpeg / ScreenCaptureKit) + sync audio+screen+mascot = ~2 days, (b) auto-edit script (silence detection + zoom + captions) = ~2 days, (c) Gemini TTS narration generation + mix = ~1 day, (d) 4-channel export = ~1 day, (e) real session shoot + human review = ~1 day (Kaan+Francesco wall-clock).

**v2.0 dependency:** Phase 24 djay overlay (Beat A source) + Phase 22 mascot anticipation (Beat B source) + Phase 19 ack bank + silence beat (Beat C source) + Phase 26 viral post drafts (text-side of the wave) + `mocks/vibemix-cinematic-storyboard.html` (storyboard reference) + Phase 15 recording pipeline (source recordings).

**Anti-slop watch:** Auto-edit smoothing over the real reactions (cutting the natural pauses that make it feel alive). Mitigation: human review of the 30s master cut by Kaan + Francesco — they have the ear for "this feels alive" vs "this feels scripted." If it feels scripted, re-shoot, don't re-edit.

---

## Feature 9: Cross-Phase Integration Audit Gate

**Reference products:**
- **OpenObserve** — open-source observability platform; logs/metrics/traces unified. ([OpenObserve](https://openobserve.ai/))
- **Tracetest** — observability-driven development; test creation/run/view in one place; CNCF landscape. ([Tracetest](https://tracetest.io/learn/top-9-tools-for-observability-driven-development))
- **gsd-integration-checker (vibemix-internal)** — the v2.0 audit gate that produced `v2.0-MILESTONE-AUDIT.md`. Already proven on v2.0 — caught the `register_library` orphan.
- **Anthropic's three-tier eval** — rules-based + visual + LLM-as-judge — covers the "every seam validated" pattern from a different angle. ([Anthropic evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents))

**Table stakes (must include):**
- **`gsd-integration-checker` re-run for v2.1** — same auditor as v2.0; re-runs after every v2.1 phase + once at milestone close. Produces `v2.1-MILESTONE-AUDIT.md` with the same format.
- **Orphan-shipped surface inventory** — list every "method exists, no call sites" finding. v2.0 produced 1 (`register_library`); v2.1 target is 0.
- **Cross-phase wiring matrix** — same matrix as v2.0 audit. Every v2.1 phase declares its "from → to" connections; auditor verifies each is WIRED, not just DEFINED.
- **Source-level wiring tests** — for every cross-phase connection, a unit test that imports the call site and asserts the dependency is constructed and threaded. v2.0 has 1733 → 1961 such tests; v2.1 adds the new ones.
- **Pre-existing failure carry-forward** — v2.0 has 10 pre-existing test failures, all out-of-scope per phase verifications. v2.1 audit carries these forward, doesn't regress, opportunistically closes.
- **Anti-pattern scan** — `grep` for `TODO|FIXME|XXX|NotImplementedError|pass # TODO` across `src/`. v2.0 baseline: 20 TODO hits (mostly XML passthrough comments), 0 stubs. v2.1 target: don't regress.

**Differentiators (vibemix angle):**
- **Gate is itself code-traceable** — every audit claim cites a file + line. "WIRED" means a grep returns ≥1 call site. "DEFINED, NOT CALLED" means grep returns the def but no calls. Auditor's verdicts are reproducible.
- **Plan ladder tracking** — each phase has a Plan → Verification ladder; auditor checks every Plan is shipped or explicitly DEFERRED with rationale. v2.0 had 3 deferred Plans (15-04 + 16 entire phase + Wave 6-Discord) — all tracked.
- **Kaan-action surface roll-up** — the audit produces a criticality-ranked list of Kaan-actions (CRITICAL / HIGH / MEDIUM / LOW). v2.1 target: every CRITICAL closes autonomously (per `gsd-autonomous fully`); v2.0 had 3 CRITICAL items still open at milestone close.

**Anti-features (don't build):**
- **Live observability dashboard** (Grafana + Prometheus + Loki) — for a desktop app with single-user scope, this is over-engineering. CI + audit reports are enough.
- **Distributed tracing across the LiveKit pipeline** — debugging-time tool, not ship-time gate. Add only when bugs justify it.
- **Auto-fix orphans** — auditor is a checker, not a fixer. Human reads the report, decides if the orphan is a real gap or accepted tech debt.
- **External SaaS audit service** — auditor is `.planning/agents/gsd-integration-checker` (Claude-internal); no external dep.
- **Mandatory 100% coverage / 100% wiring** — accepting one or two known-deferred items is fine. v2.0 had `CitationIpcShim` accepted-deferred to v2.x — same pattern.
- **Code-coverage gate (>80% line coverage)** — easy to game with worthless tests. Wiring + integration > coverage %.

**Complexity:** **S (Small, ~2-3 E-days)** — `gsd-integration-checker` already exists from v2.0 (proved itself by producing the audit). v2.1: (a) declare cross-phase wiring matrix per new phase as it ships (~10 min per phase), (b) auditor re-runs at milestone close (~30 min), (c) close any orphans found (varies — orphans should be rare since v2.1 explicitly closes v2.0's). The "feature" is mostly process, not engineering — but the process IS the close-out gate.

**v2.0 dependency:** ALL surfaces (extends every v2.0 phase) + `gsd-integration-checker` itself (the auditor agent) + `.planning/milestones/v2.0-MILESTONE-AUDIT.md` (template + baseline).

**Anti-slop watch:** Auditor declaring "PASS" on cosmetic check while missing a real gap. Mitigation: every audit run requires a sample-trace verification — pick 3 random REQ-IDs, manually trace from REQ → code path → test → run; if any fails, audit verdict is invalid. (v2.0 audit did this implicitly; v2.1 makes it explicit.)

---

## Feature 10: Day-Zero Ops Live

**Reference products:**
- **Ollama launch** — 171k stars over multi-year build; current MLX-on-Apple-Silicon news cycle still drives stars. ([Ollama Releases](https://github.com/ollama/ollama/releases))
- **Bun launch (2022)** — +20,000 stars in one month on Beta release; HN front page coordinated.
- **Tauri 1.5 / 2.0 launches** — blog post + release notes + Twitter/X push coordinated.
- **AFFiNE** — 1,000 stars in first month via Product Hunt + Reddit coordinated launch. ([AFFiNE playbook](https://dev.to/iris1031/how-to-get-more-github-stars-the-definitive-guide-33k-stars-case-study-11h8))
- **GitHub Trending mechanics** — concentrating distribution into a 48-hour window pushes to #1 Trending. ([Launch-Day Diffusion paper](https://arxiv.org/html/2511.04453v1))
- **Show HN + Product Hunt + Reddit + Twitter** — 4-channel simultaneous push is the canonical OSS launch pattern.

**Table stakes (must include):**
- **Discord server live** — Phase 26 Wave 6 deferred in v2.0. v2.1 provisions: server + 6-8 channels (#welcome / #help / #show-and-tell / #controller-mappings / #bug-reports / #releases / #off-topic) + auto-role bot (assign role on rules-accept) + welcome message. Roles: `dj`, `developer`, `early-adopter`. ([Discord autorole bots](https://github.com/topics/autorole))
- **15+ pre-seeded stars on Day 1** — Kaan + Francesco + Momo + Bravoh team + Bravoh closed-beta DJ contacts + dev-network friends. Coordinated message ~2 hours before public launch.
- **Proxy load test verified** — 100 RPS × 5 min, p99 < 500ms (per Phase 26 OPS-06 scaffold). Bravoh-proxy already exists; v2.1 actually runs the test, not just scripts it.
- **healthz endpoint live** — Bravoh-proxy `/healthz` returns 200 + JSON `{status, latency_ms, rate_limit_remaining}`. Status page or simple uptime monitor. Phase 26 OPS scaffold extends.
- **Launch trigger sequence** — T-30 / T+0 / T+5 / T+24h scripts ready: T-30 = warm DMs to seed list; T+0 = Show HN post + IG Reel + X thread + Reddit r/DJs/r/programming; T+5 = reply triage in Discord; T+24h = thank-you post + first-day metrics. Phase 26 scaffold; v2.1 finalizes.
- **Repository hygiene final pass** — README hero finalized (Phase 26), social preview image set, topics tagged (dj/livekit/gemini/ai-assistant/audio/midi), badges live, issue templates published, CONTRIBUTING / SECURITY / CODE_OF_CONDUCT / LICENSE present.

**Differentiators (vibemix angle):**
- **Day-Zero scripts are version-controlled, not memory** — Phase 26 already shipped `scripts/day-zero/*.sh` (or equivalent). v2.1: every "launch action" is a script + a rehearsed run. Less "did Kaan remember to post on Reddit" risk.
- **Bravoh + vibemix coordinated push** — vibemix isn't a solo launch. Bravoh's 140k-view Instagram + closed-beta DM list amplifies vibemix's launch wave. (PROJECT.md positions vibemix as the funnel toward Bravoh waitlist.)
- **DJ + Developer dual-audience** — every Show HN is dev-coded; every IG Reel is DJ-coded. Same product, two voices. Francesco runs the DJ side; Kaan runs the dev side.
- **First open-source AI-for-DJ tool at this quality** — competitive density is low (no Ollama-of-DJ-AI exists). The Show HN angle writes itself: "Show HN: vibemix — an AI DJ co-host that reacts to your set in real time, fully local, MIT, Gemini-only."

**Anti-features (don't build):**
- **Paid launch ads at scale** — budget is 150-200€ (PROJECT.md). 50€ on IG/TikTok, 100€ on X, rest as float. Not a 5-figure launch.
- **Influencer partnerships** — slow + expensive. Francesco's DJ network is the warm-channel; no paid sponsorships.
- **Pre-launch waitlist** — vibemix is download-immediate; no waitlist. (Funnel is Bravoh's waitlist, not vibemix's.)
- **Email-capture lead magnet on the repo** — repo is download-immediate. Email capture lives on the Bravoh-side post-download confirmation (Memory: "Email collector on download" is Active in PROJECT.md, scoped post-download not pre-).
- **Multi-day staggered launch ("soft launch Monday, hard launch Friday")** — concentrate into a 48-hour window; staggered loses GitHub Trending momentum.
- **AI-generated launch posts** — slop. Kaan + Francesco write the threads; AI assists drafting.
- **Discord paid moderator tier** — community is small Day-Zero; Kaan + Francesco + Momo moderate.

**Complexity:** **M (Medium, ~4-5 E-days)** — Discord provisioning + bot config = ~1 day. Pre-seeded star coordination (DMs + warm list) = ~1 day (mostly wall-clock). Proxy load test execution + result analysis = ~0.5 day. healthz endpoint live + simple uptime monitor (e.g., UptimeRobot free tier) = ~0.5 day. Repo hygiene final pass (badges + topics + social preview + issue templates) = ~1 day. Launch trigger script rehearsal = ~0.5 day. Some of this is wall-clock blocked on Bravoh team coordination.

**v2.0 dependency:** Phase 26 day-zero ops scaffold (extends — executes the deferred Wave 6/7) + Bravoh-side proxy (rate limit + healthz) + Phase 21 signed binaries (the artifact users download) + README + BRANDING.md (the front door).

**Anti-slop watch:** Show HN post that reads like marketing copy. Mitigation: Kaan writes it personally, dev voice, technical detail front-and-center, no superlatives, no "revolutionary." Lift tone from Bun / Ollama / Astro launch posts.

---

## Feature 11: Public RC Cut + Ship

**Reference products:**
- **Ollama release cadence** — every release tagged with detailed changelog, binaries linked, social push coordinated. ([Ollama Releases](https://github.com/ollama/ollama/releases))
- **Bun / Astro / Tauri release patterns** — blog post + GitHub release with binaries + Twitter announcement + Discord ping coordinated within ~1 hour.
- **GitHub release with assets** — DMG + MSI + SHA256 checksums + signatures + release notes.
- **Tauri's tauri-action GitHub workflow** — produces signed installers cross-platform in one CI run. ([Tauri Tutorial](https://tech-insider.org/tauri-tutorial-cross-platform-rust-app-2026/))

**Table stakes (must include):**
- **Signed binary tagged + GitHub release published** — `v0.2.0-rc1` (or `v1.0.0-rc1` if Kaan picks that semver). Signed DMG (Mac) + signed MSI (Windows) + SHA256 + release notes + signature verification command in description.
- **README hero finalized** — branded banner artwork, 30s demo film embedded, one-paragraph value prop, install buttons, feature matrix, controller grid, screenshots, FAQ, "Built by Bravoh" footer.
- **Social posts on 4 channels** — Show HN draft + X/Twitter thread + Instagram Reel + Reddit (`r/DJs`, `r/programming`, `r/MachineLearning`). All drafts in `marketing/posts/*.md` (Phase 26 already drafted; v2.1 finalizes).
- **Discord launch announcement** — Day 1 server welcome message + #releases pin.
- **Email coordination** — Kaan's dev-network DM list + Bravoh closed-beta opt-in list.
- **Tag + release-notes generation** — `git tag` + `gh release create` + auto-pulled changelog from `CHANGELOG.md`.

**Differentiators (vibemix angle):**
- **30s demo film embedded in release notes** — most OSS releases are text-only. vibemix's release notes lead with the cinematic demo (Feature 8) — the launch artifact and the marketing artifact are the same file.
- **Honest "RC" labeling** — `v0.2.0-rc1` is honest; `v1.0` is aspiration. Kaan decides at cut time. RC labeling signals "release candidate, please break it" — invites bug reports, sets expectation correctly. (Memory: there was a `v0.1.0-rc1` already; v2.1 lifts that promise.)
- **Bravoh-funnel footer** — README "Built by Bravoh" footer + link to Bravoh waitlist. Every star is a chance to convert.
- **Open-source first, no paid tier** — there is no paid tier for vibemix. The product is the funnel. Releasing without monetization is the differentiator (vs Cursor / Continue / Tabby / Codeium freemium walls).

**Anti-features (don't build):**
- **`v1.0.0` premature release** — if the autonomous hallucination gate (Feature 1) flags slop above threshold, don't ship as `v1.0`. RC labeling is the safety valve.
- **Auto-update bundled in the RC** — opt-in only; auto-update for an OSS desktop AI app needs more bake time. Manual upgrade + in-app banner is enough.
- **Cross-promo with another launching tool** — coordinated launches dilute attention; vibemix is solo on launch day.
- **Press embargo / pre-launch leaks to TechCrunch** — wrong audience (developers + DJs aren't reading TC about OSS); Show HN + Reddit + DJ-IG IS the press.
- **Localized launch (multi-language posts)** — English-only in v1 (PROJECT.md Out of Scope).

**Complexity:** **S (Small, ~2-3 E-days)** — most surfaces are wired (Phase 21 scaffold + Phase 26 drafts). v2.1 work: README hero finalize = ~1 day. Tag + release + binaries upload = ~0.5 day (CI does the heavy lift). Social posts finalize from drafts = ~0.5 day. Coordinated push timing rehearsal = ~0.5 day. Mostly cut-and-publish from already-staged artifacts.

**v2.0 dependency:** Phase 21 (signed binaries) + Phase 26 (drafts + README + day-zero scripts) + Feature 8 (demo film for release notes) + Feature 10 (day-zero ops infra) + Feature 5 (one-click install verified).

**Anti-slop watch:** Release notes being LLM-generated marketing slop ("introducing vibemix, the revolutionary AI DJ assistant"). Mitigation: release notes are Kaan-written, dev voice, what-changed-focused, no superlatives. Tone reference: Bun release notes, Astro release notes, Tauri release notes.

---

## Feature 12: Real GLB Mascot Animations Autonomously

**Reference products:**
- **Meshy** — text-to-3D model generator; quad-friendly outputs. (Industry standard 2026.)
- **Hunyuan3D** — Tencent's open-source text-to-3D model; high-quality mesh outputs.
- **Rodin Hyper3D** — competitive text-to-3D platform.
- **Mixamo** — Adobe's auto-rig + animation library; FBX export → GLB convert. The canonical auto-rig for indie 3D.
- **MASCOZ** — free 3D VTuber model maker. ([MASCOZ tutorial](https://www.youtube.com/watch?v=GRs4EKA0kTg))
- **Live3D VTuber Maker** — desktop VTuber mascot tool with rigged models. ([Live3D](https://live3d.io/tutorial/vtuber-maker-desktop-mascot))
- **`mcp__blender__*` MCP tools** — Blender automation available in vibemix's Claude environment.

**Table stakes (must include):**
- **Single VTuber-style 3D character** — per memory (`project_mascot_as_vtuber_personality_surface`). "DJ bat" placeholder; refined or replaced via Meshy/Hunyuan3D.
- **Mixamo-rigged base** — standard humanoid skeleton; compatible with Three.js's `SkinnedMesh`.
- **5 `prep_*` GLB animations** — `prep_head_turn`, `prep_lean_in_hyped`, `prep_settle`, `prep_lean_in_neutral`, `prep_freeze_shocked`. Phase 22 shipped 5 STUBS; v2.1 replaces with real animations.
- **8-12 react_* + dance_* clips** — `react_surprised`, `react_focused`, `dance_groove`, `dance_peak`, `idle_breathe`, `idle_sway`. Mix of Mixamo library + custom keyframes via Blender MCP.
- **Idle / breathing loop** — continuous Mood layer (Feature 4); ~3-5s loop with subtle chest rise + occasional weight shift.
- **GLB export pipeline** — Mixamo FBX → Blender GLB-export via MCP automation; consistent skeleton + bone names across all clips so Three.js's AnimationMixer can switch clips on the same SkinnedMesh.
- **Talk clip × 3 amplitude bands** — `talk_calm`, `talk_normal`, `talk_energetic`; modulated by Gemini TTS RMS in Feature 4.

**Differentiators (vibemix angle):**
- **Autonomously generated via Claude + Blender MCP** — per `gsd-autonomous fully` mode + Phase 12 MCP toolchain. No artist task. (Memory: artist task was the v2.0 stub-shipping path; v2.1 explicitly autonomizes via memory `feedback_autonomous_no_grey_area_pause`.)
- **Single placeholder character, identifiable as vibemix's mascot** — "DJ bat" name is placeholder; the brand decision is Kaan-driven, not Claude-driven. Claude ships a competent rig; Kaan vets the design.
- **Mascot rig is the brand surface** — VTuber-grade rendering quality is the bar (per memory). Decision boundary: if the rig looks indie-3D-cheap, it reads as AI slop. If it looks polished, it reads as a real character.
- **`/hatch` user-gen mascots = v2.x stretch** — explicitly out of v2.1 scope per memory.

**Anti-features (don't build):**
- **AI-generated 3D models without Blender cleanup pass** — Meshy/Hunyuan3D outputs need topology cleanup, UV checks, scale normalization. Auto-generate → manual sanity check via Blender MCP.
- **Multiple selectable characters** — v2.1 is single mascot. Selection-UI is feature creep.
- **Procedural facial animation / lipsync** — Mixamo trap (no blendshapes); Feature 4 anti-feature covers this.
- **Photorealistic mascot** — uncanny valley; CDJ-Whisper-aesthetic stays stylized + warm.
- **Animated cape / hair physics** — performance + dev-time cost; not worth it for v2.1.
- **Real-time generative animation (AI-driven motion)** — generative motion looks weird; keyframed clips with additive blending is the right plane.
- **Avatar customization (clothing, color)** — out of scope; single character.

**Complexity:** **M (Medium, ~5-7 E-days)** — Meshy/Hunyuan3D character generation + iteration to acceptable design = ~2 days (Kaan-vet loop). Mixamo auto-rig + animation library scrape (8-12 clips) = ~1 day. Blender MCP cleanup + GLB export pipeline + bone-name normalization = ~2 days. Three.js AnimationMixer integration verification = ~1 day. Talk-clip × 3 amplitude variants = ~1 day.

**v2.0 dependency:** Phase 22 prep_* stubs (REPLACES — Phase 22's stubs were byte-copied from Mixamo today; v2.1 ships the real ones) + Phase 22 AdditiveLayer + Three.js renderer in Tauri webview + `mcp__blender__*` MCP tools.

**Anti-slop watch:** Mascot animations looking janky / amateur. Mitigation: VTuber-grade is the bar. Decision-gate: if Kaan looks at it and the rig reads as "indie-3D-AI-slop," kick to a Bravoh-side artist as last resort. (This is one of the cases where memory `feedback_autonomous_no_grey_area_pause` applies — Claude continues, but flags as "needs Kaan visual sign-off.")

---

## Feature 13: 2 Hard Tek Detectors (DISTORTION_CLIMB + ACID_LINE_ENTRY)

**Reference products:**
- **`G-followup-1-hard-tek-dsp.md`** — vibemix internal research; 8 Hard Tek detectors locked with thresholds + reference tracks. v2.0 shipped 6 (`KICK_SWAP` etc.); v2.1 closes 2 (`DISTORTION_CLIMB` + `ACID_LINE_ENTRY`).
- **Roland TB-303 history** — acid-line signature (resonant filter sweep + saw + slide + accent on a 7-step pattern). Hardfloor "Acperience" + Josh Wink "Higher State of Consciousness" are canonical reference. ([TB-303 Wikipedia](https://en.wikipedia.org/wiki/Roland_TB-303))
- **Hard Tek genre — distortion as climb signature** — distortion is processing layer on the 303; "ride the drive" to build energy (sub-genre signature). ([Acid line processing](https://gearspace.com/board/electronic-music-instruments-and-electronic-music-production/878603-how-do-you-process-your-acid-lines.html))
- **librosa onset detection + spectral_centroid + spectral_flux** — the DSP primitives.

**Table stakes (must include):**
- **`DISTORTION_CLIMB` detector** — DSP signature: spectral centroid rising over 4-8 bars AND crest factor rising AND harmonic distortion (THD proxy) rising. Fires when all three trend up monotonically; cooldown 12s. Closes "AI says 'getting hyped' generically" — instead AI says "the distortion is climbing into the next phase."
- **`ACID_LINE_ENTRY` detector** — DSP signature: bandpass filter peak at 600-2500Hz with rapid resonance (envelope follower jitter) + 7/8-step pattern detection in the audio onset stream. Closes "AI says 'lead synth' when it's a 303 sweep" — Kaan's exact slop class.
- **Threshold tuning against reference tracks** — `scripts/tune_hard_tek_detectors.py` already exists (Phase 17). v2.1: feed 10-15 Hard Tek reference tracks (Kaan's collection), tune thresholds until detector fires match Kaan-labeled events.
- **GenreRouter slot** — both detectors slot into the Hard Tek genre roster via `GenreRouter` (Phase 17 atomic dispatch). No restructuring needed.
- **Citation grammar** — both fire `[ev:DISTORTION_CLIMB@<t>]` / `[ev:ACID_LINE_ENTRY@<t>]`; EvidenceRegistry registers them like every other event (Phase 18).

**Differentiators (vibemix angle):**
- **Hard Tek subculture wedge** — Kaan's primary genre + a high-engagement underground audience (memory: `project_phase_16_kaan_dj_testing`). DISTORTION_CLIMB + ACID_LINE_ENTRY signal "this AI knows Hard Tek, not just techno-genre." Hard Tek IG community is small but loud.
- **DSP-grounded, not vibes-based** — every other AI-music-tool says "energy rising"; vibemix names the actual signal change. Citation contract makes this auditable.
- **8-detector Hard Tek roster complete** — v2.0 shipped 6 cross-genre; v2.1 adds 2 Hard-Tek-specific. Per-genre detector dispatch (Phase 17 G-followup research) wins on specificity.

**Anti-features (don't build):**
- **20+ micro-detectors per sub-genre** — over-engineering; long tail of false positives.
- **Real-time generative DSP analysis (ML model on every frame)** — costs CPU + battery; classical DSP (centroid, flux, crest, THD-proxy) is enough.
- **"AI auto-detects which sub-sub-genre"** — slop trap; genre auto-detect is one-shot at session start (Phase 17 + Feature 2's library embedding does this).
- **Citing detector internals in user-facing reactions** ("the spectral centroid rose by 230 Hz over 4 bars") — too technical; user-facing reads "the distortion is climbing."
- **Universal across all genres** — these are explicitly Hard Tek slot detectors. House, techno, DnB don't fire them.

**Complexity:** **S (Small, ~3-4 E-days)** — Phase 17 GenreRouter + tuning harness already exist. DSP work: DISTORTION_CLIMB (~1 day, three-signal trend detection), ACID_LINE_ENTRY (~1.5 days, the 7-step pattern is the tricky part), threshold tuning against reference tracks (~1 day, Kaan-in-loop), tests + registry registration (~0.5 day).

**v2.0 dependency:** Phase 17 GenreRouter + EventDetector + Hard Tek genre roster (extends — adds 2 to the existing 6) + Phase 18 EvidenceRegistry (citation registration) + `scripts/tune_detectors.py` (tuning harness) + `G-followup-1-hard-tek-dsp.md` research (DSP recipe + reference tracks).

**Anti-slop watch:** False positives on tracks that aren't Hard Tek (e.g., DISTORTION_CLIMB firing on a deep house filter sweep). Mitigation: GenreRouter ensures these only fire when active genre = Hard Tek; tune threshold conservatively (prefer false-negative — miss a fire — over false-positive — fire wrong).

---

## Cross-Feature Dependencies

```
Feature 1 (Hallucination Gate)
    │
    ├─ scores Feature 4 (mascot timing)
    ├─ scores Feature 7 (profile-injected reactions)
    └─ scores Feature 13 (new detectors)

Feature 2 (Library Intelligence)
    │
    └─ feeds Feature 7 (profile cites tracks)
    └─ closes register_library orphan

Feature 3 (Debrief UI)
    │
    ├─ feeds Feature 7 (regeneration runs post-debrief)
    └─ docks into Feature 8 (debrief artifact can be filmed)

Feature 4 (4-layer mascot)
    │
    └─ requires Feature 12 (real GLBs)

Feature 5 (One-click install)
    │
    └─ requires Feature 6 (signing keys live)

Feature 8 (Demo film)
    │
    ├─ requires Feature 4 (anticipation lean-in for Beat B)
    ├─ requires Feature 12 (real mascot rig)
    └─ feeds Feature 11 (release notes embed)

Feature 9 (Audit gate)
    │
    └─ verifies ALL other features wired

Feature 10 (Day-Zero ops)
    │
    └─ requires Feature 6 (proxy load test)

Feature 11 (RC ship)
    │
    ├─ requires Feature 5 (install verified)
    ├─ requires Feature 6 (signed binary)
    ├─ requires Feature 8 (demo film)
    ├─ requires Feature 10 (ops live)
    └─ requires Feature 1 (gate passed)
```

**Phase-ordering implications:**

1. **Foundation tier (sequence first):** Feature 12 (real GLBs) → Feature 4 (4-layer mascot) → Feature 2 (library) → Feature 13 (2 detectors) → Feature 7 (profile). These extend v2.0 surfaces directly.
2. **Verification tier (after foundation):** Feature 1 (hallucination gate) — scores everything from foundation tier. Needs them in to be evaluable.
3. **UI tier (parallel-able):** Feature 3 (debrief UI) can run in parallel with foundation tier; depends on DEBRIEF slot from v2.0 only.
4. **Ship-prep tier (sequence last):** Feature 5 (install) → Feature 6 (security) → Feature 9 (audit gate) → Feature 8 (demo film) → Feature 10 (Day-Zero) → Feature 11 (RC ship).

The roadmapper decides Plan-ladder decomposition. This dep matrix is the input.

---

## MVP Definition

### Launch With (v2.1 RC)

Every feature above ships in v2.1. By definition — every v2.0 carry-forward closes; v2.1 IS the unified-cut.

**P1 (blocks RC):** Features 1, 2, 3, 5, 6, 8, 9, 10, 11 — listed in priority matrix above.
**P2 (lifts quality, doesn't block):** Features 4, 7, 12, 13 — could defer to v2.2 if velocity dictates, but `gsd-autonomous fully` mode targets all-in.

### Add After Validation (v2.2)

- `/hatch` user-gen mascot system (per memory: stretch)
- ProDJ Link integration (per memory: deferred from v2.0 candidates)
- Mixxx OSC live integration (per memory: deferred — upstream PR still draft)
- Multi-language UI (currently English-only)
- Stem separation in pipeline (per memory: out of scope, explicit anti-feature)
- Interactive Q&A in debrief mode

### Future Consideration (v3+)

- Bravoh-integrated identity (single sign-on bridges vibemix → Bravoh waitlist)
- iPad / iOS port
- DAW integration (Logic / Ableton / FL Studio)
- Real-time stream-to-Twitch/YouTube hook
- User-supplied custom voice cloning

---

## Sources

### LLM-as-judge / eval harness
- [DeepEval by Confident AI](https://deepeval.com/) — pytest-native multimodal eval framework
- [DeepEval LLM-as-Judge guide](https://deepeval.com/guides/guides-llm-as-a-judge)
- [Anthropic — Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- [Arize AI LLM-as-Judge templates](https://arize.com/llm-as-a-judge/)
- [Braintrust — What is LLM-as-a-judge?](https://www.braintrust.dev/articles/what-is-llm-as-a-judge)

### Library intelligence
- [Gemini API embeddings docs](https://ai.google.dev/gemini-api/docs/embeddings)
- [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Algoriddim djay Pro](https://www.algoriddim.com/) + [Neural Mix Pro](https://www.algoriddim.com/neural-mix-pro)
- [rekordbox 7 features](https://rekordbox.com/en/feature/overview/) + [Spotify integration](https://rekordbox.com/en/2025/09/rekordbox-for-mac-win-spotify-support/)
- [Mixed In Key harmonic mixing](https://mixedinkey.com/harmonic-mixing-guide/)

### Debrief UI / DJ pedagogy
- [Strava Built for Mars case study](https://builtformars.com/case-studies/strava)
- [Whoop UX evaluation](https://everydayindustries.com/whoop-wearable-health-fitness-user-experience-evaluation/)
- [Hudl Technique (golf forum)](https://forum.practical-golf.com/t/hudl-technique-video-recording-app/805)
- [Serato History support](https://support.serato.com/hc/en-us/articles/223455687-History)
- [Rekordbox History tutorial](https://www.deejayplaza.com/en/articles/rekordbox-history)
- [Radical Candor — feedback sandwich](https://www.radicalcandor.com/blog/feedback-sandwich-praise-criticism)

### Mascot 4-layer state machine
- [Three.js AnimationMixer](https://threejs.org/docs/pages/AnimationMixer.html) + [AnimationAction](https://threejs.org/docs/pages/AnimationAction.html)
- [Live2D Cubism](https://www.live2d.com/en/cubism/about/)
- [Warudo character docs](https://docs.warudo.app/docs/assets/character)
- [VTubeStudio plugins](https://github.com/DenchiSoft/VTubeStudio/wiki/Plugins)
- [Open-LLM-VTuber](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber)
- [crossFadeTo discussion (three.js)](https://discourse.threejs.org/t/animationaction-crossfadeto-not-working/63467)

### One-click install / TCC
- [Tauri Windows Installer](https://v2.tauri.app/distribute/windows-installer/)
- [Tauri macOS Code Signing](https://v2.tauri.app/distribute/sign/macos/)
- [Loom Mac permissions](https://support.atlassian.com/loom/kb/mac-app-installation-reset-accessibility-permission/)
- [Raycast onboarding](https://medium.com/@b6pzeusbc54tvhw5jgpyw8pwz2x6gs/using-raycast-001-introduction-installation-9dd58eea8836)
- [macOS TCC deep dive](https://www.rainforestqa.com/blog/macos-tcc-db-deep-dive)

### OSS security / threat model
- [Ollama vulnerability (May 2026)](https://thehackernews.com/2026/05/ollama-out-of-bounds-read-vulnerability.html)
- [Ollama exposed servers (Jan 2026)](https://thehackernews.com/2026/01/researchers-find-175000-publicly.html)
- [Cursor local model security forum](https://forum.cursor.com/t/ollama-lm-studio-support/5130)

### Long-term memory / profile
- [Reverse engineering ChatGPT/Claude memory](https://manthanguptaa.in/posts/memory_is_a_mistake/)
- [Claude memory explained](https://simonwillison.net/2025/Sep/12/claude-memory/)
- [Claude vs ChatGPT memory](https://support.claude.com/en/articles/11817273-use-claude-s-chat-search-and-memory-to-build-on-previous-context)

### Demo film generation
- [Loom AI screen recorder](https://www.loom.com/products/ai-screen-recorder)
- [Descript video editing](https://www.descript.com/video-editing)
- [Tella + Screen Studio + DemoPolish overview](https://demopolish.com/alternatives/loom/)
- [Vibrantsnap AI screen recording](https://www.vibrantsnap.com/blog/10-alternatives-to-loom)

### Integration audit
- [OpenObserve](https://openobserve.ai/)
- [Tracetest (CNCF)](https://tracetest.io/learn/top-9-tools-for-observability-driven-development)
- [vibemix-internal — v2.0 Milestone Audit](`.planning/milestones/v2.0-MILESTONE-AUDIT.md`)

### Day-Zero ops / launch
- [Launch-Day Diffusion: HN Impact on GitHub Stars (arxiv)](https://arxiv.org/html/2511.04453v1)
- [AFFiNE 33K stars playbook](https://dev.to/iris1031/how-to-get-more-github-stars-the-definitive-guide-33k-stars-case-study-11h8)
- [Ollama Releases](https://github.com/ollama/ollama/releases)
- [Tauri 2.0 RC announcement](https://v2.tauri.app/blog/tauri-2-0-0-release-candidate/)
- [Discord autorole bots](https://github.com/topics/autorole)

### Mascot 3D rigging
- [MASCOZ free 3D VTuber maker](https://www.youtube.com/watch?v=GRs4EKA0kTg)
- [Live3D VTuber Maker](https://live3d.io/tutorial/vtuber-maker-desktop-mascot)
- [Rokoko VTuber rigging tutorial](https://www.rokoko.com/insights/vtuber-rigging-tutorial)

### Hard Tek DSP
- [Acid line processing — Gearspace](https://gearspace.com/board/electronic-music-instruments-and-electronic-music-production/878603-how-do-you-process-your-acid-lines.html)
- [Roland TB-303 — Wikipedia](https://en.wikipedia.org/wiki/Roland_TB-303)
- [Chicago-style 303 acid bassline guide](https://musictech.com/guides/essential-guide/how-to-create-a-chicago-style-acid-house-bassline/)

### Internal references
- `.planning/milestones/v2.0-MILESTONE-AUDIT.md` — v2.0 ship audit (orphan inventory, Kaan-action surface)
- `.planning/milestones/v2.0-REQUIREMENTS.md` — v2.0 REQ-IDs (94 reqs, 56 satisfied end-to-end)
- `.planning/research/v2-buckets/D-mascot-emotion.md` — 4-layer additive blending recipe
- `.planning/research/v2-buckets/E-debrief-pedagogy.md` — debrief UI patterns, SBI/STAR-AR framing
- `.planning/research/v2-buckets/F-library-intelligence.md` — Gemini Embedding 2 + sqlite-vec + Bravoh pipeline port
- `.planning/research/v2-buckets/G-followup-1-hard-tek-dsp.md` — 8 Hard Tek detectors locked
- `.planning/research/v2-buckets/SYNTHESIS.md` — v2.0 cross-bucket synthesis
- `.planning/PROJECT.md` — v2.1 milestone scope
- `mocks/vibemix-app-ui.html` — live session UI design contract
- `mocks/vibemix-cinematic-storyboard.html` — 30s demo storyboard reference
- `mocks/vibemix-direction-final.html` — CDJ Whisper visual direction baseline

---

*Feature research for: vibemix v2.1 "The Unified Cut" — public RC milestone*
*Researched: 2026-05-14*
*Mode: `gsd-autonomous fully` — every blocker discharged autonomously*
