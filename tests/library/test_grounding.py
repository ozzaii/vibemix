# SPDX-License-Identifier: Apache-2.0
"""Plan 28-04 — grounding decision + threshold tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from vibemix.library._cosine import EMBEDDING_DIM
from vibemix.library.grounding import (
    CITATION_THRESHOLD,
    TRACK_AWARE_EVENTS,
    UNCERTAIN_THRESHOLD,
    Citation,
    Grounding,
    identify_playing,
)


@pytest.fixture
def fake_embedder() -> MagicMock:
    # Phase 90: grounding now routes through the public ``embed_audio_bytes``
    # seam (backend-agnostic), no longer ``_client.models.embed_content``.
    e = MagicMock()
    e.embed_audio_bytes.return_value = np.asarray(
        [0.1] * EMBEDDING_DIM, dtype=np.float32
    )
    return e


@pytest.fixture
def fake_store() -> MagicMock:
    s = MagicMock()
    s.search.return_value = [("t000", 0.9)]
    return s


class _FakeLibrary:
    def __init__(self, track_ids: set[str] | None = None) -> None:
        self._track_ids = track_ids or set()

    def lookup_by_id(self, track_id: str):
        return object() if track_id in self._track_ids else None


def test_thresholds_locked() -> None:
    assert CITATION_THRESHOLD == 0.7
    assert UNCERTAIN_THRESHOLD == 0.6
    assert "TRACK_CHANGE" in TRACK_AWARE_EVENTS
    assert "LAYER_ARRIVAL" in TRACK_AWARE_EVENTS
    assert "MIX_MOVE" in TRACK_AWARE_EVENTS


def test_cited_decision_above_threshold(fake_embedder, fake_store) -> None:
    fake_store.search.return_value = [("t000", 0.85)]
    c = identify_playing(
        fake_embedder, fake_store, b"audio", event_type="TRACK_CHANGE"
    )
    assert c is not None
    assert c.decision == "cited"
    assert c.track_id == "t000"
    assert c.is_cited is True


def test_cited_decision_requires_library_self_match(fake_embedder, fake_store) -> None:
    fake_store.search.return_value = [("stale-track", 0.95)]

    c = identify_playing(
        fake_embedder,
        fake_store,
        b"audio",
        event_type="TRACK_CHANGE",
        library=_FakeLibrary({"fresh-track"}),
    )

    assert c is not None
    assert c.decision == "unregistered_track"
    assert c.track_id is None
    assert c.is_cited is False


def test_library_self_match_allows_registered_track(fake_embedder, fake_store) -> None:
    fake_store.search.return_value = [("t000", 0.85)]

    c = identify_playing(
        fake_embedder,
        fake_store,
        b"audio",
        event_type="TRACK_CHANGE",
        library=_FakeLibrary({"t000"}),
    )

    assert c is not None
    assert c.decision == "cited"
    assert c.track_id == "t000"


def test_uncertain_decision(fake_embedder, fake_store) -> None:
    fake_store.search.return_value = [("t000", 0.65)]
    c = identify_playing(
        fake_embedder, fake_store, b"audio", event_type="MIX_MOVE"
    )
    assert c.decision == "uncertain"
    assert c.track_id is None
    assert c.is_cited is False


def test_below_threshold_decision(fake_embedder, fake_store) -> None:
    fake_store.search.return_value = [("t000", 0.4)]
    c = identify_playing(
        fake_embedder, fake_store, b"audio", event_type="TRACK_CHANGE"
    )
    assert c.decision == "below_threshold"
    assert c.track_id is None


def test_non_track_aware_event_skipped(fake_embedder, fake_store) -> None:
    """Cost-gate: HEARTBEAT, KAAN_SPOKE etc. don't trigger grounding."""
    c = identify_playing(
        fake_embedder, fake_store, b"audio", event_type="HEARTBEAT"
    )
    assert c is None
    fake_embedder.embed_audio_bytes.assert_not_called()


def test_no_audio_returns_below_threshold(fake_embedder, fake_store) -> None:
    c = identify_playing(
        fake_embedder, fake_store, None, event_type="TRACK_CHANGE"
    )
    assert c.decision == "below_threshold"
    fake_embedder.embed_audio_bytes.assert_not_called()


