# INTEL-01 spec - Rekordbox ANLZ structure ingest

**Date:** 2026-05-27
**Scope:** implementation-ready spec for the first intelligence-excellence phase
**Depends on:** `.planning/research/2026-05-27-intelligence-excellence-direction.md`
**Code posture:** PR-1/PR-2 bridge implemented: `anlz_ingest.py`,
`CueSource="anlz"`, `excerpt.py` DJ -> ANLZ -> auto priority, caller-injected
ingest wiring, product CLI orchestration, cache-safe ANLZ vectors, and
`intel_anlz_audit.py` are wired with focused tests.

## Goal

Make Rekordbox ANLZ the primary offline structure source for vibemix:

```text
DJ cues -> Rekordbox ANLZ PSSI -> CUE-DETR -> DSP fallback -> whole-track fallback
```

For Kaan's current library this turns the app from heuristic cue guessing into
ground-truth section reasoning over ~91% of analyzed tracks.

## Local probe evidence

Probe run on Kaan's machine via `scripts/eval/intel_anlz_audit.py`, 2026-05-27.
Default discovery scans both the current `share/PIONEER/USBANLZ` tree and the
legacy `PIONEER/USBANLZ` tree:

```text
ANLZ .EXT files:             493
ANLZ .EXT with PSSI:         449
ANLZ parse errors:           0
PSSI moods:                  high=346, mid=101, low=2
phrase count min/med/max:    1 / 19 / 158
.EXT with .DAT sibling:      493
.DAT with PQTZ beatgrid:     493
PSSI with PQTZ beatgrid:     449
PPTH paths:                  493
PPTH unique basenames:       477
PPTH duplicate basenames:    12
library tracks in cache:     1547
library unique basenames:    1385
library duplicate basenames: 157
PPTH basenames matched to library cache: 476 / 477
```

Implications:

- PSSI coverage is high enough to be product-primary.
- `.DAT` `PQTZ` provides per-beat timing for every PSSI file observed.
- PPTH basename matching is viable but must be collision-aware.
- We do not need `master.db`, SQLCipher, process memory, screen vision, or PRO DJ
  LINK for this phase.

## Source facts

pyrekordbox exposes these tags with:

```python
from pyrekordbox.anlz import AnlzFile
anlz = AnlzFile.parse_file(path)
pssi_tags = anlz.getall_tags("PSSI")
ppth_tags = anlz.getall_tags("PPTH")
pqtz_tags = dat_anlz.getall_tags("PQTZ")
```

Relevant tag facts:

- `.EXT`:
  - `PPTH`: source audio path, often `?/basename.ext` in local Rekordbox folders.
  - `PSSI`: phrase structure.
  - `PCO2` / `PCOB`: cue lists.
  - `PQT2`: extended beat-grid-ish data, but in practice only sparse tempo
    anchors on Kaan's files. Do not use it as the primary beat-to-time map.
- `.DAT` sibling:
  - `PQTZ`: per-beat grid. `tag.get_times()` returns beat times in seconds;
    `tag.get_bpms()` returns BPM per beat; `tag.get_beats()` returns beat-in-bar.

pyrekordbox ANLZ docs:

- https://pyrekordbox.readthedocs.io/en/stable/formats/anlz.html
- PSSI phrase entries specify phrase start `beat`; phrase continues until the
  next phrase start or PSSI header `end_beat`.

## Proposed module

Add:

```text
src/vibemix/library/anlz_ingest.py
```

Import posture:

- stdlib + dataclasses + pathlib at top level;
- lazy import `pyrekordbox.anlz.AnlzFile` inside parse functions;
- no SQLCipher imports;
- no `pyrekordbox.db6`;
- no audio decode;
- no eager local-model load;
- no file writes.

## Public API

```python
@dataclass(frozen=True, slots=True)
class AnlzBeatGrid:
    times_s: tuple[float, ...]      # per-beat absolute seconds from PQTZ
    bpms: tuple[float, ...]         # per-beat BPM from PQTZ
    beat_in_bar: tuple[int, ...]    # 1..4-ish from PQTZ

@dataclass(frozen=True, slots=True)
class AnlzPhrase:
    index: int
    mood: int
    kind: int
    raw_label: str
    cue_label: CueLabel | None
    start_beat: int
    end_beat: int
    start_s: float
    end_s: float
    confidence: float
    flags: dict[str, int]

@dataclass(frozen=True, slots=True)
class AnlzTrackMeta:
    ext_path: Path
    dat_path: Path
    ppth_path: str
    basename_key: str
    beatgrid: AnlzBeatGrid
    phrases: tuple[AnlzPhrase, ...]
```

Functions:

```python
def iter_anlz_ext_files(root: Path | None = None) -> Iterator[Path]: ...

def parse_anlz_bundle(ext_path: Path) -> AnlzTrackMeta | None: ...

def build_anlz_index(root: Path | None = None) -> AnlzIndex: ...

def match_track_to_anlz(track: TrackEntry, index: AnlzIndex) -> AnlzTrackMeta | None: ...

def anchors_from_anlz(track: TrackEntry, meta: AnlzTrackMeta, *, max_cues: int) -> list[CueAnchor]: ...
```

`parse_anlz_bundle` returns `None` honestly when any required structure is
missing:

- no PSSI;
- no PPTH;
- no sibling `.DAT`;
- no PQTZ;
- empty beatgrid;
- no phrase with a mappable cue label.

It should not raise for ordinary missing analysis.

## Beat-to-time conversion

Use `.DAT` `PQTZ`:

```python
times = pqtz.get_times()  # seconds, one item per beat
```

PSSI uses one-indexed absolute beat numbers. Convert with:

```python
idx = max(0, beat - 1)
if idx < len(times):
    return times[idx]
```

Fallback for a phrase end beyond the last known beat:

```python
last_time = times[-1]
last_bpm = bpms[-1] if bpms else track.bpm
return last_time + (idx - (len(times) - 1)) * 60.0 / last_bpm
```

Only use the fallback when `last_bpm > 0`; otherwise drop that phrase. This is
still grounded in the final known grid segment and avoids fabricating a tempo.

Do not use `.EXT` `PQT2` as the first choice. In observed files it had only two
tempo anchors while `.DAT` `PQTZ` carried every beat.

## PSSI role mapping

`CueAnchor` currently supports:

```text
intro | build | breakdown | drop | outro
```

ANLZ phrase labels are richer/different. Preserve the original `raw_label` in
`AnlzPhrase`; only map to `CueAnchor` when we can do so honestly enough.

### Mood 1: high

This is the best EDM/dance vocabulary and should receive the highest ANLZ
confidence.

| PSSI kind | Rekordbox label | CueAnchor label | Base confidence |
|-----------|-----------------|-----------------|-----------------|
| 1 | Intro 1/2 | intro | 0.84 |
| 2 | Up 1/2/3 | build | 0.82 |
| 3 | Down | breakdown | 0.84 |
| 5 | Chorus 1/2 | drop | 0.80 |
| 6 | Outro 1/2 | outro | 0.84 |
| other | unknown | None | drop from CueAnchor list |

High mood flag handling:

- `kind=1`, `k1=1` -> `Intro 1`; otherwise `Intro 2`.
- `kind=2`, `k2=1` -> `Up 2`; `k1=1` -> `Up 3`; otherwise `Up 1`.
- `kind=5`, `k1=1` -> `Chorus 2`; otherwise `Chorus 1`.
- `kind=6`, `k1=1` -> `Outro 1`; otherwise `Outro 2`.

The expanded label is useful later; the `CueAnchor` label stays coarse.

### Mood 2: mid

Mid mood uses pop-ish labels. Boundaries are still useful; labels are less
precise for techno.

| PSSI kind | Rekordbox label | CueAnchor label | Base confidence |
|-----------|-----------------|-----------------|-----------------|
| 1 | Intro | intro | 0.72 |
| 2-7 | Verse 1-6 | build | 0.56 |
| 8 | Bridge | breakdown | 0.64 |
| 9 | Chorus | drop | 0.66 |
| 10 | Outro | outro | 0.72 |

The verse -> build mapping is deliberately low-confidence. It gives the embedder
a useful window but tells downstream consumers to hedge.

### Mood 3: low

Low mood is rare on this rig and much less dance-specific.

| PSSI kind | Rekordbox label | CueAnchor label | Base confidence |
|-----------|-----------------|-----------------|-----------------|
| 1 | Intro | intro | 0.60 |
| 2-7 | Verse 1/2 variants | build | 0.42 |
| 8 | Bridge | breakdown | 0.50 |
| 9 | Chorus | drop | 0.52 |
| 10 | Outro | outro | 0.60 |

For `CueAnchor` consumers, a confidence floor should decide whether to keep low
mood anchors. For future `SectionIntelligence`, keep them all as sections.

## Confidence adjustment

Start with the base confidence above. Then adjust:

- subtract `0.10` when phrase duration is under 8 bars;
- subtract `0.08` when phrase duration is over 96 bars;
- subtract `0.08` when beat-to-time required extrapolation past PQTZ;
- subtract `0.05` when `fill != 0` and the phrase end is trimmed to fill start;
- clamp to `[0.0, 0.92]`.

Keep only `CueAnchor`s with final confidence `>= 0.45` for the `excerpt.py`
fallback tier. Future live suggestions should likely use a higher floor
(`>= 0.60`) before speaking timing claims.

## Fill handling

PSSI entries may contain:

```text
fill
beat_fill
```

Docs describe fill as short improvisational changes at phrase ends. V1 should:

- preserve fill fields in `AnlzPhrase.flags`;
- if `fill != 0` and `start_beat < beat_fill < end_beat`, use `beat_fill` as
  `end_beat` for the cue window boundary, because the fill is less stable for a
  clean mix-in/out;
- do not create separate fill anchors yet.

## Path indexing and matching

Observed PPTH examples include:

```text
?/Six ou Sept - Reality.mp3
```

Build an index:

```python
basename_key = normalize(Path(ppth_path.replace("?/", "")).name)
index.by_basename[basename_key].append(meta)
```

Normalization:

- lowercase;
- Unicode normalize NFC;
- strip surrounding whitespace;
- compare full basename including extension first.

Matching:

1. If `TrackEntry.filepath` basename matches exactly one meta, return it.
2. If multiple metas share the basename:
   - if PPTH contains path segments beyond basename, try suffix match against
     normalized `TrackEntry.filepath`;
   - if still multiple, return `None` and record a collision.
3. If no basename match, return `None`.

Reason:

- PPTH unique-basename match covers nearly all observed ANLZ entries.
- Duplicate basenames are real both in PPTH and in the library cache.
- A wrong ANLZ match is worse than no ANLZ; fallback to CUE-DETR/DSP is safer.

## Integration point

Modify `src/vibemix/library/excerpt.py::anchors_for_track`:

```text
1. structural DJ cue/loop marks -> source="dj"
2. ANLZ PSSI phrases -> source="anlz"
3. detect_cues_auto(...) -> source="auto"
4. [] -> caller whole-track fallback
```

Required `CueSource` change:

```python
CueSource = Literal["dj", "anlz", "auto"]
```

This is the only cross-module type-contract change needed for INTEL-01.

## Anti-hallucination rules

- Never create an ANLZ anchor without a parsed PSSI phrase and a PQTZ time.
- Never match ANLZ to a track through an ambiguous basename collision.
- Never synthesize BPM from filename/title.
- Never touch `master.db`.
- Never treat `.EXT` PSSI as live playhead data. It is offline structure only.
- Preserve source/confidence so downstream surfaces can hedge.

## Tests to add first

Create fixtures as plain dataclass/container fakes rather than checking binary
ANLZ files into the repo at first.

### Unit tests for mapping

`tests/library/test_anlz_ingest.py`

- high mood maps kind 1/2/3/5/6 -> intro/build/breakdown/drop/outro.
- high mood unknown kind drops from `CueAnchor` list.
- mid mood verse maps to low-confidence build.
- low mood anchors below the confidence floor drop when configured.
- fill trims end beat when valid.
- phrase end uses next phrase beat, last phrase uses `end_beat`.

### Unit tests for beat-to-time

- beat 1 maps to `PQTZ.times[0]`.
- beat N maps to `PQTZ.times[N - 1]`.
- beyond-grid beat extrapolates from final BPM.
- beyond-grid beat with no BPM drops phrase.

### Unit tests for path matching

- unique basename matches.
- duplicate basename with suffix match resolves.
- duplicate basename without suffix match returns `None`.
- unmatched basename returns `None`.

### Integration-ish tests for `excerpt.py`

- DJ cue wins over ANLZ.
- no DJ cue + ANLZ returns `source="anlz"` anchors.
- no ANLZ falls back to `detect_cues_auto`.
- ANLZ parse exception falls back to `detect_cues_auto`.

### Regression checks

- importing `vibemix.library.anlz_ingest` does not import `pyrekordbox.db6`.
- importing `vibemix.library.excerpt` remains heavy-dep-light.
- `git grep "Rekordbox6Database\\|pyrekordbox.db6" src/vibemix/library`
  remains empty except explicit negative tests/docs.

## CLI / debug command

Add later, after module tests:

```text
uv run python -m vibemix library anlz-stats --json
```

Output:

```json
{
  "ext_files": 493,
  "with_pssi": 449,
  "with_pqtz": 493,
  "matched_tracks": 476,
  "duplicate_basenames": 12,
  "moods": {"1": 346, "2": 101, "3": 2},
  "parse_errors": 0
}
```

This gives future debugging a source-backed view instead of relying on memory.

## Follow-on unlocks

Once INTEL-01 lands, the next phases become straightforward:

- `INTEL-02`: store per-section CLAP vectors, not only pooled track vectors.
- `INTEL-03`: rank section-to-section transitions.
- `INTEL-04`: export smart hot cues using ANLZ sections.
- `INTEL-05`: hand the agent a grounded `MusicalContextPacket`.

The important thing: ANLZ is not just "better cues." It is the structural spine
that lets the agent reason musically without pretending raw audio comprehension
comes from the LLM.
