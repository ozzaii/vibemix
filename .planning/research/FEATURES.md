<!-- refreshed: 2026-05-11 -->
# Feature Research

**Domain:** AI live co-host for DJs (real-time hype-man / coach voice assistant for DJ software)
**Researched:** 2026-05-11
**Confidence:** MEDIUM-HIGH (high on existing-product landscape and controller mapping availability, medium on user-mode psychology and anti-feature predictions, low on "what hasn't been tried" because no shipping product like vibemix exists)

## Domain Framing

vibemix is product-greenfield: no shipping AI-co-host product talks back into a DJ's ear during a live set as either hype-man or coach. The adjacent landscape splits cleanly:

- **AI-in-the-DJ-software** (djay Pro AI Neural Mix, VirtualDJ 2026 AIPrompt, PulseDJ copilot, Rekordbox stems) — these are *track-tools* (separation, recommendation, automation). None talk. None react. None coach.
- **AI music production** (BandLab AI, Ableton + Claude MCP, Suno/Udio) — for making tracks, not playing them live.
- **Human DJ coaches / MCs** — the actual reference for the product. The "real DJ friend in your ear" bar.

The interesting tension: every existing AI-for-DJ product makes the DJ's job *easier* (auto-mix, auto-recommend, auto-separate). vibemix is the first that doesn't help the DJ mix — it reacts, hypes, or critiques. That's the wedge.

## Feature Landscape

### Table Stakes (Users Expect These)

Features that, if missing, make the product feel broken or unprofessional. Open-source DJs will dismiss vibemix if these aren't there.

| Feature | Why Expected | Complexity | User Mode | Interaction Mode | Notes |
|---------|--------------|------------|-----------|------------------|-------|
| One-click installer (signed/notarized DMG + MSI) | Free open-source audio tools that require Terminal commands have ~5% conversion from interest to install. PulseDJ and djay are one-click. | M | All | Both | DMG already feasible (Kaan has Apple Dev account); Windows code-signing cert is ~€200/yr |
| Auto-detect master output device | Hardcoded BlackHole assumption was a known POC limitation. Every DJ has a different audio chain (BlackHole / Loopback / Soundflower on mac; VB-Cable / Voicemeeter / WASAPI loopback on Windows). | M | All | Both | WASAPI loopback on Windows means *no virtual cable needed* — big UX win |
| Output destination picker (headphones vs speakers) | DJs cue with headphones; AI voice goes either in-ear (solo monitor) or to the room. Must be a one-line choice. | S | All | Both | Already in active scope |
| Voice picker (male / female, Gemini TTS prebuilt) | Voice assistants without voice choice feel impersonal. Gemini TTS has ~10+ prebuilt voices in male/female. | S | All | Both | Already in active scope |
| Genre picker at session start | Phase-detection thresholds (drop/build/breakdown) differ massively between techno (steady 130 BPM, long builds) and pop (varied BPM, song-form structure). Auto-detect is research-grade. | S | All | Both | Already in active scope — calibrates RMS gates |
| Three skill modes (Beginner / Intermediate / Pro) with distinct prompts | Beginners need encouragement + basic vocab; Pros need terse, technical, peer-level talk. Same voice for both = uncanny valley either way. | M | All | Both | Already in active scope — see prompt-template matrix below |
| Two interaction modes (Hype-man / Coach) | The core product duality. Stakeholder explicit. | M | All | (defines mode) | Already in active scope |
| Mic gating during AI talk | If AI hears its own voice via speakers, it triggers reactions to itself. POC solves this with `MicBuffer._current_gain() = 0` during AI talk + 350ms hold. | S | All | Both | Already implemented in POC |
| Curated MIDI mappings for popular controllers | DDJ-FLX4, DDJ-400, DDJ-FLX6, DDJ-FLX10, DDJ-1000, DDJ-SX3, XDJ-RX3, Numark Party Mix Live, Hercules Inpulse 300, Hercules Inpulse 500. Without this, "AI knows what you're doing" doesn't ground. | L | All | Both | See [Controller Mapping Availability](#controller-mapping-availability) — Mixxx has open-source XML mappings for most; FLX10/SX3/RX3 need manual mapping from MIDI implementation charts |
| Generic-MIDI fallback for unmapped controllers | The 10-controller curated list covers ~70-80% of mid-tier DJs but not the long tail. Without fallback, unmapped users see "controller not supported" and bounce. | M | All | Both | Already in active scope; less semantic context but still functional |
| Cross-platform (macOS + Windows) | macOS-only would block ~60% of the addressable DJ audience. Windows DJs are a larger market than Mac DJs in DDJ-controller demographic. | L | All | Both | Already in active scope; Linux excluded |
| Calibration wizard on first run | First-run setup for audio software is the #1 abandonment point. Sonarworks, Room EQ Wizard, every audio interface uses a wizard pattern. | M | All | Both | Already in active scope; see [Calibration Wizard UX](#calibration-wizard-ux-pattern) |
| Session recording (audio + AI voice + event log) | The POC already does this. Open-source users will expect to share clips, debug bad reactions, replay favorite moments. | S | All | Both | Already implemented in POC (`input.wav` / `voice.wav` / `events.jsonl`) |
| Push-to-mute / quick disable hotkey | When the AI is wrong or annoying mid-set, the DJ needs ONE keypress to silence it without breaking flow. Universal voice-assistant complaint: "I can't make it shut up." | S | All | Both | Critical anti-frustration feature |
| Don't talk over vocal sections | DJs know: never talk over the lyrics. AI talking through a vocal hook = product failure. Phase detector should flag "vocals_present" and gate AI replies. | M | All | Both | Hard requirement — research-validated |
| Reaction frequency throttle | "10-15 seconds of AI talk is the max before crowd tunes out" applies to AI too. Per-event cooldown + global silence budget needed. | S | All | Both | POC has per-type cooldown; needs global "max AI talk per minute" budget |
| Hallucination grounding (audio evidence packet) | POC pattern: pass RMS values + recent events + timing in prompt so AI describes what's actually playing. Open-source skeptics will catch hallucinations fast. | M | All | Both | Already in active scope — hard release gate |

