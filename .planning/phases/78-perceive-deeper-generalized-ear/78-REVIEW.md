---
phase: 78-perceive-deeper-generalized-ear
reviewed: 2026-05-26T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - src/vibemix/library/genre_prototypes.py
  - src/vibemix/state/coach.py
  - src/vibemix/state/deltas.py
  - src/vibemix/state/genre/genre_reconcile.py
  - src/vibemix/state/music_state.py
  - src/vibemix/state/refresh.py
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: fixed
fixed:
  warning: 4
  info: 0
fix_commits:
  WR-01: 9e40de6
  WR-02: f2e2735
  WR-03: db974a0
  WR-04: 07bd33a
---

# Phase 78: Code Review Report

**Reviewed:** 2026-05-26
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Reviewed the Phase 78 additive changes against the focus checklist. The hard invariants hold:

- **Single-writer (#1):** Confirmed via grep — every assignment of `detected_genre`, `genre_confidence`,
  `prev_perceive`, `trajectory_narrative` lives in `refresh._tick_once`, all inside the
  `with state._lock:` block (opened at refresh.py:378, function returns after it). The genre holder is
  READ via `get_latest()`, never written by refresh. No second writer.
- **Generation-token guard (Phase-77 CR-01 class):** The slow-worker / fast-superseding-worker ordering
  is handled correctly — a stale worker that finishes after a newer `clear()` + dispatch sees
  `my_gen != _inflight_gen` and discards its write. No stale clobber on the `_latest` latch.
- **Cold-path byte-identity:** Both new render branches are strictly falsy-gated (`if prev:`,
  `if state.trajectory_narrative:`); the genre gate at coach.py:357 is unchanged. `_compose_trajectory`
  returns `""` on a cold state. 29 Phase-78 tests pass.
- **`normalize_embedding_confidence`:** Numerically sound — verified anchors (0.25→0.5, 1.0→1.0,
  sub-floor maps `<0.5`), monotone increasing, clamped `[0,1]`, `span<=0` div-by-zero guard present.
- **Rule-1 abstain preserved:** sub-floor / unknown embedding → `reconcile_genre` returns the DSP tuple →
  routed through `apply_genre_hysteresis` → still abstains. Cannot assert an unsupported genre.
- **Composition discipline:** `genre_prototypes` delegates all centroid/cosine/centering math to
  `library.centering` + `library._cosine` — no re-rolled math. No `genai.Client`, no API key, no torch,
  no hardcoded model literal on any new path (grep-clean). numpy float32 / L2-norm correct.

One real logic defect (WR-01) defeats the phase's headline purpose in the embedding↔DSP **agreement**
case, plus two genuine data-race / consistency issues and one prototype-pollution issue. None are
crashes, data-loss, or security risks, so no Critical. Note: `genre_source` is not yet wired into
`main()` (kwarg defaults to `None`) — the dispatch path is dormant in the live app until Plan 04, which
lowers the blast radius of the race findings but they must be fixed before that wiring lands.

## Warnings

### WR-01: Embedding↔DSP agreement silently falls back to DSP confidence, re-triggering the Pitfall-4 over-suppression the phase exists to fix

**File:** `src/vibemix/state/refresh.py:450-461`
**Issue:** The commit guard is
`if rec_label == emb_label and emb_label not in ("unknown", raw_genre):`. When the embedding and DSP
**agree** on the label (`emb_label == raw_genre`), the `not in (..., raw_genre)` clause is False, so
`emb_won` stays False and the code falls to the DSP branch — committing `genre_confidence =
round(raw_genre_conf, 2)`.

`reconcile_genre` already computed the correct fused value. Verified empirically:

```
reconcile_genre("techno", 0.9, "techno", 0.3)  ->  ("techno", 0.9333)   # render-band, would clear 0.5
refresh commits instead:                            genre_confidence = 0.3  # < 0.5 render gate -> SUPPRESSED
```

So when both sources agree AND the high-trust embedding is confident but the per-tick DSP score is below
0.5 (common — DSP is the coarse 3-band proxy), the genre line is **suppressed at coach.py:357 even though
both signals confidently agree**. This is precisely the over-suppression the module docstring
(genre_reconcile.py:5-9) and the refresh comment (refresh.py:430-439) claim to fix, and it fires in the
most common real case (agreement). It also re-introduces the "first 3 ticks suppressed" problem the
comment says it avoids, because agreement now routes through the dwell on DSP confidence.

**Fix:** Trust `reconcile_genre`'s output instead of re-deriving the win condition from labels. Commit
the reconciled tuple whenever the embedding produced the winning (render-band) label — including the
agreement case — and only skip the hysteresis resync when the committed label already equals
`genre_hysteresis.current_label`:

```python
emb_won = False
if genre_source is not None:
    latest = genre_source.get_latest()
    if latest is not None:
        emb_label, emb_conf = latest
        rec_label, rec_conf = reconcile_genre(emb_label, emb_conf, raw_genre, raw_genre_conf)
        # Embedding won iff reconcile returned the embedding label at render-band conf.
        if rec_label == emb_label and emb_label != "unknown" and rec_conf >= 0.5:
            if genre_hysteresis.current_label != rec_label:
                genre_hysteresis.current_label = rec_label
                genre_hysteresis.pending_label = None
                genre_hysteresis.pending_ticks = 0
            committed_genre = rec_label
            state.detected_genre = committed_genre
            state.genre_confidence = round(rec_conf, 2)
            emb_won = True
if not emb_won:
    committed_genre = apply_genre_hysteresis(raw_genre, genre_hysteresis)
    state.detected_genre = committed_genre
    state.genre_confidence = round(raw_genre_conf, 2)
```

### WR-02: Unlocked lazy init of `_protos`/`_store`/`_centroid` is a data race between concurrent off-loop workers

**File:** `src/vibemix/library/genre_prototypes.py:262-276, 290`
**Issue:** `_ensure_prototypes()` and `_ensure_store()` mutate `self._protos`, `self._labels`,
`self._centroid`, `self._store` **outside** `self._lock`. Each TRACK_CHANGE spawns a fresh daemon worker
(`refresh._dispatch_genre_lookup`) with no in-flight guard, so two workers can run concurrently. The
tuple assignment `self._protos, self._labels, self._centroid = load_or_build_prototypes(store)` is three
separate attribute stores; a second worker (or a future reader) can observe `_protos` set while
`_centroid` is still `None` (or a `_protos`/`_centroid` pair from different builds). The `classify_playing`
None-check (line 291) makes the torn-read *safe-ish* (it abstains), but it is still an unsynchronized
data race on shared mutable state and can do redundant full prototype rebuilds.

**Fix:** Guard the lazy init under the existing lock (double-checked):

```python
def _ensure_prototypes(self) -> None:
    if self._protos is not None:
        return
    store = self._ensure_store()
    protos, labels, centroid = load_or_build_prototypes(store)
    with self._lock:
        if self._protos is None:
            self._protos, self._labels, self._centroid = protos, labels, centroid
```

(and protect `_ensure_store()`'s `self._store = open_store()` similarly, or document that the holder is
single-worker-only and add an in-flight guard in `_dispatch_genre_lookup`).

### WR-03: `_compose_trajectory` "last move" uses the full 12s window, contradicting its "mirror recent_moves[8s]" claim and the coach output

**File:** `src/vibemix/state/refresh.py:224-227`
**Issue:** `state.recent_moves` is populated from `controller_state.moves_since(now - 12.0)` (refresh.py:623)
— a 12-second window. `_compose_trajectory` reports `min(recent_moves, key=lambda m: m[0])` over that full
window, so the trajectory can emit `"last move: bass-swap 11s ago"` while the coach's `recent_moves[8s]`
block (coach.py:369, `age <= 8.0`) simultaneously says `recent_moves[8s]: NONE`. The inline comment
claims it mirrors "coach's recent_moves[8s] sort" but it never applies the 8s filter — the two surfaces
disagree about whether a move happened, which is exactly the kind of internal inconsistency that reads as
AI slop.

**Fix:** Filter to the same 8s window the coach uses before picking the newest move:

```python
recent_8s = [m for m in recent_moves if m[0] <= 8.0]
if recent_8s:
    age, label = min(recent_8s, key=lambda m: m[0])
    parts.append(f"last move: {label} {age:.0f}s ago")
```

### WR-04: `"unknown"` is built as a real prototype and competes in the tie-margin, able to suppress a correct genre

**File:** `src/vibemix/library/genre_prototypes.py:127-133, 162-166`
**Issue:** `build_prototypes` derives labels from `set(label_of.get(tid, "unknown") ...)`. Any track not
found in the Rekordbox cache, or whose parent folder is literally absent, maps to `"unknown"` and
contributes a real centered-mean prototype row labeled `"unknown"`. In `classify`, that `"unknown"`
prototype then competes in `cosine_topk(k=2)`: it can be the runner-up and shrink the
`best_sim - second_sim` gap below `PROTO_MARGIN`, forcing a real, correct genre into abstain — or it can
itself be `best_label = "unknown"` at high cosine. The abstain path in `reconcile_genre` handles the
`emb_label == "unknown"` case correctly, but a real genre being margin-suppressed by a junk "unknown"
cluster is a silent miss.

**Fix:** Exclude the `"unknown"` proxy when building prototype rows so it never competes:

```python
labels = sorted({label_of.get(tid, "unknown") for tid in ids} - {"unknown"})
```

(and keep the `protos.shape[0] == 0` empty-table abstain for the all-unknown corpus).

## Info

### IN-01: `genre_source` is unwired — dormant in the live app until Plan 04

**File:** `src/vibemix/state/refresh.py:281, 689, 746`
**Issue:** `genre_source` is threaded through as a `None`-default kwarg only; nothing in `main()`
constructs a `GenrePrototypeLookup` or passes it in (grep confirms no construction site). The entire
embedding-genre / off-loop-dispatch path is therefore inert in the shipped app today. This is consistent
with the "Plan 04 wires it" comments and is fine as additive scaffolding, but the WR-02 race and WR-01
logic defect must be fixed before that wiring lands or they ship live.
**Fix:** No action this phase; track WR-01/WR-02 as blockers for the Plan-04 wiring commit.

### IN-02: Unbounded daemon-worker spawn per TRACK_CHANGE; no join at shutdown

**File:** `src/vibemix/state/refresh.py:233-254`
**Issue:** `_dispatch_genre_lookup` spawns a new `daemon=True` thread per TRACK_CHANGE with no in-flight
cap and no cooperative `stop_event`. Daemon threads won't block process exit (so no hard leak), and
TRACK_CHANGE has an upstream cooldown, so this is low-risk — but a flapping audible-track signal could
spawn many overlapping `classify_playing` workers (which also amplifies the WR-02 race). The project
convention is that long-running coroutines take `stop_event`; these are short-lived, so a daemon is
acceptable, but an in-flight guard (skip dispatch if a worker is already running) would be cleaner.
**Fix:** Add a single `threading.Event`/busy flag so only one genre worker runs at a time; drop the
dispatch (it's superseded anyway) when one is in flight.

### IN-03: `cosine_topk` uses bare `assert` for shape/dtype contracts (stripped under `python -O`)

**File:** `src/vibemix/library/_cosine.py:112-134` (called by `genre_prototypes.classify`)
**Issue:** `classify` feeds `cosine_topk`, whose shape/dtype invariants are enforced with `assert`. Under
`python -O` (optimized bytecode) all asserts are stripped, so a malformed embedding shape would pass
silently into the dot-product instead of failing loud. Pre-existing in `_cosine.py`, not introduced by
Phase 78, but the new `classify` path is now a caller. Low priority — production runs are not typically
`-O`.
**Fix:** If `-O` distribution is ever a target, convert the load-bearing contract asserts to explicit
`raise ValueError`. No action needed this phase.

---

_Reviewed: 2026-05-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
