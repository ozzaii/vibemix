# CODEX_READY — Technologic ROBOT voice on the PILL streak/combo (gamification voice)

> **Proof-ledger:** anchors 4/4 verified @ working tree (pill streak field `suggestion.py:1391-1404`, combo line `context_compiler.py:637-678`, combo `decision_runtime.py:397-414`, robot voice recipe proven this session) · premise HOLDS (pill already TRACKS streak/combo but emits it as **text only — no voice**) · invariants clean (pill is Inv#2-grounded → voice fires only on a REAL streak; anti-slop frequency-cap required) · the robot voice + de-gap recipe are ear-validated by Kaan this session.
>
> **Author:** Claude (voice-R&D session, 2026-06-04). **Status:** direction LANDED + recipe proven; NOT wired. **Companion to** [`CODEX_READY-CHATTERBOX-VOICE-WIRED.md`](CODEX_READY-CHATTERBOX-VOICE-WIRED.md) (the engine/wiring that this rides on). **For:** Codex A routing.

---

## TL;DR — the surface map (Kaan-decided, 2026-06-04)

Three voice surfaces, distinct identities:

```
LIVE co-host  = "pranker" voice (human friend)         -> tts_chain (wired, gated; see companion packet)
PILL streak   = Daft Punk "Technologic" ROBOT          -> THIS PACKET (gamification callouts)
LEARN tutor   = undecided (robot was floated then moved to pill)
```

The pill already computes a streak/combo and shows it as text ("combo xN"). **The move: give the combo/streak moment a VOICE — the Technologic robot, speaking a short verb-list callout** ("Combo, x five. Keep it. Run it."). Imperative-command cadence = gamification by nature; the robot identity is distinct from the live human-friend co-host. Anti-slop by design (short, earned, capped).

---

## ORGANIZER RECONCILIATION — read before wiring (cross-ref `PILL-FAFO-AND-LEVELUP.md`)

The robot voice recipe below is **locked and great** (Kaan ear-validated). But this packet says "the streak is already grounded, the voice is purely additive" and that is HALF true — and the wrong half is dangerous to wire blind.

**The number is grounded; what it COUNTS is wrong.** Verified at working tree: the streak increment (`suggestion.py:1370-1404`) is fed by `_selected_move_grade(suggestion)` → `grade.get("deserved")` — it ticks when **the engine rates its own un-played SUGGESTION** clean/deserved as you advance, NOT when you executed a transition a live judge graded from real audio. The FAFO workflow (8 agents, landed `3bacbe76`) confirmed this independently: "the engine applauding its own picks, one decision-class from 'sessions opened.'" The `context_compiler.py:670` "combo xN" atom is a grounded NUMBER, but it measures self-applause, not your mixing.

**So if we wire this killer robot voice to the CURRENT streak, we ship the worst case: a callout that SOUNDS earned but isn't.** A great voice celebrating the engine liking its own suggestions is slop in a better coat, and it is exactly the gamification the team just purged (`826fddc9`).

**The gate before the robot speaks (two parts, both from FAFO + Kaan's "live'dan ayrı" call):**
1. **Re-bind what the streak counts** to consecutive EXECUTED transitions a live judge graded clean from real audio, each tick resolving a cited `[ev:BEATMATCH_GRADED@…]` / `[judge:…]`. That live event does NOT exist on the bus today (practice-loop / recorder only) — so this is real plumbing, not a quick wire.
2. **Put it on a surface SEPARATE from the live eyes-off pill** (debrief / a deliberately-opened progress surface), per Kaan's decision. The robot streak callout is a post-or-aside gamification beat, never a competing voice over the live deck.

Sequencing: robot recipe = ✅ now (proven). Grounding re-bind + separate surface = the prerequisite before it speaks. Wire the voice to the *real* streak, on the *right* surface — then it is both sick and honest.

---

## The robot voice recipe (proven this session, ear-validated)

```
engine   : Chatterbox-Turbo MLX 8bit via mlx-audio  (same engine as the companion packet)
ref      : ~/.cache/vibemix/robot_voice_ref.wav
           = Daft Punk "Technologic" fanmade-acapella, 0:00 first 15s, sped x1.3 (atempo, pitch-preserved),
             NO UVR separation (cleaning stripped the vocoder character — Kaan: "temizlik mahvedebilir", confirmed)
temp     : 0.2   (sweet spot: 0.1 stutters/drags, 0.4 looser)
phrasing : verb-list staccato — "cue it, mix it, drop it, ride it"  (Technologic's own cadence)
```

### TWO HARD REQUIREMENTS (learned the hard way this session)

1. **De-gap is MANDATORY.** The Technologic ref is inherently gappy/slow → the clone inherits ~2/3 dead air (a long line rendered to **32s** of which only ~11s was speech). Punctuation tweaks did NOT fix it (comma vs period = same 32s). The fix is a **silence-trim post-process** on the rendered PCM:
   `ffmpeg -af "silenceremove=stop_periods=-1:stop_duration=0.2:stop_threshold=-38dB"` (32s → 11s, flowing). The pill-voice sink MUST run this (or an equivalent in-process trim) or the robot speaks "aralı aralı".
2. **Keep callouts SHORT.** The gappy/slow robot makes long text unbearable. Streak callouts must be ≤ ~8-10 words (a combo callout is naturally short — good fit). Long monologues are NOT for this voice.

---

## Where the pill streak/combo lives (anchors @ working tree)

- `src/vibemix/runtime/suggestion.py:1391-1404` — the streak is **incremented** here (`previous_progress["streak"] + 1`, clamped 0-999) and written into the pill `progress`. `:1354` seeds `"streak": 0`.
- `src/vibemix/intel/context_compiler.py:637-678` — builds the grounded **"combo xN"** evidence atom (`value=streak`, `unit="streak"`, `forbidden_phrases=("guaranteed streak","perfect streak")`). This is the grounded source the voice should cite.
- `src/vibemix/intel/decision_runtime.py:397-414` — `streak>=2 → "combo x{streak}"` in the decision bits.

So the streak is **already grounded** (Inv#2-safe) and milestone-detectable. The voice is purely additive: on a streak milestone, speak a short robot callout.

---

## Wiring sketch (for Codex — confirm call-site, then build)

1. On a streak **milestone** (NOT every increment — see frequency-cap below), build a short robot callout from the grounded combo value, e.g. `f"Combo, x {streak}. Keep it. Run it."` (verb-list staccato).
2. Render via `ChatterboxLocalTTS(ref=robot_voice_ref).synthesize_pcm(text, on_pcm)` (the provider from the companion packet already exposes `synthesize_pcm` — the non-LiveKit sink path, mirrors MOSS `local_tts.py:482`).
3. **De-gap** the rendered PCM (silence-trim) before it hits the audio sink.
4. Play through the pill's audio path (confirm the sink — the pill is a UI element; this may route through the existing tutor/event audio sink at `__main__.py:294` `moss.synthesize_pcm`, or need a small new pill-audio hook — Codex to trace).

---

## Open decisions / owner-gates (route these)

- **O1 (shared with companion packet) — `mlx-audio` into the project venv / shipped dep surface.** Apple-only; reintroduces `transformers` 5.x. Until installed, `chatterbox_available()=False` → no robot voice. Same gate as the live-voice packet.
- **Which milestones speak? (anti-slop — Kaan gate).** Speaking on EVERY combo increment = slop. Candidates: milestones (x3 / x5 / x10), or first-combo-of-session, or new-personal-best. Must be frequency-capped + earned. Inv#2: only on a REAL streak (the value is already grounded).
- **De-gap implementation.** Post-process the PCM with a silence-trim (ffmpeg or an in-process numpy gate), or pre-trim the ref. Recommend a reusable PCM silence-trim helper since the robot voice is inherently gappy on every line.
- **De-conflict with the live co-host voice.** The pill robot callout and the live co-host (pranker) could speak at once — needs a gate (don't talk over each other; the pill callout is a UI/gamification beat, the co-host is the in-ear friend).
- **LEARN tutor voice = still open** (robot was floated for learn, then reassigned to pill; learn tutor voice TBD).

## Invariants / safety

- Speech-RENDER + a new gamification trigger; does NOT touch reaction grounding. The streak value is already a grounded Inv#2 atom (`context_compiler.py:670`), so a streak callout is citable by construction.
- Anti-slop: short + capped + earned. A combo callout that fires every increment would be slop — the cap is the gate.

## Assets / proof-of-concept (this session, in `~/Downloads/`)

- Robot ref: `~/.cache/vibemix/robot_voice_ref.wav` (also `~/Downloads/LEARN_voice_robot_ref.wav`).
- Proof clips (robot voice, de-gapped): `VIBEMIX_anthem_take{1,2,3}.wav` ("Cue it, mix it, drop it, ride it … Vibe Mix. Run it."), `FRANCESCO_short_take{1,2,3}.wav`, `TECH_*` (temp ladder 0.1/0.2/0.4), `LEARN_intro_take*.wav`.
- Bench scripts: `~/.cache/vibemix-tts-bench/{tech,anthem,francesco3}.py` + the de-gap one-liner above.
- Memory: `project_chatterbox_turbo_tts_evaluated` (two-voice-split + de-gap block).