def test_embed_failure_graceful(fake_embedder, fake_store) -> None:
    fake_embedder.embed_audio_bytes.side_effect = RuntimeError(
        "proxy 502"
    )
    c = identify_playing(
        fake_embedder, fake_store, b"audio", event_type="TRACK_CHANGE"
    )
    assert c.decision == "below_threshold"
    assert c.cosine == 0.0


def test_empty_store_returns_below_threshold(fake_embedder) -> None:
    s = MagicMock()
    s.search.return_value = []
    c = identify_playing(
        fake_embedder, s, b"audio", event_type="TRACK_CHANGE"
    )
    assert c.decision == "below_threshold"


def test_grounding_class_holds_latest_citation(fake_embedder, fake_store) -> None:
    g = Grounding(fake_embedder, fake_store, library=_FakeLibrary({"t000"}))
    assert g.get_latest_citation() is None

    fake_store.search.return_value = [("t000", 0.85)]
    g.on_event("TRACK_CHANGE", b"audio")
    latest = g.get_latest_citation()
    assert latest is not None
    assert latest.track_id == "t000"


def test_grounding_class_doesnt_store_unregistered_track(fake_embedder, fake_store) -> None:
    g = Grounding(fake_embedder, fake_store, library=_FakeLibrary({"other"}))
    fake_store.search.return_value = [("t000", 0.85)]

    citation = g.on_event("TRACK_CHANGE", b"audio")

    assert citation is not None
    assert citation.decision == "unregistered_track"
    assert g.get_latest_citation() is None


def test_grounding_class_doesnt_store_below_threshold(
    fake_embedder, fake_store
) -> None:
    g = Grounding(fake_embedder, fake_store)
    fake_store.search.return_value = [("t000", 0.4)]
    g.on_event("TRACK_CHANGE", b"audio")
    assert g.get_latest_citation() is None


def test_grounding_clear(fake_embedder, fake_store) -> None:
    g = Grounding(fake_embedder, fake_store)
    fake_store.search.return_value = [("t000", 0.85)]
    g.on_event("TRACK_CHANGE", b"audio")
    assert g.get_latest_citation() is not None
    g.clear()
    assert g.get_latest_citation() is None


def test_clear_during_inflight_on_event_discards_stale_citation(
    fake_embedder, fake_store
) -> None:
    """Phase 77 review CR-01 — generation token discards a stale on_event write.

    Simulates the WIRE-01 race where the agent's ``asyncio.wait_for`` fires
    ``TimeoutError`` and calls ``grounding.clear()`` while the executor thread
    is still inside ``on_event`` (between embed/cosine and the final
    ``_latest = citation`` write). The per-dispatch generation token in
    ``Grounding.on_event`` must detect the intervening ``clear()`` and DROP
    the (now-stale) citation instead of resurrecting it — otherwise a
    timed-out lookup's late write resurrects a wrong ``[track:<id>]`` for the
    wrong track (invariant #3). Mirrors the recall race test
    ``test_clear_during_inflight_on_event_discards_stale_latch``.

    The race is staged by wrapping ``store.search`` with a callable that
    fires ``g.clear()`` after the generation token has been captured (bumped
    at the very start of ``on_event``) but BEFORE the final lock-protected
    write — the same window the executor thread sits in under live load.
    """
    g = Grounding(fake_embedder, fake_store)
    fake_store.search.return_value = [("t000", 0.85)]

    original_search = fake_store.search

    def racing_search(*args, **kwargs):
        result = original_search(*args, **kwargs)
        g.clear()  # bumps _inflight_gen between dispatch and write
        return result

    fake_store.search = racing_search  # type: ignore[method-assign]

    citation = g.on_event("TRACK_CHANGE", b"audio")
    # The caller still sees the cited result (embed + cosine happened) but
    # the latch was NOT mutated — the deadline contract holds.
    assert citation is not None
    assert citation.is_cited is True
    assert g.get_latest_citation() is None, (
        "stale executor write must be discarded after intervening clear()"
    )


def test_event_id_format() -> None:
    c = Citation(
        event_id="ev-test",
        decision="cited",
        track_id="t000",
        cosine=0.85,
        ts=1000.0,
    )
    assert c.event_id == "ev-test"
    assert c.is_cited is True
