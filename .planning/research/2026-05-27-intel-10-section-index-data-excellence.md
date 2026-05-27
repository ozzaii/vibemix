# INTEL-10: section index and data-excellence storage plan

**Date:** 2026-05-27
**Lane:** data excellence / retrieval / section intelligence
**Depends on:** INTEL-01, INTEL-02, INTEL-03, INTEL-07, INTEL-09
**Status:** build-prep spec; no product code touched

## Why this exists

The current library store is clean and intentionally narrow:

- one 512-d local CLAP vector per track;
- two interchangeable backends: `SqliteVecStore` and `NumpyStore`;
- sqlite-vec is storage-only;
- all ranking runs through `library._cosine.cosine_topk()`;
- cue-anchored ingest mean-pools cue windows back to one track vector;
- content-hash cache is keyed by file bytes, backend tag, and strategy version.

That design should not be contorted into section search. Track-level vectors are
still useful for crate discovery and broad vibe retrieval. Section-aware mixing
needs a second index whose row is a musical section, not a whole track.

The data-excellence move is:

```text
track_id -> one track vector
section_id -> one section vector + deterministic section metadata
```

Keep both. Do not replace one with the other.

## Current local seams

### Store

`src/vibemix/library/store.py`

- `LibraryStore.add_batch([(track_id, vector), ...])`
- `LibraryStore.search(query_vector, k)`
- `LibraryStore.search_centered(query_vector, k)`
- `LibraryStore.delete(track_ids)`
- `LibraryStore.snapshot_hash()`

### Backends

`src/vibemix/library/index_numpy.py`

- vector file: `~/.cache/vibemix/library-clap_vectors.npy`
- ID file: `~/.cache/vibemix/library-clap_ids.json`
- strict row alignment;
- shape `(N, 512)`;
- atomic writes.

`src/vibemix/library/index_sqlite_vec.py`

- db file: `~/.cache/vibemix/library-clap.db`
- table: `vec_library(track_id, embedding)`
- reads all rows ordered by `track_id`;
- shared Python cosine ranking.

### Ingest

`src/vibemix/library/ingest.py`

- `ingest_source()` iterates source tracks.
- `_embed_track_cue_anchored()` maps cues to windows, embeds each window, then
  mean-pools back to one vector.
- When no usable structure exists, it whole-track embeds.
- It never stores fake vectors.
- Current strategy version: `INGEST_CUE_STRATEGY_VERSION`.

### Cue/source boundary

`src/vibemix/library/excerpt.py`

- `anchors_for_track()` returns DJ cues first, auto cues second.
- It currently has no ANLZ branch.
- It emits `CueAnchor` with `source in {"dj", "auto"}`.

`src/vibemix/library/cue_types.py`

- `CueAnchor(label, start_s, end_s, confidence, source)`.
- `CueSource` currently needs `"anlz"` before INTEL-01 can land.

## Proposed architecture

Add a sibling section-store surface, parallel to `LibraryStore`.

```text
src/vibemix/library/section_store.py
src/vibemix/library/section_index_numpy.py
src/vibemix/library/section_index_sqlite_vec.py
src/vibemix/library/section_ingest.py
src/vibemix/library/section_types.py
```

Do not mutate the existing `LibraryStore` API in the first slice. A separate
surface lowers risk and preserves every current test about track-level search.

## Data contracts

### `SectionId`

Use a deterministic string ID.

```text
<track_id>#s<zero_padded_index>
```

Example:

```text
t000123#s004
```

Rules:

- section index is ordered by start beat/time;
- ID is stable across re-ingest if the same ANLZ phrase boundaries survive;
- if boundaries change, the strategy hash changes and stale section rows are
  replaced for that track;
- never expose file paths through IDs.
- provenance (`dj`, `anlz`, `auto`, `fallback`) is metadata, not part of the
  public ID. Raw analysis variants can use a separate debug `analysis_id` later.

### `SectionRecord`