### Differentiators (Competitive Advantage)

Features unique to vibemix or substantially better than the adjacent products. These drive shareability and the marketing-wedge function.

| Feature | Value Proposition | Complexity | User Mode | Interaction Mode | Notes |
|---------|-------------------|------------|-----------|------------------|-------|
| **Live voice reaction to master output** | First product to do this. Every other AI-for-DJ tool is silent. The shareable moment ("my AI hyped me up on that drop") is the marketing wedge. | L | All | Both | Core thesis. POC validates technical feasibility. |
| **Magnitude-aware EQ/fader awareness in prompts** | "Slight high boost" vs "killed the lows" — the AI describes the *DJ's move*, not just "knob moved". Makes coach feedback specific. Makes hype-man feel observant. | M | All | Both | Already in active scope |
| **Absolute set-timeline awareness** | "You're 2:44 into the set; the drop happened 11 seconds ago" — makes the AI feel present, not generic. Other AI tools don't track set time. | S | All | Both | Already in active scope |
| **Audible-deck detection (A/B/mix)** | POC's `audible_deck` detection means AI talks about the track that's *actually playing*, not whatever's loaded. Solves the #1 hallucination class. | M | Int+Pro | Coach | POC has this in `cohost_v2.py` |
| **Session replay with AI-voice timeline** | Records master audio + AI voice + event log per session. DJ can listen back and review: "where did the AI nail it? where did it miss?" Becomes a coaching artifact in itself. | M | All | Coach | POC already records; needs minimal playback UI |
| **"Highlight reel" export** | After-set: AI summarizes the 3 best moments (peak drop, cleanest transition, biggest energy build) with timestamps. DJ exports as MP4 with AI voiceover. Highly shareable on IG/TikTok = direct funnel to Bravoh. | M | All | Both | NOT v1 — v1.1 candidate; flagged as differentiator because it directly serves marketing |
| **Coach scorecard at session end** | After Coach-mode session: short text summary — "12 transitions, 8 clean, 2 train-wrecks, 2 abrupt. Strongest: 14:32 build into break. Weakest: 21:17 bass clash." Beginners get growth signal. | M | Beg+Int | Coach | Builds on existing event log |
| **Genre-tuned phase thresholds** | Most AI music tools assume one genre. vibemix recalibrates RMS gates per genre at session start. Techno builds last 30s; pop builds last 8s. | M | All | Both | Already in active scope |
| **Mascot easter egg (mascot.html)** | Canvas sprite that reacts to RMS at 30Hz. Already exists in POC. Optional dock-bar widget = personality signal, viral screenshots. | S | All | Both | Keep as optional widget, not core UI |
| **"Coach this moment" manual trigger** | Hotkey or pad on controller → AI critiques the last 30 seconds on demand. Empowers the DJ to ask, vs being lectured at. Solves chatty-AI complaint. | M | Int+Pro | Coach | Builds on POC's manual trigger via mascot WS |
| **Bravoh-managed API key (zero-config free)** | No API key signup, no Gemini account creation, no Pay-as-you-go enrollment. Just install and play. Friction kills virality. | M | All | Both | Already in active scope; requires API-abuse protection layer |
| **Open-source under bravoh/vibemix** | First Bravoh OSS release. Stars + GitHub presence funnel devs/DJs to Bravoh waitlist. | S | All | Both | Already in active scope |

### Anti-Features (Commonly Requested, Often Problematic)

