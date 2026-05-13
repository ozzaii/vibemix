# Phase 17 — Reaction-Reel Capture Protocol

**Status:** Locked spec — instructs Kaan how to capture the 30-min reel that feeds the slop grading gate.
**Source-of-truth for:** ROADMAP Phase 17 Success Criterion #1.
**Audience:** Kaan (operator), and any future re-record runs after a Phase 10 cycle.

---

## 1. Reel Shape — the 5 × 6-min Segment Matrix

The reel is **30 minutes**, split into **five 6-minute segments**, one per genre. Each segment further splits into **3 min Hype-man + 3 min Coach** at the same skill level. Across all five segments, every axis is represented: **5 genres × 2 modes × 3 skill levels** (Beginner appears in 1 segment, Intermediate in 2, Pro in 2 — covering the canonical distribution per CONTEXT Area 2).

| Segment | Minutes | Genre           | First 3 min mode | Last 3 min mode | Skill level   |
|---------|---------|-----------------|------------------|-----------------|---------------|
| 1       | 0-6     | **techno**      | **Hype-man**     | **Coach**       | Intermediate  |
| 2       | 6-12    | **house**       | **Hype-man**     | **Coach**       | Beginner      |
| 3       | 12-18   | **drum & bass** | **Hype-man**     | **Coach**       | Intermediate  |
| 4       | 18-24   | **disco**       | **Hype-man**     | **Coach**       | Pro           |
| 5       | 24-30   | **pop**         | **Hype-man**     | **Coach**       | Pro           |

Coverage check: techno + house + drum & bass + disco + pop = 5 genres. Each segment hits both modes. Skill distribution: 1× Beginner, 2× Intermediate, 2× Pro. All three Phase 17 axes are represented inside 30 minutes.

---

## 2. Capture Setup — Pre-Flight Checklist

Run these in order. Do not skip steps. The grading gate is only as honest as the capture.

1. **Boot vibemix** — either the shipped binary or `python -m vibemix` from the repo. Confirm the calibration wizard has already been completed previously (the session must launch directly into the live UI, not the wizard).
2. **Open djay Pro** with the prepared playlist. Kaan curates the playlist ahead of time: 6 minutes of playable, mixable material per genre, with at least one transition per segment that gives the AI something to react to. The playlist is locked before recording — no live re-curation, which would bias the reel toward "easy" moments.
3. **Start a QuickTime screen+audio recording** of djay Pro (File → New Screen Recording, select djay Pro window or full display, ensure system audio is in the output). The QuickTime `.mov` sits parallel to the vibemix `recordings/<session>/` tree — it gives raters the same visual + audio context the AI saw. Without it, raters score blind on voice alone and miss "did the AI react to a real cue or invent one?".
4. **Start the vibemix session** via the normal Start button in the live UI. This writes to `recordings/<YYYYMMDD-HHMMSS>/` per Phase 15-02 — see Section 3 for the output shape.
5. **Run the 30-min reel exactly per the segment table above.** Switch mode (Hype-man → Coach) at the 3-min mark of each segment via the Settings drawer. Switch skill level (Beginner / Intermediate / Pro) at the segment boundary every 6 minutes. Stick to the genre planned for the segment — no skipping ahead, no re-doing a segment because it "felt off". If a segment goes wrong, finish the reel, note it in `session-notes.md` next to the recording, and decide post-hoc whether to re-record.
6. **End the session via the normal close path** so `session.json` gets the `ended_at_iso` field populated per Plan 15-02. Do not Ctrl-C — that leaves the session metadata mid-write and the reaction extractor will reject the recording as incomplete.

---

## 3. What Gets Recorded — Output Shape

After capture, the artefact tree is:

```
recordings/<YYYYMMDD-HHMMSS>/
├── session.json    — metadata: started_at_iso, ended_at_iso, persona, skill, genre tags, settings snapshot
├── events.jsonl    — append-only event timeline; expect ≥40 entries of {"kind": "ai_text", ...} over 30 min
├── voice.wav       — 24kHz mono int16; the AI's TTS output (the reactions raters will score)
└── input.wav       — 16kHz mono int16; the captured music + mic mix
```

Outside the recordings tree:

```
<wherever QuickTime saves>/<reel-name>.mov  — screen+audio capture of djay Pro
```

The `events.jsonl` `ai_text` records carry the reaction text + timing fields the recorder (`src/vibemix/audio/recorder.py`) writes via `log_event("ai_text", ...)`. Plan 17-02's `grade.py` reads these to identify reactions and extracts each reaction's ±15s context window for the rater. **≥40 reactions are expected** over 30 minutes based on POC observation (cohost_v4 / Plan 15-02 deferred-items note).

---

## 4. Reaction Extraction

No manual extraction step. Plan 17-02's `scripts/reaction_reel/grade.py` reads `recordings/<session>/events.jsonl` and walks all `kind=="ai_text"` entries in shuffled-deterministic order, presenting each reaction's voice.wav slice + ±15s of music context + screen snapshot for the rater to score. The rater never sees the original event order, the persona/mode/skill metadata, or the reaction text in transcript form during grading — they hear voice.wav and grade by ear, against the rubric in `17-RUBRIC.md`.

Reaction count: if `events.jsonl` shows fewer than 25 `ai_text` records, the reel under-represents the event surface and should be re-recorded. If it shows more than ~80, the prompt templates are over-firing and Phase 10 needs a calibration pass before grading is meaningful.

---

## 5. Out of Scope

This document does **not** cover the act of running the reel on launch day. Kaan does that with the shipped binary on his rig, with his playlist, in his apartment — outside the autonomous phase scope. What Phase 17 ships (this document + `17-RUBRIC.md` + `17-ITERATION-LOOP.md` + `scripts/reaction_reel/grade.py` + `scripts/reaction_reel/analyze.py`) is the bench. The recording itself is human work executed after the phase closes, and its result lands at `.planning/phases/17-reaction-reel-slop-grading-gate/17-GATE-RESULT.md` as the verification artefact for VERIFY-02.
