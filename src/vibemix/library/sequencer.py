# SPDX-License-Identifier: Apache-2.0
"""sequencer — order a candidate pool into an N-slot set that follows a target
energy curve, using only technically-valid (Camelot + BPM±6%) transitions, via
beam search.

This is the set-sequencing module of the Vibe Mix engine (design:
``.planning/research/vibe-mix-engine-research.md`` §B). It is **pure-compute**:
no Gemini, no network, no store. The discover/agent layer builds a pool of
``PoolTrack`` (resolving vectors + key/BPM/energy) and hands it here; this
module is a pure function of its inputs.

Problem shape (locked, §B):
    NOT TSP/Hamiltonian — it is **fixed-length subset-selection + ordering**
    under a *positional* energy target (the same track has a different cost at
    slot 3 vs slot 17) with a non-Markovian distinctness constraint. The model
    is a depth-N trellis; **beam search** is the right tool (A* with a hard
    frontier cap, no admissible heuristic needed).

Grounding / honesty discipline (mirrors ``next_suggestion.py`` and Cardinal
Invariant #3 "trust the audio"):
    * Transition validity degrades on missing metadata to a **PASS**, never a
      reject — a track with no key/BPM does not collapse the graph. We reject
      ONLY when both sides are known and genuinely incompatible.
    * When the strict graph is too sparse to fill the set, we walk a
      **relaxation ladder** (widen BPM, then allow unknown-key bridges) and
      **TAG** every relaxed edge so the UI can warn ("BPM jump here"). We never
      silently emit an invalid transition, and never fabricate a track.
    * If the frontier dies entirely, we return the best honest **partial** set
      rather than padding it.

Cost model (§B). Per slot a node cost and per edge an edge cost; every term is
normalized to ``[0, 1]`` across the pool so the weights ``alpha..epsilon`` are
sane ``[0, 1]`` taste dials (else the squared-energy term, range ~1e4, would
silently dominate the ``1-cos`` coherence term, range ~2):

    node[slot]  = alpha * (energy - curve[slot])**2   # normalized -> [0,1]
                - gamma * surprise                     # optional, default 0
                + delta * recency                      # optional, default 0
                + epsilon * library_bias               # optional, default 0
    edge[a, b]  = beta  * (1 - coh[a, b])              # 1 - cosine, -> [0,1]
                + zeta  * (1 - harmonic[a, b])         # graded Camelot tiebreak (S1)

Runtime: ~10k partial evals x microsecond cosine -> well under 100ms at
M=50, N=20.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from vibemix.intel.transition_scorer import bpm_folded_delta_pct, harmonic_score
from vibemix.library._cosine import l2_normalize
from vibemix.state import harmonics

# ---------------------------------------------------------------------------
# Curve presets — energy targets parameterized by NORMALIZED set position
# (0..1), so np.interp resamples each to ANY n_slots. Values are 0..100 to
# match the (also-0..100) energy scale. Knot lists are deliberately short and
# hand-shaped; np.interp draws the straight segments between them.
# ---------------------------------------------------------------------------
CURVE_PRESETS: dict[str, list[float]] = {
    # Warm-up: start low, climb steadily to a moderate ~75 — never peaks.
    "opener": [25.0, 35.0, 50.0, 62.0, 75.0],
    # Prime time: ramp into a sustained 85-95 plateau, the headline hour.
    "peak_time": [55.0, 75.0, 88.0, 92.0, 90.0, 93.0],
    # After-hours: medium-high HYPNOTIC oscillation, no big drops (stays >=70).
    "after_hours": [72.0, 80.0, 74.0, 82.0, 76.0, 84.0, 78.0],
    # Festival: multi-peak with FAST recovery between drops (no long valleys).
    "festival": [60.0, 92.0, 70.0, 95.0, 72.0, 96.0, 78.0],
}

# Default cost weights. alpha (curve adherence) and beta (coherence) carry v1;
# the optional taste terms default OFF (their dicts are empty -> term == 0).
_DEFAULT_WEIGHTS: dict[str, float] = {
    "alpha": 1.0,  # energy-curve adherence (the primary objective)
    "beta": 0.6,  # sonic coherence between consecutive tracks
    "zeta": 0.10,  # graded Camelot-adjacency edge tiebreak (S1, small by design)
    "gamma": 0.0,  # surprise reward (set surprise dict to enable)
    "delta": 0.0,  # recency penalty
    "epsilon": 0.0,  # library-bias nudge
}

# BPM relaxation ladder (§B): start strict at 6%, widen on a dead frontier.
# The final rung also permits unknown-key bridges (penalized + TAGGED).
_BPM_LADDER: tuple[float, ...] = (0.06, 0.08, 0.12)

# Near-duplicate guard: same title and cosine above this => one is dropped so
# the set cannot "mix a track into itself".
_NEAR_DUP_COS = 0.995

# Jaccard ceiling for the returned candidate set — each pair must share at most
# this fraction of tracks (=> each candidate is >= 30% distinct at 0.7).
_JACCARD_MAX = 0.7

# Cue-aware transition hints. Missing cues remain "unknown" and therefore pass;
# when cue metadata exists, weak structure is tagged as a relaxed edge instead
# of silently looking like a clean mix.
_MIX_IN_FRAC = 0.35
_MIX_OUT_FRAC = 0.55
_MIX_CUE_FLOOR_S = 64.0


@dataclass(frozen=True, slots=True)
class PoolTrack:
    """One candidate track, fully resolved by the discover/agent layer.

    ``vec`` is the L2-normalized embedding (unit-norm => dot == cosine ==
    sonic_coherence). ``bpm`` / ``camelot`` / ``energy`` are honest-nullable;
    missing values degrade gracefully (never block sequencing).
    """

    track_id: str
    title: str
    artist: str
    vec: np.ndarray  # (D,) float32, L2-normalized
    bpm: float | None
    camelot: str | None
    energy: float | None  # 0..100, or None -> BPM-proxy / 0-contribution
    duration_s: float = 0.0
    cues: Sequence[Any] = ()


@dataclass(frozen=True, slots=True)
class SetCandidate:
    """One ranked, ordered set proposal."""

    track_ids: list[str]
    cost: float
    energy_fit: float  # mean |track_energy - curve[slot]| (0..100; lower=better)
    avg_coherence: float  # mean consecutive cosine (0..1; higher=smoother)
    # (from_id, to_id, reason) for each transition we had to RELAX to keep the
    # set connected — the UI surfaces these as "BPM jump here" style warnings.
    relaxed_transitions: list[tuple[str, str, str]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Curve resampling
# ---------------------------------------------------------------------------
def resample_curve(curve: str | list[float] | np.ndarray, n_slots: int) -> list[float]:
    """Resample a preset name OR a raw 0..100 list to EXACTLY ``n_slots`` points.

    The preset/list is treated as knots equally spaced over the normalized set
    position [0, 1]; ``np.interp`` draws the value at each of the ``n_slots``
    evenly-spaced sample positions. Works for any length (fewer or more tracks
    than the preset has knots).
    """
    if n_slots <= 0:
        return []
    if isinstance(curve, str):
        if curve not in CURVE_PRESETS:
            raise KeyError(
                f"unknown curve preset {curve!r}; "
                f"known: {sorted(CURVE_PRESETS)}"
            )
        knots = np.asarray(CURVE_PRESETS[curve], dtype=float)
    else:
        knots = np.asarray(curve, dtype=float)
    if knots.size == 0:
        return [0.0] * n_slots
    if knots.size == 1:
        return [float(knots[0])] * n_slots
    if n_slots == 1:
        # single slot -> the curve's own midpoint (a sensible scalar target)
        return [float(np.interp(0.5, np.linspace(0.0, 1.0, knots.size), knots))]
    src_x = np.linspace(0.0, 1.0, knots.size)
    dst_x = np.linspace(0.0, 1.0, n_slots)
    return [float(v) for v in np.interp(dst_x, src_x, knots)]


# ---------------------------------------------------------------------------
# Transition gate (mirrors next_suggestion.py both-known degrade)
# ---------------------------------------------------------------------------
def _transition_valid(
    a: PoolTrack,
    b: PoolTrack,
    bpm_tol: float = 0.06,
    *,
    allow_unknown_key_bridge: bool = False,
) -> tuple[bool, bool]:
    """Is ``a -> b`` a technically-valid mix? Returns ``(relaxed, valid)``.

    Camelot: reject ONLY when BOTH keys are known and not
    ``harmonics.compatible`` (``compatible`` returns False on unknown, so a
    missing key MUST pass or the graph collapses — exactly the degrade
    ``next_suggestion`` uses). BPM: reject only when BOTH are known and
    the nearest 0.5x/1x/2x BPM fold is outside ``bpm_tol``. Missing metadata
    => PASS.

    Structural mixability is handled by ``_structural_relax_reason`` in the
    beam edge-admission path: cue metadata never hard-rejects a track, but weak
    mix-in/out anchors are penalized and surfaced as relaxed transitions.

    ``relaxed`` is informational here (always False) — the ladder in the beam
    sets the relaxed flag based on which rung admitted the edge; this predicate
    just answers strict-vs-current-tolerance validity.
    """
    # Camelot gate — both known + incompatible => reject (unless bridging).
    if (
        a.camelot is not None
        and b.camelot is not None
        and not harmonics.compatible(a.camelot, b.camelot)
    ):
        if not allow_unknown_key_bridge:
            return False, False
        # bridging keeps it but it is a relaxed (penalized) edge
        return True, True

    # BPM gate — both known + outside tolerance => reject.
    if (
        a.bpm is not None
        and b.bpm is not None
        and a.bpm > 0
        and (bpm_folded_delta_pct(a.bpm, b.bpm) or 0.0) > bpm_tol
    ):
        return False, False

    return False, True


# ---------------------------------------------------------------------------
# Energy resolution — explicit -> BPM-proxy -> 0-contribution
# ---------------------------------------------------------------------------
def _resolve_energies(pool: list[PoolTrack]) -> tuple[np.ndarray, np.ndarray]:
    """Return (energy[M] in 0..100, has_energy_mask[M] bool).

    For tracks with an explicit energy, use it. Otherwise fall back to a
    pool-relative min-max-normalized BPM proxy (0..100). Tracks with neither
    energy nor BPM contribute 0 to the curve term (mask False) — coherence and
    harmonics drive their placement. NEVER blocks on energy (§B).
    """
    m = len(pool)
    energies = np.zeros(m, dtype=float)
    has = np.zeros(m, dtype=bool)

    bpms = np.array(
        [p.bpm if (p.bpm is not None and p.bpm > 0) else np.nan for p in pool],
        dtype=float,
    )
    finite = bpms[np.isfinite(bpms)]
    bmin = float(finite.min()) if finite.size else 0.0
    bmax = float(finite.max()) if finite.size else 0.0
    bspan = bmax - bmin

    for i, p in enumerate(pool):
        if p.energy is not None:
            energies[i] = float(np.clip(p.energy, 0.0, 100.0))
            has[i] = True
        elif np.isfinite(bpms[i]):
            # min-max BPM proxy; if the whole pool is one BPM, span==0 -> 50.
            energies[i] = 50.0 if bspan <= 0 else (bpms[i] - bmin) / bspan * 100.0
            has[i] = True
        # else: energy term contributes 0 for this track (has stays False)
    return energies, has


# ---------------------------------------------------------------------------
# Beam search
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class _Beam:
    """A partial path through the trellis."""

    used: frozenset[int]  # set of pool indices already placed
    order: tuple[int, ...]  # placement order (slot 0 .. slot k)
    cost: float
    relaxed: tuple[tuple[int, int, str], ...]  # (a_idx, b_idx, reason)


def _predecupe(pool: list[PoolTrack], coh: np.ndarray) -> list[int]:
    """Drop near-duplicates (same title + cos>0.995): keep the first, so the
    set can't mix a track into itself. Returns the surviving pool indices."""
    keep: list[int] = []
    for i in range(len(pool)):
        dup = False
        for j in keep:
            if (
                coh[i, j] > _NEAR_DUP_COS
                and pool[i].title.strip().lower() == pool[j].title.strip().lower()
            ):
                dup = True
                break
        if not dup:
            keep.append(i)
    return keep