Features the team will be tempted to build (or asked to build) that should be deliberately excluded. The DJ-software adjacent products show why each one fails for live use.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Real-time numeric set-rating score** | "Show my live mix score! 7.2/10!" Gamification temptation. Streamers love metrics. | Music isn't a game. Scoring a live performance mid-set creates anxiety, distracts from feel, and is what the DJ TikTok community already mocks about AI. Reduces the AI from "friend" to "judge". | Post-session Coach scorecard (qualitative + timestamped, not /10) — see Differentiators |
| **AI generates / plays the next track for you** | "AutoMix AI" (djay Pro, VirtualDJ) does this. Easy to ship. | Defeats the entire premise. vibemix is for *DJs who DJ*. Auto-track-selection makes the human a passenger. Bravoh isn't competing with djay Pro Automix — it's solving a different problem. | Stay silent on track choice. Coach can comment on a chosen track ("solid pick for this energy"), never recommend the next one in v1. v1.1 could add opt-in next-track suggestion as Coach feature only. |
| **AI recommends what to mix next mid-set** | PulseDJ's whole product. Visible market traction. | Same as above: this is PulseDJ's space, not vibemix's. Recommending next-track reduces the DJ. vibemix's positioning is "the friend in your ear", not "the assistant in your library". | Out of scope entirely for v1. If added later, it's an opt-in Pro-mode feature, not core. |
| **Twitch / YouTube live-streaming integration** | "Stream my AI co-host set!" Streamer demand. | Adds OBS-virtual-camera-style complexity, copyright issues with broadcast music, latency tuning per platform. Out of scope already; correctly. | Recording-for-later-sharing is enough. DJ can route their own OBS however they want. |
| **Multi-language UI** | International appeal. | English-only chrome with multilingual AI voice (Gemini TTS supports many languages — the AI can hype in Italian, English, French) is the sweet spot. UI translation = QA explosion. | Already correctly out of scope. AI voice language is a separate setting from UI language. |
| **Custom voice cloning** | "Make the AI sound like me / my favorite DJ / Drake." | Legal nightmare. Copyright minefield. Gemini TTS prebuilt voices are good enough. Custom cloning would be a competitive moat... and a lawsuit moat. | Prebuilt voices only. Already correctly out of scope. |
| **AI auto-EQs / auto-mixes for you** | "Why not have it adjust my EQ when I miss a low cut?" | Pioneer / Algoriddim already do auto-EQ in Automix mode. Doing it via vibemix would require *writing MIDI back to the controller* — opens motorized-fader / feedback-loop / hardware-state-mismatch problems. And again: vibemix doesn't replace DJ skill. | Coach mode *describes* what should have happened ("you could have cut the lows on deck B around 14:30"), never does it for you. |
| **Real-time set-rating leaderboard** | Social gamification. | Cringe. Kills the "real DJ friend" vibe instantly. DJs hate being publicly scored. | None — don't build. |
| **AI talks every X seconds / heartbeat mode** | "Make it more present!" Easy to implement. POC has heartbeat events. | Universal voice-assistant complaint: too chatty. Crowd tunes out at 10s; AI tunes the DJ out faster. Filling silence with AI talk = AI slop. | Event-gated only. Heartbeat events should be rare (POC default: very long cooldown). User-tunable cooldown but default conservative. |
| **AI tries to predict the crowd reaction** | "How are people feeling?" Hooks to the crowd-reading literature. | The AI can't see the crowd. It can hear master output. Pretending to know what the dance floor is doing = hallucination by design. | Stay within sensed reality: audio, MIDI, screen. Comment on the DJ's moves and the music itself, never the crowd. |
| **Headphone-cue listening** | "Hear what I'm cueing before I mix it!" Logical request. | Kaan confirmed in POC: Gemini conflates cue with master and produces wrong reactions. | Already correctly out of scope. Document this in README so users don't request it. |
| **DAW / Logic / Ableton integration** | "AI co-host while I produce!" Adjacent market. | Different product. Different event model (no live audience). Different audio context. Different user. | Already correctly out of scope. |
| **Mobile / iPad version** | Reach. | DJ software runs on laptops in 99% of pro use. iPad djay users are a casual segment with different needs. Different platform-engineering stack. | Already correctly out of scope. |
| **Linux support** | Open-source culture expectation. | Small DJ audience on Linux. WASAPI / CoreAudio equivalents (PulseAudio / PipeWire) double the audio-stack QA cost. | Already correctly out of scope. Document clearly so the OSS community doesn't expect it. |
| **AI generates social-share-ready highlight videos automatically without DJ review** | "Auto-post my best moments to IG!" Influencer demand. | Auto-posting AI-generated content = brand risk + privacy risk + crap-content risk. Especially if AI got the highlight wrong. | "Highlight reel export" (in Differentiators) is *manual export*, never auto-publish. DJ reviews before sharing. |
| **AI rates the song / criticizes the producer's track** | "Was that drop good?" Tempting prompt direction. | The AI is critiquing the DJ's *use* of the music, not the music itself. Critiquing tracks = unsolicited opinion on other artists = potentially offensive to producer friends. | Coach comments on selection-fit ("this track's energy doesn't match where you're going"), never on track quality. |
| **Mascot.html as the shipped main UI** | It's fun. Already exists. | Looks like a hobby project, not a polished product. Distracts from credibility. | Already correctly out of scope as primary UI; keep as optional widget / easter egg. |
| **Live screenshare to other DJs (collaborative mode)** | "B2B with AI in the middle!" | Network sync, audio routing across machines, multiple controllers — explosion. | Out of scope. Single-DJ, single-machine v1. |

## Hype-Man Mode: What That Actually Looks Like

Stakeholder framing: "party energy reactions". Translating to product behavior:

### What Real Club Hype-Men / MCs Do
- **Short call-and-response** — "When I say [X], y'all say [Y]!" — coined by MC Cowboy, still the standard.
- **Crowd commands** — "Hands in the air!", "Make some noise!", "Let me hear you scream!"
- **Energy callouts** — short, punchy, never longer than 10-15 seconds.
- **Drop-anticipation** — "Here it comes!" right before the drop, not after.
- **Affirmation of the music** — "This one!", "Tune!", "DJ DJ DJ!"
- **Crowd recognition** — "Detroit, I see you!", "Front row going crazy!"

### What Vbemix Hype-Man Should Adopt
- Reactions in the **drop / peak / build phases**, mostly silent in groove and low phases.
- **2-5 word reactions** are ideal. "OH this drop." "Filthy bassline." "Pull up."
- **Anticipation-aware** — comment on build *during* the build ("ohhhh here it comes"), not 8 bars after the drop.
- **Track-aware where possible** — if `nowplaying-cli` resolves the track, "ohh you're playing [X], classic" lands harder than generic hype.
- **Silence is hype** too. A long pause before the drop, then a single "YES" — more impactful than constant chatter.

### What Vbemix Hype-Man Should Never Do
- Talk over vocal sections — universal MC rule, applies harder to AI because it can't read the room when it's wrong.
- Generic "let's gooo" / "turn up" / "this is fire" filler — the AI-slop trap. Specificity beats hype.
- React more than ~once per 30-90 seconds of music (genre-dependent; techno tolerates less talk than pop).
- Claim crowd reaction it can't see ("look at this dance floor go!").
- Sound auto-tuned or processed. Gemini TTS prebuilt voices already sound natural — don't add effects.
- Use 2010-era hip-hop hype tropes if the DJ is playing techno. Genre-match the vocabulary.

## Coach Mode: What That Actually Looks Like

Stakeholder framing: "DJ skill feedback on mixes, EQ, transitions". Translating to product behavior:

### What Real DJ Instructors Say (Vocabulary Sample)
- **Transitions**: "phrase matching", "clean cut", "long blend", "train-wreck", "abrupt", "rushed", "you came in late on the 1", "let the breakdown play through".
- **EQ**: "cut the lows on the incoming", "two basslines together rarely work", "you killed the highs too early", "mid-range mud", "frequency clash", "kept the kicks together — clean swap".
- **Energy**: "you peaked too early", "give the crowd a breath", "build through, don't bail before the drop", "energy dip felt intentional", "good restraint".
- **Selection**: "doesn't match the energy where you're going", "vibe shift was too jarring", "smart segue from house to techno", "this track's tempo arc fits the moment".
- **Crowd-feel proxy** (since AI can't see crowd): comment on the *DJ's energy management on the master output*, never on the crowd directly.

### What Vbemix Coach Should Adopt
- **Constructive language** — describe the move, then the result, then the option. "You cut the bass on B at 14:32, but kept the highs hot — that left a mid-range stack for two bars. Could have softened the mids on A first."
- **Phrase-aware feedback** — phrase-matching is the #1 thing instructors teach. Detector for "transition started on the 1 vs mid-phrase" is implementable from BPM + onset timing.
- **Mode-tuned tone**:
  - *Beginner Coach*: warm, encouraging, explains terms inline. "Nice — you matched the BPMs. Next time try also bringing in the new track on the start of an 8-bar phrase so the drop lines up."
  - *Intermediate Coach*: peer-level, names techniques. "Clean cut. EQ swap on the 1, classic move."
  - *Pro Coach*: terse, technical, peer-level, doesn't explain basics. "Two basslines on the outro of B, half a bar before swap." — implies the DJ already knows that's a thing to fix.
- **Specific timestamp references** — "at 14:32" not "earlier in the set". Already feasible from event log.
- **End-of-session summary** — quantified count of transitions, classified by quality. Gives the beginner a "I grew" signal.

### What Vbemix Coach Should Never Do
- Use generic praise ("great mix!", "love the vibe!") — that's the AI-slop trap.
- Critique track choice as if it were the DJ's responsibility to entertain *the AI*. The AI is the critic of *technique*, not of taste.
- Critique the DJ's musical preferences — "I don't like dubstep" is out of scope.
- Compare to other DJs by name — legal + cringe risk.
- Give live mid-mix critique that distracts ("you should have killed those lows" mid-build is too late and disruptive).
  - **Default**: critique fires *after* the transition is complete, not during.
  - **Pro mode opt-in**: live mid-mix nudges OK if user enables.
- Score numerically (/10). Use qualitative bands: clean / decent / abrupt / train-wreck.

## Skill-Tier Prompt-Template Matrix

Each cell is a distinct prompt template / persona. 6 templates total.

| | Hype-Man | Coach |
|---|---------|------|
| **Beginner** | Encouraging, warm, simple energy callouts ("Yes! That drop hit!"). Avoid technical terms. Celebrate small wins (a clean BPM-match alone is celebration-worthy). | Warm, teaches as it critiques. Explains terms inline. Asks "did you mean to do that?" Focused on: phrase matching, bass cut on swap, not playing two vocals together, energy curve. |
| **Intermediate** | Peer-level hype. References technique casually ("filthy EQ on that swap"). Mix of energy and acknowledgment. | Peer-level critique, names techniques without explaining them. Calls out tighter stuff: phrase alignment within 4 bars, frequency clash in mids, build/drop timing. Less explanation. |
| **Pro** | Sparse, terse, knowing. The kind of friend who says "yeah" when the drop lands and means it. Speaks rarely, lands hard. Genre-fluent vocabulary. | Terse, technical, peer-level. Comments on subtle stuff: phrase-internal timing, sub-bass overlap, energy arc across 20-minute window, transition family choice. Assumes total fluency. |

### Beginner Wants to Be Told
- "That was a clean transition."
- "Try cutting the lows on the incoming track before you bring in the highs."
- "Your BPM-match was solid."
- "This track's energy is dropping — that's fine, you're building back up."
- "You played two vocals together for a sec there — try mixing through the instrumental section next time."

### Intermediate Wants to Be Told
- "Clean phrase-match on that swap."
- "Mid-range got muddy when both tracks had the lead synth — try cutting mids on one."
- "You could have ridden the breakdown 16 more bars before bringing in the build."
- "Tempo ramp was smart there."

### Pro Wants to Be Told
- (Hype) "Yes." [silence].
- (Coach) "Sub on B was hot through the swap." (and nothing else; the Pro knows what to do).
- (Coach) "Bar 4 of the transition was the weak point."
- (Coach, controller-aware) "Filter sweep on A leading the swap — nice."

## Calibration Wizard UX Pattern

Reference products: Sonarworks SoundID Reference, Room EQ Wizard, every audio interface's first-run flow.

### Step Sequence (recommended)
1. **Welcome + permissions** — request microphone, accessibility (for window screen-capture), and audio-device permissions. macOS will show system dialogs; pre-empt them with a "we need these because…" screen.
2. **Audio output check** — pick where the AI voice goes (in-ear headphones, USB earbuds, separate room speakers). Test tone plays. User confirms "I heard the tone."
3. **DJ-software audio capture** — detect virtual audio cable (BlackHole on mac, VB-Cable on Windows) OR use WASAPI loopback (Windows native, no install) OR Core Audio loopback (mac equivalent in macOS 13+). Auto-pick best path; show fallback instructions if no cable installed.
4. **DJ-software window picker** — list running windows; user picks Serato / rekordbox / VirtualDJ / djay Pro / Traktor. Test screenshot displayed back to user — "is this your DJ app?"
5. **Controller detection** — scan MIDI inputs. If a curated controller is detected, "DDJ-FLX4 detected — mapping loaded ✓". If not, "We don't have a curated map for this controller. Generic MIDI fallback will work but with less context. Want to help us add yours?"
6. **Genre + mode + voice picker** — set defaults for the session. User can change anytime mid-session.
7. **Play test** — start a track. AI says one calibration line ("I hear you. Loud and clear. Let's go."). User confirms volume / latency / device feel.

### What NOT to Do in the Wizard
- Don't ask for an API key. (We're shipping with one.)
- Don't ask the user to manually configure audio routing in their OS-level settings — auto-detect or fall back gracefully.
- Don't make any step required if it can be skipped (window picker can default to "all windows" if the user is impatient).
- Don't show technical jargon ("sample rate", "buffer size") unless an advanced toggle is opened. Auto-pick sensible defaults.

