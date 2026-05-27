# SPDX-License-Identifier: Apache-2.0
"""next_suggestion — the pill "what's next" engine.

Given the vector of the track playing now, rank the user's OWN library by
mean-centered cosine similarity and return ONE grounded next-track suggestion
("play a similar track, don't jump the vibe A→C"). The pill surfaces it.

This is the grounded shortlist path for the Pill Advancer:

* **Seed is a stored VECTOR, not a track_id.** The now-playing track is already
  identified and its 512-dim CLAP vector already lives in ``library-clap.db``
  (folder-ingest / Rekordbox import embedded it). We read it back — zero API cost, zero
  latency in steady state — instead of re-embedding like ``similar_to`` does.
* **Grounding (Cardinal Invariant #2).** Only track_ids present in BOTH the
  store and the live library can be suggested; every candidate is resolved via
  ``library.lookup_by_id`` and skipped if absent (store/library skew). The pill
  can never show an invented track — honest silence (``None``) when nothing
  qualifies.
* **Mean-centered ranking is the DEFAULT** (``store.search_centered``, the
  anisotropy fix) — the same path ``similar_to`` uses, so each seed gets a
  distinct neighbour set rather than "everything ~0.92 similar".
* **Set-aware selection stays bounded by the embedding shortlist.** The search
  still defines "near the current vibe"; grounded section/cue evidence can then
  promote the best mix point inside that shortlist.
* **Harmonic / BPM refine is Phase 2** — a POST-filter on the embedding
  shortlist (embedding similarity stays the primary ranker). Candidates lacking
  key/BPM degrade gracefully (kept, never dropped for missing metadata). When
  no key/BPM is available at all (folder-only library) it is embedding-only and
  ``why = "similar vibe"``.
* Rekordbox cue hints are surfaced only when already present on the resolved
  library entry. We never run cue detection inside the realtime pill path.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from vibemix.library._cosine import l2_normalize
from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry
from vibemix.library.section_vectors import resolve_section_vector
from vibemix.library.store import LibraryStore
from vibemix.state import harmonics

SECTION_POSITION_CONFIDENCE_FLOOR = 0.50
TRANSITION_ALTERNATIVE_LIMIT = 3


@dataclass(frozen=True, slots=True)
class NextSuggestion:
    """One grounded next-track suggestion for the pill."""

    track_id: str
    title: str
    artist: str
    similarity: float  # mean-centered cosine, 4dp
    why: str  # short grounded reason, e.g. "similar vibe" / "similar vibe · 8A · 128"
    camelot: str | None  # None unless Rekordbox-resolved (honest-null)
    bpm: float | None  # None unless Rekordbox-resolved
    transition: dict | None = None  # optional set-aware cue/timing payload
    transition_alternatives: tuple[dict, ...] = ()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class _SuggestionOption:
    track_id: str
    entry: TrackEntry
    similarity: float
    camelot: str | None
    bpm: float | None
    why: str


def seed_vector_for_track_id(store: LibraryStore, track_id: str) -> np.ndarray | None:
    """Read back the stored CLAP vector for ``track_id`` (the cached seed).

    Returns ``None`` if the id is not in the store. No embedding, no network —
    this is the steady-state ~free path (the now-playing track is already
    embedded).
    """
    ids, vectors = store._backend.load_all()
    try:
        idx = ids.index(track_id)
    except ValueError:
        return None
    if idx >= len(vectors):
        return None
    return np.asarray(vectors[idx], dtype=np.float32).copy()


def next_suggestion(
    store: LibraryStore,
    library: RekordboxLibrary,
    *,
    seed_vector: np.ndarray,
    seed_track_id: str | None,
    played_ids: set[str],
    seed_camelot: str | None = None,
    seed_bpm: float | None = None,
    source_deck: str | None = None,
    target_deck: str | None = None,
    k: int = 5,
    bpm_window: float = 15.0,
    live_remaining_bars: int | None = None,
    live_playhead_confidence: float = 0.0,
    blend_active: bool = False,
    source_position_s: float | None = None,
) -> NextSuggestion | None:
    """Rank the library by similarity to ``seed_vector`` → one next suggestion.

    Returns ``None`` (honest silence) when nothing qualifies — never a
    fabricated track.

    Phase 2 (``seed_camelot``/``seed_bpm`` provided) post-filters the embedding
    shortlist by Camelot compatibility + a BPM window; candidates missing
    key/BPM PASS the filter (degrade gracefully).
    """
    # Match similar_to's query path: normalize the seed before the centered
    # search (search_centered centers + renorms; the input must be L2-normed
    # so the centroid subtraction is meaningful).
    qvec = l2_normalize(np.asarray(seed_vector, dtype=np.float32))

    # Over-fetch so the seed + played + library-skew + harmonic drops still
    # leave at least one survivor.
    over = k + len(played_ids) + 8
    candidates = store.search_centered(qvec, k=over)

    refine = seed_camelot is not None or seed_bpm is not None
    options: list[_SuggestionOption] = []
    for tid, sim in candidates:
        if tid == seed_track_id or tid in played_ids:
            continue
        entry = library.lookup_by_id(tid)
        if entry is None:  # store/library skew — skip ungrounded ids
            continue

        cand_camelot = harmonics.to_camelot(entry.key) if entry.key else None
        cand_bpm = entry.bpm if (entry.bpm and entry.bpm > 0) else None

        if refine:
            # Camelot: drop only when BOTH keys are known and incompatible.
            if (
                seed_camelot is not None
                and cand_camelot is not None
                and not harmonics.compatible(seed_camelot, cand_camelot)
            ):
                continue
            # BPM: drop only when BOTH are known and outside the window.
            if (
                seed_bpm is not None
                and cand_bpm is not None
                and abs(cand_bpm - seed_bpm) > bpm_window
            ):
                continue

        # Build the "why" honestly from what we actually resolved.
        bits = ["similar vibe"]
        if cand_camelot is not None:
            bits.append(cand_camelot)
        if cand_bpm is not None:
            bits.append(f"{cand_bpm:g}")
        cue_hint = _cue_hint(entry)
        if cue_hint is not None:
            bits.append(cue_hint)
        why = " · ".join(bits)

        options.append(
            _SuggestionOption(
                track_id=tid,
                entry=entry,
                similarity=float(sim),
                camelot=cand_camelot,
                bpm=cand_bpm,
                why=why,
            )
        )

    if not options:
        return None

    chosen, transition, alternatives = _select_set_aware_option(
        store,
        library,
        options,
        seed_track_id=seed_track_id,
        seed_vector=qvec,
        source_deck=source_deck,
        target_deck=target_deck,
        live_remaining_bars=live_remaining_bars,
        live_playhead_confidence=live_playhead_confidence,
        blend_active=blend_active,
        source_position_s=source_position_s,
    )

    return NextSuggestion(
        track_id=chosen.track_id,
        title=chosen.entry.title,
        artist=chosen.entry.artist,
        similarity=round(float(chosen.similarity), 4),
        why=chosen.why,
        camelot=chosen.camelot,
        bpm=chosen.bpm,
        transition=transition,
        transition_alternatives=alternatives,
    )


def _select_set_aware_option(
    store: LibraryStore,
    library: RekordboxLibrary,
    options: list[_SuggestionOption],
    *,
    seed_track_id: str | None,
    seed_vector: np.ndarray,
    source_deck: str | None,
    target_deck: str | None,
    live_remaining_bars: int | None,
    live_playhead_confidence: float,
    blend_active: bool,
    source_position_s: float | None,
) -> tuple[_SuggestionOption, dict | None, tuple[dict, ...]]:
    """Pick the best grounded option, preferring proven mix-point evidence.

    The embedding shortlist still defines the candidate universe. Within that
    universe, a section-level transition slate can promote a lower-ranked track
    only when the scorer returns a live-safe cue recommendation. If no option
    has grounded transition evidence, the original top embedding survivor wins.
    """
    if seed_track_id is None:
        return options[0], None, ()

    destination_vectors = _vectors_for_track_ids(store, [option.track_id for option in options])
    ranked: list[tuple[tuple[float, float, float, float], _SuggestionOption, dict | None]] = []
    for order, option in enumerate(options):
        transition = transition_payload_for_candidate(
            store,
            library,
            seed_track_id=seed_track_id,
            seed_vector=seed_vector,
            candidate_track_id=option.track_id,
            source_deck=source_deck,
            target_deck=target_deck,
            remaining_bars=live_remaining_bars,
            playhead_confidence=live_playhead_confidence,
            blend_active=blend_active,
            source_position_s=source_position_s,
            destination_vector=destination_vectors.get(option.track_id),
        )
        ranked.append((_selection_key(option, transition, order), option, transition))

    ranked.sort(key=lambda item: item[0], reverse=True)
    _, option, transition = ranked[0]
    alternatives = _ranked_alternatives(ranked)
    selected = (
        alternatives[0]["transition"]
        if alternatives
        else annotate_transition_selection(transition, option.similarity)
    )
    return option, selected, alternatives


def vectors_for_track_ids(store: LibraryStore, track_ids: list[str]) -> dict[str, np.ndarray]:
    """Load cached whole-track vectors for a bounded set of ids."""
    return _vectors_for_track_ids(store, track_ids)


def _vectors_for_track_ids(store: LibraryStore, track_ids: list[str]) -> dict[str, np.ndarray]:
    needed = set(track_ids)
    if not needed:
        return {}
    try:
        ids, vectors = store._backend.load_all()
    except Exception:
        return {}
    out: dict[str, np.ndarray] = {}
    for idx, track_id in enumerate(ids):
        if track_id in needed and idx < len(vectors):
            out[track_id] = np.asarray(vectors[idx], dtype=np.float32).copy()
    return out


def _selection_key(
    option: _SuggestionOption,
    transition: dict | None,
    order: int,
) -> tuple[float, float, float, float]:
    if transition is None:
        return (0.0, _similarity_component(option.similarity), -float(order), 0.0)
    return (
        1.0,
        _selection_score(option, transition),
        _similarity_component(option.similarity),
        -float(len(transition.get("risk_flags", ()) or ())),
    )


def _selection_score(option: _SuggestionOption, transition: dict) -> float:
    return _selection_score_for_similarity(option.similarity, transition)


def annotate_transition_selection(transition: dict | None, similarity: float | None) -> dict | None:
    """Attach stable selection metadata to a grounded transition payload."""
    if transition is None:
        return None
    annotated = dict(transition)
    annotated["selection_score"] = round(_selection_score_for_similarity(similarity, transition), 6)
    annotated["selection_basis"] = "section_transition"
    return annotated


def ranked_transition_alternatives(
    alternatives: tuple[dict, ...],
    refreshed_transitions: dict[str, dict | None],
) -> tuple[dict, ...]:
    """Re-rank existing alternative payloads after a live transition refresh.

    ``next_suggestion`` owns the set-aware selection math; the runtime holder
    calls this to reselect inside the already-issued embedding shortlist as the
    source playhead moves, without running a full library search on every frame.
    """
    ranked: list[tuple[tuple[float, float, float, float], dict, dict | None]] = []
    for order, raw in enumerate(alternatives):
        track_id = raw.get("track_id")
        if not isinstance(track_id, str) or not track_id:
            continue
        similarity = _float_or_none(raw.get("similarity"))
        transition = refreshed_transitions.get(track_id, raw.get("transition"))
        transition = annotate_transition_selection(transition, similarity)
        ranked.append(
            (
                _alternative_selection_key(similarity, transition, order),
                raw,
                transition,
            )
        )
    ranked.sort(key=lambda item: item[0], reverse=True)
    return _ranked_alternatives_from_payloads(ranked)


def _ranked_alternatives(
    ranked: list[tuple[tuple[float, float, float, float], _SuggestionOption, dict | None]],
) -> tuple[dict, ...]:
    payloads = [
        (
            sort_key,
            {
                "track_id": option.track_id,
                "title": option.entry.title,
                "artist": option.entry.artist,
                "similarity": round(float(option.similarity), 4),
                "why": option.why,
                "camelot": option.camelot,
                "bpm": option.bpm,
            },
            annotate_transition_selection(transition, option.similarity),
        )
        for sort_key, option, transition in ranked
    ]
    return _ranked_alternatives_from_payloads(payloads)


def _ranked_alternatives_from_payloads(
    ranked: list[tuple[tuple[float, float, float, float], dict, dict | None]],
) -> tuple[dict, ...]:
    out: list[dict] = []
    for rank, (_, raw, transition) in enumerate(ranked[:TRANSITION_ALTERNATIVE_LIMIT], start=1):
        option = dict(raw)
        candidate_id = f"tr_{rank:03d}"
        if transition is not None:
            transition = dict(transition)
            transition["candidate_id"] = candidate_id
        option["candidate_id"] = candidate_id
        option["rank"] = rank
        option["selected"] = rank == 1
        option["transition"] = transition
        out.append(option)
    return tuple(out)


def _alternative_selection_key(
    similarity: float | None,
    transition: dict | None,
    order: int,
) -> tuple[float, float, float, float]:
    if transition is None:
        return (0.0, _similarity_component(similarity or 0.0), -float(order), 0.0)
    return (
        1.0,
        _selection_score_for_similarity(similarity, transition),
        _similarity_component(similarity or 0.0),
        -float(len(transition.get("risk_flags", ()) or ())),
    )


def _selection_score_for_similarity(similarity: float | None, transition: dict) -> float:
    transition_score = _float01(transition.get("score"), 0.0)
    confidence = _float01(transition.get("confidence"), 0.0)
    similarity_score = _similarity_component(similarity or 0.0)
    return 0.42 * transition_score + 0.28 * confidence + 0.30 * similarity_score


def _similarity_component(similarity: float) -> float:
    return _float01((float(similarity) + 1.0) / 2.0, 0.0)


def _float_or_none(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _float01(value: object, default: float) -> float:
    try:
        raw = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, raw))


def transition_payload_for_candidate(
    store: LibraryStore,
    library: RekordboxLibrary,
    *,
    seed_track_id: str | None,
    seed_vector: np.ndarray,
    candidate_track_id: str,
    source_deck: str | None,
    target_deck: str | None,
    remaining_bars: int | None,
    playhead_confidence: float,
    blend_active: bool,
    source_position_s: float | None,
    destination_vector: np.ndarray | None = None,
) -> dict | None:
    """Return a set-aware cue recommendation for the chosen candidate.

    This is best-effort and never replaces the grounded track suggestion: when
    section/cue evidence is missing or weak, it returns ``None`` and the caller
    keeps the older track-level pill behavior.
    """
    if not seed_track_id:
        return None
    source_entry = library.lookup_by_id(seed_track_id)
    destination_entry = library.lookup_by_id(candidate_track_id)
    if source_entry is None or destination_entry is None:
        return None
    seed_vector = l2_normalize(np.asarray(seed_vector, dtype=np.float32))
    try:
        from vibemix.intel.transition_scorer import (
            LivePosition,
            TransitionScoringInput,
            score_transition_slate,
        )
        from vibemix.library.section_builder import (
            best_source_section,
            destination_sections,
            sections_for_entry,
            transition_source_for_position,
        )

        source_sections = sections_for_entry(source_entry)
        grounded_source_position_s = (
            source_position_s
            if source_position_s is not None
            and playhead_confidence >= SECTION_POSITION_CONFIDENCE_FLOOR
            else None
        )
        source_selection = "default_section"
        section_timing_basis = None
        if grounded_source_position_s is not None:
            source, section_remaining_bars, section_timing_basis = transition_source_for_position(
                source_sections,
                grounded_source_position_s,
            )
            source_selection = (
                "upcoming_section"
                if section_timing_basis == "section_lookahead"
                else "current_section"
            )
            if section_remaining_bars is not None:
                remaining_bars = section_remaining_bars
        else:
            source = best_source_section(source_sections)
        destinations = destination_sections(sections_for_entry(destination_entry))
        source_vector_result = resolve_section_vector(
            store,
            source.section_id,
            fallback_vector=seed_vector,
        )
        if destination_vector is None:
            destination_vector = seed_vector_for_track_id(store, candidate_track_id)
        destination_vector_results = {
            section.section_id: resolve_section_vector(
                store,
                section.section_id,
                fallback_vector=destination_vector,
            )
            for section in destinations
        }
        vectors = {
            section_id: result.vector
            for section_id, result in destination_vector_results.items()
            if result.vector is not None
        }
        semantic_basis_by_section = {
            source.section_id: source_vector_result.basis,
            **{
                section_id: result.basis
                for section_id, result in destination_vector_results.items()
            },
        }
        slate = score_transition_slate(
            TransitionScoringInput(
                source=source,
                destinations=tuple(destinations),
                source_vector=source_vector_result.vector,
                destination_vectors=vectors,
                semantic_basis_by_section=semantic_basis_by_section,
                candidate_pool_track_ids=frozenset({candidate_track_id}),
                live_position=LivePosition(
                    remaining_bars=remaining_bars,
                    playhead_confidence=playhead_confidence,
                    blend_active=blend_active,
                ),
                mode="live",
            ),
            max_candidates=1,
        )
    except Exception:
        return None
    if not slate:
        return None
    candidate = slate[0]
    timing_basis = _timing_basis(
        candidate.start_in_bars,
        section_timing_basis,
        grounded_source_position_s,
    )
    return {
        "candidate_id": candidate.candidate_id,
        "source_deck": _deck_label(source_deck),
        "target_deck": _deck_label(target_deck),
        "from_track_id": candidate.from_track_id,
        "to_track_id": candidate.to_track_id,
        "from_section_id": candidate.from_section_id,
        "to_section_id": candidate.to_section_id,
        "from_role": candidate.from_role,
        "to_role": candidate.to_role,
        "from_start_s": candidate.from_start_s,
        "from_end_s": candidate.from_end_s,
        "to_start_s": candidate.to_start_s,
        "to_end_s": candidate.to_end_s,
        "from_bpm": candidate.from_bpm,
        "to_bpm": candidate.to_bpm,
        "from_camelot": candidate.from_camelot,
        "to_camelot": candidate.to_camelot,
        "cue_slot": candidate.cue_slot,
        "start_in_bars": candidate.start_in_bars,
        "score": candidate.score,
        "confidence": candidate.confidence,
        "semantic_basis": candidate.semantic_basis,
        "scores": asdict(candidate.components),
        "timing_basis": timing_basis,
        "timing_anchor": _timing_anchor(timing_basis),
        "source_anchor_s": _source_anchor_s(candidate, timing_basis),
        "source_selection": source_selection,
        "risk_flags": list(candidate.risk_flags),
        "reasons": list(candidate.reasons),
    }


def _timing_basis(
    start_in_bars: int | None,
    section_timing_basis: str | None,
    source_position_s: float | None,
) -> str | None:
    if start_in_bars is None:
        return None
    if section_timing_basis is not None:
        return section_timing_basis
    return "section_playhead" if source_position_s is not None else "bar_lock"


def _timing_anchor(timing_basis: str | None) -> str | None:
    if timing_basis == "section_lookahead":
        return "source_section_start"
    if timing_basis == "section_playhead":
        return "source_section_end"
    if timing_basis == "bar_lock":
        return "live_bar_countdown"
    return None


def _source_anchor_s(candidate, timing_basis: str | None) -> float | None:
    if timing_basis == "section_lookahead":
        return candidate.from_start_s
    if timing_basis == "section_playhead":
        return candidate.from_end_s
    return None


def _deck_label(deck: str | None) -> str | None:
    if deck is None:
        return None
    deck = deck.strip().upper()
    return deck if deck in {"A", "B"} else None


def _cue_hint(entry) -> str | None:
    """Return a concise first structural cue hint from existing library metadata."""
    cues = [
        cue
        for cue in (getattr(entry, "cues", ()) or ())
        if getattr(cue, "type", "") in {"cue", "loop"} and getattr(cue, "start_s", -1) >= 0
    ]
    if not cues:
        return None
    cue = min(cues, key=lambda c: float(getattr(c, "start_s", 0.0) or 0.0))
    name = str(getattr(cue, "name", "") or "").strip()
    label = f"cue {name.lower()}" if name else _cue_label_from_number(getattr(cue, "number", -1))
    return f"{label} @ {_format_mmss(float(getattr(cue, 'start_s', 0.0) or 0.0))}"


def _cue_label_from_number(number: int) -> str:
    if 0 <= number <= 7:
        return f"hot {chr(ord('A') + number)}"
    if number == -1:
        return "memory cue"
    return "cue"


def _format_mmss(seconds: float) -> str:
    total = max(0, round(seconds))
    return f"{total // 60}:{total % 60:02d}"


__all__ = [
    "SECTION_POSITION_CONFIDENCE_FLOOR",
    "TRANSITION_ALTERNATIVE_LIMIT",
    "NextSuggestion",
    "annotate_transition_selection",
    "next_suggestion",
    "ranked_transition_alternatives",
    "seed_vector_for_track_id",
    "transition_payload_for_candidate",
    "vectors_for_track_ids",
]
