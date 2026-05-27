# SPDX-License-Identifier: Apache-2.0
"""next_suggestion — the pill "what's next" engine.

Given the vector of the track playing now, rank the user's OWN library by
mean-centered cosine similarity and return ONE grounded next-track suggestion
("play a similar track, don't jump the vibe A→C"). The pill surfaces it.

This is the embedding-only Phase 1 of the Pill Advancer:

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
from vibemix.library.rekordbox import RekordboxLibrary
from vibemix.library.store import LibraryStore
from vibemix.state import harmonics

SECTION_POSITION_CONFIDENCE_FLOOR = 0.50


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

    def to_dict(self) -> dict:
        return asdict(self)


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
        transition = transition_payload_for_candidate(
            store,
            library,
            seed_track_id=seed_track_id,
            seed_vector=qvec,
            candidate_track_id=tid,
            source_deck=source_deck,
            target_deck=target_deck,
            remaining_bars=live_remaining_bars,
            playhead_confidence=live_playhead_confidence,
            blend_active=blend_active,
            source_position_s=source_position_s,
        )
        why = " · ".join(bits)

        return NextSuggestion(
            track_id=tid,
            title=entry.title,
            artist=entry.artist,
            similarity=round(float(sim), 4),
            why=why,
            camelot=cand_camelot,
            bpm=cand_bpm,
            transition=transition,
        )
    return None


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
            bars_until_section_end,
            best_source_section,
            destination_sections,
            section_at_position,
            sections_for_entry,
        )

        source_sections = sections_for_entry(source_entry)
        grounded_source_position_s = (
            source_position_s
            if source_position_s is not None
            and playhead_confidence >= SECTION_POSITION_CONFIDENCE_FLOOR
            else None
        )
        source = (
            section_at_position(source_sections, grounded_source_position_s)
            if grounded_source_position_s is not None
            else best_source_section(source_sections)
        )
        section_remaining_bars = bars_until_section_end(source, grounded_source_position_s)
        if section_remaining_bars is not None:
            remaining_bars = section_remaining_bars
        destinations = destination_sections(sections_for_entry(destination_entry))
        if destination_vector is None:
            destination_vector = seed_vector_for_track_id(store, candidate_track_id)
        vectors = (
            {section.section_id: destination_vector for section in destinations}
            if destination_vector is not None
            else {}
        )
        slate = score_transition_slate(
            TransitionScoringInput(
                source=source,
                destinations=tuple(destinations),
                source_vector=seed_vector,
                destination_vectors=vectors,
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
    return {
        "candidate_id": candidate.candidate_id,
        "source_deck": _deck_label(source_deck),
        "target_deck": _deck_label(target_deck),
        "from_track_id": candidate.from_track_id,
        "to_track_id": candidate.to_track_id,
        "from_section_id": candidate.from_section_id,
        "to_section_id": candidate.to_section_id,
        "cue_slot": candidate.cue_slot,
        "start_in_bars": candidate.start_in_bars,
        "score": candidate.score,
        "confidence": candidate.confidence,
        "timing_basis": _timing_basis(candidate.start_in_bars, grounded_source_position_s),
        "risk_flags": list(candidate.risk_flags),
        "reasons": list(candidate.reasons),
    }


def _timing_basis(start_in_bars: int | None, source_position_s: float | None) -> str | None:
    if start_in_bars is None:
        return None
    return "section_playhead" if source_position_s is not None else "bar_lock"


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
    "NextSuggestion",
    "next_suggestion",
    "seed_vector_for_track_id",
    "transition_payload_for_candidate",
]
