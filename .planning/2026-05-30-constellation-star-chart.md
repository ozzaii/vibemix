# vibemix — The Constellation Star-Chart (2026-05-30)

> The fourth and capstone investigation workflow. Where the dead-path hunt asked
> "what's dead vs unwired?", the strategic brief asked "where's the leverage?", and
> the Judge blueprint asked "what can a deterministic engine honestly decide?" — this
> one asks: **vibemix is a galaxy of engines (stars); which CONSTELLATIONS (3+ stars
> feeding each other) create a capability/experience/moat no single engine has?**
>
> Method: a 40-agent workflow — cataloged **128 stars** across 7 subsystems, composed
> 10 candidate constellations, each adversarially verified (stars real? feeds real?
> magic real? lock-fit? new-slop-risk?), then a cosmographer charted DRAW_NOW / NEXT /
> LATER. The Judge is ONE star, not the center. **Every claim re-grounded to file:line
> against HEAD on `live-tuning-or-brain`.** Stats: 128 stars · 10 constellations · 1
> DRAW_NOW · 6 DRAW_NEXT · 3 DRAW_LATER · 0 fading.

## The galaxy as it stands

**Mostly lit on the backend, dark at the surface.** The perception spine is bright and
load-bearing: `MusicState` single-writer, `EvidenceRegistry` citation gating, the coach
loop, CLAP/CUE-DETR/deck-context — and as of tonight's `6dc07ab3`/`41ccd726`,
`skill_recognizer.recognize` is now live-wired into `runtime/coach.py:392` (cited→credit,
un-cited→zero). The **two darkest real stars**: (a) **the Judge** —
`transition_judge.judge_transition` + `signal_frame_from_capture` have ZERO production
callers (only test refs); and (b) **the skill-tree's face** — the mastery galaxy is fully
plumbed to the webview (`progress.py:397` emits `"skills"` → schema
`messages.schema.json:3459` → `messages.ts:998` optional envelope → `ws-client.ts:80`
re-dispatches `ipc.learn.progress_state`) but **NO learn view reads `.skills`/`stage`/
`learn_fill`**. The orphan dividend: **most wins here are wiring, not new engines.**

## The tiers

| Tier | # | Constellation | Axis | Effort | Slop risk |
|---|---|---|---|---|---|
| **DRAW NOW** | **[84]** | **Earned Wall** | mastery · mostly_wiring | **M** | **none** |
| DRAW NEXT | [72] | Receipt of Mastery | mastery | M+ | low |
| DRAW NEXT | [58] | The Receipt (honest-abstain mix scorecard) | viral-conversion | M+ | low |
| DRAW NEXT | [52] | Shareable Set Card | viral-conversion | L | low |
| DRAW NEXT | [48] | Honest Debrief Ledger | mastery | M | low |
| DRAW NEXT | [44] | The Verdict Source (Judge→Mastered ev) | mastery | L→XL | low |
| DRAW NEXT | [38] | Honest Verdict Line | viral-conversion | S | **med** |
| DRAW LATER | [42] | Remembered Reasons | mastery | — | low |
| DRAW LATER | [34] | Honest Hindsight / Earned Mastery Witnessed | mastery | — | low |

**Fading stars: none.** Every constellation is real architecture — failures are all
*sequencing* (feed depends on the unwired Judge producer) or *honest mis-scoping*, never
fiction-with-no-path.

## The only DRAW_NOW — [84] Earned Wall

*mastery · mostly_wiring · M-effort · slop-risk ZERO*

**Stars:** `SkillTree.compute` (`skill_tree.py:262`) + `LearnProgress.skills` live block
(`progress.py:146`) + skills IPC seam (`progress.py:397`→schema `:3459`→`messages.ts:998`)
+ `learn/ws-client.ts:80` + `_credit_live_skill_demo` (`runtime/coach.py:113`).

**The magic:** your whole DJ self at a glance — six skills, each half-lit *Competent* from
lessons, one or two *Mastered* from real cited sets, every Mastered tappable to its proof.

