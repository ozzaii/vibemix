# MAP — SVEN, the live co-host (the soul, Kaan's #1)

Read-only map of the intel→voice wiring on the **default master-only rig**, with
file:line evidence and REAL-vs-ASPIRATIONAL verdicts. Branch `ux-redesign-impeccable`.

> Note on memory drift: `CLAUDE.md` and MEMORY.md say `coach.py` lives at
> `src/vibemix/state/coach.py` and that `apply_live_claim_guard` lives at
> `intel/eq_move_model.py`. **Both are wrong on disk.** The live coach loop is
> `src/vibemix/runtime/coach.py`; `apply_live_claim_guard` is defined at
> `src/vibemix/state/deck_context.py:2999`. `intel/eq_move_model.py` is only the
> tiny DSP *predictor* (`predicted_band_gains`/`canonical_eq_move`), consumed by
> `deck_context.py`. Map the real files, not the docs.

---

## 0. TL;DR

On the **default master-only rig** (BlackHole 2ch, one stereo master mix,
Rekordbox internal mixer, no per-deck routing config) the only intel signal that
can put a *causal coaching claim* in Sven's mouth is the **EQ/filter move guard**
(`eq_move_model` → `_licensed_move_effect`), and that only fires **when a MIDI
controller is connected and emitting moves**. The two richer intel engines —
the **Vibe Judge** (`transition_judge`) and the **10-signal transition scorer**
(`transition_scorer` → `build_transition_verdict_voice_line`) — are both **hard
two-deck-gated and abstain on master-only by construction**, so they never reach
voice. `move_grade` never touches the live voice path at all.

Net effect = the believed **narrator→coach gap is REAL**: with no controller (or
on a pure audio-only capture, which is exactly what an automated 3-hour replay
will feed) Sven has **zero grounded coaching evidence** in the prompt and falls
back to the prompt's "coach the music's direction" branch — i.e. it narrates the
sound it hears, dressed as forward-looking coaching, because the prompt *tells*
it to coach but the *evidence* to coach with isn't there.

---

## 1. The wiring, end to end (master-only rig)

### 1a. Prompt already says "coach", not "narrate" — REAL

The identity is already a coach, by default, in BOTH modes:

- `src/vibemix/prompts/matrix.py:397` `SVEN_COACH_IDENTITY` — "You don't describe
  the music back to him … You COACH: every time you speak, you hand him one move,
  one read, or one forward-nudge."
- `matrix.py:436` `HYPE_INTERMEDIATE = SVEN_COACH_IDENTITY` — the coach identity is
  the default cell even in "hype" mode (the describe-license v4 hype cell was
  retired; see the bench memory `project_sven_prompt_bench_measured`: identity
  swap beat the describe-license +0.79 friend).
- `matrix.py:403` explicitly handles the empty-evidence case: *"When
  recent_moves[8s] is NONE … you coach the MUSIC's direction instead."* This is
  the line that becomes narration-in-coach-clothing when no intel reaches it.

**VERDICT: REAL but it is the *aspirational* half.** The prompt is not the gap.
The gap is that the prompt's "coach the forward" needs grounded lookahead/move
evidence, and on master-only that evidence is empty, so the model is left with
only "coach the music's direction" (= describe what you hear).

### 1b. The speak-gate — REAL, and it is a *value* gate, not a coach producer

`src/vibemix/runtime/speak_gate.py`:

- `decide_speak_gate(...)` (`speak_gate.py:119`) is the **pre-generation** gate:
  it decides whether an event is even worth asking the LLM about.
- Describe-bank-prone events `{HEARTBEAT, PHASE, LAYER_ARRIVAL, PHRASE_BOUNDARY,
  SUB_LAYER_ARRIVAL, TRACK_CHANGE}` (`speak_gate.py:30-39`) stay **silent unless a
  grounded voice payload is already attached** (`speak_gate.py:143-146`).
- The grounded payload keys it checks (`speak_gate.py:21-28`):
  `next_suggestion_voice_line`, `transition_verdict_voice_line`,
  `set_progress_voice_line`, `judge_evidence_line`.