## Controller Mapping Availability

Findings from researching open-source mapping sources for the 10 curated controllers:

| Controller | Mixxx Official Mapping | Mixxx Community | Pioneer/Hercules MIDI Chart | Notes |
|------------|------------------------|-----------------|-----------------------------|-------|
| Pioneer DDJ-FLX4 | ✓ Yes (`Pioneer-DDJ-FLX4.midi.xml` in `mixxxdj/mixxx/main/res/controllers/`) | ✓ | ✓ AlphaTheta Help Center | Best-mapped; POC already supports |
| Pioneer DDJ-400 | "In development" wiki status; community-mapped extensively (4-deck mapping at `apmiller108/pioneer_ddj400_mixxx_mapping`) | ✓ | ✓ | Mainstream beginner controller; well-documented |
| Pioneer DDJ-FLX6 | Not in official Mixxx mapping list per public wiki | Community mappings exist | ✓ AlphaTheta Help Center publishes MIDI message list | Map from chart |
| Pioneer DDJ-FLX10 | Not officially mapped in Mixxx (newer 4-channel) | Algoriddim community has unofficial mapping; some Reddit/forum efforts | ✓ AlphaTheta Help Center | Most complex; 4 channels, stems buttons, jog displays |
| Pioneer DDJ-1000 | "In development" wiki status | Community-mapped extensively | ✓ | Common rekordbox 4-channel |
| Pioneer DDJ-SX3 | DDJ-SX/SX2 officially mapped; SX3 community-mapped | ✓ | ✓ | Map by analogy from SX2 |
| Pioneer XDJ-RX3 | All-in-one player, not in Mixxx official | Some community efforts | ✓ Pioneer publishes diagram | All-in-one (has built-in screen) — handle as standalone-like |
| Numark Party Mix Live | Listed in Transitions DJ supported list; some Mixxx community | Community | Numark publishes MIDI map | Entry-level controller |
| Hercules DJControl Inpulse 300 | ✓ Yes (official Mixxx mapping) | ✓ | ✓ Hercules publishes mapping doc | Well-supported |
| Hercules DJControl Inpulse 500 | Manual chapter in Mixxx 2.5 docs; some MIDI mapping issues reported in 2.5.0 | Community | ✓ Hercules publishes | Master/headphone knobs are hardware-only (don't send MIDI) |

**Implication for v1:** Mixxx open-source mapping XML is a strong foundation for ~6 of the 10 controllers (FLX4, DDJ-400, Inpulse 300 are well-mapped; SX/SX2 covers SX3 by analogy; DDJ-1000 has community work). The newer controllers (FLX10, FLX6, RX3) need manual mapping from Pioneer/AlphaTheta's published MIDI message lists, which are publicly documented at support.pioneerdj.com. Total mapping work estimate: ~2-4 days per controller for full magnitude-aware EQ + fader + transport + pad coverage. **Total: 20-40 dev-days for all 10 controllers.**

**License note:** Mixxx is GPL2+. vibemix cannot copy Mixxx mapping XML verbatim into an MIT/Apache-licensed product without potentially triggering GPL infection (depends on whether the XML is "code" or "data" — legally murky for mapping files). **Safer path:** Use Mixxx mappings as *reference* for which MIDI message means what on each controller, then write fresh mapping data in vibemix's own format. The MIDI messages themselves (CC numbers, note numbers) are facts published by Pioneer/Hercules and are not copyrightable.

## Competitor Feature Analysis

| Feature | Algoriddim djay Pro AI | VirtualDJ 2026 | PulseDJ Copilot | BandLab AI | vibemix Approach |
|---------|-----------------------|----------------|-----------------|------------|-----------------|
| Stem separation | ✓ Real-time Neural Mix (AudioShake-powered) | ✓ AI stems built-in | — | ✓ (for production) | ✗ Not needed — we don't manipulate audio, only react to it |
| Auto-mix / auto-transition | ✓ Automix AI (calculates fade durations, EQ adjustments) | ✓ Auto-mix mode | ✗ | — | ✗ Anti-feature — we don't replace DJ skill |
| Next-track recommendation | ✓ Auto-suggest based on key/BPM/energy | ✓ AIPrompt (natural-language playlist queries) | ✓ Core product feature | — | ✗ Anti-feature for v1 — defer indefinitely |
| Real-time set commentary / voice | ✗ | ✗ (lyrics extraction is text, not voice) | ✗ | ✗ | ✓ **Core unique value** |
| Hype-man / energy reactions | ✗ | ✗ | ✗ | ✗ | ✓ **Core unique value** |
| Coach / technique feedback | ✗ | ✗ | ✗ | ✗ | ✓ **Core unique value** |
| Skill-tier-aware (Beginner/Intermediate/Pro) | ✗ | ✗ | ✗ | ✗ | ✓ Differentiator |
| MIDI controller library | ✓ 30+ supported, deep mapping | ✓ Wide support | ✓ Reads via file-watching, not direct MIDI | — | ✓ Curated 10 + generic fallback |
| Cross-platform (mac + win) | ✓ Mac + iOS only on Pro AI (Windows version less feature-rich) | ✓ Mac + Win + Linux | ✓ Mac + Win | ✓ Web + mobile | ✓ Mac + Win |
| Free | $5/mo or one-time | Free tier exists; Pro is $19/mo | Free in beta | Freemium | ✓ Free (we eat API cost) |
| Open-source | ✗ | ✗ | ✗ | ✗ | ✓ **Differentiator + marketing wedge** |
| Local-first / runs on user's machine | ✓ | ✓ | ✓ (offline-capable) | ✗ Cloud | ✓ Audio + state local, only Gemini calls go out |
| Voice picker | n/a | n/a | n/a | n/a | ✓ Differentiator |
| Genre-aware behavior | Auto-genre detect for recommendations | Yes (AIPrompt understands genre) | Yes | n/a | ✓ Differentiator — phase detection tuned per genre |

**Synthesis:** vibemix doesn't compete with any of these on their core feature (track manipulation / recommendation / generation). It occupies an empty quadrant: *live voice commentary on the DJ's performance*. The only adjacent failure mode is "AI talks during music" → "annoying chatbot" → bad UX. The product wins or loses on the *quality of the voice's restraint and grounding*, not on feature breadth.

## Feature Dependencies

```
Cross-platform audio capture
    └──requires──> Auto-detect master output device
                       └──requires──> Calibration wizard (output device picker step)

Curated MIDI mappings
    └──enhances──> Magnitude-aware EQ/fader awareness
                       └──enhances──> Coach mode quality (technique critique)
                                          └──enhances──> Skill-tier prompt-template matrix

Genre picker
    └──requires──> Genre-tuned phase thresholds
                       └──requires──> Phase-detection (drop/build/breakdown)
                                          └──enhances──> Both Hype-man + Coach reactions

Hallucination grounding (audio evidence packet)
    └──requires──> AudioBuffer snapshot features (POC has this)
                       └──blocks──> All AI inference (hard release gate)

Hype-man mode <──conflicts──> Coach mode at same time
    (User picks one per session; mid-session toggle OK)

Voice picker
    └──requires──> Gemini TTS streaming (POC has this)

Mic gating
    └──requires──> Levels.voice tracking (POC has this)
    └──blocks──> AI hearing its own voice (critical correctness gate)

Vocal-section detection
    └──requires──> Phase detector + frequency-band analysis
                       └──blocks──> AI talking over lyrics (critical etiquette gate)

Session recording (POC has this)
    └──enables──> Highlight reel export (v1.1)
    └──enables──> Coach scorecard at session end (v1)
    └──enables──> Session replay UI (v1.x)

Bravoh-managed API key
    └──requires──> API-usage abuse protection (rate-limit, per-client quota)
                       └──blocks──> Open-source release (we'd get drained without it)
```

### Dependency Notes

- **Calibration wizard is the gate**: every audio-related feature needs the wizard's output (which device, which DJ window, which controller). Wizard quality determines first-session success rate.
- **Curated MIDI mappings → Coach quality**: without magnitude-aware EQ events, Coach can only say "you moved a knob", not "you killed the lows on the incoming". The whole differentiation collapses without good mappings.
- **Vocal-section detection is a hard gate**: an AI that talks over lyrics is a product-killing flaw. Cheaper to ship later with vocal detection working than to ship faster without it.
- **Hallucination grounding is a hard release gate**: Kaan has called this out as a release blocker. No grounding = no ship.
- **Session recording → Highlight reel → Marketing virality**: the recording layer (already built in POC) is the foundation for the post-session shareable content that drives the Bravoh waitlist funnel. Don't break it during the refactor.

## MVP Definition

### Launch With (v1) — The Bravoh-Wedge Drop

Minimum viable product to validate the concept AND serve the marketing function.

- [x] **Cross-platform audio capture** (macOS Core Audio loopback + Windows WASAPI loopback, auto-detected) — without this, half the audience is locked out
- [x] **Calibration wizard** (first-run, 7 steps as documented) — without this, install conversion fails
- [x] **3 skill modes × 2 interaction modes (6 prompt templates)** — the stakeholder-defined product matrix
- [x] **Voice picker (male/female, Gemini TTS prebuilt)** — table stakes for voice products
- [x] **Genre picker + genre-tuned phase thresholds** — without this, techno DJs and pop DJs get the same wrong thresholds
- [x] **10 curated controller mappings + generic MIDI fallback** — without curated, Coach mode is generic; with all 10, ~70-80% of users get full experience
- [x] **Magnitude-aware EQ/fader events** — the "AI knows your move" effect
- [x] **Push-to-mute hotkey** — anti-frustration baseline
- [x] **Vocal-section gating** — AI shuts up over lyrics (hard etiquette gate)
- [x] **Reaction frequency throttle + per-event cooldowns** — anti-chatty
- [x] **Hallucination grounding (audio evidence in prompts)** — hard release gate
- [x] **Session recording (input.wav + voice.wav + events.jsonl)** — keep what POC has
- [x] **Coach scorecard at session end (Beginner + Intermediate)** — gives Beginner mode a growth signal, justifies Coach mode existence
- [x] **One-click installer** (signed DMG + signed MSI) — distribution baseline
- [x] **Bravoh-managed API key + abuse protection** — zero-config experience
- [x] **Audible-deck detection (carry from POC)** — solves #1 hallucination class

### Add After Validation (v1.x — within 1-2 months of launch)

Features added once core is working and users are giving feedback.

- [ ] **Highlight reel export** — when usage shows users sharing recordings manually, automate the best-clip extraction. Marketing-funnel multiplier.
- [ ] **Session replay UI** — simple timeline player for the recorded session (currently raw WAV files). Users will want this.
- [ ] **"Coach this moment" manual trigger** — when chatty-AI feedback appears in early reviews, give users explicit control.
- [ ] **More controller mappings (next 5-10 beyond the curated 10)** — driven by user requests in GitHub issues.
- [ ] **Live mid-mix Coach nudges (Pro mode only, opt-in)** — only after the default deferred-critique mode is validated as safe.
- [ ] **Mascot widget as optional dock toy** — keep the easter egg, polish it.
- [ ] **Custom prompt-template editor (Pro mode)** — let users tune their own AI persona. Power-user feature.

### Future Consideration (v2+)

Features to defer until product-market fit is established and there's resource to spend on them.

- [ ] **Next-track recommendation (opt-in)** — only if user research strongly demands it, and only as a Coach-mode suggestion ("might want something in C minor next"), never auto-play.
- [ ] **DAW integration (Logic, Ableton, FL)** — "the next conquest" per the stakeholder doc. Different product really; spin off later.
- [ ] **iOS/iPad version** — only if mobile DJ-software market shifts. Currently desktop-locked.
- [ ] **Linux support** — only if OSS community contributes the audio layer.
- [ ] **Custom voice cloning** — never, unless legal landscape changes radically.
- [ ] **Multi-language UI chrome** — only after critical mass in non-English markets.
- [ ] **Library scanner / track-recommendation AI** — POC has a file-watcher already; reactivate as v1.1 if recommended.
- [ ] **Streaming integration (Twitch/YouTube)** — not the product. Users can route through OBS themselves.
- [ ] **Multi-DJ B2B mode** — interesting but huge complexity. Way out.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Live voice reaction to master output | HIGH | HIGH (POC validates) | P1 |
| Hype-man mode (3 tiers) | HIGH | MEDIUM (prompt engineering) | P1 |
| Coach mode (3 tiers) | HIGH | MEDIUM-HIGH (prompt + scorecard logic) | P1 |
| Calibration wizard | HIGH (gates everything) | MEDIUM | P1 |
| Cross-platform audio capture | HIGH | HIGH (Windows is new) | P1 |
| 10 curated MIDI mappings | HIGH | HIGH (per-controller work) | P1 |
| Generic MIDI fallback | MEDIUM | LOW | P1 |
| Voice picker | MEDIUM | LOW (Gemini TTS built-in) | P1 |
| Genre picker + thresholds | HIGH (affects feel) | LOW-MEDIUM | P1 |
| Vocal-section gating | HIGH (etiquette gate) | MEDIUM | P1 |
| Hallucination grounding | HIGH (release gate) | LOW (POC done) | P1 |
| Push-to-mute hotkey | MEDIUM | LOW | P1 |
| Coach scorecard at session end | MEDIUM | LOW-MEDIUM | P1 |
| One-click installer | HIGH (distribution gate) | MEDIUM | P1 |
| Bravoh-managed API key + abuse protection | HIGH | MEDIUM | P1 |
| Magnitude-aware EQ events | HIGH (differentiation) | LOW (POC done for FLX4) | P1 |
| Session recording (carry from POC) | MEDIUM | LOW (exists) | P1 |
| Audible-deck detection (carry from POC) | HIGH (anti-hallucination) | LOW (exists) | P1 |
| Highlight reel export | HIGH (virality) | MEDIUM | P2 |
| Session replay UI | MEDIUM | MEDIUM | P2 |
| "Coach this moment" manual trigger | MEDIUM | LOW | P2 |
| More controller mappings (11-20) | MEDIUM | HIGH | P2 |
| Live mid-mix Coach nudges (opt-in) | MEDIUM | LOW | P2 |
| Mascot widget polish | LOW | LOW | P2 |
| Custom prompt-template editor | LOW (power users) | MEDIUM | P3 |
| Next-track recommendation | LOW (anti-feature for now) | HIGH | P3 |
| DAW integration | MEDIUM (future) | XL | P3 |

**Priority key:**
- P1: Must have for v1 launch (~30 features)
- P2: Should have, add within v1.x (1-2 months post-launch)
- P3: Future consideration, post-PMF

## Specific Anti-Pattern Warnings for Implementation

Distilled from competitor analysis and voice-assistant UX research:

1. **Don't fill silence with AI talk.** Default cooldowns should err long (30-90s between reactions). User can shorten if they want a chattier mode. Universal voice-assistant complaint is verbosity.
2. **Don't have the AI describe what it just heard.** "I'm hearing a drop now!" is robotic. The AI should *react* ("yesss") not narrate. The audio is right there.
3. **Don't have the AI explain its reasoning unprompted.** Coach mode should not say "I'm telling you this because…" — just the feedback.
4. **Don't let the AI gain confidence from absence of evidence.** If no MIDI events arrive for 60 seconds, the AI shouldn't assume "the DJ is in a flow state, time to comment" — silence is also valid signal.
5. **Don't make the AI sound the same in all three skill tiers.** Beginner and Pro should feel like different friends, not the same voice with different word counts.
6. **Don't ship with the AI talking over a vocal hook even once in the demo.** First impressions kill. The vocal-gate must be tight before any public demo recording.
7. **Don't show a "score" for the user mid-session.** Post-session qualitative summary only.
8. **Don't auto-publish anything.** Recording → user reviews → user shares. Always.

## Sources

### Existing AI music tools surveyed
- [Algoriddim Neural Mix Pro](https://www.algoriddim.com/neural-mix) — real-time stem separation, MIDI-mappable Neural Mix commands
- [Algoriddim djay Pro AI press release](https://www.algoriddim.com/press_releases/362-algoriddim-reinvents-djing-with-world-s-first-real-time-vocal-and-instrumental-separation-on-new-djay-pro-ai)
- [VirtualDJ 2026 AI features (Digital DJ Tips)](https://www.digitaldjtips.com/virtualdj-2026/) — AIPrompt folder, auto-lyrics
- [VirtualDJ 2026 review (gearnews)](https://www.gearnews.com/virtualdj-2026-dj/)
- [VirtualDJ 2026 review (MusicTech)](https://musictech.com/news/gear/virtualdj-2026/)
- [PulseDJ AI Copilot overview](https://blog.pulsedj.com/ai-dj-software) — track recommendation, file-watcher architecture, MyStyle personalization
- [BandLab AI tools](https://blog.bandlab.com/bandlab-ai-tools-best-ai-music-generator/) — production-side comparison
- [Claude in Ableton (MusicTech)](https://musictech.com/news/industry/claude-can-now-be-plugged-into-ableton/) — production-side AI assistant pattern

### DJ technique / coaching / MC vocabulary
- [Hype man (Wikipedia)](https://en.wikipedia.org/wiki/Hype_man) — historical role definition, MC Cowboy callouts
- [Things to say on the mic as a DJ (DJ Pro Tips)](https://djprotips.com/tips-for-mcing-as-a-dj/) — 10-15s talk limit guidance
- [DJ Transitions Masterclass — Phrasing, EQ & Filters (YouTube)](https://www.youtube.com/watch?v=Fd9jEpFG6II)
- [EQ Mixing techniques (DJ TechTools)](https://djtechtools.com/amp/2012/03/11/eq-critical-dj-techniques-theory/)
- [Anatomy of a great DJ mix (DJ.Studio)](https://dj.studio/blog/anatomy-great-dj-mix-structure-energy-flow-transition-logic)
- [Common beginner DJ mistakes (ClubReady)](https://www.clubreadydjschool.com/tribe-talk/getting-started/7-common-beginner-dj-mistakes/)
- [10 mistakes beginner DJs make (Digital DJ Tips)](https://www.digitaldjtips.com/10-things-beginner-djs-do-that-pros-dont/)
- [How to read the dancefloor for energy cues (Learningtodj)](https://learningtodj.com/blog/how-to-read-the-dancefloor-for-energy-cues/)
- [Control the energy level (Mixed In Key)](https://mixedinkey.com/book/control-the-energy-level-of-your-dj-sets/)
- [Behind the booth — reading a crowd (Relentless Beats)](https://relentlessbeats.com/2026/02/behind-the-booth-how-djs-read-a-crowd-and-control-a-nights-energy/)

### Controller mappings / MIDI references
- [Mixxx DDJ-FLX4 mapping (GitHub)](https://github.com/mixxxdj/mixxx/blob/main/res/controllers/Pioneer-DDJ-FLX4.midi.xml) — official open-source XML
- [Mixxx Pioneer DDJ controllers wiki](https://github.com/mixxxdj/mixxx/wiki/Pioneer-Ddj-Controllers)
- [Mixxx Hercules Inpulse 500 wiki](https://github.com/mixxxdj/mixxx/wiki/Hercules-DJControl-Inpulse-500)
- [Pioneer DDJ-400 4-deck community mapping](https://github.com/apmiller108/pioneer_ddj400_mixxx_mapping)
- [Mixxx MIDI Controller Mapping File Format](https://github.com/mixxxdj/mixxx/wiki/Midi-Controller-Mapping-File-Format)
- [Pioneer DJ MIDI Maps forum](https://forums.pioneerdj.com/hc/en-us/community/topics/200303046-MIDI-Maps)
- [AlphaTheta DDJ-FLX10 MIDI-compatible software](https://support.pioneerdj.com/hc/en-us/articles/16716711647129-DDJ-FLX10-MIDI-compatible-software)
- [Rekordbox MIDI mapping customization (AlphaTheta)](https://support.pioneerdj.com/hc/en-us/articles/40182116223257-How-to-customize-rekordbox-MIDI-mapping)

### UX / onboarding / anti-chatty research
- [Intelligent assistants have poor usability (NN/Group)](https://www.nngroup.com/articles/intelligent-assistant-usability/) — verbosity is the #1 complaint
- [Sonarworks speaker calibration onboarding](https://support.sonarworks.com/hc/en-us/articles/20378216058514-Setting-up-with-speaker-calibration) — wizard pattern reference
- [Room EQ Wizard onboarding](https://producelikeapro.com/blog/room-eq-wizard/) — measurement wizard pattern
- [When AI in UX stops helping and starts annoying (Monsoonfish)](https://monsoonfish.com/when-ai-in-ux-stops-helping-and-starts-annoying/)
- [Why chatbot UX is annoying users (Clutch)](https://clutch.co/resources/fix-your-chatbot-ux)

### Industry overview
- [The 10 Best AI DJ Tools for 2026 (ZIPDJ)](https://www.zipdj.com/blog/best-ai-dj-tools)
- [AI Tools and Software for DJ Workflows 2026 (DJ.Studio)](https://dj.studio/blog/ai-dj-workflow-programs-tools)
- [Rise of AI DJs in 2026 (ZIPDJ)](https://www.zipdj.com/blog/ai-djs)
- [How AI is changing DJ sets in 2025 (Next Sound)](https://nextsound.net/features/how-ai-is-changing-dj-sets-and-electronic-music-production-in-2025)

### Internal references
- `/Users/ozai/projects/dj-set-ai/.planning/PROJECT.md` — stakeholder vision and active scope
- `/Users/ozai/projects/dj-set-ai/.planning/codebase/ARCHITECTURE.md` — POC capabilities (audio capture, MIDI ingestion, phase detection, audible-deck detection, mic gating, session recording)

---
*Feature research for: AI live co-host for DJs (vibemix)*
*Researched: 2026-05-11*