```python
@dataclass(frozen=True, slots=True)
class SectionRecord:
    section_id: str
    track_id: str
    ordinal: int
    role: str
    role_confidence: float
    start_s: float
    end_s: float
    start_beat: int | None
    end_beat: int | None
    bpm: float | None
    camelot: str | None
    energy: float | None
    source: Literal["dj", "anlz", "auto", "fallback"]
    source_confidence: float
    embedding_strategy: str
    content_hash: str
    analysis_run_id: str
    role_mapper_version: str
    section_extraction_version: str
```

Notes:

- `role` comes from INTEL-07 ontology, not raw ANLZ labels.
- `role_confidence` is confidence in the normalized role, not in audio decode.
- `energy` can be null in v1; deterministic audio energy can fill it later.
- `content_hash` is track file hash plus section window and strategy version.
- `analysis_run_id`, `role_mapper_version`, and `section_extraction_version`
  follow INTEL-17 so a bad suggestion can be traced back to the section build
  that produced it.
- This record is metadata. The vector lives in the vector backend.

### `SectionVectorRow`

```python
section_id: str
vector: np.ndarray  # shape (512,), float32, L2-normalized
```

The section vector table should not duplicate all metadata. Keep metadata in a
JSON sidecar or sqlite table so vector backends stay simple and parity-safe.

## Storage shape

### Sqlite primary

Use one db file:

```text
~/.cache/vibemix/sections-clap.db
```

Tables:

```sql
CREATE VIRTUAL TABLE vec_sections USING vec0(
  section_id TEXT PRIMARY KEY,
  embedding FLOAT[512] distance_metric=cosine
);

CREATE TABLE section_meta (
  section_id TEXT PRIMARY KEY,
  track_id TEXT NOT NULL,
  ordinal INTEGER NOT NULL,
  role TEXT NOT NULL,
  role_confidence REAL NOT NULL,
  start_s REAL NOT NULL,
  end_s REAL NOT NULL,
  start_beat INTEGER,
  end_beat INTEGER,
  bpm REAL,
  camelot TEXT,
  energy REAL,
  source TEXT NOT NULL,
  source_confidence REAL NOT NULL,
  embedding_strategy TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  updated_at REAL NOT NULL
);

CREATE INDEX idx_section_meta_track ON section_meta(track_id);
CREATE INDEX idx_section_meta_role ON section_meta(role);
```

Ranking posture:

- mirror `SqliteVecStore`;
- load `section_id, embedding ORDER BY section_id ASC`;
- rank with shared Python cosine;
- then join metadata by selected IDs.

Do not use sqlite-vec KNN in v1. Determinism beats cleverness here.

### Numpy fallback

Use:

```text
~/.cache/vibemix/sections-clap_vectors.npy
~/.cache/vibemix/sections-clap_ids.json
~/.cache/vibemix/sections-clap_meta.jsonl
```

Rules:

- `.npy` and IDs mirror `NumpyStore`;
- JSONL maps `section_id -> SectionRecord`;
- writes are atomic as a set;
- load validates that every vector ID has metadata and every metadata row has a
  vector ID;
- failure is loud, not partial.

## API surface

```python
class SectionStore:
    @property
    def backend_name(self) -> str: ...

    def add_batch(
        self,
        items: list[tuple[SectionRecord, np.ndarray]],
    ) -> None: ...

    def search(
        self,
        query_vector: np.ndarray,
        *,
        k: int = 20,
        role_filter: set[str] | None = None,
        exclude_track_ids: set[str] | None = None,
    ) -> list[tuple[SectionRecord, float]]: ...

    def load_track_sections(self, track_id: str) -> list[SectionRecord]: ...

    def delete_track(self, track_id: str) -> None: ...

    def snapshot_hash(self) -> str: ...

    def close(self) -> None: ...
```

Rules:

- `add_batch` replaces all rows with the same `section_id`;
- `delete_track(track_id)` removes both vectors and metadata for one track;
- `search` still uses `_cosine.cosine_topk()`;
- role filtering happens before final top-k if cheap, otherwise after top-k with
  overfetch;