def sequence_set(
    pool: list[PoolTrack],
    *,
    curve: str | list[float] | np.ndarray,
    n_slots: int,
    energy: dict[str, float] | None = None,
    weights: dict[str, float] | None = None,
    beam_width: int = 48,
    n_candidates: int = 4,
    bpm_tol: float = 0.06,
    surprise: dict[str, float] | None = None,
    recency: dict[str, float] | None = None,
    library_bias: dict[str, float] | None = None,
) -> list[SetCandidate]:
    """Order ``pool`` into an ``n_slots`` set tracking ``curve`` via beam search.

    Returns 3-5 (``<= n_candidates``) ranked, Jaccard-diverse ``SetCandidate``s,
    cheapest first. Honest-degrade throughout: short set when the pool/graph
    can't fill the slots, relaxed-and-TAGGED edges when the strict graph is too
    sparse — never an invalid untagged transition, never a fabricated track.

    ``energy`` optionally overrides per-track energy by track_id (else
    ``PoolTrack.energy`` -> BPM-proxy -> 0). ``surprise`` / ``recency`` /
    ``library_bias`` are optional per-track-id dicts feeding the (default-off)
    taste terms.
    """
    if not pool:
        return []

    w = {**_DEFAULT_WEIGHTS, **(weights or {})}
    m = len(pool)

    # Pool < slots => shorten the set + resample the curve (§B). Never pad.
    n_slots = min(n_slots, m)
    curve_vals = np.asarray(resample_curve(curve, n_slots), dtype=float)

    # --- Precompute the M x M coherence (cosine) Gram once. Vectors are
    # unit-norm so V @ V.T == pairwise cosine == sonic_coherence (§B). ---
    V = np.stack([l2_normalize(np.asarray(p.vec, dtype=np.float32)) for p in pool])
    coh = (V @ V.T).astype(float)
    np.clip(coh, -1.0, 1.0, out=coh)

    # --- Precompute the M x M graded-harmonic matrix once (S1). The binary
    # Camelot gate (`_transition_valid`) still decides ADMISSION; this graded
    # term only re-ranks among already-valid mixes (Invariant #3 untouched).
    # ``harmonic_score`` is memoized by Camelot pair so its parse runs once per
    # distinct (src, dst) key pair (<=24^2), not once per (i, j) edge — sub-ms
    # even at the 200-track pool cap. Unknown key on either side -> 1.0 (zero
    # graded cost), mirroring the gate's degrade-to-pass: a track with no key
    # metadata is never ranked a worse blend than a known-suboptimal key. ---
    harm = np.ones((m, m), dtype=float)
    _harm_cache: dict[tuple[str, str], float] = {}
    for i in range(m):
        ca = pool[i].camelot
        if ca is None:
            continue
        for j in range(m):
            if i == j:
                continue
            cb = pool[j].camelot
            if cb is None:
                continue
            score = _harm_cache.get((ca, cb))
            if score is None:
                score = harmonic_score(ca, cb)[0]
                _harm_cache[(ca, cb)] = score
            harm[i, j] = score

    # Pre-dedupe near-identical tracks, then operate on the survivors.
    survivors = _predecupe(pool, coh)
    if len(survivors) < n_slots:
        n_slots = len(survivors)
        curve_vals = np.asarray(resample_curve(curve, n_slots), dtype=float)
    if n_slots == 0:
        return []

    # --- Energies (explicit override -> PoolTrack.energy -> BPM-proxy -> 0). ---
    base_energy, has_energy = _resolve_energies(pool)
    if energy:
        for i, p in enumerate(pool):
            if p.track_id in energy:
                base_energy[i] = float(np.clip(energy[p.track_id], 0.0, 100.0))
                has_energy[i] = True

    # --- Optional taste vectors, normalized to [0,1] across the pool. ---
    def _norm_vec(d: dict[str, float] | None) -> np.ndarray:
        v = np.zeros(m, dtype=float)
        if not d:
            return v
        for i, p in enumerate(pool):
            v[i] = float(d.get(p.track_id, 0.0))
        lo, hi = float(v.min()), float(v.max())
        if hi - lo > 1e-12:
            v = (v - lo) / (hi - lo)
        else:
            v[:] = 0.0
        return v

    surprise_v = _norm_vec(surprise)
    recency_v = _norm_vec(recency)
    libbias_v = _norm_vec(library_bias)

    # --- Node cost per (track, slot). The curve term is squared error
    # normalized by the max possible squared error (100^2 = 1e4) so it lands in
    # [0,1] alongside the [0,1] edge term — the dial-sanity fix from §B. A
    # track with no energy signal (has_energy False) contributes 0 here. ---
    diff = base_energy[:, None] - curve_vals[None, :]  # (M, n_slots)
    sq_err = (diff * diff) / (100.0 * 100.0)  # -> [0,1]
    sq_err[~has_energy, :] = 0.0
    taste = (
        -w["gamma"] * surprise_v
        + w["delta"] * recency_v
        + w["epsilon"] * libbias_v
    )  # (M,)
    node_cost = w["alpha"] * sq_err + taste[:, None]  # (M, n_slots)

    def edge_cost(a: int, b: int) -> float:
        # 1 - cosine (CLAP vibe) + the graded harmonic tiebreak (S1). The binary
        # Camelot/BPM gates already admitted this edge; harm[a, b] only re-ranks
        # among valid mixes (unknown key -> harm 1.0 -> zero added cost).
        return w["beta"] * (1.0 - coh[a, b]) + w["zeta"] * (1.0 - harm[a, b])

    # --- Beam search over the depth-n_slots trellis. ---
    width = min(beam_width, max(8, m))
    seed_order = sorted(survivors, key=lambda i: node_cost[i, 0])[:width]
    beams: list[_Beam] = [
        _Beam(used=frozenset({i}), order=(i,), cost=float(node_cost[i, 0]), relaxed=())
        for i in seed_order
    ]

    survivor_set = set(survivors)

    for slot in range(1, n_slots):
        next_beams: list[_Beam] = []
        for beam in beams:
            last = beam.order[-1]
            expanded = False
            for j in survivor_set:
                if j in beam.used:
                    continue
                relaxed_flag, reason = _edge_admit(
                    pool[last], pool[j], bpm_tol, _BPM_LADDER[0]
                )
                if relaxed_flag is None:  # strictly invalid at the tightest rung
                    continue
                step = (
                    beam.cost
                    + float(node_cost[j, slot])
                    + edge_cost(last, j)
                )
                new_relaxed = beam.relaxed
                if reason is not None:
                    step += _RELAX_PENALTY
                    new_relaxed = (*beam.relaxed, (last, j, reason))
                next_beams.append(
                    _Beam(
                        used=beam.used | {j},
                        order=(*beam.order, j),
                        cost=step,
                        relaxed=new_relaxed,
                    )
                )
                expanded = True
            # Frontier rescue: if NO strict neighbor exists, walk the relaxation
            # ladder for this beam so the set stays connected (each relaxed edge
            # is TAGGED). Honest-degrade, never fabricate.
            if not expanded:
                for j, reason in _relaxed_neighbors(pool, last, beam.used, survivor_set, bpm_tol):
                    step = (
                        beam.cost
                        + float(node_cost[j, slot])
                        + edge_cost(last, j)
                        + _RELAX_PENALTY
                    )
                    next_beams.append(
                        _Beam(
                            used=beam.used | {j},
                            order=(*beam.order, j),
                            cost=step,
                            relaxed=(*beam.relaxed, (last, j, reason)),
                        )
                    )

        if not next_beams:
            # Whole frontier dead -> stop and return the best honest partial.
            break

        # --- Dominance dedup: two partials with the same (tail, used-set) are
        # interchangeable for the future, so keep only the cheaper. Exact
        # pruning AND diversity (§B). ---
        best_by_sig: dict[tuple[int, frozenset[int]], _Beam] = {}
        for b in next_beams:
            sig = (b.order[-1], b.used)
            cur = best_by_sig.get(sig)
            if cur is None or b.cost < cur.cost:
                best_by_sig[sig] = b
        beams = sorted(best_by_sig.values(), key=lambda b: b.cost)[:width]

    # Rank finished/partial beams cheapest-first.
    beams.sort(key=lambda b: b.cost)

    # --- Jaccard-diverse final selection: greedily accept the cheapest beam
    # whose track set is < _JACCARD_MAX overlapping with all already accepted. ---
    selected: list[_Beam] = []
    for b in beams:
        b_ids = frozenset(b.order)
        if all(_jaccard(b_ids, frozenset(s.order)) <= _JACCARD_MAX for s in selected):
            selected.append(b)
        if len(selected) >= n_candidates:
            break
    if not selected and beams:  # diversity filter too strict -> at least one
        selected = [beams[0]]

    return [_to_candidate(b, pool, curve_vals, coh, base_energy, has_energy) for b in selected]


