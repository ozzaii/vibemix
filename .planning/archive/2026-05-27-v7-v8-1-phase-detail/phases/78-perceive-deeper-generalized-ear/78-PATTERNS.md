# Phase 78: PERCEIVE — Deeper, Generalized Ear - Pattern Map

**Mapped:** 2026-05-26
**Files analyzed:** 7 (3 src modified, 1 src new, 3 test new)
**Analogs found:** 7 / 7 (every file has a strong in-repo analog — this phase is ~90% wiring of existing primitives)

All line anchors below were re-verified against live source this session (not trusted from RESEARCH.md alone).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/vibemix/state/music_state.py` (MOD) | model (dataclass) | transform | `detected_genre`/`deck_state` ADDITIVE field block (music_state.py:47-69) | exact (same file, same idiom) |
| `src/vibemix/state/refresh.py` (MOD) | service (single-writer loop) | event-driven / batch | genre write batch (refresh.py:339-352) + deck-snapshot copy-in (refresh.py:472-501) | exact |
| `src/vibemix/state/coach.py` (MOD) | service (prompt render) | transform | `genre=` gate (coach.py:334-335) + decks[…]/recent_moves gated render (coach.py:311-366) | exact |
| `src/vibemix/state/deltas.py` (NEW, optional) | utility (pure helpers) | transform | `state/genre/genre_autodetect.py` pure-scoring module | role-match |
| `src/vibemix/library/genre_prototypes.py` (NEW) | service (embedding lookup) | request-response / batch | `library/grounding.py` (embed→center→cosine + `Grounding` holder) + `library/store.py::search_centered` | exact (sibling) |
| `tests/state/test_coach_perceive.py` (NEW) | test | — | `tests/state/test_coach.py:253-296` (genre golden) | exact |
| `tests/state/test_refresh_perceive.py` (NEW) | test | — | `tests/state/test_refresh.py` / `test_refresh_deck.py` | role-match |
| `tests/library/test_genre_prototypes.py` (NEW) | test | — | `tests/library/test_centering.py` (synthetic corpus + tmp_path monkeypatch) | exact |

## Pattern Assignments

### `src/vibemix/state/music_state.py` (model, ADDITIVE fields) — PERCEIVE-01/02

**Analog:** the existing additive-field convention in the SAME file.

**Field-block idiom to copy** (music_state.py:47-69) — the `detected_genre`/`deck_state` block is the exact precedent for "add a new SINGLE-WRITER field with a falsy default + a comment asserting golden-equivalence":
```python
# Phase 52 (GENRE-01) — ... SINGLE-WRITER (_tick_once only) ...
# Additive defaults preserve golden-equivalence: no behavior changes until
# _tick_once writes them. Anti-slop is enforced at the SOURCE ...
detected_genre: str = "unknown"
genre_confidence: float = 0.0
```

**New fields to add (mirror this block, falsy defaults — cold-path byte-identity):**
- PERCEIVE-01: `prev_perceive: dict = field(default_factory=dict)` — prior-tick scalar snapshot, default `{}`.
- PERCEIVE-02: `trajectory_narrative: str = ""` — composed narrative, default `""`.

**Bounded-field precedent already present** (read-only inputs to PERCEIVE-02 — do NOT add new buffers):
- `phase_history: list` capped at 6 (music_state.py:127) — phrase scale.
- `recent_moves: list` 12s window (music_state.py:123) — moves scale.
- `long_arc: list` (~120s, 10s hop, music_state.py:126) + `buildup_score: float` (music_state.py:102) — energy-arc scale.
- `time_in_phase` property (music_state.py:150-152), `phase`/`phase_started_at` (music_state.py:38-39).

---

### `src/vibemix/state/refresh.py` (single-writer loop) — PERCEIVE-01/02/03

**Analog:** the `_tick_once` lock batch — the ONLY writer of `MusicState` (invariant #1).

**The lock batch boundary** (refresh.py:306 `with state._lock:`): every new write MUST live inside this block. Verified the genre write at 339-352, phase_history append at 408-413, recent_moves at 504, long_arc at 508.

**Genre write to reconcile/feed (PERCEIVE-03)** — keep this DSP path, feed the embedding result alongside (refresh.py:339-352):
```python
raw_genre, raw_genre_conf = score_genre(bpm_cache, {...band shares...}, smoothed_crest, _cached_profiles())
committed_genre = apply_genre_hysteresis(raw_genre, genre_hysteresis)
state.detected_genre = committed_genre
state.genre_confidence = round(raw_genre_conf, 2)
```
PERCEIVE-03 reconciles `(emb_genre, emb_conf)` (from the off-loop holder) with `(raw_genre, raw_genre_conf)` here, then runs `apply_genre_hysteresis` on the committed label. Render gate at coach.py:334 (`>= 0.5`) is unchanged — so confidence scales MUST reconcile to that band (see Pitfall 4 in RESEARCH).

**Off-loop → single-writer holder pattern (PERCEIVE-03 anti-second-writer)** — copy the deck-snapshot copy-in idiom (refresh.py:472-501): an external producer writes its OWN holder; `_tick_once` reads `deck_source.snapshot()` and is the ONLY place `state.deck_state.decks` is assigned. The genre-prototype lookup mirrors this — it runs off-loop on TRACK_CHANGE, stores its result in a thread-safe holder, and `_tick_once` READS the holder and writes `state.detected_genre`. NEVER write `state.detected_genre` from the lookup thread.
```python
# refresh.py:472-481 — the copy-in idiom to mirror for the genre holder read
if deck_source is not None:
    deck_snap = deck_source.snapshot()       # read external holder
    ...
    state.deck_state.decks = deck_snap       # single-writer assignment (only here)
    state.deck_state.updated_at = now
