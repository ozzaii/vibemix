# Phase 89 — Plan Check (pre-execution)

**Verdict: PASS-WITH-CONCERNS**
**Checked:** 2026-05-26 · 3 plans (89-01, 89-02, 89-03) · goal-backward + scope-fence + seam-truth audit
**Baseline:** green under the project interpreter (`.venv` 3.12 → `tests/library/test_rekordbox.py` 10 passed). All seams the plans claim were verified to exist with matching signatures.

---

## Goal-backward — does the trio deliver the MVP walking skeleton?

Goal: detect collection.xml → parse clean metadata → cue-anchored excerpts → clap_engine embed → sqlite-vec store + a `library ingest` CLI.

| Goal truth | Covered by | Status |
|---|---|---|
| Auto-detect collection.xml (no path arg) | 89-01 T2 `RekordboxSource.detect()` + default_paths | COVERED |
| Parse clean metadata (genre/label/rating/cues/Camelot/beatgrid) | 89-02 T1/T2 enriched `_track_to_entry` + `_mark_to_cue` | COVERED |
| Cue-anchored ≤80s excerpts (dj-first, auto fallback, whole-track fallback) | 89-03 T1 `excerpt.py` + T2 ingest rewire | COVERED |
| On-device clap_engine embed (512-dim, no upload) | 89-01 T2 + 89-03 T2 `embed_audio_file`/`embed_audio_bytes` | COVERED |
| sqlite-vec store + content-hash cache, resumable + honest | 89-01 T2 mirrors `folder_ingest`; namespaced strategy version | COVERED |
| `library ingest` CLI (auto-detect or explicit path) | 89-01 T2 `_cmd_library_ingest` + subparser | COVERED |
| `search`/`similar` resolve ingested titles (library.pkl) | 89-01 via `_write_library_cache` reuse | COVERED |

No gap between "tracks ready + searchable" and what the plans build. The end-to-end vertical is fully covered. The wave-1 whole-track embed is an honest interim (Plan 01 objective states so); Plan 03 replaces it with cue-anchored windows — that is a deliberate refinement, **not** a scope reduction of any LOCKED decision.

## Scope-fence compliance (CONTEXT.md `<scope_fence>`)

| READ-ONLY / forbidden | Touched by any plan? |
|---|---|
| `library/clap_engine.py`, `docs/clap-engine.md` | NO — consumed via constructor + `embed_audio_*` only |
| `library/cue_types.py`, `library/cue_detect.py` | NO — imported as types/fn only (89-03) |
| `library/discovery.py / energy.py / sequencer.py / export_rekordbox.py` | NO |
| `EMBEDDING_DIM` flip (1536→512) | NO — 89-01 T2 explicitly "store whatever clap_engine returns; do NOT flip"; dim-mismatch on a non-empty store raises an actionable RuntimeError naming the CLAP-wiring session |
| `.planning/codebase/orphans.csv` | NO |
| SQLCipher `master.db` / `Rekordbox6Database` | NO — grep-gate acceptance criteria in 89-01 T2 + 89-02 T2 keep it dormant |

`files_modified` across the three plans confirms it: only NEW files (`sources/`, `ingest.py`, `excerpt.py`) + extends `rekordbox.py` + appends to `__main__.py`. **Zero scope-fence violations.**

## Wave / dependency correctness

- 89-01 `depends_on: []` (wave 1) · 89-02 `depends_on: []` (wave 1) · 89-03 `depends_on: [89-01, 89-02]` (wave 2). Graph is acyclic, no forward refs.
- **Wave-1 file ownership is disjoint:**
  - 89-01 owns: `sources/*`, `ingest.py`, `__main__.py`, `tests/library/test_ingest.py`, `test_sources_rekordbox.py`
  - 89-02 owns: `rekordbox.py`, `tests/library/test_rekordbox.py`, `fixtures/synthetic_collection.xml`
  - No overlap. 89-01 *reads* `rekordbox.py` (consumes `RekordboxLibrary`) but does not write it. CORRECT.
- 89-03 rewires `ingest.py` + `tests/library/test_ingest.py` (both 89-01-owned) in wave 2 — correctly serialized after 89-01. CORRECT.

## Anti-shallow / offline-honest-green

- Every task has `read_first` (concrete file+line pointers) and concrete `acceptance_criteria` with grep/exit-code checks. Good.
- FakeClapEmbedder (deterministic seeded 512-d, L2-normed) at every test module top — no torch / no network / no key. Good.
- `RekordboxLibrary.CACHE_PATH` tmp-monkeypatch (`isolated_cache`) reused — the real `library.pkl` gotcha is honored. Good.
- Honest-failure tests (per-file/per-window broad-except → skip, never a faked vector) match Invariant #3. Good.
- TDD red→green discipline (strict-xfail in T1, flipped in T2) is sound.

