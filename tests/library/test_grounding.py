# SPDX-License-Identifier: Apache-2.0
"""Plan 28-04 — grounding decision + threshold tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest

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
    e = MagicMock()
    e._client = MagicMock()
    e._client.models.embed_content.return_value = SimpleNamespace(
        embeddings=[SimpleNamespace(values=[0.1] * 768)]
    )
    return e


@pytest.fixture
def fake_store() -> MagicMock:
    s = MagicMock()
    s.search.return_value = [("t000", 0.9)]
    return s


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
    fake_embedder._client.models.embed_content.assert_not_called()


def test_no_audio_returns_below_threshold(fake_embedder, fake_store) -> None:
    c = identify_playing(
        fake_embedder, fake_store, None, event_type="TRACK_CHANGE"
    )
    assert c.decision == "below_threshold"
    fake_embedder._client.models.embed_content.assert_not_called()


def test_embed_failure_graceful(fake_embedder, fake_store) -> None:
    fake_embedder._client.models.embed_content.side_effect = RuntimeError(
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
    g = Grounding(fake_embedder, fake_store)
    assert g.get_latest_citation() is None

    fake_store.search.return_value = [("t000", 0.85)]
    g.on_event("TRACK_CHANGE", b"audio")
    latest = g.get_latest_citation()
    assert latest is not None
    assert latest.track_id == "t000"


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