```

**PERCEIVE-01 prev-snapshot capture** — write LAST inside the lock batch, after all this-tick writes (so the NEXT tick reads a consistent prior). Place after the existing writes, before lock release. Default `{}` means the first tick has no prior → render abstains.

**PERCEIVE-02 trajectory compose** — read the already-bounded fields (`phase_history`, `buildup_score`, `recent_moves`) inside the lock and assign `state.trajectory_narrative`. No new accumulation; recomputed each tick.

---

### `src/vibemix/state/coach.py` (prompt render) — PERCEIVE-01/02/03

**Analog:** `evidence_line` (coach.py:256-432) — all prompt grammar lives here; every block is `if <field>:`-gated for cold-path byte-identity.

**The genre gate (PERCEIVE-03 render — UNCHANGED, must stay green)** (coach.py:334-335):
```python
if state.detected_genre != "unknown" and state.genre_confidence >= 0.5:
    e.append(f"genre={state.detected_genre}")
```
PERCEIVE-03 changes only the SOURCE of these values in refresh.py — this render line and its goldens (`test_coach.py:260-296`) stay byte-identical.

**Gated-render idiom to copy for PERCEIVE-01/02** — the decks[…] / recent_moves[8s] branches (coach.py:311-353) are the exact precedent: a falsy field appends ZERO bytes:
```python
recent_8s = [(age, label) for age, label in state.recent_moves if age <= 8.0]
if recent_8s:                                  # cold → [] → omit (byte-identical)
    ...
    e.append(f"recent_moves[8s]: {mv}")
```

**PERCEIVE-02 trajectory render** — mirror this exactly:
```python
if state.trajectory_narrative:                 # cold → "" → omit
    e.append(f"trajectory[{state.trajectory_narrative}]")
