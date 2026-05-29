# SPDX-License-Identifier: Apache-2.0
"""Library-grounded harmonic practice for the Camelot lesson."""
from __future__ import annotations

from types import SimpleNamespace

from vibemix.learn.harmonic_practice import (
    HarmonicPracticePair,
    HarmonicPracticeTrack,
    build_harmonic_practice_prompt,
    harmonic_practice_citations,
    pick_harmonic_practice_pair,
)
from vibemix.library.track_relation import compute_relation
from vibemix.state.evidence_registry import EvidenceRegistry


def _track(
    track_id: str,
    *,
    key: str,
    bpm: float = 128.0,
    title: str | None = None,
    artist: str = "Artist",
    rating: int = 0,
    play_count: int = 0,
):
    return SimpleNamespace(
        track_id=track_id,
        title=title or track_id,
        artist=artist,
        bpm=bpm,
        key=key,
        camelot=None,
        rating=rating,
        play_count=play_count,
    )


def test_picks_familiar_compatible_pair_from_user_library() -> None:
    library = SimpleNamespace(
        tracks={
            "anchor": _track(
                "anchor",
                key="Am",
                bpm=128.0,
                title="Anchor",
                rating=5,
                play_count=30,
            ),
            "match": _track(
                "match",
                key="Em",
                bpm=130.0,
                title="Neighbor",
                rating=4,
                play_count=15,
            ),
            "clash": _track(
                "clash",
                key="Ebm",
                bpm=129.0,
                title="Wrong Kind",
                rating=5,
                play_count=40,
            ),
        }
    )

    pair = pick_harmonic_practice_pair(library)

    assert pair is not None
    assert pair.source.track_id == "anchor"
    assert pair.target.track_id == "match"
    assert pair.relation.harmonic_compatible is True
    assert pair.why == f"8A{chr(8594)}9A, +2 BPM"


def test_seed_track_id_keeps_user_chosen_source_track() -> None:
    library = SimpleNamespace(
        tracks={
            "seed": _track("seed", key="Cm", bpm=124.0),
            "neighbor": _track("neighbor", key="Gm", bpm=125.0),
            "popular": _track("popular", key="Am", rating=5, play_count=99),
        }
    )

    pair = pick_harmonic_practice_pair(library, seed_track_id="seed")

    assert pair is not None
    assert pair.source.track_id == "seed"
    assert pair.target.track_id == "neighbor"


def test_returns_none_when_library_has_no_known_compatible_keys() -> None:
    library = SimpleNamespace(
        tracks={
            "unknown": _track("unknown", key="", bpm=124.0),
            "clash": _track("clash", key="Ebm", bpm=126.0),
        }
    )

    assert pick_harmonic_practice_pair(library, seed_track_id="unknown") is None


def test_prompt_is_specific_and_bounded() -> None:
    pair = _pair("t1", "t2")

    text = build_harmonic_practice_prompt(pair)

    assert len(text) <= 260
    assert text.startswith("your library pair:")
    assert "Artist - Source" in text
    assert "Artist - Target" in text
    assert "load the first, then tap continue." in text


def test_citations_require_registry_resolution_and_safe_track_ids() -> None:
    pair = _pair("t1", "bad id")
    registry = EvidenceRegistry()
    registry.register_library(SimpleNamespace(tracks={"t1": None, "bad id": None}))

    assert harmonic_practice_citations(pair, registry) == ("[track:t1]",)
    assert harmonic_practice_citations(pair, None) == ()


def _pair(source_id: str, target_id: str) -> HarmonicPracticePair:
    source = HarmonicPracticeTrack(
        track_id=source_id,
        title="Source",
        artist="Artist",
        bpm=128.0,
        camelot="8A",
    )
    target = HarmonicPracticeTrack(
        track_id=target_id,
        title="Target",
        artist="Artist",
        bpm=130.0,
        camelot="9A",
    )
    relation = compute_relation(
        src_track_id=source.track_id,
        dst_track_id=target.track_id,
        cosine=0.0,
        src_camelot=source.camelot,
        dst_camelot=target.camelot,
        src_bpm=source.bpm,
        dst_bpm=target.bpm,
    )
    return HarmonicPracticePair(
        source=source,
        target=target,
        relation=relation,
        score=1.0,
    )
