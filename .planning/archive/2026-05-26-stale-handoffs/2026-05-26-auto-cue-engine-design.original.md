# Auto-Cue Engine — Design Spec (clean upgrade)

**Date:** 2026-05-26
**Session role:** producer (`source="auto"` CueAnchors). Ingestor/consumer = separate session.
**Status:** synthesized from 7 parallel research agents; ready to build.

## Why this is the moat

Auto-cue detection is vibemix's core differentiator. It closes two gaps at once:

1. **Coverage** — un-cued tracks otherwise have no CLAP/embedding anchor. Audio-derived
   cues give every track a mixable window without depending on the DJ's library cues.
2. **Structure-aware AI** — extracting intro/build/breakdown/drop/outro from *audio*
   (not metadata, like djay Pro AI's Core ML path) feeds embedding excerpts AND opens
   live suggestions ("enter on hot cue 2, exit at the breakdown"). Works even for a DJ
   who never cued their library — that is the moat no shipping product unifies.

**Competitive bar** (teardown): ~90% usable-cue rate, high precision, **downbeat-locked**
(off-downbeat cues are worse than none — MIK's #1 complaint). Differentiation: genre-agnostic
with **no Rekordbox-style "Mood gate"** that catastrophically mislabels a whole track; one
engine feeding both live suggestions and embedding excerpts.

## What exists today (the upgrade base — NOT greenfield)

`src/vibemix/library/cue_detect.py` — working v0.5 `detect_cues(audio_path, max_cues=4) -> list[CuePoint]`:
- ffmpeg → mono 16k; 1 Hz `sub_share` curve (reuses live `_dsp.sub_share`).
- breakdown(kill)/re-entry(drop) edges relative to track's busy-median.
- coarse BPM (`band_limited_autocorr`); snaps candidates to bar downbeat (`lock_downbeat_phase`,
  no-op when conf < 0.5); phrase fillers (`estimate_phrase_length_bars` {8,16,32}).
- emits `intro / reentry / breakdown / phrase` point cues; single `load` cue on no-structure.

Consumer: `embed.py::_embed_audio_cue_anchored` (line 490) — anchors an 80s window AT each cue,
means the vectors. Ignores `end_s`. `# MULTI-VECTOR SEAM` (line 509) = future per-cue storage.

**Gaps:** no SSM/Foote boundaries (misses non-bass structure), point cues not spans, no `build`/`outro`,
no `confidence` (the downbeat lock returns one — currently discarded), `CuePoint` ≠ `CueAnchor` contract.

## Stack constraint (load-bearing)

DSP deps are **numpy + scipy only** — essentia/librosa are NOT installed and NOT in pyproject
(CLAUDE.md's "essentia available" is wrong). The client engine stays pure numpy/scipy to honor
one-click install. allin1 (MIT, even tiny 24MB weights) pulls torch+demucs+NATTEN-compile+madmom
(~2-3 GB, py3.10, compile hazard) AND its taxonomy lacks `drop`/`build` → **server-side / optional
backbone only (boundaries+grid), never bundled in the client.**

## The seam (FIXED — do not redesign)

`src/vibemix/library/cue_types.py`, shared with the ingestor session:

```python
@dataclass(frozen=True, slots=True)
class CueAnchor:
    label: Literal["intro", "build", "breakdown", "drop", "outro"]
    start_s: float
    end_s: float            # ≤80s mixable window
    confidence: float       # 0..1
    source: Literal["dj", "auto"]
```

Engine produces `source="auto"`; DJ-lib produces `source="dj"`. Migration: `reentry→drop`,
`phrase→` nearest section, add `build`+`outro`. Richer fields (bars, snapped, camelot, role) stay
**internal** to the engine — the cross-session contract is exactly these 5 fields.

**Open seam question (flagged, not blocking):** the Literal has no `"section"` for non-dance
generic mid-track. v1 honors the seam: non-dance emits only `intro`+`outro`. Extend later if Kaan wants.

## Engine design (v1, pure DSP)

Pipeline: decode → per-frame features → boundaries → label segments → dance-gate → mixable windows → confidence.

1. **Boundaries** — keep the sub-energy edge finder; ADD a Foote-novelty pass: build a local
   self-similarity matrix over a per-frame feature vector (band shares + RMS + onset density),
   convolve a checkerboard kernel → novelty curve → adaptive peak-pick (`mean + k·std`). Catches
   melodic breakdowns / vocal sections the bass-only edges miss. O(N²) on N≈360 frames = trivial offline.

2. **Labeled segment spans** — for each segment aggregate features; assign `{intro,build,breakdown,drop,outro}`
   by **track-relative** signatures (percentile-normalized `e_s=(E−P30)/(P95−P30)`, NOT absolute dB —
   reuse `classify_phase_percentile` logic, NOT `_classify_phase_v4`):
   - intro = first segment, low/rising energy
   - build = strong positive normalized slope, rising highs, **followed by higher-energy segment**
   - breakdown = mid-track, bass collapse (`sub≤0.12`, drop≥0.15 vs neighbor), mid/high persist
   - drop = energy top-tier (`e_s≥0.90`), full-band, entry-jump, **preceded by build/breakdown**
   - outro = last segment, decaying, bass thinning
   Plus a small min-cost **grammar** pass (intro-first, outro-last, drop-after-build-or-breakdown,
   build-before-lift) and **relative ranking** (loudest full-band = drop, lowest-bass mid = breakdown).

3. **Dance-degrade gate** (anti-hallucination, runs before any build/drop/breakdown):
   G1 beat presence (valid BPM + convincing kick autocorr peak), G2 dynamic range `(P95−P30)/P95≥0.35`,
   G3 a distinct full-band energy-max segment. ALL pass → dance labels available. Any fail → GENERIC:
   `intro`+`outro` only, never a fabricated drop. (This is the no-Mood-gate moat: graceful, not catastrophic.)

4. **Mixable windows** — window = mix-region within section, phrase-snapped both edges:
   intro/outro 32 bars, drop/breakdown 16 bars; `bars=min(target, floor(80/bar_s/phrase)·phrase)`;
   `end_s=min(start_s+W, section_end, start_s+80)`. Internal `snapped` flag = lock conf≥0.5; when false,
   the live co-host must not promise beatmatched entry (honesty contract). Phrase origin = intro downbeat.

5. **Confidence** — geometric mean of four grounded factors:
   `(boundary_salience · label_margin · grid_conf · method_agreement)^(1/4)`.
   `grid_conf` = the `lock_downbeat_phase` confidence currently discarded. `method_agreement` = offline
   analyzer vs live-detector-shape corroboration. Isotonic-calibrate later against `source="dj"` cues so
   0.8 ≈ 80% hit. `CONFIDENCE_FLOOR≈0.5`: below it, consumer falls back to mean-excerpt / live pill hedges.

### Known gap (interim accepted)

No true downbeat/beat-grid tracker (madmom absent). Use the dep-free autocorr-comb lock +
±20% bar tolerance + honest `snapped=False`. Add madmom as optional backend ONLY if live testing
shows audible phrase drift. Guard the octave-error case via a systematic-offset detector across cues.

## Reliability plan ("assess the reliability")

- **Leg 1 — DJ-cue cross-check (primary, free ground truth):** for tracks with `source="dj"` cues
  (Kaan's Rekordbox library), `mir_eval.segment.detection` boundary-F at 0.5s and 3s of auto vs dj.
  Ship-gate: HR3F ≥ 0.75, HR.5F ≥ 0.5.
- **Leg 2 — Kaan's ear:** ~25 tracks he knows; render energy curve + cue markers + `[label, mm:ss, conf]`;
  ≥80% of conf≥0.5 cues "right or off-by-≤1 beat".
- **Leg 3 — self-consistency:** determinism (pure DSP → identical out), BPM/phrase sanity, stability under re-encode.
- Yardstick dataset if formal eval wanted: **Raveform** (TISMIR 2024, EDM, CC BY 4.0, 10-label) — NOT Harmonix (pop).

Failure guards: systematic-offset (octave error), label-margin+energy-slope (drop-vs-build),
low-coverage logging (missed breakdown), hysteresis/dedup (over-segmentation).

## Build order

1. `cue_types.py` (seam) + tests.
2. Upgrade `cue_detect.py` → `detect_cues` returns `list[CueAnchor]`: Foote boundaries, segment spans,
   build+outro, dance-gate, windows, confidence. TDD against synthetic + real tracks.
3. Run on real `/Users/ozai/Music` tracks offline → observe.
4. Reliability legs 1+3 (+ surface leg 2 to Kaan).
5. Wire `embed.py` consumer to `end_s`; document; notify.

## Build & reliability log (2026-05-26, shipped)

Built TDD-first. `detect_cues` now returns `list[CueAnchor]` (`source="auto"`); seam
`cue_types.py` created; `embed.py` consumer rewired (`usable=list(cues)`, `window=end_s-start`);
`CueAnchor` exported from `vibemix.library`. Full suite: **313 passed, 1 xfailed** (pre-existing
budget gate, unrelated). Import-boundary gate (`test_no_live_path_import`) stays green (state.detectors
imports kept lazy).

**Seeing it in action surfaced two real bugs the synthetic tests missed (the loop):**
1. **Dance-gate false-negative on compressed masters.** Original G2 (raw-RMS dynamic range ≥0.35)
   demoted a 160 BPM hardtechno track (0.19 dyn-range, brick-walled) to GENERIC → every cue collapsed
   to "intro". G3 (full-band-margin ≥0.15) never passed (segment products differed <0.03). **Fix:**
   replaced G2+G3 with G1 (periodic kick) + **G2' = spread of track-NORMALIZED segment energy ≥0.40**
   (self-relative → survives compression). All real dance tracks now pass.
2. **Over-segmentation** (20-30 micro-segments/track). **Fix:** `_MIN_SECTION_S=16s` boundary merge +
   `_FOOTE_K` 1.0→1.5. Now ~5-12 sections.
3. **Labeler noise** (every segment labeled → loud mid sections mislabeled "intro"; "build" spam).
   **Fix:** label only canonical anchors (intro, build-into-drop, breakdown, drop(s), outro), skip the
   rest — precision over coverage.

**Reliability sweep (40 real tracks, hardtechno/psytrance/etc):** 0 crashes, 1 empty (honest), 5
degraded to intro/outro (12.5%), **31/40 (78%) full drop-bearing structure**, avg 4.2 cues/track,
windows always ≤80s, confidence mean 0.57 / **85% ≥0.5** (lows correctly flag octave-confused BPM).
Determinism: identical on repeat. Analysis ~0.6s/track avg.

**Known limitations (acceptable v1, noted):** (a) BPM octave errors on some psytrance (~140 read as 70)
lower confidence honestly rather than mislabel; (b) no true downbeat tracker (madmom absent) — interim
autocorr-comb lock + honest internal `snapped` flag; (c) DJ-cue cross-check (strongest auto metric)
needs a Rekordbox `collection.xml` export (KAAN-ACTION — the cue DB is SQLCipher `master.db`, untouched);
(d) seam has no neutral `"section"` label, so non-dance emits only intro+outro (extend seam if wanted).