## Import-safety (torch/laion_clap absent in CI)

- `clap_engine` / `cue_detect` lazy-import their heavy deps (verified at source). The new modules mirror that contract (top level = stdlib + numpy + light types).
- `import vibemix.library.<X>` does NOT pull torch (verified live). The plans' `torch`/`laion_clap` absence assertions are satisfiable.

---

## Findings

### WARNING 1 — Plan 03 import-safety check is unsatisfiable as written
`89-03` Task 1 verify + acceptance:
`python3 -c "import sys, vibemix.library.excerpt; assert 'torch' not in sys.modules and 'google.genai' not in sys.modules"`

`vibemix/library/__init__.py` **eagerly** imports `agent → embed → model_router → google.genai`. Therefore importing **any** `vibemix.library` submodule (including `excerpt`) runs `__init__` first and `google.genai` is ALWAYS in `sys.modules`. Verified live: the assertion FAILS today. The `torch`-absence half is correct and is the part that actually matters for CI (torch/laion_clap are the deps absent in CI; `google.genai` IS installed). 
**Fix:** drop the `google.genai` clause from the 89-03 T1 check — assert only `'torch' not in sys.modules` (and optionally `'laion_clap' not in sys.modules`), matching 89-01/89-02's correctly-scoped checks. Executor must not "fix" this by lazy-loading genai in `library/__init__` (that touches shared surface out of scope).

### WARNING 2 — SCHEMA_VERSION bump (89-02) couples folder_ingest cache; sequence dependency vs declared parallelism
`89-02` T2 bumps `RekordboxLibrary.SCHEMA_VERSION` 1→2 because `TrackEntry` gains fields. `folder_ingest._write_library_cache` (which `89-01` reuses for `library.pkl`) pickles `TrackEntry` under `RekordboxLibrary.SCHEMA_VERSION`. The two plans run in the **same wave (1)** with no declared ordering. If 89-01 lands first, its `ingest.py` produces a v1 cache with the OLD TrackEntry shape; after 89-02 lands (v2 + new fields), `try_load_cache` correctly invalidates the stale v1 pickle (the `blob.version != SCHEMA_VERSION` guard) — so it is self-healing, not a corruption risk. But a fresh-ingest test written under 89-01 that asserts a specific cached-vector round-trip could transiently see a shape change if both land in one merge.
**Disposition:** non-blocking — the version guard makes it honest-by-design (stale cache misses → cold re-parse). No fix required; flagged so the executor merges 89-01 and 89-02 together (they're one wave) and re-runs the full suite post-merge rather than asserting cross-plan cache state mid-wave.

### WARNING 3 — `_mark_to_cue` Type today is a string default ("cue"), 89-02 assumes int-mapping
Current `_mark_to_cue` does `str(_safe_get(mark, "Type", default="cue"))` — pyrekordbox may surface `Type` as a string already, OR an int per the research table. 89-02 T2's action correctly says "handle both (int-coerce in try/except, then map; if already a known label string pass through)". This is the right defensive posture, but the fixture (89-02 T1) drives it with string ints (`Type="3"`, `Type="4"`) — the executor must confirm against a REAL pyrekordbox 0.4.4 element that `Type` arrives as the expected type, since the synthetic fixture can't prove the live duck-typed shape. The existing `test_load_xml_round_trip` covers real-element access; 89-02 should extend that same real-element path, not only the synthetic fixture.
**Disposition:** non-blocking — the action already hedges both representations. Flagged so the executor doesn't ship a synthetic-only proof of the Type mapping.

### INFO — `IngestReport` reuse is exact-shape compatible
89-01 reuses `folder_ingest.IngestReport` (fields: total/embedded/skipped_cached/failed/cost_estimate_eur/failures/embed_strategy) — verified present with `.as_dict()`. Good reuse, no new report type needed. The `embed_strategy` field can carry the cue-anchored label in 89-03 for free.

---

## Scope sanity
- 89-01: 2 tasks / 7 files · 89-02: 2 tasks / 3 files · 89-03: 2 tasks / 4 files. All within budget. Clean TDD-paired tasks.

## Bottom line
The three plans **WILL achieve the phase goal** — full Rekordbox detect→parse→excerpt→embed→store vertical with a CLI, end-to-end, scope-fence-clean, dependency-correct, offline-honest-green. The three warnings are quality nits; only WARNING 1 is a guaranteed acceptance-check failure and must be corrected (delete the `google.genai` clause from 89-03 T1) before/at execution. None block the goal.

**PASS-WITH-CONCERNS** — fix WARNING 1 (one-clause deletion in 89-03), heed WARNING 2/3 at merge time.
