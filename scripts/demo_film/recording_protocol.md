# Recording Protocol — 3min+ Raw DJ Session

**Purpose:** capture the raw footage that feeds `scripts/demo_film/cut.sh`.

**Who:** Kaan or Francesco. Live session.

**Output:** `scripts/demo_film/raw/dj_session_<YYYY_MM_DD>.mov` (gitignored).

---

## Setup checklist

- [ ] vibemix running (live mode, not debrief replay).
- [ ] BlackHole 2ch audio routing live (djay Pro → BlackHole → both
      vibemix + speakers).
- [ ] Pioneer DDJ-FLX4 controller connected over USB (or any v0.1
      supported controller — see `docs/midi-controllers.md`).
- [ ] djay Pro (or Mixxx) in performance mode, real library loaded.
- [ ] Quartz screen capture target = djay Pro window (not full
      desktop — overlay visibility is paramount).
- [ ] Mascot overlay window visible + positioned bottom-right of
      djay Pro window.
- [ ] Audio levels checked — master output not clipping,
      vibemix voice output to second pair of speakers (NOT into
      session output — that would feedback).

---

## Recording target

- **Duration:** 3 minutes minimum (gives ~6× the 30s cut budget).
- **Format:** ProRes 422 LT or H.264 high-quality.
- **Resolution:** at least 1080p (downsampled in cut.sh re-encode).
- **Frame rate:** 60fps preferred (smoother mascot blends in slow-mo
  later if needed).
- **Audio:** 48kHz stereo, captured directly from the BlackHole feed
  (NOT via mic — captures pure session output without room
  reverb / typing).

---

## What to play during the session

Curate a 3-track sequence that EXERCISES the demo beats:

1. **Track 1 (0:00 – 1:30):** mid-energy track. Builds toward a drop
   at ~1:00. Demonstrates `prep_lean_in_hyped` → drop → `react_drop`.
2. **Track 2 (1:30 – 2:30):** mix in a layer (hi-hat / vocal / bass)
   at a clean 32-bar mark. Demonstrates `prep_lean_in_neutral` →
   layer arrival → cited reaction.
3. **Track 3 (2:30 – end):** smooth EQ-driven transition. Demonstrates
   controller-aware reaction (MIDI move detection grounding).

Real tracks — Kaan/Francesco's actual library. NO music-stock library
(rights complications + sounds generic).

---

## What NOT to do

- Don't talk over the session (mic capture is forbidden in v0.1; this
  also applies to the recording — no voice-over track yet, see
  `vo_policy.md`).
- Don't fake a controller move for the camera. The mascot reads MIDI
  in real time — fake moves produce fake reactions, viewers can tell.
- Don't re-shoot the same beat 5 times and cut between takes — Pitfall
  P57 sniff test: cuts should be temporally adjacent in the source.
- Don't enable AI post-effects in OBS / ScreenStudio. Raw is the
  product.

---

## After recording

```bash
mv ~/Movies/raw.mov scripts/demo_film/raw/dj_session_$(date +%Y_%m_%d).mov
```

Then update `cuts.json`:

```json
{
  "source": "raw/dj_session_2026_05_15.mov",
  ...
}
```

Then proceed to `3beat_structure.md` cut planning, then `cut.sh`.

