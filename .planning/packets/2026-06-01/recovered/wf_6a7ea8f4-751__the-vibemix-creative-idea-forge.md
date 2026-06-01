# THE VIBEMIX CREATIVE IDEA FORGE

**Date:** 2026-05-31
**Purpose:** A scored, anti-slop-disciplined idea bank for vibemix — every idea names the real primitive it stands on and the exact DJ moment it lights up, so we build only what the engine can ground (or honestly invent).

**Scoring:** `total_score = novelty + feasibility + moat_fit + wow` (max 20). The Top 10 rank by total, then wow as tiebreak.

**The shelf — 33 ideas:** 16 STRONG · 8 SHIP_SOON · 5 EXPLORE · 3 MOONSHOT · 1 CUT.

The discipline that decided every verdict: an idea ships only if it can be **grounded** (tied to real audio/MIDI/library/event evidence, citation-resolvable) or is honestly a **creative-generative** surface where invention is the point (naming a set, a greeting frame). The recurring kill-shot below is the same one over and over — *a primitive named in the pitch doesn't exist yet, or it leans on the engine's documented weak axis (live beat/phrase tracking, crowd perception). A friend who guesses is worse than one who shuts up.*

---

## 1. THE TOP 10 — the ones to actually consider building

### 1. Drop-On-Cue Pilot — `19` (n5 f4 m5 w5) · SHIP_SOON
**Pitch:** When the pill picks the next track, it doesn't just say "play this" — it names the exact hot-cue to ride in on and the blend window to start, because the Vibe Judge scored the harmonic/bass-collision fit of *that cue region*, not the whole track.
**DJ moment:** Outgoing track 32 bars from outro; the pill surfaces a candidate AND lights its intro cue — "load this on cue 2, it's bass-clear and 8A→8A, start the blend in the next 16." You hit load, drop on the named cue, the Judge already cleared the collision.
**Primitives:** CLAP what-plays-next pill × CUE-DETR auto-cue engine × deterministic Vibe Judge.
**Verdict reasoning:** The cue-region + key match is fully groundable and citable. The trap is the "exact bar to start the blend" sub-claim — live downbeat/phrase alignment between two playing decks is the Judge's weakest axis. Scope v1 to cue-region + blend-*window*; let the exact live bar abstain, or live only in Viber/prep where ANLZ beatgrid is known. Bass-collision per *region* is net-new torch-free DSP (CUE-DETR gives boundaries, not a low-band profile).
**Smallest proof:** Offline, no live audio, no Gemini, zero cost. ~20 known-good human transitions. Per incoming track: CUE-DETR regions → per-region Camelot + a prototype sub-200Hz RMS collision score against the outgoing tail → have the Judge score region-fit vs whole-track-fit. Win: region-level scoring agrees with the human-chosen mix point measurably more than whole-track, and the Judge abstains on the ambiguous ones.

### 2. Learning Your Tells — `19` (n5 f4 m5 w5) · STRONG
**Pitch:** A real friend learns your habits — "you always rush the bass swap," "you let breakdowns run too long." Accumulate detected-event *patterns* into the long-term profile (recurring early bass-EQ-up before the phrase boundary; breakdown durations over your own median) and let the coach name YOUR pattern by name, with the count — only once enough grounded repetitions make it a real pattern.
**DJ moment:** The third time this session you do the thing you always do, the co-host names it as your habit — with the tally.
**Primitives:** phrase_boundary + breakdown_kick_kill + kick_swap detectors × MIX_MOVE timing × long-term profile aggregation × consent gate.
**Verdict reasoning:** Count/duration tells (breakdown-over-median, drift) are safe. The slop exposure is phrase-relative *timing* tells — if the bar grid is off, "you rush the bass swap" inverts into a false accusation, the trust-killer. Also slow-burn UX: reads empty for early users until enough sessions land.
**Smallest proof:** Instrument ONE count-based tell end-to-end — breakdown-duration-vs-personal-median — across 3+ recorded sessions. Confirm the profile builder accumulates past MIN_CITATIONS_PER_TENDENCY, the coach references it by name with real cited timestamps, AND a control session of normal behavior produces ZERO false tells. Only then layer in bar-relative timing behind a tighter citation floor.

