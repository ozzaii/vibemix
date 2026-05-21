<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Plan 59-05 — Gemini-vision deck-read accuracy eval + KAAN-ACTION gate. -->

# Gemini-Vision Deck-Read Accuracy Eval (DECK-02)

The **gate** that decides whether the Gemini-vision deck-read leg is allowed to
feed deck-state — and for which apps. This is the single biggest hallucination
risk in Phase 59: re-enabling vision un-does a deliberate v4 anti-hallucination
killswitch (`dj_cohost.py: screen_jpeg = None`, *"Screen + MIDI metadata caused
hallucination"*). A vision-misread key badge is a **silent error** — the same
hallucination class as a wrong library tag.

So vision-sourced keys stay **GATED OUT** of `deck_poller` (`vision_enabled=False`
by default — conservative-by-design) until this eval clears the **accuracy floor**
on a corpus of **real screenshots from Kaan's rig**.

> **This is a KAAN-ACTION.** Engineering built the vision read + this harness, but
> only Kaan can supply the real-rig screenshot corpus and sign off the gate. Until
> then, vision is dormant and the co-host runs XML-or-unknown — the safe state.

---

## 1. KAAN-ACTION — collect the corpus

Kaan supplies a small corpus of **real screenshots** from his actual rig. Coverage
priorities (per RESEARCH §Spike 2 + Open Q1):

- **djay Pro** — PRIMARY (Kaan's main app). Most screenshots here.
- **Serato / Traktor / Engine** — if available, even a few each (cross-app fallback
  is the whole point of the vision leg).
- **Light + dark themes** — dark mode + busy waveforms degrade OCR-style reads; both
  must be represented.
- **Both decks visible where possible** — the **silent / second-deck badge
  readability is the key open question** (RESEARCH Open Q1). A second deck whose
  badge is dimmed/inactive is exactly the case the cross-deck clash logic
  (Phase 60) depends on, so label it honestly (use `null` if you can't read it).

Aim for ~15-30 screenshots total to start; more djay than the others.

---

## 2. Ground-truth labeling format

Each image gets a sibling `<stem>.json` with the truth the badge **actually shows**:

```
eval/deck_vision/corpus/        # (you create this — gitignored or local)
  djay_001.jpg      djay_001.json
  djay_dark_002.png djay_dark_002.json
  serato_001.jpg    serato_001.json
  traktor_001.jpg   traktor_001.json
```

```json
{
  "app": "djay",
  "theme": "dark",
  "decks": [
    {"side": "A", "title": "Strobe",  "key": "8A", "bpm": 128},
    {"side": "B", "title": null,      "key": null, "bpm": null}
  ]
}
```

Rules:

- `app` ∈ `djay | serato | traktor | engine | …` (lowercase). Drives the per-app
  gate.
- A field that is **not legible** on the screenshot → `null`. A `null` truth is
  scored CORRECT iff the read ALSO returns `null` — this **rewards honest
  abstention and penalizes a guess**, which is the entire anti-hallucination
  point.
- `key` may be Camelot (`8A`), musical (`Am`), or open-key — the harness
  normalizes both truth and read via `harmonics.to_camelot` before comparing.
- `bpm` is recorded for context but is **not part of the gate** (least
  hallucination-sensitive field).

---

## 3. The accuracy floor (the gate definition)

The gate constant lives in `run_eval.py`:

```python
ACCURACY_FLOOR: float = 0.90   # per-app enable threshold
```

Per app, the harness computes **title accuracy** and **key accuracy**
(Camelot-normalized exact match, `null↔null` correct). The **overall** per-app
accuracy (combined title + key) is the number the gate is decided on.

| Per-app overall accuracy | Outcome |
|--------------------------|---------|
| `≥ ACCURACY_FLOOR` | **ENABLE** vision-sourced keys for that app, at the **below-XML** `deck_vision.VISION_CONF` (a misread can never out-cite a pre-analyzed XML tag). |
| `< ACCURACY_FLOOR` | **GATED** — that app degrades to **XML-or-unknown**; vision stays dormant for it. This is the conservative-by-design path, **not a failure**. |

`ACCURACY_FLOOR` is the starting bar. Kaan tunes/locks it against the measured
real-rig numbers at the gate, mirroring `eval/THRESHOLD-LOCK.md` discipline (a
deliberate, justified change — never an autonomous edit after sign-off).

Why so high? Because the failure mode is silent: a confidently-cited wrong key
clashes the audience's ear, not just a log. The floor must be high enough that an
*enabled* app's reads are trustworthy even at the lower vision confidence.

---

## 4. Run it (the live path — opt-in only)

```bash
PYTHONPATH=src python3 eval/deck_vision/run_eval.py eval/deck_vision/corpus
# machine-readable report too:
PYTHONPATH=src python3 eval/deck_vision/run_eval.py eval/deck_vision/corpus --json /tmp/deck_vision_report.json
```

Requires `GEMINI_API_KEY` (repo-root `.env` — **no new key**). This harness is the
**only** live-Gemini path in Plan 59-05 and is **opt-in**: the default fast suite
(`PYTHONPATH=src python3 -m pytest -q`) does **not** import or run it and makes
**no live Gemini call**.

Exit code: `0` iff every app in the corpus cleared the floor; non-zero surfaces a
below-floor app for the review (a below-floor app is a *gated* outcome, not a
crash).

---

## 5. Vision stays gated until this eval passes

Until an app clears the **accuracy floor** here and Kaan flips
`DeckPoller(vision_enabled=True)` for it, **vision must NOT feed deck-state**:

- `deck_poller.py` defaults `vision_enabled=False` — vision dormant, co-host runs
  XML-or-unknown.
- The reaction-path `dj_cohost.py: screen_jpeg = None` killswitch is **untouched**
  regardless — the vision deck-read is a **separate** structured call, never the
  reaction turn.
- Enabling vision for an app is the *only* step gated behind this eval. The wiring
  exists so the slot is structurally present; the gate is the human sign-off.

Record the per-app enable/gate decision (and the measured accuracy) in
`.planning/phases/59-full-deck-awareness-grounding/59-05-SUMMARY.md`.
