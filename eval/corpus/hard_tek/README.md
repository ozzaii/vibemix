# Hard Tek reference corpus (Phase 30 SENSE-20)

Curated set used by `scripts/tune_detectors.py --genre-override=hard_tek <wav...>`
to validate `DISTORTION_CLIMB` + `ACID_LINE_ENTRY` detector thresholds against
real Hard Tek tracks (140-180 BPM band).

## Acquisition policy

Per Phase 27 corpus policy (`eval/corpus/LICENSES.md`):

- **Archive.org** — CC-BY / CC-BY-SA Hard Tek mixes + tracks.
- **CCMixter** — CC-BY remixable tracks.
- **FMA (Free Music Archive)** — CC-licensed electronic + hard techno.

Tracks ship with full attribution + license in `eval/corpus/LICENSES.md`.
**No DRM / no commercial pressings.**

## Layout

```
eval/corpus/hard_tek/
├── README.md              ← this file
├── audio/
│   ├── <slug>.wav         ← 16kHz mono OR original sample rate (harness resamples)
│   └── ...
└── <slug>.json            ← per-track sidecar with expected fire timestamps
```

The per-track JSON sidecar carries the F1-scoring ground truth:

```json
{
  "title": "Track Title",
  "artist": "Artist Name",
  "bpm": 160,
  "license": "CC-BY 4.0",
  "source_url": "https://archive.org/...",
  "expected_fires": [
    { "type": "DISTORTION_CLIMB", "t_seconds_estimate": 84.0 },
    { "type": "ACID_LINE_ENTRY",  "t_seconds_estimate": 120.0 }
  ],
  "why_included": "Industrial Hard Tek with sustained kick wall + acid breakdown"
}
```

## Curated set (KAAN-ACTION pending)

Tracks 1-5 below are TBD. Status tracked in `.planning/KAAN-ACTION-LEGAL.md`
under `HARDTEK-CORPUS-001`. Until tracks land, CI runs against synthetic
fixtures in `tests/state/detectors/test_distortion_climb.py` +
`test_acid_line_entry.py`.

| # | Slug | Title | Artist | BPM | Length | License | Why |
|---|------|-------|--------|-----|--------|---------|-----|
| 1 | TBD | TBD | TBD | 150 | TBD | TBD | Baseline distortion-climb anchor |
| 2 | TBD | TBD | TBD | 160 | TBD | TBD | Acid-line entry mid-track |
| 3 | TBD | TBD | TBD | 170 | TBD | TBD | Distorted-kick + acid stack |
| 4 | TBD | TBD | TBD | 175 | TBD | TBD | Clean hard tek (negative — neither overlay should fire) |
| 5 | TBD | TBD | TBD | 180 | TBD | TBD | Edge BPM upper-bound — verify GenreRouter still routes hard_tek |

## Tuning run

```bash
python scripts/tune_detectors.py \
    --genre-override=hard_tek \
    --bpm-override=160 \
    eval/corpus/hard_tek/audio/*.wav \
    --csv eval/tuning/hard_tek_$(date +%Y-%m-%d).csv
```

Output: per-fire CSV with `detector_name`, `t_seconds`, `score`, `threshold`.
Cross-check against the per-track JSON sidecar in Phase 16 ear-audit.

## Synthetic fallback (current CI coverage)

Until the 5 anchor tracks land, the two overlay detectors are exercised by
deterministic synthetic fixtures in CI:

- `tests/state/detectors/test_distortion_climb.py` — clipped 60Hz square +
  white-noise mix walks rising-flatness curve through 9 ticks. 6 tests.
- `tests/state/detectors/test_acid_line_entry.py` — log-linear 250→600Hz
  sweep + rising tone-amp drives the Q proxy from ~2 to ~40. 6 tests.

These pin the algorithmic contracts; real-track F1 scoring is the gap that
HARDTEK-CORPUS-001 closes.

## Replay through Phase 27 eval harness

Once tracks land, the same WAVs feed `scripts/eval/replay_harness.py` for
per-detector-per-genre F1 scoring (Phase 27 EVAL-03 matrix). The hard_tek
genre slice must clear F1 ≥ 0.80 per detector before v1 release. The
2-judge cross-check rubric (Gemini-only — no Anthropic in product per
project memory) lives in `eval/rubrics/`.