- `exclude_track_ids` is required for "find next track section" so the current
  track does not recommend itself.

## Ingest plan

### Phase A: section extraction only

Build records without embeddings.

```python
def sections_for_track(track: TrackEntry, anlz_index: AnlzIndex | None) -> list[SectionRecord]
```

Source priority:

1. DJ cues and loops, when present and structural.
2. Rekordbox ANLZ PSSI phrases.
3. CUE-DETR / current auto-cue output.
4. whole-track fallback section.

Output:

- one or more `SectionRecord`;
- stable roles from INTEL-07;
- no fake section when file is missing;
- no raw file path persisted.

### Phase B: section embedding

Slice each section window and embed it.

```python
def embed_sections(
    track: TrackEntry,
    sections: list[SectionRecord],
    embedder: _Embedder,
    slicer: Callable[[str, float, float], bytes],
) -> list[tuple[SectionRecord, np.ndarray]]
```

Rules:

- section window max stays 80s for CLAP compatibility;
- long sections split into subwindows and mean-pool within that section;
- every output vector is L2-normalized;
- one bad subwindow skips that subwindow;
- all subwindows failing drops that section, not the whole track;
- all sections failing can still whole-track fallback as one `fallback` section.

### Phase C: section ingest orchestrator

```python
def ingest_sections_source(
    source: _Source,
    embedder: _Embedder,
    section_store: SectionStore,
    *,
    track_store: LibraryStore | None = None,
    anlz_index: AnlzIndex | None = None,
    cache: sqlite3.Connection | None = None,
) -> SectionIngestReport
```

Behavior:

- use the same source iteration as `ingest_source()`;
- resolve local path once;
- build section records;
- embed section windows;
- write section rows;
- optionally keep the existing track-level ingest untouched;
- write a report with `tracks_total`, `sections_total`, `sections_embedded`,
  `sections_cached`, `sections_failed`, `tracks_without_structure`.

Do not make this the default ingest path until eval proves value.

## Cache strategy

Current CLAP cache stores one vector per track content hash. Section vectors need
their own key namespace.

Recommended key bytes:

```text
sha256(file_bytes)
|| backend_tag
|| SECTION_EMBED_STRATEGY_VERSION
|| section_start_s_rounded_ms
|| section_end_s_rounded_ms
|| role
|| source
```

Start with:

```text
SECTION_EMBED_STRATEGY_VERSION = "v1-clap-section-anlz-aware"
```

Why include role/source?

- Same audio window can be generated by different structural sources.
- A DJ cue and ANLZ phrase at the same time should not silently collide if their
  role/confidence differs.
- Cache rows are cheap; correctness is more important than maximal reuse.

## Retrieval patterns

### Section search

```python
search_sections(query, role_filter={"intro", "groove"}, k=20)
```

Used for:

- finding candidate mix-in sections;
- finding sections similar to current section;
- generating smart cue review sets.

### Transition slate input

The transition engine should not search tracks directly. It should receive:

- current section record;
- target role filters from INTEL-07 grammar;
- top section search results;
- track-level features for key/BPM/energy refinement.

### Prep set construction

The set builder can keep track-level discovery first, then use section search to
score transitions inside the candidate pool:

```text
track vibe search -> candidate pool -> section pairs -> transition slate
```

This avoids the "section search returns a perfect intro from a totally wrong
track" failure mode.

### Live pill

Live mode should search only when the current/next section changes or the loaded
track changes. Do not run section search at 10 Hz.

Suggested cache key:

```text
(track_id, section_id, pool_hash, taste_hash, grammar_profile)
```

## Metadata quality gates

Add an audit script:

```text
scripts/eval/intel_section_index_audit.py
```

Metrics:

