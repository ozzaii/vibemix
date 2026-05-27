# vibemix v2 Research Synthesis

**Date:** 2026-05-14
**Inputs:** 7 first-wave bucket reports + 4 second-wave followups + 1 cross-bucket viral demo combiner + cert recon. 11 research artifacts, ~28,000 words of research, ~25 OPUS tool-use sessions.

---

## I. EXECUTIVE TL;DR

Five strategic calls that came out of the swarm — each independent, each load-bearing:

1. **Latency is fixable without leaving cascade.** Verified: `SpeechHandle.interrupt(force=True)` works on Gemini 3 Flash → TTS cascade through `livekit-plugins-google==1.5.8`. Gemini context caching works for `gemini-3-flash-preview` (1024-token floor, requires padding to stay above when prompt-dieting). Prompt diet + caching = 500–1500ms TTFT win. Predictive firing + pre-canned ack bank + mascot anticipation = additional 800–1500ms of perceived latency masked. Sub-2s voice-to-voice is achievable.

2. **The single biggest grounding win is `KICK_SWAP`.** v4's `LAYER_ARRIVAL` detector fires on band-share diff but missed the moment that defines Hard Tek — clean sub kick → distorted layered kick. 3-field detector (centroid + harmonic_ratio + crest) closes it. Plus 7 more Hard Tek detectors locked. This is the direct fix for Kaan's "surface-level" critique.

3. **The citation linter is the technical implementation of the anti-slop thesis.** Grammar `[ev:KICK_SWAP@<t>]` / `[aud:peak_rms@<t>]` / `[midi:filter_open@<t>]` / `[track:Camelot_8A→9A]`, regex enforcement, in-memory Evidence registry. Sentence-level strip for debrief, response-level for live (drop-and-fall-back-to-ack-bank). Applies cross-mode (live + debrief + library + genre). Stdlib `re` is sufficient. Phasing: v1.0 prompt-only-no-enforcement, v1.1 live enforcement, v2.0 cross-mode.

4. **djay Pro Mac is the only viral-demo-tractable overlay target.** Rekordbox + Serato render to canvas → AX returns nothing useful. `kyleawayan/djay-pro-bridge` proves djay's AX surface works. 12 hand-mapped pointable elements, 5–7 engineering days. **Mixxx OSC is demoted** — it's draft PR #14388, not in shipped Mixxx 2.5.6. Pioneer ProDJ Link is wrong-market (CDJ-only, not bedroom). The viral demo anchors on **djay Pro overlay + MIDI controller grounding + mascot anticipation**.

5. **Bravoh's library pipeline is 80% portable code** — `service.py` embed functions, L2-normalize, SSL/429 retry, pydub MP3 transcoding lift verbatim from `/var/www/bravoh-backend/app/services/embedding/`. Gemini Embedding 2 = 1536-dim, **80s audio cap** (empirical correction from docs' claim of 180s), MP3/WAV only. sqlite-vec is the vector store (7.6k stars, embedded, pip wheels Mac+Win). 5k tracks = $72 one-time embed cost, well within budget.

---

## II. THE 11 RESEARCH ARTIFACTS