```

**PERCEIVE-01 delta render** — prefer Δ-phrasing over the bare `hearing[rms=…]` scalar (coach.py:284-289) when a prior exists AND change clears the floor; abstain (omit) below floor. Calibration is a pure helper (place in `deltas.py` or as a `@staticmethod` here). Anti-slop contract: low confidence OMITS, never asserts.

---

### `src/vibemix/state/deltas.py` (NEW, optional — pure helpers) — PERCEIVE-01

**Analog:** `state/genre/genre_autodetect.py` — a pure, fully-unit-testable scoring module with NO state write (`score_genre` returns a tuple; the caller in `refresh.py` does the write).

**Pattern to copy:** module-level load-bearing constants with `_`-prefix + `UPPER_SNAKE` public floors, pure functions returning values, `from __future__ import annotations`. `render_delta(label, cur, prev, *, floor, fmt)` returns a phrasing string or `None` to abstain (None on cold path = `prev is None`). Keep calibration a deterministic monotone map (logistic over normalized delta, or bucketed high/med/low) — NO library, NO training.

---

### `src/vibemix/library/genre_prototypes.py` (NEW) — PERCEIVE-03

**Analog (primary):** `library/grounding.py` — the embed→center→cosine-top1-vs-library precedent + the `Grounding` thread-safe holder. **Analog (math):** `library/store.py::search_centered` (store.py:63-90) — the canonical center-BOTH-with-SAME-centroid sequence.

**Imports pattern (library-tier convention):**
```python
from __future__ import annotations
import numpy as np
from vibemix.library._cosine import EMBEDDING_DIM, cosine_topk, l2_normalize
from vibemix.library.centering import center_and_renorm, load_or_compute_centroid
from vibemix.library.store import open_store
from vibemix.library.rekordbox import RekordboxLibrary
```

**Center-both-with-SAME-centroid (copy from store.py:82-90 — do NOT hand-roll):**
```python
ids, vectors = self._backend.load_all()
centroid = load_or_compute_centroid(vectors, self._backend.snapshot_hash())
if centroid is None:                            # N<2 degenerate guard → fall back
    return cosine_topk(query_vector, vectors, ids, k)
