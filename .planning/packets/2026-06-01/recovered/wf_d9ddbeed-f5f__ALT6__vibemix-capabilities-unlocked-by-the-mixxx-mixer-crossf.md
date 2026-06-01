# vibemix capabilities unlocked by the Mixxx mixer/crossfader-curve spec

## IDEA 1 — `mixer_physics.py`: the "Move Effect" engine that KILLS R-SLOP (the big one)

**Name:** Grounded Move-Effect Resolver

**What it unlocks:** The #1 live slop bug — the co-host claiming "you rode the crossfader and brought the energy up" with no proof of what the move *did* to the audio. A new import-light helper `src/vibemix/state/mixer_physics.py` implements the clean-room Mixxx law: `mixxx_xfade_gains(position, transform, mode)` (additive + const-power + reverse, `enginexfader.cpp:16-84`) and `db_taper_gain(pos, min_db, max_db, neutral)` (`controlbehavior.cpp:170-229`). Given a known move (`xfader 64→112`, or `line-fader-A up 0.4→0.9`) read off the `deck_mixer` snapshot, it computes the **expected orientation-gain delta in dB** for each deck. Then it checks that prediction against the **measured `audio_delta`** vibemix already attaches to the `ai_message` row (`deck_context.py:1661` `volatile=...+audio_delta+audio_window`). The claim is licensed ONLY when computed-expected-sign ∧ measured-sign agree and magnitudes are within tolerance — exactly Invariant #2/#3.

**vibemix integration point:** New `expected_move_effect(move, deck_mixer, audio_window) -> ExpectedEffect` called from `live_claim_policy` / `apply_live_claim_guard` (`deck_context.py:2239`). It upgrades the guard from "I won't claim that move did X" (`LIVE_MOVE_EFFECT_HELD_REPLY`) to affirmatively *licensing* the causal claim. Replaces the crude 0-127 bucket `_xfader_factor` (`deck_context.py:3254-3267`) with the real curve. Emits an `EvidenceRegistry` citation like `[move_effect: xfaderB +17dB ✓measured +14dB]`.

**The DJ moment:** Mid-blend, the co-host says *"that crossfader sweep just brought deck B up about 15 dB — the new track's now the loud one, clean handoff"* — and it's true because both the curve math and the RMS rise agree. No more "you brought the faders up" when `recent_moves=[]`.

**Grounded?** Yes — the deepest possible grounding. The claim is double-gated: predicted-from-physics AND confirmed-in-audio. This is the whole anti-slop thesis made computable.

---

## IDEA 2 — Move-Intent Classifier: "you cut it" vs "you blended it" vs "you bumped the gain"

**Name:** Mixer Gesture Discriminator

**What it unlocks:** Today vibemix can't tell *which tool* did the work — line fader vs crossfader vs trim/pregain are different skills in the Earned tree, but the engine collapses them. With the full gain-stage chain (pregain × volume-taper × orientation-gain, `enginepregain.cpp` + `enginemixer.h:167-176`), `mixer_physics` can attribute a measured level change to its *most likely source*: a sharp edge-of-travel jump with `transform`-curve signature ⇒ crossfader cut; a smooth dB-taper ramp ⇒ line fader; a level shift with NO fader/xfader MIDI ⇒ trim/ReplayGain. It also reads the crossfader *curve mode* — an additive/scratch-curve cut feels and sounds different from a const-power blend, and the math distinguishes them (additive = off-deck stays near full until the very end; const-power = `sqrt`-normalized 0.707 crossover).

**vibemix integration point:** Feeds `event_detector` — turns the generic `MIX_MOVE` into typed sub-events (`MIX_MOVE_CUT`, `MIX_MOVE_BLEND`, `MIX_MOVE_GAIN_RIDE`). Reads the controller's xfader-curve setting from the matched profile in `midi/profiles/` (the 10-controller catalog) so it knows whether that DJ's hardware is on a sharp or smooth curve. Decorates the `recent_moves` list with `tool` + `curve_mode`.

**The DJ moment:** *"Nice — you didn't slam the crossfader, you rode the line fader up over four bars. That's the smoother way to bring a vocal in."* The co-host names the technique, not just the result.

**Grounded?** Yes — attribution is from MIDI source + the curve-shaped level signature + measured audio. It abstains (falls to generic "the level came up") when the signature is ambiguous, per honest-null.

---

## IDEA 3 — Faithful Practice Mixer in MiniDeck (the own mini-DJ / learning engine)

**Name:** True-Curve Practice Mixer

**What it unlocks:** Upgrades `MiniDeck` (`miniplayer.py:99`) from a toy (one global `xfader` + fixed `cos/sin` `_equal_power_gains` at `:69-79`) into a faithful practice rig that matches real hardware. Add per-deck volume faders (the `ControlAudioTaperPot(-20,0)` dB taper), the real 3-mode crossfader law with selectable `transform` (curve sharpness) and `mode` (additive vs const-power), orientation routing (LEFT/RIGHT/CENTER, where center bypasses the xfader), and per-block **ramped gain** (`applyRampingGain` anti-click, one `np.linspace` multiply). The student can now practice the *same* mix-move physics in the trainer that their controller produces live — and because the engine knows the exact gains, every practice move is perfectly gradeable.

**vibemix integration point:** Extend `DeckState` (`miniplayer.py:83-96`) with `vol_a`, `vol_b`, `xfader_curve`, `xfader_mode`; rewrite `_equal_power_gains` → `mixxx_xfade_gains` (the SAME `mixer_physics` clean-room as Idea 1 — one module serves both the trainer and the live gate); `render_block` (`:130-135`) computes `gain_a = vol_a · g_left`, `gain_b = vol_b · g_right` ramped. Set the trainer's default `transform`/`mode` from the student's matched `midi/profiles/` controller so practice mirrors their gear. Tests at `tests/audio/test_miniplayer.py` migrate off the cos/sin pin.