- tracks indexed;
- sections indexed;
- average sections per track;
- role distribution;
- source distribution;
- ANLZ coverage;
- fallback-section rate;
- section duration min/median/max;
- vectors missing metadata;
- metadata missing vectors;
- duplicate section IDs;
- self-search sanity: a section should retrieve nearby sections from related
  tracks more often than random.

Fail gates for v1:

- 0 duplicate section IDs;
- 0 vector/meta mismatches;
- 0 vectors with non-512 dimension;
- 0 non-float32 vectors;
- fallback-section rate below an agreed threshold for the target library;
- at least 80% of local tracks have more than one section when ANLZ exists.

## Test plan

### Store tests

- `test_section_numpy_add_load_search`
- `test_section_sqlite_add_load_search`
- `test_section_store_parity_matches_numpy`
- `test_section_store_delete_track_removes_meta_and_vectors`
- `test_section_store_snapshot_hash_changes_on_add_delete`
- `test_section_store_rejects_vector_meta_mismatch`
- `test_section_search_excludes_current_track`
- `test_section_search_role_filter`

### Ingest tests

- `test_sections_for_track_prefers_dj_cues`
- `test_sections_for_track_uses_anlz_when_no_dj_cues`
- `test_sections_for_track_falls_back_to_auto`
- `test_sections_for_track_whole_track_fallback`
- `test_section_embedding_splits_long_section`
- `test_section_embedding_one_bad_subwindow_nonfatal`
- `test_section_embedding_all_subwindows_drop_section`
- `test_section_cache_key_changes_with_window`
- `test_section_ingest_report_counts_failures`

### Migration safety tests

- existing `tests/library/test_store.py` unchanged;
- existing `tests/library/test_store_parity.py` unchanged;
- existing `tests/library/test_ingest.py` unchanged;
- importing `section_store.py` does not import torch, LiveKit, Tauri, or model
  clients;
- track-level search results are byte-identical before and after adding the
  section package.

## Migration strategy

1. Land section types and extraction tests.
2. Land `SectionStore` with numpy backend first.
3. Land sqlite backend and parity tests.
4. Land section ingest behind an explicit CLI or flag.
5. Run audit on Kaan's library and store the audit report in `.planning/eval/`
   or `eval/`.
6. Only then wire `search_sections` into `LibraryToolset`.
7. Only after that wire transition slate and context compiler.

Do not mix this with codebase cleanup. It is a distinct data-model migration.

## Risks

### Row explosion

A 1,000-track library with 20 sections per track becomes 20,000 rows. That is
fine for load-all cosine in v1, but live search should cache slates and avoid
recomputing on every tick.

Mitigation:

- cap sections per track for embedding at first, e.g. 24;
- keep all metadata but embed only operationally useful sections;
- use overfetch + filters, then benchmark.

### Section vectors are too short

Very short phrase windows may not produce stable CLAP vectors.

Mitigation:

- enforce minimum 8s for embedding windows;
- expand a short section to phrase-neighbor context when safe;
- store original section boundaries separately from embedding window boundaries.

### Embedding model lacks temporal semantics

CLAP can identify sonic similarity, not "this is the rising part of a build" by
itself.

Mitigation:

- role comes from ANLZ/ontology, not CLAP;
- vector similarity is only one component in transition scoring;
- evaluate T-CLAP/MERT/MuQ later through INTEL-03 gates.

### Store parity drift

Adding new backend logic could break the hard-won Mac/Win parity contract.

Mitigation:

- copy the storage-only pattern;
- keep `_cosine.cosine_topk()` as the ranking chokepoint;
- add section parity fixtures before product wiring.

## Recommendation

Build the section index as a sibling subsystem, not a replacement:

- keep `LibraryStore` track-level and stable;
- add `SectionStore` as the new retrieval surface;
- share vector math;
- separate metadata from vector storage;
- gate all wiring behind audits and parity tests;
- avoid live integration until prep search proves value.

This keeps the current app safe while giving the intelligence engine the data
shape it actually needs: searchable musical moments, not only searchable tracks.