**Why slop-risk zero:** read-only render of deterministically-derived stage flags; nothing
enters the co-host voice. `mastered`/`first_mastered_at` is ONLY ever set by a CITED live
demo (Inv #2/#3), so the wall **literally proves nothing was given** — a real trophy case,
not a pitch. Fits v11.0 "Earned" exactly. **Blocked on nothing.**

**First step:** add a one-line Python serializer that folds `SkillTree.compute(progress)`
into `LearnProgress.snapshot()` (keep the stage rule single-source in Python — avoids the
manifest-drift cost of re-deriving `COMPETENT_THRESHOLD=0.6`/weights in TS), extend the
schema + `npm run codegen:ipc`, then build `SkillWall.ts` as a 6-row Canvas-2D render
reusing the pill/mascot draw path, each Mastered notch tappable to its cited demo.

## The brightest composition the Judge enables (the spine)

**Judge → recorder → debrief → skill-tree** (#58 → #48 → #44 → Earned Wall). ONE new
producer — the Judge wired into the coach loop emitting `transition_judged` rows — lights
up FOUR downstream consumers already built and waiting: the honest-abstain receipt, the
first-class-abstention ledger, the earned-Mastered ev-source, and the shareable card's
headline. **But none fires until that producer exists.**

**Critical honesty gate:** the scorer is still a stub (`transition_judge.py:58` — "scoring
lands in later tasks"), and a confidently-wrong grade is its OWN new hallucination class.
So the producer **must ship abstaining-only first** — emit verdicts only where both signals
are trustworthy, write "didn't grade it" everywhere else. That honest-abstain mode is
shippable and on-thesis today; the numeric grade is not.

## Real blockers the chart surfaced (don't trip on these)

- **`transition_judged` is hard-gated out of debrief:** `chapters.py:104` rejects any
  non-`"event"` kind *before* `_KIND_MAP`. A `kind="transition_judged"` row is silently
  dropped until that gate is extended.
- **The capture seam has a type-mismatch:** `coach.py:195` types `audio_capture_context`
  as a `dict`, but `deck_signal.py:23` requires the live `DeckAudioCapture` object + a
  keyword-only `t_session` + a `source→source_trusted` adapter (`DeckTrack.source`,
  `deck_state.py:48`). The Receipt's "mostly_wiring" hides this real glue.
- **The Mastered keystone (#44) is L→XL, not L:** `recognize()` HARDCODES
  `citation_check('ev', ...)` at `skill_recognizer.py:240` (no source param, no judge
  path); `JUDGE_VERDICT` event type doesn't exist; `harmonic_mixing` is pinned in
  `_HONEST_UNCREDITABLE_V11` (`:107`, guarded by `test_unsignalled_skills_never_auto_master`).
  The voice-citation step (add `judge` to `EVIDENCE_SOURCES` + `_SOURCE_ALT`) is correct;
  the credit feed is unbuilt.
- **DO NOT relitigate the [34] profile loop-back:** `build_profile` aggregates exactly the
  5 locked fields (`builder.py:205-247`, schema `additionalProperties:false`,
  `schema.py:78-86`). Folding verdict counts in is a hard lock violation. Dead on arrival.

## OSS / sexify

No new OSS swaps warranted — the engine layer is settled (CLAP ONNX, CUE-DETR, sqlite-vec
locked). The delight wins are wiring-and-render:
- **Earned Wall render (#84) IS the sexify win** — Canvas-2D, reuses mascot/pill path, six
  notches lighting Competent→Mastered. Highest first-run-delight payoff, and grounded.
- **Shareable Set Card (#52)** is the GitHub-star/waitlist flywheel. Ship the TRUE subset
  (`9 TRACKS · 1H 12M · TECHNO`) now; inherit the "top mix" line after the Judge→recorder wire.
- **Don't mint a grade-label vocab (CLEAN/SEXY/BOMB) yet** — `transition_judge` emits a 0-1
  float; labels off a stub scorer manufacture the exact slop the locks forbid.

## The first constellation to draw

**[84] Earned Wall first** — the only DRAW_NOW: stars real, feeds real, magic real, slop
risk zero, fits the active v11.0 "Earned" milestone, effort bounded M. It's the *face* of
the 102/103 mastery spine that already shipped tonight (`6dc07ab3`/`41ccd726`) and that
nothing paints. **Build the face of what's already earned, then wire the Judge into the
coach loop as the second move** — that single producer lights the four waiting consumers.

## Four-workflow convergence

The dead-path hunt ("the single highest-confidence unwired connection"), the strategic
brief ("the one move I'd make first"), the Judge roadmap ("the keystone closes itself"),
and this constellation map ("the only DRAW_NOW") **all four independently converged on the
same seam: the v11 skill-tree live→UI render.** That is the signal.

---
*Source: workflow `wf7s6yhn3` / run `wf_e3bc6867-ac1`, 40 agents, 2.17M tokens, 1 pipeline
stage dropped (a structured-output miss on one verify lane — did not affect the chart).*
