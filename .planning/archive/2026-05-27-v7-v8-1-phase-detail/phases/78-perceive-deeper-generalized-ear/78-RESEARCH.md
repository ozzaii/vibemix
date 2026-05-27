# Phase 78: PERCEIVE — Deeper, Generalized Ear - Research

**Researched:** 2026-05-26
**Domain:** Python in-process state enrichment (numpy vector math, single-writer dataclass, prompt rendering) — NO new external deps
**Confidence:** HIGH (every claim verified against live code this session; no library version risk because nothing new is installed)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**PERCEIVE-01 — deltas + calibrated confidence**
- The evidence packet is extended **additively**: each surfaced fact gains a delta-from-prior and a calibrated confidence. Raw scalars are NOT removed (other consumers may read them); the *prompt rendering* prefers the delta phrasing.
- Display is **confidence-gated**: facts below a floor are omitted/abstained rather than asserted (anti-slop, invariant #2/#3 spirit).
- Delta computation reads the prior `MusicState` snapshot; the single-writer refresh loop owns the write (invariant #1). No second writer.

**PERCEIVE-02 — multi-scale trajectory**
- A rolling trajectory is maintained in `MusicState` across scales: bar → phrase → track → set, plus a short **recent-moves** list (MIDI/EQ/fader/blend events already detected).
- Surfaced to the prompt as a **compact narrative string** (e.g., "3rd phrase of an energy build; last move: bass-swap 20s ago"), not a raw array dump.
- Written ONLY by the refresh loop (invariant #1). Bounded ring/window — no unbounded growth.

**PERCEIVE-03 — mean-centered nearest-prototype genre**
- Build a **genre-prototype table** from the existing cached 1536-dim library embeddings (mean of each genre cluster).
- `detected_genre` = nearest prototype by **mean-centered cosine** (query-side centering only — the anisotropy fix; persisted vectors untouched). €0 (cached vectors, no new API calls).
- The lookup **feeds the single-writer refresh loop's `detected_genre`/`genre_confidence`** (already fields in `music_state.py:55-56`) — it does NOT introduce a second writer. Confidence-floored.
- This augments (not replaces wholesale) the existing genre-chain detector path; reconcile so there's one coherent `detected_genre` source per refresh tick.

### Claude's Discretion
- Exact delta/confidence struct shape, calibration function (e.g., logistic over normalized distance), trajectory window sizes, prototype-table storage location (cache under `~/.cache/vibemix/`) — planner's call, smallest additive diff, follow `state/` + `library/` conventions.
- Whether prototype table is precomputed once + cached vs lazy-built on first genre query.

### Deferred Ideas (OUT OF SCOPE)
- The three lenses (hype/critique/tutor) interpreting this deepened evidence → Phase 79.
- Gemini hearing the audio as a secondary ear → Phase 80.
- Proving the depth measurably (bench) + Kaan's-ear verdict → Phase 81.
- Any NEW DSP detector or MIR lib — permanently out (license wall + scope).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PERCEIVE-01 | Prompt evidence carries deltas + calibrated confidence per fact (not raw absolute scalars), so Gemini reads changes and can abstain. | `MusicState` already carries every scalar needed for deltas (`rms`, `bands`, `onset_density`, `bpm`, `crest_factor`, `buildup_score`, `energy_curve`, `long_arc`). A prior-snapshot field + a pure delta-render helper in `coach.py` is the whole job. See §Architecture Pattern 1. |
| PERCEIVE-02 | The prompt carries a multi-scale trajectory (phrase / energy-arc / recent-moves) so Gemini reasons over time, not a single snapshot. | The raw multi-scale material already lives in `MusicState`: `phase`/`phase_started_at`/`phase_history` (phrase scale), `energy_curve`/`long_arc`/`buildup_score` (energy-arc), `recent_moves` (DJ moves). Job = compose them into ONE bounded narrative string, written in `refresh.py`, rendered in `coach.py`. See §Architecture Pattern 2. |
| PERCEIVE-03 | `detected_genre` driven by a mean-centered nearest-prototype lookup over cached embeddings (86.5%-validated, €0). | All plumbing exists: `library/centering.py` (`load_or_compute_centroid` + `center_and_renorm`), `store.search_centered`, `_cosine.cosine_topk`, `library.db` (399 cached 1536-d vectors). Genre proxy = parent folder of `TrackEntry.filepath` in `library.pkl`. Reconcile with existing `score_genre` DSP path. See §Architecture Pattern 3. |
</phase_requirements>

## Summary

Phase 78 is **pure in-process enrichment** — zero new packages, zero new processes, zero new ws ports, zero new AI calls. Every input it needs already exists in the codebase; the work is composing what's there into change-shaped evidence and wiring a genre-prototype lookup over already-cached vectors. This is the lowest-supply-chain-risk phase class possible: nothing is installed, so the package-legitimacy and version-staleness threat surfaces are empty.

The three requirements decompose cleanly along the existing single-writer architecture:

- **PERCEIVE-01 (deltas + confidence):** `MusicState` already holds every absolute scalar. Add ONE prior-snapshot field (written last in `refresh.py`'s `_tick_once`, after all this-tick writes), then add a pure delta-render branch in `coach.evidence_line` that prefers `Δ`-phrasing when a prior exists and is confident, and abstains (omits the fact) below a floor. The calibration function is a small pure helper — no library.
- **PERCEIVE-02 (trajectory):** All three scales already exist as separate `MusicState` fields (`phase_history` = phrase, `long_arc`/`buildup_score` = energy-arc, `recent_moves` = moves). Compose them into ONE bounded narrative string in `refresh.py` (single-writer) and render it in `coach.evidence_line` as a compact `trajectory[...]` field. No new buffers — read existing fields.
- **PERCEIVE-03 (genre):** The mean-centering machinery is battle-tested for library ranking (`centering.py`, `store.search_centered`). Build a `(label → centered-mean-vector)` prototype table from the 399 cached vectors (genre proxy = parent folder of `TrackEntry.filepath`), persist as a tiny `.npy` sidecar under `~/.cache/vibemix/`, and at TRACK_CHANGE take the playing track's already-stored embedding (€0 for library tracks), center it with the SAME corpus centroid, cosine-rank to the prototypes, apply a confidence floor. The result FEEDS `refresh.py`'s existing `detected_genre`/`genre_confidence` write — reconciled with the DSP `score_genre` path so there is ONE coherent label per tick.

**Primary recommendation:** Implement all three as additive enrichments inside the existing single-writer (`refresh._tick_once`) → render (`coach.evidence_line`) seam. Reuse `library/centering.py` verbatim for PERCEIVE-03 (do NOT write a second centering implementation). Keep the cold path byte-identical: every new field defaults to a falsy/empty value and every new render branch is gated, so an un-warmed state produces v8.0-identical prompt bytes — enforced by the existing `test_coach.py` golden tests.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Compute deltas from prior snapshot | `state/refresh.py` (single writer) | — | Invariant #1: only the refresh loop may write `MusicState`. The prior snapshot is loop-local OR a `MusicState` field, but the *write* is here. |
| Calibrate per-fact confidence | `state/coach.py` (pure render helper) OR `state/` pure module | `state/refresh.py` | Calibration is a pure function over scalars; it can live as a render-side helper (no state write) since it's deterministic from the rendered fields. |
| Render delta/confidence phrasing | `state/coach.py` `evidence_line` | — | This is the prompt-boundary; all prompt grammar lives in `coach.py`. |
| Maintain multi-scale trajectory | `state/refresh.py` (single writer) | — | Invariant #1. Bounded, composed from existing fields. |
| Render trajectory narrative | `state/coach.py` `evidence_line` | — | Prompt grammar. |
| Build genre-prototype table | `library/` (new small module) | — | Prototypes are derived from `library.db` + `library.pkl` — pure library-tier concern (embeddings + folder labels). |
| Mean-center + cosine-rank genre | `library/centering.py` + `library/_cosine.py` (reused) | new prototype module | Reuse the existing anisotropy-fix chokepoint; do not duplicate centering math. |
| Write `detected_genre`/`genre_confidence` | `state/refresh.py` (single writer) | — | Invariant #1. The genre lookup *feeds* this write; it never writes `MusicState` itself. |
| Reconcile DSP-genre vs embedding-genre | `state/refresh.py` | `state/genre/` | One coherent label per tick — decided inside the single-writer batch. |

## Standard Stack

**No new packages.** This phase installs nothing. The entire stack is already present and pinned in `pyproject.toml` / `uv.lock`.

### Core (already installed — reused, not added)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `numpy` | already pinned | Centroid mean, L2-norm, cosine rank for genre prototypes | The project's sole vector-math lib (CLAUDE.md: "numpy for DSP/vector math, no torch"). `centering.py` + `_cosine.py` already use it. `[VERIFIED: src/vibemix/library/centering.py, _cosine.py]` |
| stdlib `dataclasses`, `collections.deque`, `threading`, `time` | stdlib | `MusicState` fields, bounded windows, single-writer lock | Existing idiom throughout `state/`. `[VERIFIED: src/vibemix/state/music_state.py, refresh.py]` |

### Supporting (already present in-repo — the reuse map)
| Module | Purpose | When to Use |
|--------|---------|-------------|
| `library/centering.py` | `load_or_compute_centroid`, `center_and_renorm`, `compute_centroid` — the query-side anisotropy fix | PERCEIVE-03 centering — reuse VERBATIM. `[VERIFIED: src/vibemix/library/centering.py]` |
| `library/_cosine.py` | `cosine_topk`, `l2_normalize`, `EMBEDDING_DIM=1536` | PERCEIVE-03 nearest-prototype ranking. `[VERIFIED]` |
| `library/store.py` | `open_store()`, `LibraryStore.load_all()` (via backend), `search_centered`, `snapshot_hash` | PERCEIVE-03 prototype build (load all vectors+ids once). `[VERIFIED]` |
| `library/rekordbox.py` | `RekordboxLibrary.try_load_cache()` → `tracks: dict[track_id, TrackEntry]`, `TrackEntry.filepath` | PERCEIVE-03 genre proxy: `track_id → filepath → parent folder = label`. `[VERIFIED: src/vibemix/library/rekordbox.py:85,93,112,233]` |
| `library/grounding.py` | `identify_playing` / `Grounding` — already embeds live audio + centers + cosine top-1 vs library | PERCEIVE-03 precedent for "embed playing track, rank vs library" — the genre lookup is a sibling that ranks vs *prototypes* instead of *tracks*. `[VERIFIED]` |
| `state/genre/genre_autodetect.py` | `score_genre`, `apply_genre_hysteresis`, `GenreHysteresis`, `GENRE_CONFIDENCE_MIN=0.55`, `GENRE_TIE_MARGIN=0.08`, `_HYSTERESIS_DWELL_TICKS=3` | PERCEIVE-03 reconciliation: the existing DSP genre path that the embedding genre augments. `[VERIFIED]` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Reusing `centering.py` | A fresh per-genre centering routine | REJECTED — duplicates a battle-tested chokepoint, risks centroid drift vs the ranking path. The research report explicitly says "we reuse it verbatim". |
| numpy k-means / prototype clustering | `sklearn.cluster.KMeans` | REJECTED — sklearn is NOT in the venv (research §2a: "no sklearn available"). The prototype = *centered mean of each folder-labelled cluster*, a one-line numpy `mean(axis=0)`. No clustering library needed. |
| In-corpus folder-mean prototypes | ~7 text-anchor embeds | Text anchors are the cheaper *production* variant (research §4 step 1) but require a live API call. Folder-mean prototypes are €0 and were the validated mechanism (86.5%). Planner's discretion (CONTEXT); folder-mean is the zero-cost honest-green default. |

**Installation:** none — `uv sync` already provides everything.

**Version verification:** N/A — no package is added. `numpy` version is whatever `uv.lock` pins; this phase does not constrain it.

## Package Legitimacy Audit

> This phase installs **NO external packages**. The legitimacy gate is vacuously satisfied — there is no supply-chain surface to audit.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| _(none added)_ | — | — | — | — | N/A | No new installs |

**Packages removed due to slopcheck [SLOP] verdict:** none (none proposed).
**Packages flagged as suspicious [SUS]:** none.

All modules referenced are first-party (`vibemix.*`) or already-pinned (`numpy`, stdlib). No `npm view` / `pip index` check is required because nothing is installed.

## Architecture Patterns

### System Architecture Diagram

```
                         ┌──────────────────────────────────────────────┐
   audio thread ─RMS/FFT─▶                                              │
   MIDI thread  ─moves──▶│   state/refresh.py :: _tick_once  (10Hz)      │
   track poll   ─title──▶│   ── THE SINGLE WRITER (invariant #1) ──       │
                         │                                                │
                         │  existing: rms, bands, bpm, crest, phase,      │
                         │            phase_history, energy_curve,        │
                         │            long_arc, recent_moves,             │
                         │            detected_genre/genre_confidence     │
                         │                                                │
                         │  +PERCEIVE-01: prev_snapshot field (written    │
                         │                LAST, after this-tick writes)   │
                         │  +PERCEIVE-02: trajectory_narrative str        │
                         │                (composed from existing fields) │
                         │  +PERCEIVE-03: detected_genre/conf FED by      │
                         │                genre-prototype lookup ───┐     │
                         └───────────────────────────────────────────┼────┘
                                          │ reads (read-only)         │
                                          ▼                           │
                         ┌──────────────────────────────────┐         │
                         │  state/coach.py :: evidence_line  │         │
                         │  ── render (anti-slop gated) ──    │         │
                         │  +Δ phrasing (prefer delta over    │         │
                         │     bare scalar; abstain<floor)    │         │
                         │  +trajectory[...] field            │         │
                         │  +genre= field (already wired      │         │
                         │     WIRE-04; now embedding-driven) │         │
                         └──────────────────┬─────────────────┘         │
                                            │ prompt string             │
                                            ▼                           │
                              ┌─────────────────────────┐               │
                              │  agent/dj_cohost.py      │               │
                              │  Gemini Flash reaction   │               │
                              └─────────────────────────┘               │
                                                                        │
   TRACK_CHANGE event (debounced, off-loop) ────────────────────────────┘
                         │
                         ▼
   ┌─────────────────────────────────────────────────────────────┐
   │  library/ genre-prototype lookup (NEW small module)          │
   │  build once: library.db (399×1536 cached vecs) +             │
   │              library.pkl (track_id→filepath→parent folder)   │
   │              → per-folder CENTERED mean = prototype           │
   │  persist:    ~/.cache/vibemix/genre_prototypes.npy + labels  │
   │  classify:   playing track's CACHED embedding → center w/     │
   │              SAME corpus centroid → cosine_topk vs prototypes  │
   │              → (label, conf) ; floor → "unknown"              │
   │  REUSES centering.py + _cosine.py — €0, no new embed call     │
   └─────────────────────────────────────────────────────────────┘
```

Trace the primary use case: audio/MIDI enters the single-writer loop → loop computes deltas vs the prior snapshot + composes the trajectory narrative + (on TRACK_CHANGE) consults the genre-prototype lookup → all written into `MusicState` under one lock → `coach.evidence_line` reads the snapshot and renders gated change-phrasing → Gemini reacts to *change*, not a static snapshot.

### Recommended Project Structure
```
src/vibemix/
├── state/
│   ├── music_state.py      # +prev_snapshot field, +trajectory_narrative field
│   ├── refresh.py          # +delta compute, +trajectory compose, +genre feed (single writer)
│   ├── coach.py            # +Δ render branch, +trajectory[] render, genre= already gated
│   └── deltas.py           # NEW (optional) — pure delta + calibration helpers (no state write)
└── library/
    └── genre_prototypes.py # NEW — build/persist/lookup genre-prototype table (reuses centering)
```

### Pattern 1: Prior-snapshot delta + calibrated confidence (PERCEIVE-01)
**What:** Keep a copy of the previous-tick scalar set; render `Δ` (signed change) instead of (or alongside) the bare value, and gate emission on a calibrated confidence.
**When to use:** Every scalar fact in `evidence_line` that has a meaningful rate-of-change (`rms`, band shares, `onset_density`, `bpm`, `crest_factor`).
**Single-writer rule:** The prior snapshot must be captured as the LAST step in `_tick_once` (copy the just-written values), so the NEXT tick's delta reads a consistent prior. Capture it inside the existing `with state._lock:` batch.

```python
# Source: composed from src/vibemix/state/refresh.py:306-353 (single-writer batch)
#         + src/vibemix/state/coach.py:284-296 (render gate idiom)
# refresh.py — LAST inside the lock batch, after all this-tick writes:
state.prev_perceive = {              # ADDITIVE field on MusicState, default {}
    "rms": state.rms,
    "sub": state.bands["sub"], "low": state.bands["low"],
    "mid": state.bands["mid"], "high": state.bands["high"],
    "onset_density": state.onset_density,
    "bpm": state.bpm,
    "crest": state.crest_factor,
}

# coach.py / deltas.py — pure render helper (no state write):
def render_delta(label: str, cur: float, prev: float | None,
                 *, floor: float, fmt: str = "+.0%") -> str | None:
    """Return 'label rose 18%' phrasing, or None to ABSTAIN below floor.
    prev is None on the first tick (cold path → return None → omit)."""
    if prev is None or prev == 0.0:
        return None                          # cold path: byte-identical
    rel = (cur - prev) / abs(prev)
    if abs(rel) < floor:                     # change too small → abstain
        return None
    verb = "rose" if rel > 0 else "fell"
    return f"{label} {verb} {abs(rel):{fmt}}"
```

**Calibration note:** "calibrated confidence" = a deterministic monotone map (e.g. logistic over the normalized delta magnitude, or a simple bucketed `high/med/low`). Keep it a pure function — no library, no training. Per CONTEXT it's Claude's discretion; the anti-slop contract is only that *low confidence omits the fact* (abstain), never asserts it.

### Pattern 2: Multi-scale trajectory narrative (PERCEIVE-02)
**What:** Compose the THREE existing scales into one bounded human-readable string.
**Scales already in `MusicState` (no new buffers):**
- **phrase scale:** `phase` + `time_in_phase` (property) + `phase_history` (last 6 transitions). `[VERIFIED: music_state.py:38-39,127; refresh.py:408-413]`
- **energy-arc scale:** `long_arc` (~120s RMS, 10s hop) + `buildup_score` (trailing 8s monotonic climb) + `energy_curve` (last ~12s). `[VERIFIED: music_state.py:35,102,126; refresh.py:393,508]`
- **recent-moves scale:** `recent_moves` (last 12s, deck-attributed). `[VERIFIED: music_state.py:123; refresh.py:504]`

```python
# Source: src/vibemix/state/refresh.py:393,408-413,504,508 (fields already written)
#         + src/vibemix/state/coach.py:346-366 (recent_moves/phase_history render idiom)
# refresh.py — compose inside the lock batch (single writer), BOUNDED output:
def compose_trajectory(state, now) -> str:
    parts = []
    if state.phase_history:
        chain = "→".join(... last 3 ...)            # "build→drop→groove"
    arc = "building" if state.buildup_score > 0.4 else "settled"
    if state.recent_moves:
        age, label = min(state.recent_moves)        # newest move
        parts.append(f"last move: {label} {age:.0f}s ago")
    state.trajectory_narrative = "; ".join(parts)   # ADDITIVE field, default ""

# coach.py — gated render, mirrors the recent_moves[8s] branch:
if state.trajectory_narrative:                       # cold → "" → omit
    e.append(f"trajectory[{state.trajectory_narrative}]")
```

**Bound contract:** Reuse the existing bounded fields (`phase_history` capped at 6, `recent_moves` 12s window). The narrative string is recomputed each tick from those — no new accumulation, no unbounded growth (CONTEXT requirement).

### Pattern 3: Mean-centered nearest-prototype genre (PERCEIVE-03)
**What:** Replace/augment the DSP `score_genre` with an embedding lookup that ranks the playing track's cached embedding against per-genre centered-mean prototypes.

```python
# Source: src/vibemix/library/centering.py:90-143 (load_or_compute_centroid, center_and_renorm)
#         + src/vibemix/library/_cosine.py (cosine_topk, l2_normalize)
#         + src/vibemix/library/rekordbox.py:233 (lookup_by_id → TrackEntry.filepath)
# library/genre_prototypes.py — build once, cache to ~/.cache/vibemix/genre_prototypes.npy
from pathlib import Path
from vibemix.library.centering import load_or_compute_centroid, center_and_renorm
from vibemix.library.store import open_store
from vibemix.library.rekordbox import RekordboxLibrary

def build_prototypes() -> tuple[np.ndarray, list[str]]:
    store = open_store()
    ids, vectors = store._backend.load_all()             # (N,), (N,1536) float32
    centroid = load_or_compute_centroid(vectors, store.snapshot_hash())
    if centroid is None:                                  # N<2 degenerate guard
        return np.empty((0, EMBEDDING_DIM), np.float32), []
    centered = center_and_renorm(vectors, centroid)       # SAME corpus centroid
    # genre proxy = parent folder of each track's filepath
    lib = RekordboxLibrary(); lib.try_load_cache()
    label_of = {}
    for tid in ids:
        te = lib.lookup_by_id(tid)
        label_of[tid] = Path(te.filepath).parent.name if te else "unknown"
    # per-label CENTERED mean = prototype (numpy mean(axis=0), re-L2-norm)
    protos, labels = [], []
    for label in sorted(set(label_of.values())):
        rows = centered[[i for i,t in enumerate(ids) if label_of[t]==label]]
        protos.append(l2_normalize(rows.mean(axis=0))); labels.append(label)
    return np.stack(protos), labels

def classify(track_embedding: np.ndarray, protos, labels,
             centroid, *, floor=0.25, margin=0.05) -> tuple[str, float]:
    q = center_and_renorm(track_embedding, centroid)      # SAME centroid
    ranked = cosine_topk(q, protos, labels, k=2)
    if not ranked: return ("unknown", 0.0)
    (best, s0), *rest = ranked
    second = rest[0][1] if rest else -1.0
    if s0 < floor or (s0 - second) < margin:              # anti-slop floor + margin
        return ("unknown", float(max(0.0, s0)))
    return (best, float(s0))
```

**Where it slots in `refresh.py`:** the genre lookup is **off-loop, debounced on TRACK_CHANGE** (research §4 step 2) — NOT every 10Hz tick (cosine over a handful of prototypes is cheap, but the track only changes on flips). The *result* feeds the existing single-writer write at `refresh.py:339-352`:
```python
# Existing DSP path (refresh.py:339-352) stays; reconcile:
raw_genre, raw_conf = score_genre(...)                    # DSP prior (cheap, every tick)
emb_genre, emb_conf = <latest embedding lookup result>    # off-loop, on TRACK_CHANGE
# Reconciliation policy (planner decides exact rule, CONTEXT discretion):
#   prefer embedding when emb_conf clears its floor; else fall back to DSP;
#   apply_genre_hysteresis on the COMMITTED label (no flicker).
committed = apply_genre_hysteresis(<reconciled raw>, genre_hysteresis)
state.detected_genre = committed
state.genre_confidence = round(<reconciled conf>, 2)
```

**Render is ALREADY wired (WIRE-04):** `coach.py:334-335` emits `genre=<name>` when `detected_genre != "unknown" and genre_confidence >= 0.5`. PERCEIVE-03 only changes the *source* of the value, not the render — so the existing `test_coach.py:253-296` genre golden tests still pin the contract.

### Anti-Patterns to Avoid
- **Second writer to `MusicState`:** The genre lookup, delta compute, and trajectory compose MUST NOT write `MusicState` from any thread but the refresh loop. Run the lookup off-loop, return a value, write it in `_tick_once`. (Invariant #1; mirrors how `deck_source.snapshot()` is copied in at refresh.py:472-501.)
- **Duplicating centering math:** Do NOT hand-roll a centroid/normalize for genre. Call `centering.load_or_compute_centroid` + `center_and_renorm` — the SAME centroid the ranking path uses. A divergent centroid silently corrupts accuracy (research: centering is *the* load-bearing fix).
- **Centering persisted vectors:** Centering is QUERY-SIDE only. Never mutate `library.db`. (centering.py docstring; CONTEXT.)
- **Unbounded trajectory growth:** Compose from existing bounded fields each tick; never accumulate into a growing list.
- **Asserting low-confidence facts:** Below floor → OMIT (abstain), never `genre=unknown` spam or a 0%-delta line. (Anti-slop, invariant #2/#3.)
- **Breaking cold-path byte-identity:** Every new field defaults falsy; every new render branch is `if <field>:`-gated. A cold/un-warmed state must produce v8.0-identical prompt bytes (golden tests enforce this).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Corpus mean-centering | A new centroid+L2 routine | `library/centering.py` (`load_or_compute_centroid`, `center_and_renorm`) | Battle-tested, snapshot-hash-cached, degenerate-guarded; a divergent centroid corrupts genre accuracy. |
| Cosine top-K ranking | argsort/argpartition by hand | `library/_cosine.py::cosine_topk` | The P55 parity chokepoint — deterministic tie-break, float32 assertion, Mac/Win bit-identical. |
| Genre confidence floor / tie-margin / dwell | A new debounce | `state/genre/genre_autodetect.py` (`GENRE_CONFIDENCE_MIN`, `GENRE_TIE_MARGIN`, `apply_genre_hysteresis`, `GenreHysteresis`) | Same anti-flicker idiom already used for DSP genre — reconcile through it for ONE coherent label. |
| Track-id → genre label | A new metadata DB | `RekordboxLibrary.lookup_by_id` → `TrackEntry.filepath` → parent folder | The validated genre proxy (research §1) — Kaan's crate names ARE the labels. |
| Centroid persistence/caching | A new cache format | The `.npy` + `.meta.json` sidecar pattern (`centering.CENTROID_PATH`) | Mirror it for `genre_prototypes.npy` — atomic write, snapshot-hash keyed, best-effort. |

**Key insight:** Phase 78 is ~90% wiring of existing primitives. The only genuinely new code is (a) ~2 `MusicState` fields, (b) ~2 pure render helpers in `coach.py`/`deltas.py`, and (c) one small `library/genre_prototypes.py` that *composes* `centering` + `_cosine` + `rekordbox`. If a task is building new infrastructure, it's wrong — the infra exists.

## Runtime State Inventory

> Not a rename/refactor/migration phase — but PERCEIVE-03 reads on-disk cached state, so the relevant cache inventory is noted for the planner.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data (read-only inputs) | `~/.cache/vibemix/library.db` (399×1536 cached vectors, verified present 6.4M), `library.pkl` (1547 tracks w/ filepath; 399 embedded), `library_centroid.npy` + `.meta.json` (existing corpus centroid) | READ only — build prototypes from these. Never mutate. |
| New cache artifact written | `~/.cache/vibemix/genre_prototypes.npy` + label sidecar (NEW, written by `genre_prototypes.build`) | Create. Snapshot-hash keyed so it auto-rebuilds when `library.db` changes. Tests MUST monkeypatch its path to tmp (mirror the `RekordboxLibrary.CACHE_PATH` test gotcha in CLAUDE.md). |
| Live service config | None — fully in-process, no external service touched. | None — verified by code read (no httpx/keyring/network in the genre path). |
| Secrets/env vars | None — genre lookup uses CACHED vectors (€0); only genuinely-unknown tracks would need `GEMINI_API_KEY`, and the honest-green default uses folder-mean prototypes requiring no live embed. | None for the unit-testable path. |
| Build artifacts | None — no package rename, no egg-info, no compiled output. | None. |

**The canonical question — what runtime state has stale data after this lands?** Only `genre_prototypes.npy`, and it self-heals via the snapshot-hash key (same mechanism as `library_centroid.npy`). Nothing else caches a derived genre.

## Common Pitfalls

### Pitfall 1: Second-writer creep on the genre lookup
**What goes wrong:** Running the genre-prototype lookup on a background thread that writes `state.detected_genre` directly → two writers → invariant #1 violation → race with `_tick_once`.
**Why it happens:** The lookup is naturally off-loop (debounced on TRACK_CHANGE) and it's tempting to write the result where it's computed.
**How to avoid:** Mirror `Grounding` (grounding.py:169-265): the off-loop worker stores its result in a thread-safe holder; `_tick_once` READS the holder and writes `MusicState`. Only `_tick_once` ever touches `state.*`.
**Warning signs:** Any `state.detected_genre =` outside `refresh._tick_once`. The repo has static-gate precedent for single-writer enforcement (tests/state).

### Pitfall 2: Centroid divergence between ranking and genre
**What goes wrong:** Building prototypes with a freshly-computed centroid while the live track is centered with a different (cached) centroid → garbage cosine.
**Why it happens:** Forgetting that BOTH prototype-build AND live-classify must use the SAME corpus centroid.
**How to avoid:** Always go through `load_or_compute_centroid(vectors, store.snapshot_hash())` for both. Store the centroid (or its snapshot hash) alongside the prototypes so a live classify uses the matching one.
**Warning signs:** Genre accuracy collapses to near-random; cosine scores cluster near 0 or near 1 uniformly (the anisotropy signature — research: raw 0.78, centered 0.06).

### Pitfall 3: Cold-path prompt drift
**What goes wrong:** A new delta/trajectory field emits text on the very first tick (no prior, empty trajectory) → breaks the v8.0 golden bytes → `test_coach.py` fails.
**Why it happens:** Not gating the new render branches on a warm/non-empty precondition.
**How to avoid:** Every new field defaults falsy (`prev_perceive={}`, `trajectory_narrative=""`); every render branch is `if <field>:`-gated; `render_delta` returns `None` when `prev is None`. The existing golden tests (`test_coach.py` byte-identity assertions) are the safety net — run them RED-first on a cold state.
**Warning signs:** `test_coach.py` golden/byte-identity tests fail on an empty `MusicState()`.

### Pitfall 4: Genre confidence-floor mismatch
**What goes wrong:** Embedding cosine confidence is on a different scale than the DSP `score_genre` confidence (centered cosine ~0.25 floor vs DSP's 0.55). Surfacing the raw cosine as `genre_confidence` while `coach.py` gates at `>= 0.5` could either over-suppress or over-assert.
**Why it happens:** Two confidence scales reconciled into one field with a single render gate.
**How to avoid:** Decide the reconciliation contract explicitly (CONTEXT discretion): either (a) normalize the embedding cosine into the same [0,1] band the render gate expects, or (b) adjust which confidence is written. Pin it with a unit test asserting a known centered-cosine maps to an above/below-floor render.
**Warning signs:** `genre=` never appears live (over-suppressed) or appears on weak matches (over-asserted).

### Pitfall 5: Library/rekordbox test cache clobber
**What goes wrong:** A prototype-build test that calls `RekordboxLibrary().try_load_cache()` or `open_store()` without path monkeypatching overwrites the real `~/.cache/vibemix/library.pkl` / `genre_prototypes.npy`.
**Why it happens:** Documented CLAUDE.md gotcha: "library/rekordbox tests MUST monkeypatch `RekordboxLibrary.CACHE_PATH` to a tmp dir."
**How to avoid:** Every PERCEIVE-03 test monkeypatches `RekordboxLibrary.CACHE_PATH`, `centering.CENTROID_PATH`/`CENTROID_META_PATH`, and the new prototype path to a `tmp_path`. Mirror `tests/library/test_centering.py` fixtures.
**Warning signs:** Test run mutates real cache; subsequent live session re-embeds or mis-labels.

## Code Examples

All verified patterns are inline in §Architecture Patterns 1-3 (each tagged with its source file:line). They are reused-primitive compositions, not new external API usage. No additional external-API examples are needed because no new library is introduced.

## State of the Art

| Old Approach (v8.0) | Current Approach (Phase 78) | When Changed | Impact |
|--------------------|-----------------------------|--------------|--------|
| Bare absolute scalars in `evidence_line` (`rms=0.42 bpm=174`) | Δ-phrasing preferred (`kick density rose 18%`), abstain below floor | This phase (PERCEIVE-01) | Gemini reads change, not snapshots — the documented fix for the "shallowness" |
| Single-snapshot prompt (no time context beyond `recent_moves`/`phase_history` raw fields) | One composed `trajectory[...]` narrative across phrase/energy-arc/moves | This phase (PERCEIVE-02) | Gemini reasons over set shape |
| `detected_genre` from DSP `score_genre` (BPM/band/crest axes only) | Mean-centered nearest-prototype over cached embeddings, reconciled with DSP | This phase (PERCEIVE-03) | 86.5% accuracy at €0 vs coarse 3-band DSP |

**Deprecated/outdated:** Nothing removed. PERCEIVE-01/02 are *additive* render branches (raw scalars stay for other consumers); PERCEIVE-03 *augments* (not deletes) the DSP genre path.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The 86.5% nearest-prototype accuracy generalizes to the live classify path (the research validated it on in-corpus prototypes; live tracks may be unknown-to-library). | PERCEIVE-03 | If a live track is NOT in the library, it needs a fresh audio embed (the only recurring cost). The confidence floor + abstain contract makes a wrong genre fail safe (→ "unknown"), so the *risk* is "no genre" not "wrong genre" — acceptable. Verify the unknown-track path is gated. |
| A2 | Folder-name genre proxy is stable enough for prototypes on Kaan's real library. | PERCEIVE-03 | Folder labels are a proxy, not ground truth (research §3 caveat). The phase is unit-tested on synthetic/known prototypes; the live "does it feel deeper" judgment is the parked Phase-81 + Kaan's-ear item — so a soft label is acceptable here. |
| A3 | A single render gate (`genre_confidence >= 0.5`, coach.py:334) can serve both DSP and centered-cosine confidence after reconciliation. | Pitfall 4 | If scales can't be reconciled to one gate, the planner must split or normalize. Flagged as a discretion decision needing a pinning test. |

**These are the only `[ASSUMED]` items.** Everything else in this research was verified against live code this session.

## Open Questions

1. **Reconciliation policy: embedding-genre vs DSP-genre when they disagree.**
   - What we know: Both produce `(label, confidence)`; CONTEXT says "augment, not replace wholesale; one coherent label per tick."
   - What's unclear: The exact precedence rule (embedding-wins-when-confident vs fuse-as-prior).
   - Recommendation: Prefer embedding when its (normalized) confidence clears the floor; fall back to DSP `score_genre` otherwise; run BOTH through `apply_genre_hysteresis` on the committed label. Pin with a unit test of an agree case + a disagree case. (Discretion per CONTEXT — planner decides; this is the simplest coherent rule.)

2. **Prototype build timing: precompute-on-launch vs lazy-on-first-genre-query.**
   - What we know: CONTEXT explicitly leaves this to the planner.
   - What's unclear: launch latency vs first-classify latency tradeoff.
   - Recommendation: Lazy-build on first TRACK_CHANGE classify, cached snapshot-hash-keyed (mirrors `library_centroid.npy`). Cheap (one `mean(axis=0)` per folder over 399 vecs); no launch-time cost; self-heals on library change.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `numpy` | all three requirements (vector math) | ✓ | uv.lock pin | — |
| `~/.cache/vibemix/library.db` | PERCEIVE-03 prototype build | ✓ | 399 vecs, 6.4M (verified) | Degenerate guard: N<2 → centroid None → genre stays "unknown" (no crash) |
| `~/.cache/vibemix/library.pkl` | PERCEIVE-03 genre labels | ✓ | 1547 tracks, 272k (verified) | Missing track → label "unknown" → excluded from prototypes |
| `GEMINI_API_KEY` | ONLY for genuinely-unknown-track live embed (not the unit path) | ✓ (.env) | — | Library-track classify is €0/cached; honest-green tests use cached vectors only — no key needed |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none blocking — the cached-vector path needs no network/key.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (`[tool.pytest.ini_options]` in `pyproject.toml`) |
| Config file | `pyproject.toml` |
| Quick run command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q tests/state/test_coach.py tests/state/test_genre_autodetect.py` |
| Full suite command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PERCEIVE-01 | Δ-phrasing rendered when prior present + change above floor | unit | `pytest tests/state/test_coach_perceive.py::test_delta_rendered_when_change_significant -x` | ❌ Wave 0 |
| PERCEIVE-01 | Abstain (omit fact) below floor; cold (no prior) byte-identical to v8.0 | unit | `pytest tests/state/test_coach_perceive.py::test_cold_path_byte_identical -x` | ❌ Wave 0 |
| PERCEIVE-01 | `_tick_once` captures prev_snapshot last, inside lock (single-writer) | unit | `pytest tests/state/test_refresh_perceive.py::test_prev_snapshot_written_in_lock -x` | ❌ Wave 0 |
| PERCEIVE-02 | trajectory narrative composed from phase_history+buildup+recent_moves, bounded | unit | `pytest tests/state/test_refresh_perceive.py::test_trajectory_composed_bounded -x` | ❌ Wave 0 |
| PERCEIVE-02 | empty trajectory → field omitted (cold byte-identity) | unit | `pytest tests/state/test_coach_perceive.py::test_empty_trajectory_omitted -x` | ❌ Wave 0 |
| PERCEIVE-03 | prototype build: per-folder centered mean from synthetic vectors+labels | unit | `pytest tests/library/test_genre_prototypes.py::test_build_centered_means -x` | ❌ Wave 0 |
| PERCEIVE-03 | classify: nearest-prototype label + floor abstains on weak/ambiguous | unit | `pytest tests/library/test_genre_prototypes.py::test_classify_floor_and_margin -x` | ❌ Wave 0 |
| PERCEIVE-03 | genre lookup result feeds `detected_genre` ONLY via `_tick_once` (single-writer) | unit | `pytest tests/state/test_refresh_perceive.py::test_genre_fed_single_writer -x` | ❌ Wave 0 |
| PERCEIVE-03 | reconciliation: embedding vs DSP agree/disagree → one coherent label | unit | `pytest tests/state/test_refresh_perceive.py::test_genre_reconciliation -x` | ❌ Wave 0 |

**Note:** the existing `tests/state/test_coach.py:253-296` genre golden tests already pin the `genre=` render gate — PERCEIVE-03 must keep them GREEN (it changes the source, not the render).

### Sampling Rate
- **Per task commit:** quick run (`test_coach.py` + new `*_perceive.py` files) — < 10s.
- **Per wave merge:** full suite (`pytest -q`) — current baseline 4399/0 green.
- **Phase gate:** full suite green + the v8.0 byte-identity golden tests green before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `tests/state/test_coach_perceive.py` — PERCEIVE-01/02 render + cold-path byte-identity
- [ ] `tests/state/test_refresh_perceive.py` — single-writer prev_snapshot + trajectory + genre-feed + reconciliation
- [ ] `tests/library/test_genre_prototypes.py` — prototype build + classify (synthetic vectors; monkeypatch all cache paths)
- [ ] Shared fixtures: synthetic `MusicState` sequence builder (for deltas/trajectory) + synthetic `(vectors, ids, label_of)` fixture (for prototypes) — likely in `tests/state/conftest.py` / `tests/library/fixtures/`
- Framework install: none — pytest already configured.

*The "does it feel deeper" judgment is explicitly a Phase-81 BENCH + Kaan's-ear item (parked, never faked). Phase 78's automated proof is the deterministic unit assertions above.*

## Security Domain

> `security_enforcement` key absent from `.planning/config.json` → treated as enabled. This phase is in-process, local, no auth/session/network surface — most ASVS categories N/A.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface — local in-process state enrichment. |
| V3 Session Management | no | No sessions. |
| V4 Access Control | no | No access boundary crossed. |
| V5 Input Validation | yes (light) | Genre labels derived from filesystem folder names + cached vectors — validate dim (`EMBEDDING_DIM` assert, already in `_cosine`/grounding) and degenerate N<2 guard (centering already does). No untrusted network input. |
| V6 Cryptography | no | No crypto; no secrets handled in the cached-vector path. |

### Known Threat Patterns for {Python in-process state}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Hallucinated genre asserted as fact | Tampering (truth) | Confidence floor + margin → abstain to "unknown" (invariant #3, the anti-slop gate). |
| Stale cache returns wrong prototypes after library change | Tampering | snapshot-hash-keyed cache (mirror `centering.py`) — auto-rebuild on store change. |
| Test run clobbers real `~/.cache/vibemix` | Tampering (dev data) | Monkeypatch all cache paths in tests (Pitfall 5). |
| Second writer races `MusicState` | Tampering (consistency) | Single-writer invariant #1 — off-loop worker → holder → `_tick_once` reads/writes (Pitfall 1). |

## Sources

### Primary (HIGH confidence — verified against live code this session)
- `src/vibemix/state/music_state.py` (lines 23-153) — `MusicState` fields, `detected_genre`/`genre_confidence` at 55-56, all delta/trajectory source fields.
- `src/vibemix/state/refresh.py` (lines 191-599) — single-writer `_tick_once`; genre write at 339-352; phase/trajectory fields at 393,408-413,504,508; deck-snapshot copy-in idiom at 472-501.
- `src/vibemix/state/coach.py` (lines 256-432) — `evidence_line` render gates; genre gate at 334-335; recent_moves/phase_history render at 346-366.
- `src/vibemix/state/event_detector.py` (lines 1-80) — recent-moves source, event taxonomy.
- `src/vibemix/library/centering.py` (full) — `load_or_compute_centroid`, `center_and_renorm`, snapshot-hash cache.
- `src/vibemix/library/_cosine.py` — `cosine_topk`, `l2_normalize`, `EMBEDDING_DIM=1536`.
- `src/vibemix/library/store.py` (lines 56-178) — `search`/`search_centered`, `open_store`, `snapshot_hash`.
- `src/vibemix/library/grounding.py` (full) — live-embed + center + cosine precedent; `Grounding` thread-safe holder pattern.
- `src/vibemix/library/folder_ingest.py` (177-197) — `track_id=folder:<sha1>`, filepath.
- `src/vibemix/library/rekordbox.py` (85-233) — `TrackEntry.filepath`, `lookup_by_id`, cache.
- `src/vibemix/state/genre/genre_autodetect.py` (50-189) — `score_genre`, `GENRE_CONFIDENCE_MIN=0.55`, `GENRE_TIE_MARGIN=0.08`, `apply_genre_hysteresis`, `GenreHysteresis`, `_HYSTERESIS_DWELL_TICKS=3`.
- `.planning/archive/2026-05-27-stale-one-mind-research/genre-from-embeddings.md` — 86.5% nearest-prototype, €0, mean-centering decisive (raw 0.779 → centered 0.058); folder-as-label proxy; live-wire recipe §4.
- `.planning/archive/2026-05-27-stale-one-mind-research/one-mind-charter.md` — EAR-speaks-in-deltas/trajectory architecture; Gemini-interprets thesis.
- `tests/state/test_coach.py` (253-296) — existing `genre=` render golden (must stay green).
- `~/.cache/vibemix/` listing — verified library.db (6.4M, 399 vecs), library.pkl (272k), library_centroid.npy present.

### Secondary (MEDIUM confidence)
- CLAUDE.md project instructions + `.planning/codebase/CONVENTIONS.md` — single-writer discipline, numpy-no-torch, `from __future__ import annotations`, library-test cache-monkeypatch gotcha.

### Tertiary (LOW confidence)
- none — no WebSearch was needed (zero new external dependencies).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — nothing new installed; every reused module verified by direct read this session.
- Architecture: HIGH — all three patterns map to existing single-writer/render seams confirmed in `refresh.py`/`coach.py`/`centering.py`.
- Pitfalls: HIGH — each derived from a concrete code invariant or a documented gotcha (CLAUDE.md, centering.py docstring, existing tests).
- PERCEIVE-03 accuracy generalization: MEDIUM — 86.5% is on in-corpus prototypes / folder labels (Assumption A1/A2); the fail-safe abstain contract bounds the downside.

**Research date:** 2026-05-26
**Valid until:** 2026-06-25 (30 days — stable; no fast-moving external deps. Re-verify only if `state/refresh.py` or `library/centering.py` is refactored.)