# Penalty added to any relaxed (ladder-admitted) edge so the optimizer prefers
# strictly-valid mixes; large enough to lose to a clean alternative, small
# enough not to swamp the curve objective.
_RELAX_PENALTY = 0.5


def _edge_admit(
    a: PoolTrack, b: PoolTrack, bpm_tol: float, rung: float
) -> tuple[bool | None, str | None]:
    """At the tightest rung: ``(relaxed?, reason)``.

    Returns ``(False, None)`` for a strictly-valid edge, ``(None, None)`` if it
    is invalid (caller skips it; the ladder may rescue it later). At rung 0 we
    do not relax, so a strict failure is just skipped.
    """
    _, ok = _transition_valid(a, b, bpm_tol=rung)
    if ok:
        reason = _structural_relax_reason(a, b)
        if reason is not None:
            return True, reason
        return False, None
    return None, None


def _relaxed_neighbors(
    pool: list[PoolTrack],
    last: int,
    used: frozenset[int],
    survivor_set: set[int],
    bpm_tol: float,
):
    """Yield ``(idx, reason)`` for neighbors admitted by widening the ladder.

    Walks the BPM ladder (6 -> 8 -> 12%) then permits unknown-key bridges, each
    TAGGED with a human-readable reason. Yields at most the first rung that
    produces any neighbor, so we relax as little as possible.
    """
    a = pool[last]
    # BPM-widening rungs (skip rung 0 = strict, already tried).
    for rung in _BPM_LADDER[1:]:
        hits: list[tuple[int, str]] = []
        for j in survivor_set:
            if j in used:
                continue
            _, ok = _transition_valid(a, pool[j], bpm_tol=rung)
            if ok:
                hits.append((j, f"BPM jump (>{int(bpm_tol * 100)}%, relaxed to {int(rung * 100)}%)"))
        if hits:
            yield from hits
            return
    # Final rung: allow key bridges (penalized) on top of the widest BPM.
    hits = []
    for j in survivor_set:
        if j in used:
            continue
        _, ok = _transition_valid(
            a, pool[j], bpm_tol=_BPM_LADDER[-1], allow_unknown_key_bridge=True
        )
        if ok:
            hits.append((j, "key bridge (no compatible Camelot move)"))
    yield from hits