### 3. In-Jokes From Past Sets — `18` (n4 f4 m5 w5) · STRONG
**Pitch:** When live audio + now-playing resolves to a track (or a vibe via CLAP) that triggered a memorable moment before, the co-host calls back: "bu yine o Boris Brejcha açılışı — geçen sefer burada full karanlığa gömmüştün." The single feature that turns "voice assistant" into "friend who was there last time."
**DJ moment:** You drop a track or vibe you've played to memorable effect in a prior logged session.
**Primitives:** memory moments store (opt-in sqlite-vec) × CLAP track→track similarity × now-playing track_resolver × `VIBEMIX_RECALL_ENABLED` gate.
**Verdict reasoning:** Exact `track_id` match = confident callback, fully grounded. CLAP vibe-similarity is coarse — a confident "you've been here before" fired on a *different* track is exactly the slop class the product exists to kill. Hard gate: exact match = confident; vibe-only match = hedged phrasing or abstain. Watch repetition fatigue and the creepiness line.
**Smallest proof:** Two-session replay on one real user — flag moments in session A, replay session B's track-resolver + CLAP stream, log every callback that WOULD fire tagged by match type. Kaan ear-judges: do exact matches land as "friend who was there," and does vibe-only ever falsely fire "you've been here" on a wrong track?

### 4. Pre-Drop Hype Countdown (felt, not narrated) — `18` (n5 f3 m5 w5) · STRONG
**Pitch:** Wire `drop_predict` to the hype-man's BODY, not words: as the predicted drop approaches on a build, the mascot winds up and the voice does a friend's rising "hee-yaa… HERE WE GO" timed to the predicted bar — then SHUTS UP on the drop so it doesn't talk over your moment. The restraint at the drop is what makes it a friend, not a commentator.
**DJ moment:** The 16 bars before a hardtechno drop where the energy coils and you want someone losing their mind *with* you.
**Primitives:** drop_predict countdown × distortion_climb + acid_line_entry detectors × mascot rig anim × hype lens × in_flight gate.
**Verdict reasoning:** Hype anchored to a *predicted* bar slops hard if it fires early or into a fake-out breakdown ("HERE WE GO" with no drop = AI sounds deaf). Feasibility-gated: the DROP substrate (drop_predict.py, buildup/distortion/acid detectors) is currently STUBBED and there's no DROP in EventType — only BUILDUP/ENERGY_SHIFT. This is build-the-engine, not wire-finished-primitives. Cost is a non-issue (restraint = fewer TTS turns).
**Smallest proof:** Offline tape test before any voice — drop_predict over ~20 labeled buildup clips across 2-3 genres; measure bars-to-drop error and abstain rate. Gate: median error ≤1 bar AND zero confident-but-wrong fires on fake-out breakdowns. Only then prototype the felt channel as mascot-anim-only (no voice), judge the wind-up-then-silence beat by ear.

