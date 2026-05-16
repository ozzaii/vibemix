# 30s Demo Film — 3-Beat Structure Doctrine

**Pitfall P57** mandate: humans cut the demo, ≤8 cuts, no auto-pacing.

This doc is the editorial bar. Every cut in `cuts.json` should map to
one of the three beats below. Cuts that don't map are slop — drop them.

---

## Beat A — Overlay highlight (0:00 – 0:08, ~8s)

**Goal:** show the live overlay reading the DJ's screen + audio.

- Mascot is in **neutral idle** (no anticipation, no reaction).
- Camera focus: vibemix overlay HUD over djay Pro / Mixxx.
- Visible UI elements: track title (grounded — real string from
  nowplaying-cli), BPM, "listening" state indicator.
- NO voice line. Pure visual establishment.

This beat answers the viewer's first question: "what AM I looking at?"

---

## Beat B — Mascot lean-in BEFORE voice (0:08 – 0:14, ~6s)

**Goal:** show grounded anticipation. The mascot reads the room and
moves FIRST. The voice comes after.

- Mascot fires a `prep_*` clip (lean_in_hyped if next beat is a drop,
  lean_in_neutral if it's a layer change).
- Cut on the prep clip's BLEND-IN frame (~150ms into the clip).
- Subtitle/caption: "anticipating drop in 8 beats..." (text on screen
  — not voice).

This is the load-bearing beat. It demonstrates the anti-slop thesis:
the mascot **reacts to what is about to happen**, not to what is
generic-AI-script-template happening.

---

## Beat C — Cited reaction (0:14 – 0:30, ~16s)

**Goal:** voice line fires WITH evidence visible.

- Mascot fires `react_*` clip + voice line ("nice — that hi-hat layer
  hits, kept the energy through").
- ON-SCREEN: the evidence string ("layer arrival at 32-bar mark") OR
  the controller move citation ("you opened the hi-pass on Deck A
  during that").
- End frame: mascot in settle pose, overlay still live.

This beat closes the demo: viewer sees that the voice was grounded —
real event → real reaction → real citation. No hallucination.

---

## Cut budget allocation

| Beat | Min cuts | Max cuts | Reasoning |
|------|----------|----------|-----------|
| A    | 1        | 2        | One establishing shot, optionally a tight UI insert. |
| B    | 2        | 3        | Prep clip start, optional close-up on overlay shift, optional caption beat. |
| C    | 2        | 3        | Voice fire, citation pop, settle. |

**Hard ceiling: 8 cuts total.** `cut.sh` rejects > 8 (Pitfall P57).

---

## Forbidden moves

- Smash cuts on every beat — TikTok pacing, kills the "real DJ friend"
  bar.
- Camera shake / zoom hits — feels like an AI ad, not a session.
- Flashy transitions (whip pan, glitch wipe, RGB split) — slop.
- Music ducking under voice — voice IS the energy hand-off, no duck.
- Speed ramps — kills the grounded feel.

---

## Reference shots / framing

- Overlay should be readable at 720p (the README hero render width).
- Mascot is small (~120px) but clearly emoting — silhouette over
  fidelity.
- DJ deck is the hero — vibemix is the assistant.

---

## Hand-off to cut.sh

Once Kaan/Francesco has the raw session + a cut timing table:

1. Fill `scripts/demo_film/cuts.json` with cut objects matching the
   schema (id, start, end).
2. Verify cut count ≤ 8.
3. Map each cut.id to one of `beat_a_*`, `beat_b_*`, `beat_c_*` for
   doctrine traceability.
4. Run `bash scripts/demo_film/cut.sh --dry-run` first to validate.
5. Run `bash scripts/demo_film/cut.sh` to produce `docs/assets/demo.mp4`.
6. Update README hero block:
   `sha256=<actual hash> path=docs/assets/demo.mp4`.
7. CI `README Hero Sync` workflow verifies on next push.

