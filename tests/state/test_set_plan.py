# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from vibemix.library.prepared_pool import PreparedPool, PreparedPoolTrack
from vibemix.state.deck_state import DeckState, DeckTrack
from vibemix.state.set_plan import derive_set_progress


def _pool() -> PreparedPool:
    return PreparedPool(
        name="Psy Plan",
        created_at=1.0,
        json_path=Path("psy-plan.json"),
        tracks=(
            PreparedPoolTrack("a", title="Opening Spiral", artist="One"),
            PreparedPoolTrack("b", title="Next Portal", artist="Two"),
            PreparedPoolTrack("c", title="Late Lift", artist="Three"),
        ),
    )


def test_derive_set_progress_matches_current_deck_track_id() -> None:
    progress = derive_set_progress(
        _pool(),
        audible_deck="A",
        deck_state=DeckState(
            decks={
                "A": DeckTrack(
                    title="Opening Spiral",
                    track_id="a",
                    confidence=0.95,
                    source="rekordbox_xml",
                )
            }
        ),
        min_deck_confidence=0.5,
    )

    assert progress == {
        "source": "prepared_pool",
        "pool_name": "Psy Plan",
        "pool_path": "psy-plan.json",
        "audible_deck": "A",
        "confidence": 0.95,
        "current_track_id": "a",
        "current_title": "Opening Spiral",
        "current_artist": "One",
        "current_index": 0,
        "total": 3,
        "next_track_id": "b",
        "next_title": "Next Portal",
        "next_artist": "Two",
    }


def test_derive_set_progress_abstains_when_off_plan_or_uncertain() -> None:
    pool = _pool()

    assert (
        derive_set_progress(
            pool,
            audible_deck="A",
            deck_state=DeckState(decks={"A": DeckTrack(track_id="missing", confidence=0.95)}),
            min_deck_confidence=0.5,
        )
        is None
    )
    assert (
        derive_set_progress(
            pool,
            audible_deck="mix",
            deck_state=DeckState(decks={"A": DeckTrack(track_id="a", confidence=0.95)}),
            min_deck_confidence=0.5,
        )
        is None
    )
    assert (
        derive_set_progress(
            pool,
            audible_deck="A",
            deck_state=DeckState(decks={"A": DeckTrack(track_id="a", confidence=0.2)}),
            min_deck_confidence=0.5,
        )
        is None
    )
    assert (
        derive_set_progress(
            pool,
            audible_deck="A",
            deck_state=DeckState(decks={"A": DeckTrack(track_id="c", confidence=0.95)}),
            min_deck_confidence=0.5,
        )
        is None
    )