q_centered = center_and_renorm(query_vector, centroid)   # SAME centroid for query
v_centered = center_and_renorm(vectors, centroid)        # SAME centroid for candidates
return cosine_topk(q_centered, v_centered, ids, k)
```
For prototypes: center all vectors with this centroid, group rows by label, `l2_normalize(rows.mean(axis=0))` per label = prototype. At classify time, center the playing track's cached embedding with the SAME centroid, `cosine_topk` vs prototypes. STORE the centroid (or its snapshot_hash) alongside prototypes so live classify uses the matching one (Pitfall 2: centroid divergence = garbage cosine).

**Genre proxy = parent folder (copy lookup from rekordbox.py):**
```python
lib = RekordboxLibrary(); lib.try_load_cache()
te = lib.lookup_by_id(track_id)                  # rekordbox.py:233 → TrackEntry | None
label = Path(te.filepath).parent.name if te else "unknown"   # TrackEntry.filepath
```

**Thread-safe holder + late-write discard (copy from grounding.py:169-265 `Grounding`):** the off-loop worker stores its result under a `threading.Lock`; a per-dispatch generation token (grounding.py:199, bumped in `clear()` at 263) discards a stale write if the dispatch was superseded. `refresh._tick_once` reads `get_latest(...)` — never the lookup thread writing `state.*`.

**Anti-slop floor + margin (the `_decide` idiom, grounding.py:74-79):** classify returns `("unknown", conf)` below a cosine floor OR within a tie-margin — mirror `score_genre`'s unknown fallback (genre_autodetect.py:153-159). Reconcile confidence into the `>= 0.5` render band.

**Cache sidecar (mirror `centering.CENTROID_PATH`):** persist `~/.cache/vibemix/genre_prototypes.npy` + `.meta.json` snapshot-hash-keyed, atomic tmp→replace, best-effort (centering.py:108-143). Auto-rebuilds when `library.db` changes. Lazy-build on first TRACK_CHANGE (RESEARCH Open Q2 recommendation).

---

### Test files (Wave 0)

**`tests/library/test_genre_prototypes.py`** — analog `tests/library/test_centering.py`:
- Copy `_anisotropic_corpus(n, seed)` synthetic-corpus builder (test_centering.py:30-46) — N L2-normalized vectors sharing a common direction → exercises the centering separation.
- **MANDATORY** monkeypatch ALL cache paths to `tmp_path`: `RekordboxLibrary.CACHE_PATH`, `centering.CENTROID_PATH` + `CENTROID_META_PATH`, and the new `genre_prototypes` path (CLAUDE.md gotcha + RESEARCH Pitfall 5 — an un-monkeypatched test clobbers the real `library.pkl`).
- Assert: per-folder centered-mean prototype build; classify floor + tie-margin abstain → `("unknown", …)`.

**`tests/state/test_coach_perceive.py`** — analog `tests/state/test_coach.py:260-296`:
- Copy the `MusicState(audible=True, …)` construction + `AICoach.evidence_line(state)` + `assert "x" in/not in out` idiom.
- Assert: Δ-phrasing rendered when prior present + change above floor; cold state (default `MusicState()`) byte-identical to v8.0 (the genre/decks goldens already pin this — keep them GREEN); empty `trajectory_narrative` → omitted.

**`tests/state/test_refresh_perceive.py`** — analog `tests/state/test_refresh.py` / `test_refresh_deck.py`:
- Assert: `prev_perceive` captured last inside the lock (single-writer); trajectory composed + bounded; genre fed ONLY via `_tick_once`; reconciliation agree/disagree → one coherent label.

## Shared Patterns

### Single-writer discipline (invariant #1)
**Source:** `state/refresh.py:306` (`with state._lock:`) + the deck holder copy-in at refresh.py:472-501.
**Apply to:** ALL three requirements. Every `state.* =` write lives inside `_tick_once`'s lock batch. Off-loop work (genre lookup) returns a value into a holder; `_tick_once` reads it. NEVER a second writer.

### Query-side mean-centering (the anisotropy fix — load-bearing)
**Source:** `library/centering.py` (`load_or_compute_centroid`, `center_and_renorm`, `compute_centroid`) + `library/store.py::search_centered`.
**Apply to:** PERCEIVE-03 ONLY. Reuse VERBATIM — do not duplicate centroid/normalize math. BOTH prototype-build and live-classify use the SAME corpus centroid keyed on `store.snapshot_hash()`. Persisted vectors are NEVER mutated (centering is query-side; centering.py:12-16).

### Cosine top-K chokepoint (P55 Mac/Win parity)
**Source:** `library/_cosine.py::cosine_topk` + `l2_normalize`, `EMBEDDING_DIM=1536`.
**Apply to:** PERCEIVE-03 nearest-prototype ranking. float32-asserted, deterministic tie-break (DESC sim, ASC id). Do NOT argsort by hand.

### Anti-slop confidence floor → abstain (invariant #2/#3)
**Source:** `state/genre/genre_autodetect.py` (`GENRE_CONFIDENCE_MIN=0.55`, `GENRE_TIE_MARGIN=0.08`, unknown fallback at :153-159, `apply_genre_hysteresis` at :176-203) + `grounding.py::_decide` (:74-79).
**Apply to:** ALL three. Below floor → OMIT the fact (PERCEIVE-01/02) or `("unknown", conf)` (PERCEIVE-03). Never assert a low-confidence fact. Reconcile genre through `apply_genre_hysteresis` for ONE coherent label per tick.

### Cold-path byte-identity (golden-test safety net)
**Source:** every gated render branch in `coach.py` (decks[…] at :311, genre= at :334, recall at :424) + falsy-default field convention in `music_state.py`.
**Apply to:** ALL three. Every new field defaults falsy; every new render branch is `if <field>:`-gated; `render_delta` returns `None` when `prev is None`. A cold `MusicState()` must produce v8.0-identical prompt bytes — enforced by `tests/state/test_coach.py`.

### Snapshot-hash-keyed cache sidecar
**Source:** `centering.py::load_or_compute_centroid` (:108-143) — `.npy` + `.meta.json`, atomic tmp→replace, best-effort, paths resolved at call-time so tests can monkeypatch.
**Apply to:** PERCEIVE-03 `genre_prototypes.npy`. Auto-heals on `library.db` change.

## No Analog Found

None. Every file has a strong in-repo analog. The only genuinely new code is ~2 `MusicState` fields, ~2 pure render helpers, and one `library/genre_prototypes.py` that *composes* existing primitives.

## Metadata

**Analog search scope:** `src/vibemix/state/`, `src/vibemix/library/`, `tests/state/`, `tests/library/`
**Files scanned (read this session):** coach.py, grounding.py, centering.py, refresh.py, genre_autodetect.py, music_state.py, _cosine.py, store.py, rekordbox.py, test_coach.py, test_centering.py
**All line anchors re-verified against live source:** yes (coach.py:334-335 ✓, refresh.py:306/339-352/408-413/472-501/504/508 ✓, music_state.py:47-69/102/123-127/150-152 ✓, centering.py:90-143 ✓, store.py:63-90 ✓, grounding.py:169-265 ✓, genre_autodetect.py:50-203 ✓, _cosine.py:cosine_topk/EMBEDDING_DIM=1536 ✓, rekordbox.py:lookup_by_id/TrackEntry.filepath ✓, test_coach.py:253-296 ✓)
**Pattern extraction date:** 2026-05-26