**The DJ moment:** A beginner drags a practice crossfader and *hears* the additive-curve hot center vs the const-power smooth blend — and the co-host coaches *"feel that? on your DDJ-FLX4's sharp curve, the other deck doesn't drop until the last 10% — that's why your cuts sound abrupt."*

**Grounded?** Yes — the practice audio IS the ground truth (vibemix renders it), so every claim about the practice mix is exact by construction.

---

## IDEA 4 — Earned competency: "Clean Gain Staging" + "Crossfader Curve Literacy"

**Name:** Gain-Staging & Curve-Mastery skill nodes

**What it unlocks:** Two new evidence-gated competencies in the Earned skill-tree, now *gradeable* because the physics exists:
- **Clean Gain Staging** — did the incoming deck arrive at unity-matched loudness (not +6 dB hot from the additive center, not buried)? `mixer_physics` computes the summed-bus level through the blend and checks it stays inside a headroom band (mirroring Mixxx's `kMaxTotalGainBySpeed=0.9` ≈ -1 dB clip guard). "Mastered" requires a *cited* live demonstration: a real transition where measured master LUFS stayed flat across the handoff.
- **Crossfader Curve Literacy** — does the student use the right curve for the job (sharp/additive for cuts & scratches, const-power for long blends)? Graded from the curve-mode + gesture data of Idea 2.

**vibemix integration point:** New competency definitions in the Earned skill-tree; lessons fill them to "Competent", and the `skill_recognizer` live call-site (already wired in `coach_loop`) credits "Mastered" only on a cited in-set demonstration — using the `mixer_physics` level/headroom evidence as the citation source.

**The DJ moment:** Debrief: *"You unlocked Gain Staging → Mastered. Track 7 into track 8: your line-fader ride kept the master within 1 dB the whole blend — that's pro headroom discipline."* With the receipt.

**Grounded?** Yes — both nodes are unlocked only by cited, measured live evidence (LUFS-flat handoff, correct curve-for-context), never by self-report.

---

## IDEA 5 — Debrief "Handoff Anatomy" receipt: the crossfade curve as a visual proof

**Name:** Transition Anatomy Card (debrief)

**What it unlocks:** For each track transition, the debrief window renders the *actual* handoff: a dual-gain curve (deck-A orientation gain falling, deck-B rising) reconstructed from the logged MIDI fader/xfader positions run through `mixxx_xfade_gains`, overlaid with the *measured* per-deck band energy from the `audio_window` snapshots. Where predicted-gain and measured-energy track together = a green "clean" segment; where they diverge (e.g., deck B's gain rose but its energy didn't because its EQ low was killed) = a flagged moment with the explanation. Crossover duration, overlap bars, and whether the center got hot (+6 dB additive) all read straight off the curve.

**vibemix integration point:** Debrief window (port 8766); consumes the per-transition `recent_moves` + `audio_window` rows; renders via the existing energy-arc UX. The curve reconstruction is pure `mixer_physics` (no new deps, numpy only).

**The DJ moment:** Post-set, the DJ scrubs to a transition and *sees* their own crossfade as a shape — *"here your blend was 6 bars but you spent 4 of them at the hot center, that's the muddy stretch I called out live."* The receipt for the live reaction.

**Grounded?** Yes — every point on the rendered curve is either a logged MIDI position (the move) or a measured audio value (the effect); the divergence flags ARE the grounding check made visible.

---

## BONUS — IDEA 6 — Cue-vs-Program split awareness ("you're cueing, not mixing yet")

**Name:** PFL / Headphone-Cue Detector

**What it unlocks:** From the PFL/head-mix/split routing spec (`enginemixer.cpp:387-435`), vibemix learns the *cueing* workflow: a deck with its PFL/cue toggle on but its volume/crossfader still down is being **previewed in the cans**, not played to the room. If the controller exposes cue state over MIDI (in the `midi/profiles/` map), vibemix stops mis-reading "deck loaded + low fader" as a botched mix and instead recognizes deliberate prep — and can coach the cueing itself (head-mix balance, beatmatch-in-headphones).

**vibemix integration point:** A `pfl`/`cue` field on `DeckState`; consulted by `event_detector` and `apply_live_claim_guard` to suppress the false "you brought a deck in" claim when the deck is PFL-only (program gain still ~0). New micro-competency: "Cue & Prep" in the Earned tree.

**The DJ moment:** *"Good — you've got track 9 cued in your headphones and beatmatched before touching the fader. That's the prep discipline most beginners skip."*

**Grounded?** Yes — gated on real MIDI cue-toggle state + measured ~0 program-bus contribution for that deck; abstains entirely if the controller doesn't report PFL.

---

**Through-line:** one clean-room `src/vibemix/state/mixer_physics.py` (clean-room of `enginexfader.cpp` + `controlbehavior.cpp` + `enginepregain.cpp`, ~30 lines, numpy-only, zero new deps) is the keystone — it backs the live R-SLOP kill (1,2,6), the practice mixer (3), the Earned nodes (4), and the debrief receipt (5). The shared physics is what converts "the AI guessed what the move did" into "the AI computed what the move did and confirmed it in the audio."

Cleanup done: deleted `/Users/ozai/projects/dj-set-ai/_mixxx_probe.txt` and `/Users/ozai/projects/dj-set-ai/_mx_grep.txt`.
