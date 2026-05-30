# vibemix — The Awakening Synthesis (2026-05-30)

> Workflow `wrar21ie3` (16 agents, 1.29M tokens). Gobbled the whole verified
> galaxy (5 agent docs + the live engine map = **159 engine entries, 106 ideas,
> 110 verified findings**), composed 12 constellations, scored each through three
> lenses (user-awakening · ship · anti-slop), then **adversarially verified** the
> synthesis against HEAD. Rescued from ephemeral tmp. Feeds the master plan.

## The one simple thing (the north star)

> **"It's a real DJ friend in your ear who actually grades your mix the moment you
> make it — and is honest enough to stay quiet when it couldn't truly see what
> happened."**

Complexity→simplicity: dozens of deterministic engines collapse to **"the Judge
decides, Gemini voices, and when unsure it abstains."** Simplicity→stars: that one
honest verdict is the keystone that lights four otherwise-dark consumers (receipt,
Mastered unlock, recap card, share headline). **Awakening = the USER:** the first
time it grades a real move correctly, it stops being AI commentary and becomes a
real DJ friend — and only the abstain-by-construction Judge buys that without slop.

## Ship one-liner

Light the Judge (abstain-first) in `coach_loop` → it becomes a friend that grades
your mix and stays honestly quiet → that one verdict unlocks the receipt, the
Earned Wall, and the shareable card behind it.

## The 12 constellations, fused-ranked (3 lenses)

| # | id | Constellation | Fused | Buildable now | Effort |
|---|----|---------------|-------|---------------|--------|
| 1 | C1 | **The Judge's Voice** — live transition verdict in the ear (abstain-first) | 8.3 | no (needs 4d join) | L |
| 2 | C5 | **It points at the deck** — overlay highlights the cue it names | 8.3 | **yes** | S |
| 3 | C3 | **Mastered, autonomously** — Judge verdict unlocks the skill | 8.2 | no (⊃ C1) | L |
| 4 | C4 | **Mascot reacts to the decided** — emote tags drive the face | 7.5 | **yes** | M |
| 5 | C2 | **The Receipt** — honest-abstain mix scorecard in debrief | 7.0 | no (⊃ C1) | M |
| 6 | C11 | **Remembered Reasons** — recall surfaces past moments live | 6.7 | **yes** (flag) | S |
| 7 | C6 | **Session Recap Card** — shareable cited true-subset PNG | 6.3 | no | M |
| 8 | C12 | **Wizard install steps** land in the onboarding flow | 6.2 | **yes** | S |
| 9 | C8 | **Library Doctor** — post-ingest readiness scorecard | 5.5 | yes (⚠ collision) | S |
| 10 | C9 | **Warn-then-allow** non-DJ capture-source guard | 5.3 | **yes** | S |
| 11 | C7 | **library cue** — standalone offline auto-hot-cue CLI | 5.0 | no (model host + CLI) | M |
| 12 | C10 | **Pill learns taste** — feedback buttons → taste model | 4.8 | no (Kaan decision) | L |

## The brightest unlit join — 4d (the recommended next move)

Wire `judge_and_record` into `coach_loop`, **abstain-first**. The entire producer
chain is BUILT + test-covered with **ZERO production callers** (only tests
reference it) — lighting this one producer makes C2, C3, C6 buildable.

**The real blocked_by (verified):** `coach_loop` is passed
`deck_audio_capture.buffers` (the rings) at `__main__.py:1438`, NOT the
`DeckAudioCapture` object that `signal_frame_from_capture` requires — the object
exists at `__main__.py:1056`. Thread the object + a `t_session` + a `lane_meta`
resolver (camelot/source_trusted/track_id from live deck state, single-writer
respected). On JUDGED also `registry.write("ev", "transition_judged", t)` so the
recognizer's credit-gate (below) passes. Abstain-first on a master-only rig.

**Lands in the ONE allowed lane:** `coach.py` / `__main__.py` are CLEAN; pill /
library / learn TS + `library/*` Python are concurrent-edit zones. Confirm
`git diff --cached --name-only` before every commit (`test_coach_skill_credit.py`
is dirty in another session; `coach.py` itself is clean).

## ★ Adversarial verification — what it CONFIRMED and what it CAUGHT

**Verdict: SUBSTANTIALLY TRUE.** The 4d recommendation is fully grounded — all 9
files exist; `judge_transition` (`transition_judge.py:45`, harmonic+bass_collision
scorer at :128/:157), `judge_and_record` (`transition_judge_runtime.py:42`,
abstain-first, never raises), `signal_frame_from_capture` (`deck_signal.py:22-58`,
needs the FULL capture object), `LiveSignalFrame` are all real with ZERO
production callers; **26 named judge tests pass green**;
`VoiceRecorder.log_event(self, kind, **fields)` at `recorder.py:312`.

**THE ONE MATERIAL DEFECT it caught (in rank-3 C3 — fold this correction):**
- ❌ "needs `judge` added to EVIDENCE_SOURCES" — **FALSE.** `judge` is ALREADY in
  `EVIDENCE_SOURCES` (`evidence_registry.py:130`), `_SOURCE_ALT` (:184), EBNF
  (:192). Shipped (commit `30b74044`).
- ❌ "lift TWO skills out of `_HONEST_UNCREDITABLE_V11`" — **FALSE twice.** The set
  is `('beatmatching',)` — ONE skill, and it must STAY (no tempo/phase signal).
  `harmonic_mixing` was already lifted and is live in `recognize()`
  (`skill_recognizer.py:141-157` returns `['harmonic_mixing']` on a compatible
  `transition_judged` verdict). Shipped (commit `cd645c73`).
- ✅ The ONE TRUE remaining C3 seam: `recognize()` at `skill_recognizer.py:261`
  hardcodes `citation_check('ev', ev_type, t)` — it gates credit on an
  `[ev:transition_judged]` citation, not `[judge:...]`. **4d writing the
  `ev:transition_judged` citation closes this** (no recognizer change needed).

**Net:** C3 is far more done than the synthesis claimed. After 4d writes both the
`[judge:]` voice-citation AND the `[ev:transition_judged]` credit-citation,
harmonic_mixing flips Mastered autonomously. beatmatching stays uncreditable by
design until a tempo/phase signal exists.

---
*Source: workflow `wf_2263e571-d92` / run `wrar21ie3`. Companion to the master plan.*