- MIX_MOVE / TRANSITION_OPPORTUNITY / DROP / genre events fall through to
  `"event_priority"` → speak (`speak_gate.py:147`).
- Manual / KAAN_SPOKE always speak (`speak_gate.py:135-136`).
- Repeat-fingerprint suppression for recent identical events (`speak_gate.py:137-142`).

Call site: `coach.py:921-946`. If `not should_speak` → log `speak_gate` event +
trace `speak_gate_suppressed` + `continue` (no generation).

**Consequence on master-only with NO controller:** the only auto events are
HEARTBEAT/PHASE/LAYER_ARRIVAL/TRACK_CHANGE — all describe-bank — and the four
grounded payload keys are produced by engines that abstain on master-only (see
1d/1e). So Sven is **mostly silenced** at idle (this is *correct* anti-slop
behavior, Invariant #5), and on the rare event it does speak it has no grounded
coaching payload → narration.

### 1c. The EQ-move guard — REAL, the ONE signal that voices on master-only

`intel/eq_move_model.py` is a pure deterministic predictor (`predicted_band_gains`
at `:46`, `canonical_eq_move` at `:79`; biquad band-gain math, no audio inspection).

It is consumed live in `state/deck_context.py`:

- `_licensed_move_effect` (`deck_context.py:2153`) returns a `MoveEffectLicense`
  **only when prediction direction == measured band direction**
  (`deck_context.py:2192-2204`). Crucially the measured delta it uses is the
  **MASTER mix band delta** (`_move_effect_audio_delta_items` →
  `state.move_audio_delta` / `render_audio_delta_items`, `deck_context.py:2074-2087`)
  — **NOT per-deck audio.** So this works on a single stereo master mix.
- `render_move_effect_context` (`deck_context.py:2688`) emits the licensed token
  into the prompt with `rule=move_effect_prediction_and_measurement_agree`
  (`:2720-2721`); unlicensed → `rule=...not_causal_proof` (`:2723-2725`).
- `apply_live_claim_guard` (`deck_context.py:2999`) is the **output-boundary
  strip guard**, wired in `agent/dj_cohost.py:3629`. It *removes* unsupported
  causal/multi-deck claims; it is **negative**, not a coach-content producer.

**VERDICT: REAL — and this is the single signal that turns Sven from narrator
into coach on a master-only mix.** But it has a **hard precondition: a connected
MIDI controller emitting EQ/filter moves.** `_licensed_move_effect` needs
`moves` (`:2168` `if not labels: return None`), and `moves` come only from
`state.recent_moves`, which is controller-derived (`event_detector.py:378-398`,
MIX_MOVE/TRANSITION_OPPORTUNITY). **No controller ⇒ no moves ⇒ no license ⇒ no
causal coaching, ever** — which is exactly the case for a recorded-audio QA replay.

### 1d. The Vibe Judge — REAL but ABSTAINS on master-only (two-deck-gated)

`state/transition_judge_runtime.py` (`judge_and_record` at `:48`) wraps the pure
`intel/transition_judge.py`. Wired into the live loop:

- `_run_live_judge` (`coach.py:447`) runs the Judge — but only `if
  deck_audio_capture is not None` (`coach.py:474-475`) and only on a
  `TRACK_CHANGE` event (`coach.py:1040`).
- On a JUDGED verdict it grounds `[judge:transition@t]` and appends
  `judge_evidence_line` to `ev.extra` (`coach.py:1058-1059`), which is one of the
  four speak-gate grounded keys.
- The policy that lets it judge vs abstain is `live_claim_policy`
  (`deck_context.py:2830`). `supported_verdict` requires
  `_supports_grounded_transition_verdict` (`deck_context.py:2880`), which demands
  **ALL of**: both decks A *and* B resolved (`:2890`), both with `track_id`
  (`:2894`), both from a **trusted source** (`:2896`), two **active** per-deck
  audio lanes (`:2898`), per-deck features for both (`:2900-2905`), per-deck
  pre/current window lanes (`:2907`), and deltas (`:2909-2914`).

**VERDICT: REAL engine, ASPIRATIONAL on master-only.** Two independent kill
switches make it abstain by construction on the default rig:
1. `deck_audio_capture is None` ⇒ `_run_live_judge` returns immediately
   (`coach.py:474`); the Judge never even runs.
2. Even if it ran, `_supports_grounded_transition_verdict` needs per-deck audio +
   two trusted-source deck identities that a master-only/internal-mixer rig
   doesn't have.
The docstring is honest about this (`coach.py:468-472`: *"Kaan's common
master-only rig … the Judge abstains … the honest-null default, not a bug"*).

### 1e. The 10-signal transition scorer → voice — REAL but TWO-DECK-GATED

`runtime/transition_verdict_voice.py::build_transition_verdict_voice_line` (`:27`)
converts the pill's already-computed transition payload into a citable prompt
receipt and is wired at `coach.py:880-886` (on PHASE/TRACK_CHANGE/
TRANSITION_OPPORTUNITY) into `ev.extra["transition_verdict_voice_line"]`.

But it abstains unless the suggestion's `transition` payload has **both**
`source_deck` and `target_deck` resolvable to distinct "A"/"B"
(`transition_verdict_voice.py:51-54`) AND live confidence above the scorer floor
(`:56-58`) AND citable to/candidate ids (`:60-66`).

The deck labels come from the SuggestionService seed resolution
(`runtime/suggestion.py:138` `target_deck = _target_deck(source_deck, side)`,
`:122-130`). On a master-only mix `audible_deck` is often `"mix"`/`"none"`, and
without two resolved deck identities the transition payload can't carry a clean
A→B pair.

**VERDICT: REAL engine, mostly ASPIRATIONAL on master-only.** This is the richest
coaching content Sven could speak (10-signal scorer: roles, keys, reasons,
risks) and it is gated behind two-deck identity resolution it usually can't get
on a single master mix. `move_grade` (`intel/move_grade.py`) feeds the scorer /
debrief / `__main__` but has **no live-voice call path** (no caller in
`coach.py` / `dj_cohost.py`).

### 1f. The other grounded voice keys — partial

- `next_suggestion_voice_line` (`runtime/suggestion_voice.py`, wired
  `coach.py:887-894`) — the pill's "what's next." Can fire on master-only *if* a
  library seed resolves (needs a resolved `track_id` from the audible deck,
  `suggestion.py:132-134`). This is forward-looking but it is **suggestion**, not
  a read of Kaan's *move*; it's "what to play next," not "how that blend went."
- `set_progress_voice_line` (`runtime/set_plan_voice.py`, wired `coach.py:895-901`)
  — set-arc progress. Coarse, not move-level.

---

## 2. The narrator→coach gap, answered precisely

> **Which intel signals actually reach voice on the default master-only rig?**

| Signal | Reaches voice on master-only? | Gate | Evidence |
|---|---|---|---|
| **EQ/filter move guard** (`eq_move_model`→`_licensed_move_effect`) | **YES — but only with a connected controller emitting moves** | needs `moves` (controller); uses master-mix delta, not per-deck | `deck_context.py:2153,2168,2192`; `event_detector.py:378-398` |
| **Vibe Judge** (`transition_judge`) | **NO — abstains** | `deck_audio_capture is None` ⇒ never runs; needs two trusted-source decks + per-deck audio | `coach.py:474,1040`; `deck_context.py:2880-2914` |
| **10-signal transition scorer voice** (`transition_verdict_voice`) | **NO (rarely) — abstains** | needs distinct A/B `source_deck`+`target_deck` + confidence floor | `transition_verdict_voice.py:51-58`; `suggestion.py:122-138` |
| **move_grade** (`intel/move_grade`) | **NO — no live-voice caller** | pill/debrief/two-deck only | no caller in `coach.py`/`dj_cohost.py` |
| next_suggestion voice | YES (if library seed resolves) — suggestion, not move-coaching | needs resolved seed `track_id` | `suggestion_voice.py`; `suggestion.py:132` |
| set_progress voice | YES — coarse arc | — | `set_plan_voice.py` |

So the **believed model is verified**: only the eq_move guard speaks coaching on
master-only, and even that needs a controller; the Judge and scorer both abstain
needing per-deck routing.

> **Why does it sound like a narrator?**

When there's no controller and no per-deck capture (the QA-replay condition):
all four grounded payload keys are empty for the auto events, so the speak-gate
silences most of them; the ones that *do* speak (manual, KAAN_SPOKE, or a
suggestion-bearing TRACK_CHANGE) hit the prompt's `recent_moves[8s] is NONE`
branch (`matrix.py:403`) and the model "coaches the music's direction" — which,
with no move and no lookahead receipt, is indistinguishable from narration.

### Ordering nit (real, secondary)

The speak-gate runs at `coach.py:921` BEFORE `judge_evidence_line` is attached at
`coach.py:1059`. So a TRACK_CHANGE that the Judge *would* ground can be silenced
by the gate before the Judge ever runs (the Judge runs inside the post-gate
generation block). On master-only this is moot (Judge abstains anyway), but it
means the Judge cannot *rescue* a describe-bank TRACK_CHANGE from the gate. Worth
noting for the rewire.

---

## 3. The SINGLE highest-leverage change

**Make the EQ/filter move guard the master-only coach spine, and stop requiring a
controller for it** — i.e. give Sven a grounded *move-effect coaching receipt*
from **master-mix audio deltas alone**, then let the prompt coach on it.

Today `_licensed_move_effect` returns `None` with no `moves` (`deck_context.py:2168`),
and the Judge/scorer both need per-deck audio. That leaves a recorded-audio replay
(no MIDI, no per-deck stems) with **nothing** to coach from. The smallest change
that flips narrate→coach on a single master mix is to **voice the master-mix
transition/energy read the scorer already computes, without the A/B deck
requirement** — because the audio replay DOES carry: band deltas, LUFS deltas,
brightness deltas, phase, energy arc, and (via the pill) a next-suggestion with
score/reasons/risks. None of those need two decks.

Two viable shapes (pick one; the first is smaller and audio-only-safe):

- **(A) Relax the scorer voice receipt to a single-mix "energy/transition read."**
  Add a master-mix branch to `build_transition_verdict_voice_line` (or a sibling
  `build_energy_read_voice_line`) that emits a citable receipt from the
  next-suggestion's `score`/`reasons`/`risks` + the master audio deltas
  (`render_audio_delta_items`), grounded by a NEW evidence source (e.g.
  `[energy:...]`) that the existing strip guard already trusts — WITHOUT requiring
  `source_deck`/`target_deck` (drop/relax `transition_verdict_voice.py:51-54`).
  This is the move that voices the scorer on a single master mix.

- **(B) Default per-deck capture ON.** Flip `deck_audio_routing` to enable on the
  common BlackHole-multichannel path so `deck_audio_capture` is non-None
  (`__main__.py:1503-1507`) and the Judge actually runs. **Rejected as the
  *single* change** because (i) it needs the user's rig to actually route two
  decks into separate channels (most won't), and (ii) it does nothing for a
  recorded *stereo master* replay, which is exactly the QA-loop input. Keep (B)
  as a real-rig follow-up, not the QA-unblocker.

The leverage: (A) is the one change that makes Sven coach with *specifics* on the
exact signal a 3-hour stereo replay can produce, with no controller and no
per-deck routing — i.e. it makes the QA harness able to *measure* coaching, not
just narration.

---

## 4. Sven lane — ordered, concrete work items

1. **[QA-unblock, audio-only] Voice the scorer/energy read on a single master
   mix.** Add a master-mix branch (no A/B deck requirement) to
   `runtime/transition_verdict_voice.py` (or new `energy_read_voice.py`) that
   builds a citable receipt from `suggestion["transition"]` score/reasons/risks +
   `render_audio_delta_items(state)`; register a grounded source so it survives
   the strip guard; attach to `ev.extra` as a new speak-gate grounded key. Wire
   in `coach.py` next to lines 880-901. Add the key to
   `speak_gate._GROUNDED_VOICE_EXTRA_KEYS` (`speak_gate.py:21`).
   *Files:* `runtime/transition_verdict_voice.py`, `runtime/coach.py:880-901`,
   `runtime/speak_gate.py:21`, `state/evidence_registry.py` (new source).

2. **[gap] Loosen the eq-move guard's controller dependency for the *coaching
   receipt* (not the causal *claim*).** Keep `_licensed_move_effect`'s causal
   license controller-gated (that's correct), but emit a *non-causal* master-mix
   energy/move-direction receipt from band/LUFS/brightness deltas even when
   `moves` is empty, so Sven can coach "the lows just pulled back, ride it" from
   audio alone. *Files:* `state/deck_context.py:2688` (`render_move_effect_context`
   currently early-returns `if not moves`, `:2696-2697`).

3. **[ordering] Run the Judge BEFORE the speak-gate on TRACK_CHANGE** so a
   would-be-grounded verdict can rescue a describe-bank event. Move the
   `_run_live_judge` block (`coach.py:1040-1059`) above `decide_speak_gate`
   (`coach.py:921`), or pre-compute `judge_evidence_line` for the gate. (No-op on
   master-only today; correctness for when per-deck IS on.)

4. **[real-rig] Default per-deck capture ON for multichannel BlackHole.** Make
   `deck_audio_routing_from_env` enable per-deck on the standard BlackHole-16ch
   layout without an env var (extend the auto branch `deck_capture.py:514-525`),
   and verify `__main__.py:1503-1507` instantiates `DeckAudioCapture`. Unblocks
   the Judge + scorer two-deck path for users who route two decks. *Gate:* needs
   a real two-deck rig to ear-verify (not the QA replay).

5. **[scorer→voice] Promote `move_grade` to a live-voice receipt.** `move_grade`
   (`intel/move_grade.py`) has no live caller; if a controller move + master-mix
   delta licenses it, surface a one-line grade receipt the same way as #1 so a
   *graded* move (not just a described one) reaches Sven. *Files:*
   `intel/move_grade.py`, new voice helper, `coach.py`.

6. **[measurement] Emit a per-turn "coach-vs-narrate" signal** the QA judge can
   read: have `coach.py` log, alongside `event`/`live_claim_guard`, whether the
   spoken line carried a grounded coaching receipt (which key) vs fell to the
   no-evidence music-direction branch. This is what lets the autonomous harness
   *score* the narrator→coach gap instead of a human ear. *Files:* `coach.py`
   `recorder.log_event` sites near 1029/1065.

---

## 5. Files of record (file:line)

- Speak-gate: `src/vibemix/runtime/speak_gate.py:21-28, 30-39, 119-147`
- Coach loop: `src/vibemix/runtime/coach.py:447-522` (`_run_live_judge`),
  `:880-901` (suggestion/transition/set voice lines), `:921-946` (speak-gate
  call), `:1040-1059` (live Judge on TRACK_CHANGE)
- EQ-move predictor: `src/vibemix/intel/eq_move_model.py:46, 79`
- EQ-move license + policy + strip guard:
  `src/vibemix/state/deck_context.py:2074-2087, 2153-2206, 2688-2726,
  2830-2914, 2999`
- Strip guard wiring: `src/vibemix/agent/dj_cohost.py:94, 3629`
- Judge runtime: `src/vibemix/state/transition_judge_runtime.py:48-79`
- Scorer voice receipt: `src/vibemix/runtime/transition_verdict_voice.py:27-91`
- Suggestion deck resolution: `src/vibemix/runtime/suggestion.py:110-150`
- Prompt identity: `src/vibemix/prompts/matrix.py:397-436`
- Deck-capture default (the master-only switch):
  `src/vibemix/__main__.py:1503-1507`; `src/vibemix/audio/deck_capture.py:462-571`
- Event taxonomy (controller-gated MIX_MOVE/TRANSITION_OPPORTUNITY):
  `src/vibemix/state/event_detector.py:375-398, 444-490`