### 5. Mastered-Moment Capture — `18` (n5 f4 m5 w4) · STRONG
**Pitch:** The Earned Wall already needs a CITED live demo to unlock "Mastered." The instant a competency masters, clip the exact audio region of the move and write it back as a named hot-cue/Serato marker — your skill-tree literally bookmarks the proof in your own library.
**DJ moment:** You nail a long EQ-swap blend cleanly for the first time; "that's your Mastered transition," and a marker named `mastered: eq-swap 0529` appears on the outgoing track to re-study later.
**Primitives:** Earned skill-tree (cited Mastered unlock) × CUE-DETR boundary snap × cue export (Serato/Rekordbox/Mixxx universal carrier).
**Verdict reasoning:** The window MUST come from the skill_recognizer citation (MIDI/event timestamps), not CUE-DETR — CUE-DETR detects song *structure*, not "the bars where you bass-swapped." Use it only to snap the cited window to the nearest musical boundary. Writing into the user's real library is destructive-adjacent: additive + reversible in its own marker namespace, never clobber existing cues, land on the correct deck's track at the right deck-relative time.
**Smallest proof:** Fully offline — one recorded WAV + its events.jsonl, find a Mastered event with a citation timestamp, snap to nearest CUE-DETR boundary, emit ONE named hot-cue into a COPY of a real Serato file via the universal Markers2 carrier. Re-open in Serato: marker on the right bars, existing cues untouched, reversible.