def _jaccard(a: frozenset[int], b: frozenset[int]) -> float:
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def _cue_start_s(cue: Any) -> float | None:
    raw = getattr(cue, "start_s", getattr(cue, "position_s", None))
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value if value >= 0.0 else None


def _cue_label(cue: Any) -> str:
    return str(
        getattr(cue, "label", None) or getattr(cue, "name", None) or ""
    ).strip().lower()


def _cue_type(cue: Any) -> str:
    return str(getattr(cue, "type", "cue") or "cue").strip().lower()


def _usable_cues(track: PoolTrack) -> list[Any]:
    return [
        cue
        for cue in (track.cues or ())
        if _cue_start_s(cue) is not None and _cue_type(cue) in {"cue", "loop", ""}
    ]


def _has_mix_in_anchor(track: PoolTrack, cues: list[Any]) -> bool:
    if not cues:
        return False
    boundary = max(_MIX_CUE_FLOOR_S, float(track.duration_s or 0.0) * _MIX_IN_FRAC)
    labels = ("intro", "in", "start")
    return any(
        (_cue_start_s(cue) or 0.0) <= boundary
        or any(token in _cue_label(cue) for token in labels)
        for cue in cues
    )


def _has_mix_out_anchor(track: PoolTrack, cues: list[Any]) -> bool:
    if not cues:
        return False
    duration = float(track.duration_s or 0.0)
    boundary = duration * _MIX_OUT_FRAC if duration > 0.0 else _MIX_CUE_FLOOR_S
    labels = ("outro", "out", "breakdown", "break")
    return any(
        (_cue_start_s(cue) or 0.0) >= boundary
        or any(token in _cue_label(cue) for token in labels)
        for cue in cues
    )