| # | File | What it does |
|---|---|---|
| 1 | `A-latency.md` | Latency engineering — predictive firing, prompt diet, ack bank, perceived-latency hacks |
| 2 | `B-industry-integrations.md` | Strategic landscape — Mixxx OSC ✅, ProDJ Link ❌, Rekordbox/Serato/Traktor/djay NO real-time API |
| 3 | `C-ui-overlay.md` | djay Pro Mac = only tractable overlay target; AX from Rust parent (not sidecar); 12-element vocabulary |
| 4 | `D-mascot-emotion.md` | 4-layer additive state machine; **anticipation layer = highest-leverage move (3 days, 400-1200ms mask)** |
| 5 | `E-debrief-pedagogy.md` | Single Gemini call per debrief; chaptered + voiced TL;DR + 3-drill cap; SBI/STAR-AR (not sandwich); REJECT mem0/vector DB for profile |
| 6 | `F-library-intelligence.md` | Gemini Embedding 2 audio; Bravoh pipeline 80% portable; sqlite-vec; cost projection 1k/5k/15k/30k |
| 7 | `G-genre-taxonomy.md` | v1.0 deep genre = Hard Tek; per-genre router architecture; biggest win = KICK_SWAP |
| 8 | `A-followup-1-cancel-and-caching.md` | EMPIRICAL: `interrupt(force=True)` works; caching needs 1024-token floor with deliberate padding |
| 9 | `B-followup-1-v11-integration-spec.md` | Mixxx OSC NOT shipped (PR #14388 draft); MIDI controller library = real spine; pyrekordbox XML import UX |
| 10 | `E-followup-1-citation-linter.md` | Full grammar + EBNF + Python `CitationLinter` class + per-mode prompt templates + telemetry as product surface |
| 11 | `G-followup-1-hard-tek-dsp.md` | 8 Hard Tek detectors locked with thresholds + reference tracks + tuning harness |
| 12 | `synthesis-viral-demo.md` | 30s storyboard + 3 signature beats + 7-day eng plan + IG/Reddit/HN angles |

---

## III. CROSS-BUCKET COMPOUNDS

The research compounds when you trace which buckets feed which. Three compound systems emerged:

### System 1 — The Latency Stack
```
A (predictive firing + cancel-on-cascade)
+ A (pre-canned ack bank, ~40 OPUS samples, sub-100ms)
+ A (prompt diet + Gemini caching, 500-1500ms TTFT win)
+ D (mascot anticipation layer, fires BEFORE voice — 400-1200ms perceived mask)
+ G (PHRASE_BOUNDARY phase-locking for predictive timing)
= sub-2s actual + sub-300ms perceived first reaction
```

### System 2 — The Anti-Slop Stack
```
A (grounded multimodal prompting — audio + screen + MIDI + now-playing)
+ G (genre-aware event taxonomy — KICK_SWAP etc. give Gemini specific events to react to)
+ E (citation linter grammar + enforcement)
+ F (library intelligence — Gemini cites real tracks, real BPM, real Camelot from imported library)
+ B (real telemetry from Mixxx OSC / Rekordbox XML / 10-SKU MIDI replaces inference)
= every claim Gemini makes traces to a real event in the user's session
```

### System 3 — The Viral Demo Stack
```
C (djay Pro overlay — amber ring on mid EQ when AI says "mids stacking")
+ D (anticipation lean-in BEFORE voice — sells AI as predictive, not reactive)
+ A (pre-canned ack within 100ms — never silence)
+ E (silence beat at 0:22-25 — anti-slop made visual)
+ B (DDJ-FLX4 MIDI events fire grounded reactions)
= one filmable 30s cut with 3 screenshot-worthy beats
```

---

## IV. PRIORITY MATRIX

The full feature inventory across all 12 docs, ranked.

### v1.0 — Ship June 2026 (clean utility launch)

Tight scope. Closes "what's actually here today + the cheap fixes." Anti-slop framing locked in copy + prompt structure, but no expensive new features. **Target ship date: ~3 weeks out.**

| Feature | Source | Effort | Why v1.0 |
|---|---|---|---|
| Hard Tek detector v1.0 set (8 events) | G-followup | 5d | Closes "surface-level" critique without scope creep |
| Prompt diet + Gemini caching | A + A-followup | 2d | Cheapest latency win (~1000ms), no anti-slop risk |
| Pre-canned ack bank (40 OPUS samples) | A | 2d | Sub-100ms first sound — "alive" feel mandatory |
| Mascot anticipation layer (3 clips) | D | 3d | 400-1200ms perceived mask, single highest-leverage |
| Citation grammar in prompt (no enforcement) | E-followup | 1d | Seeds corpus for v1.1 enforcement |
| Cert + DMG sign + GitHub Release publish | cert recon | 1d (Kaan-blocked on Issuer ID) | Required for distribution |
| rc1 fixes commit (drag + chrome + permissions) | dev session | 30 min | Already done in tree |

**v1.0 effort total: ~14 engineering days + 1 Kaan-blocked day.**

**Explicitly OUT of v1.0:**
- djay Pro overlay (v1.1 viral wave)
- Mixxx OSC (gated on PR #14388 merge)
- Pyrekordbox XML import (v1.1)
- Post-session debrief (v1.1)
- Library intelligence (v2.0)
- Predictive firing (v1.1 — needs ear-test gate per A open Q5)
- Cancel-and-refire (v1.1 — depends on predictive)
- Cross-mode citation enforcement (v1.1 live, v2.0 cross-mode)

### v1.1 — Viral Wave (~July 2026, 4-6 weeks post-launch)

The demo arsenal. Designed to land an IG/Reddit/HN wave that converts to 500–1000+ stars.

| Feature | Source | Effort |
|---|---|---|
| djay Pro overlay highlight (12 elements) | C + synthesis-viral-demo | 7d |
| Mascot 4-layer additive state machine refactor | D | 4d |
| Inline emote-tag vocab (15 tags) | D | 5d (after 1-day spike for text-channel timing) |
| Beat-coupled hip-bob (procedural) | D | 4d |
| Predictive drop firing + cancel-and-refire | A + A-followup | 5d |
| Live-mode citation linter enforcement (response-level strip + ack fallback) | E-followup | 2d |
| Pyrekordbox XML one-shot import | B-followup | 3d |
| 10-SKU MIDI controller library (9 SKUs via sniff + JSON) | B-followup | 5d |
| Post-session debrief MVP (chaptered + voiced TL;DR + 3 drills) | E | 7d |
| Long-term DJ profile (~2KB structured JSON, no vector DB) | E | 2d |
| Viral demo filming + IG/Reddit/HN posting | synthesis-viral-demo | 2d |

**v1.1 effort total: ~46 engineering days.** Calendar = 4-6 weeks with focus.

### v2.0 — Bigger Swings (Q3 2026)

Features that need infrastructure beyond what v1.0/v1.1 ships.

| Feature | Source | Why v2.0 |
|---|---|---|
| Library intelligence (file watcher → Gemini Embedding 2 → sqlite-vec) | F | Needs Bravoh-side proxy economics + indexing UX shake-out |
| "What should I play next?" library queries | F | Built on library intel + citation linter sentence-level |
| Cross-mode citation enforcement (live + debrief + library + genre) | E-followup | Built on all the above |
| Genre expansion: Techno → Tech House → DnB → Trance → UKG → Trap → Disco | G + G-followup | 1 weekend per genre with v1.0 architecture |
| Mascot procedural mouth from audio amplitude (3 talk variants) | D | After core 4-layer ships |
| Genre auto-classification via Gemini Embedding 2 nearest-neighbor | G | Built on library intel pipeline |
| Mixxx OSC behind feature flag (when PR #14388 merges) | B-followup | Gated on upstream |
| Rekordbox v1.2 overlay attempt (template matching since canvas-rendered) | C | Higher difficulty, lower ROI than djay |
| Windows overlay parity | C | Requires DPI / fullscreen Spaces work |

### Deferred / never

- **Pioneer ProDJ Link** — wrong market (CDJ hardware on Ethernet, bedroom DJs don't have it)
- **Serato / Traktor / VirtualDJ-Home / djay direct API** — no public real-time API
- **ARKit blendshape lip-sync** — Mixamo killed blendshape export in 2020
- **mem0 / vector DB for long-term DJ profile** — solves wrong problem, violates one-click-install
- **CLAP / OpenL3 / MERT** — Gemini-only product, Embedding 2 is the model
- **30-session formal eval harness** — Kaan's DJ ear is the test (memory: Phase 16 personal DJ-set testing)
- **Native audio model revert** (gemini-2.5-flash-native-audio) — regresses on grounding thesis

---

## V. THE LATENCY STACK — Unified View

Targets: <2s actual voice-to-voice, <300ms perceived first reaction.

```
T+0ms        Event detected (EventDetector.detect() returns)
T+20ms       Citation linter Evidence registry receives the event
T+50ms       Mascot anticipation lean-in fires via WS bus (D)
T+100ms      djay Pro overlay ring fires (v1.1, via Tauri webview)
T+150ms      Pre-canned ack tone plays from local disk (A)
T+200ms      session.generate_reply(extra_kwargs={cached_content: ...}) fires
T+800ms      Gemini text first-chunk arrives — citation linter validates
T+1200ms     TTS first audio chunk plays — mascot crossfades to talk_loop
T+2500ms     Reply complete — mascot returns to mood baseline
```

**The compound trick:** by T+150ms the user has already SEEN (mascot moved) and HEARD (ack tone) a response. The real Gemini reply arrives 1000–2000ms later but the perceived "live, alive" experience locked in by T+150ms.

**The cancel-and-refire path:** if a higher-priority event fires while T+200ms→T+1200ms is in flight, `SpeechHandle.interrupt(force=True)` cancels both LLM and TTS via `cancel_and_wait`. New `generate_reply` re-fires. Capped at 1 cancel per 8s to bound API cost.

**The predictive path (v1.1):** when `buildup_score > 0.7` AND `phrase_boundary_in <= 2 bars`, `generate_reply` fires ~2 bars BEFORE the drop, output buffered, released on drop confirmation OR canceled on 3s timeout.

---

## VI. THE ANTI-SLOP STACK — Unified View

Every Gemini claim grounds in a real event. Implemented as a stack:

```
Source layer    [audio buf, screen frame, MIDI ctrl, now-playing, library lookup, MIDI events]
                                          ↓
Evidence registry  in-memory dict[(source, key)] → list[t_session]
                                          ↓
EventDetector       per-genre detector set fires typed events with citation handles
                                          ↓
Prompt builder      injects evidence packet INTO Gemini prompt with citation requirement
                                          ↓
Gemini cascade      emits text with [ev:...] / [aud:...] / [midi:...] / [track:...] tokens
                                          ↓
Citation linter     validates each citation against registry; strips invalid claims
                                          ↓
TTS / display       only validated, grounded claims reach the user
```

**Failure modes covered:**
- Citation to non-existent event → strip + log
- No citations in response → live mode = drop + ack-bank fallback; debrief = sentence-strip
- Hallucinated track name → fails `track:` validation against library
- Hallucinated knob position → fails `midi:` validation against ControllerState

**Failure modes NOT covered (acceptable in v1):**
- Hallucinated event nuance ("kick was sloppy") — citation is valid (KICK_SWAP did fire) but qualifier is invented. Phase 16 ear test catches this; no automated fix in scope.

---

## VII. THE VIRAL DEMO PLAN

**Anchor: djay Pro Mac, single take, 30s, no editing tricks.**

3 signature beats (each a viral asset on its own):
1. **0:08 — "AI points at the knob"** — amber ring on mid EQ deck A as AI says "your mids are climbing on A — drop it 3dB". The screenshot captions itself.
2. **0:14 — "Anticipation lean-in BEFORE voice"** — mascot leans forward 200ms before voice arrives. Frames AI as predictive, not reactive. Counter-intuitive to viewers used to slow AI.
3. **0:22-25 — "3 seconds of silence"** — AI says nothing because nothing happened. Anti-slop made visible. This is the trust beat.

Posts (one filmable cut feeds all channels):
- **Twitter thread**: technical breakdown, Beat A hero image, code snippets, GitHub link
- **IG Reels (IT + EN)**: cinematic cut, music swell, Beat B hero
- **Reddit r/Beatmatch + r/DJs**: Beat C hero, open-source angle, EULA-friendly framing
- **HN "Show HN"**: engineering breakdown, anti-slop story, Beat A hero

Pre-seeded FAQs in comments:
- "Why not a free model?" → Gemini grounding > free
- "Where's my API key going?" → Bravoh-side proxy, BYO-key available, signed open-source
- "Does this work with Rekordbox?" → v1.1 = djay Pro, v1.2 = Rekordbox template-match attempt

**Star trajectory target:** Beat C is the trust beat that gets the second viewer to share. Beat A is the screenshot that captions itself for IG. Beat B is the surprise that gets the HN comment thread alive. Three beats = three viral surfaces.

---

## VIII. FUNNEL TO BRAVOH

Library intel is the natural funnel:
- Free tier: light use, BYO-key option OR ~100 reactions/day via Bravoh proxy
- Heavy use (5k+ library indexed + daily sessions): $0.05-0.20/day = $1.50-6/mo proxy cost
- Funnel: vibemix → Bravoh paid plan when user hits free-tier reaction cap OR wants Bravoh's full AI artist team

Bravoh-side proxy ALSO solves the API key distribution problem (constraint in CLAUDE.md). vibemix open-source binary never embeds a Gemini key; all live calls route through proxy with per-client rate limit.

**Open question for Kaan:** what's the free-tier reaction cap? Bucket F suggests 100/day; debatable.

---

## IX. CONSOLIDATED OPEN QUESTIONS

Decision points only Kaan can lock. Grouped by urgency.

### Blocks v1.0 ship (need answer in next 1-3 days)

1. **Cert: Issuer ID** — App Store Connect web UI → Users + Access → Integrations → App Store Connect API → page header UUID. Notarytool needs this for local DMG sign. **Or alternative**: app-specific password from appleid.apple.com.
2. **Rc1 sequence**: hold rc1 → ship v1.0 polished (add prompt diet + ack bank + anticipation + Hard Tek detectors = ~3 weeks) OR ship rc1 NOW signed → tech-debt to v1.0.1 + v1.1?
3. **v1.0 scope confirmation**: the 14-day v1.0 plan above (Hard Tek detectors + latency stack v1 + cert) — agree or trim?

### Blocks v1.1 design (need answer when v1.0 ships)

4. **Predictive firing aggressiveness**: conservative (DROP only, high precision) vs aggressive (any phase-shift, accept misfires). My pick: conservative for v1.1.
5. **Ack bank voice match**: Achird-voiced (seamless blend) vs distinct DJ-buddy character (clearer separation). Slight lean: Achird for consistency.
6. **Inline emote-tag vocab spike**: 1-day spike to verify Gemini text channel arrives before audio chunks. Required before committing to D's emote-tag direction.
7. **djay-only launch acceptable for viral push?** Or hold for Rekordbox overlay v1.2 (4-6 more weeks)?
8. **Mixxx OSC**: ship behind `--enable-mixxx-osc` flag for early adopters compiling PR #14388 OR wait for upstream merge?
9. **Library import UX**: drag-drop wizard vs auto-detect Rekordbox library path vs both?
10. **DDJ-FLX4 Sync note**: `0x60` (cohost_v4) vs `0x58` (Mixxx canonical). 5-min mido sniff resolves — bana controller'a basarken sniff yapayım istersen.

### Blocks v2.0 scope (can wait)

11. **Library free-tier reaction cap**: 100/day default — agree?
12. **Genre expansion order**: agree Techno → Tech House → DnB ... or different?
13. **Hard Tek anchor library**: Kaan contributes hard-tek/acidcore clips, RA/BR for the rest?
14. **Long-term DJ profile token budget**: 2KB JSON max — agree?
15. **Rekordbox overlay v1.2 effort**: template matching is brittle, RoI unclear — pursue or not?

---

## X. NEXT STEPS — Concrete kick-off plan

1. **Kaan**: provide Issuer ID (or app-specific password). Decide rc1 sequence (Q2 above). Confirm v1.0 scope (Q3).
2. **Me**: kick off `/gsd-new-milestone v2.0` with these 12 research artifacts as the input pile. Roadmap generator picks up the priority matrix, phase decomposition follows v1.0 → v1.1 → v2.0.
3. **Parallel**: commit the legitimate dev-session fixes (drag + chrome + permissions) as single atomic commit. Cert pull + sign on Issuer-ID arrival.
4. **First execution phase**: Hard Tek detector v1.0 set (G-followup spec is implementation-ready). 5 engineering days. Anchored to Kaan's DJ ear (Phase 16).
5. **Second execution phase**: latency stack v1 (prompt diet + caching + ack bank + anticipation). 7 engineering days.
6. **Third execution phase**: v1.0 ship. 1-2 days.
7. **v1.1 wave kicks off post-launch.**

---

## XI. WHAT I LEARNED FROM THE SWARM (META)

- **Empirical verification matters.** A's predictive design hung on assumption A1 (cancel on cascade). Followup 1 found the method name was wrong (`.cancel()` doesn't exist; `.interrupt(force=True)` does). Without that verification, the v1.1 design would have failed at the integration moment.
- **Negative results are load-bearing.** B's discovery that ProDJ Link is wrong-market and Mixxx OSC isn't shipped DEMOTED two confirmed v2 candidates. Without that, viral demo would have anchored on Mixxx and run into a wall.
- **Cross-bucket coupling is where the value compounds.** G's reaction-vocab fragments emit citation tokens E's linter validates against G's events. None of that exists in any single bucket — emerges in synthesis.
- **The viral demo isn't a feature, it's the engineering critical path.** synthesis-viral-demo pulled the 7-day eng plan with a kill-the-demo node (Day 1 AX bridge). That's a project plan, not a research output.

---

*End of synthesis. Total research investment: ~25 OPUS agent sessions, ~28,000 words across 12 artifacts. This document is the integration layer.*
