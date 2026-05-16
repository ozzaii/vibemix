# vibemix Eval Corpus — Real DJ Session Manifest (6 × ~30min)

> **Public-domain or CC0 sources only** — per CONTEXT EVAL-03 + Pitfall P43.
> Kaan-discharge runbook in `.planning/KAAN-ACTION-LEGAL.md §GATE-03`.

This is the schema-first markdown template for the 6 real-corpus DJ sessions
that back the hallucination-gate threshold recalibration (Plan 42-02) and the
real-corpus check mode of the eval CI workflow (`.github/workflows/eval.yml
--check-real-corpus`).

**Diversity invariant:** `≥2 genres minimum` across the 6 sessions (CONTEXT
EVAL-03 contract surface — `scripts/release/check_ear_test.sh` reads this
manifest at gate time). Phase 27-03 shipped a stricter ≥3-genre target; Phase
42 relaxes the contract surface to "≥2 genres" so the gate can still fire on
a partial corpus, with Kaan-discharge directed at the full 6-session set.

The structured JSON twin is `eval/corpus/manifest.json` (Phase 27-03 schema).
This file is the human-readable companion + license/attribution audit trail.

---

## Schema

Each session block carries the seven required fields:

| Field           | Type   | Notes                                                  |
| --------------- | ------ | ------------------------------------------------------ |
| Session ID      | str    | `<genre>_<NN>` — must match `manifest.json`            |
| Genre           | str    | `hard_tek`, `techno`, `house` (Phase 42 contract)      |
| Duration (s)    | int    | ≥ 1500 (25 min) per session                            |
| Source URL      | url    | Direct link to the public-domain / CC0 origin         |
| License         | str    | One of: `CC0`, `CC-BY`, `CC-BY-SA`, `Public Domain`   |
| Attribution     | str    | Artist + title + year (for CC-BY / CC-BY-SA records)  |
| SHA256          | hex    | `sha256sum` of the normalized 16kHz mono WAV          |

Normalization invocation (mandatory before commit):

```bash
ffmpeg -i <raw> -ac 1 -ar 16000 eval/corpus/sessions/<id>/audio.wav
sha256sum eval/corpus/sessions/<id>/audio.wav
```

---

## Sessions

### hard_tek_01

- **Session ID:** `hard_tek_01`
- **Genre:** `hard_tek`
- **Duration (s):** _placeholder — Kaan to fill_
- **Source URL:** _placeholder — archive.org / FMA Electronic_
- **License:** _placeholder — must be CC0 / CC-BY / Public Domain_
- **Attribution:** _placeholder_
- **SHA256:** _placeholder — fill after ffmpeg normalization_

### hard_tek_02

- **Session ID:** `hard_tek_02`
- **Genre:** `hard_tek`
- **Duration (s):** _placeholder_
- **Source URL:** _placeholder_
- **License:** _placeholder_
- **Attribution:** _placeholder_
- **SHA256:** _placeholder_

### techno_01

- **Session ID:** `techno_01`
- **Genre:** `techno`
- **Duration (s):** _placeholder_
- **Source URL:** _placeholder — CCMixter / FMA Electronic_
- **License:** _placeholder_
- **Attribution:** _placeholder_
- **SHA256:** _placeholder_

### techno_02

- **Session ID:** `techno_02`
- **Genre:** `techno`
- **Duration (s):** _placeholder_
- **Source URL:** _placeholder_
- **License:** _placeholder_
- **Attribution:** _placeholder_
- **SHA256:** _placeholder_

### house_01

- **Session ID:** `house_01`
- **Genre:** `house`
- **Duration (s):** _placeholder_
- **Source URL:** _placeholder — CCMixter / FMA Electronic_
- **License:** _placeholder_
- **Attribution:** _placeholder_
- **SHA256:** _placeholder_

### house_02

- **Session ID:** `house_02`
- **Genre:** `house`
- **Duration (s):** _placeholder_
- **Source URL:** _placeholder_
- **License:** _placeholder_
- **Attribution:** _placeholder_
- **SHA256:** _placeholder_

---

## Storage

All session WAV files live under `eval/corpus/sessions/<id>/audio.wav` and are
git-LFS-tracked per `.gitattributes`:

```
eval/corpus/sessions/**/*.wav filter=lfs diff=lfs merge=lfs -text
```

Fresh clones pull only the LFS pointer files; CI fetches the bytes only when
the eval gate fires (`.github/workflows/eval.yml`). Total committed size for
the full 6-session corpus: ~200 MB.

## Diversity Gate

The hallucination-gate check (`scripts/release/check_ear_test.sh`,
Plan 42-03) reads this manifest and asserts:

- `≥2 genres minimum` represented across all populated sessions.
- Every populated session has a license slot filled (no `_placeholder_`).

Current state: 0 / 6 sessions populated. The 6 placeholders above unblock
Plan 42-02 (threshold recalibration) by giving it stable IDs to read; the
real WAV bytes ship via `.planning/KAAN-ACTION-LEGAL.md §GATE-03`.

## Audit Trail

- Plan 27-03 created the structured JSON skeleton (`manifest.json`) and per-session subdirs.
- Plan 42-01 (this commit) creates the human-readable MANIFEST.md template, expands LICENSES.md schema, and ships the §GATE-03 Kaan-discharge runbook.
- Plan 42-02 will consume this manifest from `scripts/eval/recalibrate_thresholds.py`.