def _structural_relax_reason(a: PoolTrack, b: PoolTrack) -> str | None:
    """Tag weak cue structure when cue metadata exists for either side.

    No cues means unknown, not bad. If a track does carry cues, the sequencer
    expects a plausible outgoing anchor on ``a`` and incoming anchor on ``b``.
    Weakness stays a penalty/tag, never a hard rejection, so set prep remains
    robust on sparse libraries.
    """
    a_cues = _usable_cues(a)
    b_cues = _usable_cues(b)
    if not a_cues and not b_cues:
        return None

    missing: list[str] = []
    if a_cues and not _has_mix_out_anchor(a, a_cues):
        missing.append("no mix-out cue")
    if b_cues and not _has_mix_in_anchor(b, b_cues):
        missing.append("no mix-in cue")
    if not missing:
        return None
    return f"cue structure weak ({', '.join(missing)})"


def _to_candidate(
    beam: _Beam,
    pool: list[PoolTrack],
    curve_vals: np.ndarray,
    coh: np.ndarray,
    energies: np.ndarray,
    has_energy: np.ndarray,
) -> SetCandidate:
    order = beam.order
    track_ids = [pool[i].track_id for i in order]

    # energy_fit: mean |energy - curve[slot]| over slots with a real signal.
    fits = [
        abs(energies[idx] - curve_vals[slot])
        for slot, idx in enumerate(order)
        if has_energy[idx]
    ]
    energy_fit = float(np.mean(fits)) if fits else 0.0

    # avg_coherence: mean consecutive cosine (higher == smoother).
    if len(order) >= 2:
        cohs = [coh[order[k], order[k + 1]] for k in range(len(order) - 1)]
        avg_coherence = float(np.mean(cohs))
    else:
        avg_coherence = 1.0

    relaxed = [
        (pool[a].track_id, pool[b].track_id, reason) for (a, b, reason) in beam.relaxed
    ]
    return SetCandidate(
        track_ids=track_ids,
        cost=round(float(beam.cost), 6),
        energy_fit=round(energy_fit, 4),
        avg_coherence=round(avg_coherence, 4),
        relaxed_transitions=relaxed,
    )


__all__ = [
    "CURVE_PRESETS",
    "PoolTrack",
    "SetCandidate",
    "resample_curve",
    "sequence_set",
]