### 6. Why-It-Worked Receipts — `18` (n4 f5 m5 w4) · SHIP_SOON
**Pitch:** Make the debrief timeline replayable WITH its receipt — tap any transition and see the grounded reason it landed: "8A→8A, bass-clear, 6-bar blend." Turns "good set" into auditable craft.
**DJ moment:** Post-set you scrub the timeline; the two blends you felt unsure about get a real verdict, not a pat on the head.
**Primitives:** debrief window × Vibe Judge stored verdicts × evidence/citation registry.
**Verdict reasoning:** Highest feasibility in the deck (f5) — receipts are post-session, deterministic, rendered from stored verdicts, no TTS/Gemini pressure. The risk is coverage sparsity: the Judge abstains often and only deeply grounds harmonic + bass-collision, so a real timeline can read "abstained / abstained / 9-10 / abstained." Copy must stay "harmonic-cleanliness" framed ("8A→8A, bass-clear"), never "great transition" (a taste claim it can't ground).
**Smallest proof:** Replay one real set's events.jsonl through transition_judge + evidence_registry offline, dump the verdict timeline as text, count confident-cited receipts vs abstains. If a 60-min set yields ≥6–8 dense correctly-grounded receipts, the wow holds; if mostly abstains, fix beat/phase coverage before building the UI.

### 7. The Comfort-Zone Callout — `18` (n5 f4 m5 w4) · STRONG
**Pitch:** A friend who knows your set tells you when you're coasting. Compare live taste-model role-pair scores + detected events against your long-term profile — N transitions all in safe Camelot neighbors at your median BPM with no LAYER_ARRIVAL surprises → "üç track oldu hep komşu key, bir risk al — sende o var." Grounded in detected harmonic distance + event monotony, never imagined audience boredom.
**DJ moment:** Mid-set plateau — three or four in-key, on-tempo blends in a row with nothing structurally adventurous.
**Primitives:** taste_model role-pair scores × long-term profile (median BPM/key) × harmonics distance × event_detector monotony.
**Verdict reasoning:** The risk is a false "coasting" read on a DJ whose aesthetic IS tight harmonic mixing at one BPM (deep/hypnotic techno) — one confident wrong read breaks trust. Threshold must be personalized against the long-term profile (profile_projection), never a universal baseline. Copy must dare-not-scold, fire rarely, cooldown-gated. Grounding itself is clean (asserts the operator's own move-monotony).
**Smallest proof:** Offline — run the deterministic detector (N consecutive ±1 Camelot-neighbor transitions within ±X BPM of the operator's median, zero PHASE/MIX_MOVE/LAYER_ARRIVAL) against 3–5 real DJs' events.jsonl, each scored against its own profile. Kaan eyeballs the fire/silence map: fires where a coach would say "take a risk," silent on intentional groove-holds.

### 8. Call It Before It Lands — `17` (n4 f3 m5 w5) · STRONG
**Pitch:** When the Judge computes a verdict on the ARMED transition (both lanes loaded, EQ/xfader move in progress) and the score is low with a real risk_flag (harmonic_clash, bass_collision), whisper the call a beat BEFORE the swap — "ooh, basslar çakışıyor, dikkat" — the way a friend who can see your hands grabs your shoulder. Abstain = silence. The thrill is prediction, not narration-after.
**DJ moment:** Track B cued, xfader easing across, bass EQ coming up — the instant the collision is mathematically locked but the room hasn't heard it.
**Primitives:** transition_judge (risk_flags + confidence + abstain) × event_detector TRANSITION_OPPORTUNITY + MIX_MOVE gate × evidence_registry.
**Verdict reasoning:** Predictive false-positives brush Invariant #3 — warning before the swap completes grounds on *predicted* operator intent. Fire low-score+risk on an armed transition the DJ then pulls off clean → cry-wolf nag = slop. Gate hard: both lanes confirmed loaded AND a directional EQ/xfader move already in progress AND high Judge confidence. TTS TTFT must land in the sub-beat window (MOSS-TTS-Nano ~71ms makes it viable; Gemini TTFT risky).
**Smallest proof:** Offline replay, no TTS/no live rig — feed a recorded session's MusicState + MIDI tape into the Judge at each TRANSITION_OPPORTUNITY and measure (1) ms of lead-time before the swap completes (is the pre-beat window real?) and (2) cry-wolf rate: of low-score+risk verdicts, how many fired on transitions executed cleanly. Promotes to SHIP_SOON only if a real lead-time window exists with acceptable false-positive rate.

### 9. B2B Mode — trade the mix with the AI as partner — `17` (n5 f3 m4 w5) · STRONG (split-feasibility)
**Pitch:** A back-to-back where the co-host TAKES a turn: it picks the next track (CLAP + Judge), tells you the cue point and EQ plan out loud, you execute — or in a full-auto round it drives a 30s blend itself via MIDI, then hands the deck back. A real two-DJ dynamic, not a recommendation list.
**DJ moment:** Stuck for ideas at 02:00 — "your turn" — and the co-host calls the next track and the move, taking genuine creative ownership of one transition.
**Primitives:** next_suggestion.py pill × Vibe Judge × CUE-DETR cue points × MIDI maps × persona lenses.
**Verdict reasoning:** Bundled split-feasibility. The headline ("AI takes the deck") needs the full-auto half, which breaks a missing primitive — **MIDI is decode/READ-only today, no outbound write path** — and strains the moat at its highest blast radius: a late/ungrounded automated fader move isn't slop in the ear, it's slop on the speakers in front of a crowd. LiveKit+Gemini latency makes beat-accurate auto-mixing unsafe. The read-only verbal half is fully grounded and cheap (one Gemini turn per handoff) — ship that; the auto-drive is the moonshot.
**Smallest proof:** Ship ONLY the read-only verbal-partner half, no MIDI write. Practice session: pill picks track (CLAP), Judge scores (abstain if unsure), CUE-DETR supplies the cue, Gemini voices it as a B2B partner ("my pick — load X, drop it on the cue at the second breakdown, bring the bass in after 16"). 3–4 DJs do a 20-min alternating set. Measure: (a) feels like a partner vs a panel, (b) 100% of spoken cue/EQ claims grounded, (c) emotional reaction. If the verbal B2B lands the "holy shit," the auto-drive earns a separate write-MIDI spike — gated to practice only.

### 10. Gas Me Up With Receipts — `17` (n4 f4 m5 w4) · SHIP_SOON
**Pitch:** On a clean transition (Judge state=judged, high score, zero risk_flags) the hype-man doesn't say generic "sick mix" — it cites the win: "that was a perfect 8A→9A blend AND you killed the kick on the breakdown first, textbook." Specificity is the whole emotional payload; the citation-strip guarantees it never fabricates the detail.
**DJ moment:** The crowd-pleasing harmonic blend you nailed cleanly — the co-host names the exact two things you did right.
**Primitives:** transition_judge (judged + score) × Camelot table (LLM never computes) × breakdown_kick_kill detector × citation grounding Invariant #2.
**Verdict reasoning:** The harmonic half (8A→9A from the Camelot table + Judge score) is fully grounded today. "You killed the kick first" is only safe if that EQ move is a REGISTERED EvidenceRegistry field — if not, citation grounding strips it and the warm line collapses to the generic ack-bank, the exact bot-slop the idea promises to kill.
**Smallest proof:** In the replay harness, take one recorded clean-transition session and assert the generated HYPE line (a) contains the literal Camelot pair + Judge score, and (b) every clause survives the citation linter with zero strips. If the kick-kill clause strips, that proves it isn't a citable evidence field yet — ship the harmonic+Judge specificity now, gate the EQ-move detail behind a verified MIX_MOVE evidence field. No live ear-pass or Gemini spend.

---

## 2. SHIP-SOON SHORTLIST — buildable now on existing primitives

Filter: verdict SHIP_SOON, OR (feasibility ≥4 AND moat_fit ≥4). Mapped to the closest gold-mine gap id where one fits.

| Idea | total | gap id | Why it's near-term |
|---|---|---|---|
| **Why-It-Worked Receipts** | 18 | **g8** (judge-voice) · **g45** (shareable recap) | Pure offline render off stored Judge verdicts + evidence registry; no live path, no per-turn cost. The fastest "moat made visible" win. |
| **Drop-On-Cue Pilot** (region v1) | 19 | **g23** (cue moat) · g8 | Cue-region + key grounding ships now; defer the exact live bar. The headline wow of the whole forge. |
| **Learning Your Tells** (count tells only) | 19 | — | Count/duration family (breakdown-over-median) is groundable today; bar-timing family waits. |
| **In-Jokes From Past Sets** (exact-match only) | 18 | — | Exact track_id callback ships now off memory + track_resolver; vibe-match hedges/abstains. |
| **Mastered-Moment Capture** | 18 | **g23** (cue moat) | All primitives exist; the only new work is the additive/reversible marker write + deck-aware timestamping. |
| **The Comfort-Zone Callout** | 18 | — | Deterministic monotony detector + personalized threshold; LLM only voices. |
| **Gas Me Up With Receipts** | 17 | g8 | Harmonic+Judge specificity ships now; EQ-move detail gated on an evidence field. |
| **The Receipt (scorecard PNG)** | 17 | **g45** (shareable recap) | Static render off one session's events.jsonl + EvidenceRegistry; the share-mechanic that IS the moat. |
| **Resident A&R** | 17 | — | Set-difference + cosine + k-means on the already-embedded library; deterministic, torch-free, zero Gemini. The clearest Pro-tier value. |
| **Daily Challenge** | 17 | g45 | Deterministic engine is referee (not the LLM); Gemini only voices the prompt + completion. Wordle-grid share card drives the waitlist. |
| **Voice of the Skill Tree** | 17 | — | Inject the near-Mastered competency into the coach prompt; needs a no-mute fallback floor. |
| **The Honest "I Didn't Catch That"** | 17 | g8 | Pure wiring + a 4–6 line cooldown-gated phrase bank; turns the abstain into a trust feature. |
| **Read-The-Room Energy Arc** | 17 | — | Windowed arc score from existing detector stream; Gemini voices an already-correct verdict (Judge pattern). |
| **Set Shape Live** | 16 | g45 | Join of already-grounded objects (planned curve + live phases) — no extra Gemini calls for the chart. |
| **Form-Correction Coach** | 16 | — | Single rare grounded sub-clash hygiene cue off the existing bass-collision detector; high-precision / low-recall. |
| **Taste-Tuned Pill** | 16 | — | Re-rank the pill through taste + Judge as soft penalties (not hard vetoes); all deterministic, local. |
| **Welcome-Back Continuity Cold-Open** | 16 | — | Cold-open via memory_recall + free local MOSS-TTS; degrade to a clean generic greeting when no grounded history. |
| **Set Namer & Liner Notes** | 15 | g45 | Generative-OK; one local Codex call through stop-slop/negative_dict, human-in-the-loop, never auto-publish. |
| **Skill Tree Mastery Demotion** | 15 | — | Decay computes locally over existing logs; instrument silently first to calibrate N before any user-facing demotion. |

---

## 3. MOONSHOTS worth a research spike — and exactly what we lack

### Your DJ Twin — `15` (n4 f2 m4 w5) · MOONSHOT
Over many sessions the profile + taste model + tells distill into "this is how YOU mix," and the co-host predicts your NEXT move before your hand moves.
**WHAT IT REQUIRES we lack:** a *predictive* layer over (deck_context → next-MIDI-action) sequences that doesn't exist — and the perception-honesty fence: a predicted operator action is NOT a detected event, so voicing it as fact is pure hallucination (the release-blocker). Plus a brutal cold-start (sparse single-user sequences, possibly genre-unstable).
**Spike:** Offline backtest before any voicing — log (deck_context snapshot → actual next MIDI move). After ~10–15 real sessions, a dead-simple numpy k-NN/frequency model; measure top-1 accuracy vs a most-common-move base-rate. Voice nothing unless it beats base-rate by an uncanny margin (target >2×) with a confidence-floor abstain like drop_predict.

### Live Audience Co-Sign (QR → real-time grounded hype feed) — `13` (n4 f2 m3 w4) · MOONSHOT
A read-only QR opens a public web view of the SAME grounded event stream the co-host sees — "drop incoming," "this blend is clean (Judge)" — so the crowd reacts WITH the AI's verified calls.
**WHAT IT REQUIRES we lack:** breaks Invariant #4 (one local socket, 127.0.0.1:8765, test-enforced) and the local-first posture — needs a brand-new always-on multi-tenant relay (room codes, N-phone fan-out, abuse/moderation, venue-consent liability) that doesn't exist, blowing past the ~50 €/mo envelope. And a grounded pre-drop call must reach phones BEFORE the audible drop; venue wifi latency can make it land late in front of a crowd — the exact slop the product blocks, now broadcast.
**Spike:** Don't build the venue relay first. Replay one recorded session's cited ws_bus stream to a single phone browser over the same LAN; measure end-to-end event-to-phone latency, specifically whether a DROP/PHASE call lands before the audible drop. Only sub-second pre-drop delivery for one viewer justifies the fan-out investment.

### Room-Read Re-Rank — `11` (n4 f1 m2 w4) · MOONSHOT
A torch-free crowd-energy classifier makes "room reaction" a real signal that re-ranks the pill.
**WHAT IT REQUIRES we lack:** vibemix captures the BlackHole master *loopback* (clean digital program audio) — **there is no crowd/applause in the bytes to classify.** Needs a NEW second room-mic input (new capture path, wizard routing, mic-gating vs the AI's own voice and music bleed) AND a crowd-hype model that doesn't exist torch-free. Worst: it would feed the abstain-first Judge — the flagship grounded surface — so an unreliable guess manufactures slop where the moat lives. Breaks torch-free + grounding + the anti-slop gate.
**Spike:** Before any model, prove the phenomenon is even capturable — temporary room-mic tap alongside the master loopback on a real rig, hand-label "floor lifted" moments, test whether ANY cheap torch-free feature (band-limited RMS swell, transient-density spike, master-minus-mic residual) separates true crowd swells from loud breakdowns. If a dumb heuristic can't beat chance, no ONNX classifier will — CUT.

---

## 4. By-lens highlights — the single best idea per lens

| Lens | Best idea | total | Why it wins the lens |
|---|---|---|---|
| **Novel Recombinations** | **Drop-On-Cue Pilot** | 19 | Three primitives collide into a capability none has alone — and it's the single highest-wow idea in the entire forge. |
| **Emotional / Social** | **Learning Your Tells** | 19 | The deepest "this thing KNOWS me" hit, and fully grounded on accumulated detected-event patterns — no faked perception. |
| **Viral / Growth** | **The Receipt (cited scorecard PNG)** | 17 | Turns the anti-slop grounding into the share unit — every word is a real citation, abstains shown honestly; the moat *is* the marketing. |
| **Monetization** | **Resident A&R** | 17 | "Do the prep I hate, with receipts" — deterministic, torch-free, zero Gemini cost; the clearest willingness-to-pay wedge (DJs forget their own crates). |
| **Cross-Domain Steals** | **Daily Challenge** | 17 | Wordle's shareable loop where the deterministic engine — not the LLM — is the referee; verified completion, not self-report. |
| **Honest Moonshots** | **B2B Mode** | 17 | A category-defining swing whose read-only half ships now and whose auto-drive half is a clean, separable write-MIDI spike. |
| **(Anti-pattern lens)** | **Mind-Reader Crowd Hype** *(REJECTED)* | 6 | The best thing this lens produced is the documented refusal — naming the trap keeps the discipline honest. |

---

## 5. CUT list — considered and set aside

- **Mind-Reader Crowd Hype Predictor** — `6` · CUT. Ungroundable: vibemix hears the master, not the audience. "Reading the room's mood" forces fabricated crowd-perception with no sensor — breaks Invariant #3 and #2. Kept documented as a named anti-pattern, not a recommendation.

**EXPLORE (parked, not cut — need a spike to settle a single open question):**
- **Co-Pilot Handoff** — `16` · "fits the room" must reduce to "fits YOUR trajectory" (CLAP cosine vs trailing audio); also leans on deck-loaded-but-silent detection that's mid-flight in git.
- **Dare Me** — `18` · the named trigger TRANSITION_OPPORTUNITY doesn't exist; the taxonomy is retrospective, and a dare needs forward-looking phrase prediction (weakest muscle). Prove the grounding offline before building the live trigger.
- **The Save Lane** — `14` · latency physics: the rescue chain lands after the wreck self-resolves; salvage only the deterministic alarm half and measure detect-to-nudge latency.
- **Co-Streamer Banter Mode** — `14` · inter-voice "glue" is the AI faking a reaction to another AI — the single most slop-prone format; constrain glue to a deterministic template bank or CUT.
- **Engine Eval Line** — `13` · a live "set health" bar has no objective ground truth; MusicState.rms is gain-confounded (fader artifact), risking *numeric slop* that passes the citation linter. Rescope to the post-set debrief energy-arc chart.

---

## 6. Full table — lens · idea · kind · grounded · n f m w · total · verdict

| Lens | Idea | Kind | Grounded | n | f | m | w | total | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| Novel Recombinations | Drop-On-Cue Pilot | recombination | fully | 5 | 4 | 5 | 5 | **19** | SHIP_SOON |
| Emotional/Social | Learning Your Tells | feature | fully | 5 | 4 | 5 | 5 | **19** | STRONG |
| Emotional/Social | In-Jokes From Past Sets | recombination | fully | 4 | 4 | 5 | 5 | **18** | STRONG |
| Emotional/Social | Pre-Drop Hype Countdown | experience | fully | 5 | 3 | 5 | 5 | **18** | STRONG |
| Emotional/Social | Dare Me | growth | fully | 5 | 3 | 5 | 5 | **18** | EXPLORE |
| Novel Recombinations | Mastered-Moment Capture | recombination | fully | 5 | 4 | 5 | 4 | **18** | STRONG |
| Novel Recombinations | Why-It-Worked Receipts | recombination | fully | 4 | 5 | 5 | 4 | **18** | SHIP_SOON |
| Emotional/Social | The Comfort-Zone Callout | feature | fully | 5 | 4 | 5 | 4 | **18** | STRONG |
| Emotional/Social | Call It Before It Lands | recombination | fully | 4 | 3 | 5 | 5 | **17** | STRONG |
| Moonshots | B2B Mode | moonshot | partly | 5 | 3 | 4 | 5 | **17** | STRONG |
| Emotional/Social | Gas Me Up With Receipts | experience | fully | 4 | 4 | 5 | 4 | **17** | SHIP_SOON |
| Emotional/Social | Read-The-Room Energy Arc | feature | fully | 4 | 4 | 5 | 4 | **17** | STRONG |
| Viral/Growth | The Receipt (scorecard PNG) | growth | fully | 4 | 4 | 5 | 4 | **17** | SHIP_SOON |
| Monetization | Resident A&R | monetization | fully | 4 | 5 | 4 | 4 | **17** | SHIP_SOON |
| Cross-Domain | Daily Challenge | growth | fully | 4 | 4 | 5 | 4 | **17** | STRONG |
| Novel Recombinations | Voice of the Skill Tree | recombination | fully | 4 | 5 | 5 | 3 | **17** | SHIP_SOON |
| Emotional/Social | The Honest "I Didn't Catch That" | experience | fully | 4 | 5 | 5 | 3 | **17** | STRONG |
| Novel Recombinations | Set Shape Live | recombination | fully | 4 | 4 | 4 | 4 | **16** | STRONG |
| Novel Recombinations | Crate Gap Finder | recombination | fully | 4 | 3 | 5 | 4 | **16** | STRONG |
| Novel Recombinations | Co-Pilot Handoff | recombination | fully | 4 | 3 | 5 | 4 | **16** | EXPLORE |
| Viral/Growth | Proof-of-Play badges | growth | fully | 4 | 3 | 5 | 4 | **16** | STRONG |
| Cross-Domain | Form-Correction Coach | recombination | fully | 3 | 4 | 5 | 4 | **16** | STRONG |
| Novel Recombinations | Taste-Tuned Pill | recombination | fully | 3 | 5 | 5 | 3 | **16** | SHIP_SOON |
| Emotional/Social | Welcome-Back Continuity Cold-Open | experience | partly | 4 | 5 | 4 | 3 | **16** | SHIP_SOON |
| Emotional/Social | Your DJ Twin | moonshot | partly | 4 | 2 | 4 | 5 | **15** | MOONSHOT |
| Novel Recombinations | Set Namer & Liner Notes | recombination | generative-ok | 3 | 5 | 4 | 3 | **15** | STRONG |
| Cross-Domain | Skill Tree Mastery Demotion | growth | fully | 3 | 5 | 4 | 3 | **15** | STRONG |
| Cross-Domain | Co-Streamer Banter Mode | experience | fully | 4 | 3 | 3 | 4 | **14** | EXPLORE |
| Novel Recombinations | The Save Lane | recombination | fully | 4 | 3 | 4 | 3 | **14** | EXPLORE |
| Viral/Growth | Live audience co-sign | moonshot | partly | 4 | 2 | 3 | 4 | **13** | MOONSHOT |
| Cross-Domain | Engine Eval Line | feature | partly | 4 | 3 | 3 | 3 | **13** | EXPLORE |
| Novel Recombinations | Room-Read Re-Rank | moonshot | ungroundable | 4 | 1 | 2 | 4 | **11** | MOONSHOT |
| Cross-Domain | Mind-Reader Crowd Hype (REJECTED) | moonshot | ungroundable | 2 | 1 | 1 | 2 | **6** | CUT |

---

**The through-line:** the two highest-scoring ideas (Drop-On-Cue Pilot, Learning Your Tells) and the three fastest-to-ship (Why-It-Worked Receipts, The Receipt, Resident A&R) all share one trait — they make the *grounding itself* the product. The moat isn't a better prompt; it's that vibemix can cite. Every "holy shit" here is a receipt the DJ can check, or an honest silence when the engine can't. The ideas that died, died because they asked the AI to perceive something it has no sensor for. Hold that line.
