# vibemix Eval Corpus — License Records

Per CONTEXT EVAL-03 + Pitfall P43: the eval corpus uses ONLY public-domain
or CC0-licensed material. No Kaan recordings (privacy + overfit). No
proprietary tracks. This file is the authoritative source of license
provenance per session.

## Sources Allowed

1. **archive.org** — `licenseurl:*publicdomain*` or CC0 filter
2. **CCMixter** — CC0 / Attribution licenses only
3. **Free Music Archive Electronic** — public domain / CC0 only

## Session Inventory

The 6 session directories under `eval/corpus/sessions/` are populated by
Kaan via the `.planning/KAAN-ACTION-LEGAL.md §GATE-03` workflow (corpus
acquisition). Each session has its own `source.txt` with URL + license +
attribution inside the session dir; this file aggregates those for audit.

### Per-session schema (Plan 42-01 expansion)

Each block must carry six fields. Empty placeholders mean Kaan-discharge
has not landed yet.

```text
- Source URL: <direct public-domain / CC0 link>
- License:    <CC0 | CC-BY | CC-BY-SA | Public Domain>
- Attribution: <Artist — Title (Year)>
- Retrieval date: <YYYY-MM-DD>
- ffmpeg normalize: ffmpeg -i <raw> -ac 1 -ar 16000 <out>
- SHA256:    <sha256sum of normalized WAV>
```

### hard_tek_01

- **Source URL:** _placeholder — Kaan to fill from scripts/eval/source_corpus.py output_
- **License:** _placeholder_
- **Attribution:** _placeholder_
- **Retrieval date:** _placeholder_
- **ffmpeg normalize:** `ffmpeg -i raw.wav -ac 1 -ar 16000 eval/corpus/sessions/hard_tek_01/audio.wav`
- **SHA256:** _placeholder_
- **Duration:** _≥ 25 min_

### hard_tek_02

- **Source URL:** _placeholder_
- **License:** _placeholder_
- **Attribution:** _placeholder_
- **Retrieval date:** _placeholder_
- **ffmpeg normalize:** `ffmpeg -i raw.wav -ac 1 -ar 16000 eval/corpus/sessions/hard_tek_02/audio.wav`
- **SHA256:** _placeholder_
- **Duration:** _≥ 25 min_

### techno_01

- **Source URL:** _placeholder_
- **License:** _placeholder_
- **Attribution:** _placeholder_
- **Retrieval date:** _placeholder_
- **ffmpeg normalize:** `ffmpeg -i raw.wav -ac 1 -ar 16000 eval/corpus/sessions/techno_01/audio.wav`
- **SHA256:** _placeholder_
- **Duration:** _≥ 25 min_

### techno_02

- **Source URL:** _placeholder_
- **License:** _placeholder_
- **Attribution:** _placeholder_
- **Retrieval date:** _placeholder_
- **ffmpeg normalize:** `ffmpeg -i raw.wav -ac 1 -ar 16000 eval/corpus/sessions/techno_02/audio.wav`
- **SHA256:** _placeholder_
- **Duration:** _≥ 25 min_

### house_01

- **Source URL:** _placeholder_
- **License:** _placeholder_
- **Attribution:** _placeholder_
- **Retrieval date:** _placeholder_
- **ffmpeg normalize:** `ffmpeg -i raw.wav -ac 1 -ar 16000 eval/corpus/sessions/house_01/audio.wav`
- **SHA256:** _placeholder_
- **Duration:** _≥ 25 min_

### house_02

- **Source URL:** _placeholder_
- **License:** _placeholder_
- **Attribution:** _placeholder_
- **Retrieval date:** _placeholder_
- **ffmpeg normalize:** `ffmpeg -i raw.wav -ac 1 -ar 16000 eval/corpus/sessions/house_02/audio.wav`
- **SHA256:** _placeholder_
- **Duration:** _≥ 25 min_

## Diversity Gate

Per CONTEXT EVAL-03 / Pitfall P43:
- ≥ 6 sessions total
- ≥ 3 distinct genres (Phase 27-03 hard target)
- ≥ 2 genres minimum (Phase 42-01 relaxed contract surface for `check_ear_test.sh`)
- Hard Tek share ≤ 70%

Current corpus: 2 hard_tek + 2 techno + 2 house = 6 sessions, 3 genres,
hard_tek = 33.3% (2/6). Passes the gate at the skeleton level; real WAV
bytes are Kaan-discharge per `.planning/KAAN-ACTION-LEGAL.md §GATE-03`.

## Audit Trail

- 2026-05-15 — Phase 27-03: placeholder schema (6 session blocks) created.
- 2026-05-16 — Plan 42-01: schema expanded with Source URL / License /
  Attribution / Retrieval date / ffmpeg normalize / SHA256 slots. GATE-03
  runbook added to KAAN-ACTION-LEGAL.md.
